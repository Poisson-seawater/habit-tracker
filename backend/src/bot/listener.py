import os
import re
import html
import asyncio
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID
from src.database.session import SessionLocal
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore, Streak, Todo, NoTodo, Reward
from src.bot.parser import parse_command, ParserError
from src.services.score_service import calculate_daily_score, update_streaks, DEFAULT_THRESHOLDS
from src.bot.scheduler import start_scheduler
from src.services.reward_service import check_reward_lock, purchase_reward, is_allostasis_available
from src.services.softskill_service import load_tree_config, create_skill, get_user_progress, toggle_completion
from fastapi import HTTPException

# Mapping stats to their French display labels
STAT_LABELS = {
    "force": "Force 💪",
    "endurance": "Endurance 🏃‍♂️",
    "mobilite": "Mobilité 🧘‍♂️",
    "discipline": "Discipline ⚔️",
    "creativite": "Créativité 🎨",
    "connaissance": "Connaissance 📚",
    "sociabilite": "Sociabilité 🤝",
    "sante_mentale": "Santé Mentale 🧠",
    "finance": "Finance 💰",
    "organisation": "Organisation 📂",
    "spiritualite": "Spiritualité 🌌",
    "repos": "Repos 💤"
}

def format_stat_rewards(point_rewards: dict) -> str:
    parts = []
    for stat, val in point_rewards.items():
        label = STAT_LABELS.get(stat.lower(), stat.capitalize())
        parts.append(f"+{val} {label}")
    return ", ".join(parts)

# Maps the words a user can type for /set-day to the internal template keys.
# The button flow passes the internal keys (week/weekend/recup/malade) directly.
TEMPLATE_WORD_MAP = {
    "semaine": "week",
    "week": "week",
    "weekend": "weekend",
    "recovery": "recup",
    "recup": "recup",
    "sick": "malade",
    "malade": "malade",
}



def _resolve_user(db, from_user) -> User:
    """Look up (or create) the User row for a Telegram sender. Shared by the
    command router and the inline-button callback handler."""
    telegram_username = from_user.username or from_user.first_name
    user_chat_id = str(from_user.id)

    user = db.query(User).filter_by(chat_id=user_chat_id).first()
    if not user:
        user = db.query(User).filter_by(username=telegram_username).first()

    if not user:
        user = User(username=telegram_username, chat_id=user_chat_id, xp=0, level=1, gold=0)
        db.add(user)
        db.commit()
    elif user.chat_id != user_chat_id:
        user.chat_id = user_chat_id
        db.commit()
    return user

def _render_liste(db, user_id: int, l_type: str) -> str:
    """HTML text for one of the three lists. Used by typed /liste and the buttons."""
    if l_type == "todo":
        todos = db.query(Todo).filter_by(user_id=user_id, is_completed=False).all()
        if not todos:
            return "Aucun Todo en attente."
        lines = [f"- {html.escape(t.title)} (+{t.xp_reward} XP)" for t in todos]
        return "<b>Liste des Todos :</b>\n" + "\n".join(lines)
    if l_type == "habit":
        habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()
        if not habits:
            return "Aucune habitude active."
        lines = [f"- {html.escape(h.name)} ({h.type})" for h in habits]
        return "<b>Liste des Habitudes :</b>\n" + "\n".join(lines)
    if l_type == "notodo":
        notodos = db.query(NoTodo).filter_by(user_id=user_id).all()
        if not notodos:
            return "Aucune règle No-Todo."
        lines = [f"- {html.escape(n.title)}" for n in notodos]
        return "<b>Liste des No-Todos :</b>\n" + "\n".join(lines)
    return "Type de liste inconnu."

def _apply_set_day(db, user_id: int, db_template_name: str) -> str:
    """Apply a day template (internal key), recalc score & streaks, return confirmation."""
    today = datetime.date.today()
    score = calculate_daily_score(db, user_id=user_id, date=today, template_name=db_template_name)
    update_streaks(db, user_id=user_id, date=today)
    return (
        f"🩹 Template de journée mis à jour vers : \"{score.template_used.upper()}\".\n"
        f"✨ Les seuils de points ont été réajustés pour aujourd'hui !"
    )

def _create_pending_item(db, user: User, pending: str, title: str) -> str:
    """Create the item chosen via /add buttons, from the title the user typed."""
    title = title.strip()
    if not title:
        return "❌ Titre vide — action annulée. Relance /add."
    if pending == "todo":
        db.add(Todo(user_id=user.id, title=title, xp_reward=10))
        db.commit()
        return f"✅ Todo ajouté : {html.escape(title)}"
    if pending == "notodo":
        db.add(NoTodo(user_id=user.id, title=title))
        db.commit()
        return f"🚫 No-Todo ajouté : {html.escape(title)}"
    if pending == "habit_binary":
        db.add(Habit(user_id=user.id, name=title, type="binary", point_rewards={"discipline": 1}))
        db.commit()
        return f"✨ Habitude créée : {html.escape(title)} (binary)"
    if pending == "habit_quant":
        parts = title.split(maxsplit=1)
        name = parts[0]
        unit = parts[1].strip() if len(parts) > 1 else ""
        db.add(Habit(
            user_id=user.id, name=name, type="quantitative",
            unit=unit or None, point_rewards={"discipline": 1},
        ))
        db.commit()
        unit_str = f" — unité : {html.escape(unit)}" if unit else " (sans unité)"
        return f"✨ Habitude quantitative créée : {html.escape(name)}{unit_str}"
    return "❌ Action inconnue — annulée."

async def route_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    # Plain text is normally ignored, EXCEPT when an /add flow is awaiting a title or softskill creation.
    pending = context.user_data.get("pending_add")
    pending_ss = context.user_data.get("pending_ss_create")
    if not text.startswith("/") and not pending and not pending_ss:
        return

    chat = update.effective_chat
    chat_id = str(chat.id)

    db = SessionLocal()
    try:
        # Restrict to the target group, plus known users in private chats.
        # The users table IS the whitelist: an account is created (with the real
        # Telegram user ID) the first time someone posts in the group, which also
        # grants them access to DM the bot. Strangers who never posted have no
        # account, so they cannot self-register or interact via private chat.
        is_target_group = chat_id == str(TELEGRAM_GROUP_ID)
        is_known_private = (
            chat.type == "private"
            and db.query(User).filter_by(chat_id=chat_id).first() is not None
        )
        if TELEGRAM_GROUP_ID and not (is_target_group or is_known_private):
            print(f"Ignored message from unauthorized chat ID: {chat_id}")
            return

        # Resolve active user from the message sender
        user = _resolve_user(db, update.message.from_user)
        username = user.username

        # Multi-step /add flow: a previous button choice is awaiting a typed title.
        if pending:
            if text.startswith("/"):
                # A new command aborts the pending flow; fall through to normal routing.
                context.user_data.pop("pending_add", None)
            else:
                reply = _create_pending_item(db, user, pending, text)
                context.user_data.pop("pending_add", None)
                await update.message.reply_text(reply, parse_mode="HTML")
                return

        # Multi-step softskill creation flow
        if pending_ss:
            if text.startswith("/"):
                # A new command aborts the pending flow; fall through to normal routing.
                context.user_data.pop("pending_ss_create", None)
            else:
                step = pending_ss.get("step")
                branch = pending_ss.get("branch")
                
                if step == 1:
                    skill_id = text.strip().lower().replace(" ", "_")
                    if not skill_id:
                        await update.message.reply_text("❌ L'ID ne peut pas être vide. Veuillez entrer un identifiant valide (ex: negociation_active).")
                        db.close()
                        return
                    config = load_tree_config()
                    if any(s["id"] == skill_id for s in config.get("skills", [])):
                        await update.message.reply_text(f"❌ Un softskill avec l'ID '{skill_id}' existe déjà. Veuillez en entrer un autre.")
                        db.close()
                        return
                    
                    pending_ss["id"] = skill_id
                    pending_ss["step"] = 2
                    context.user_data["pending_ss_create"] = pending_ss
                    await update.message.reply_text(
                        f"ID retenu : <code>{html.escape(skill_id)}</code>\n\n"
                        f"✏️ Étape 2/4 : Entrez le <b>nom</b> du softskill (ex: Négociation Active).",
                        parse_mode="HTML"
                    )
                    db.close()
                    return
                    
                elif step == 2:
                    name = text.strip()
                    if not name:
                        await update.message.reply_text("❌ Le nom ne peut pas être vide. Veuillez entrer un nom valide.")
                        db.close()
                        return
                    pending_ss["name"] = name
                    pending_ss["step"] = 3
                    context.user_data["pending_ss_create"] = pending_ss
                    await update.message.reply_text(
                        f"Nom retenu : <b>{html.escape(name)}</b>\n\n"
                        f"✏️ Étape 3/4 : Entrez la <b>description</b> du softskill.",
                        parse_mode="HTML"
                    )
                    db.close()
                    return
                    
                elif step == 3:
                    description = text.strip()
                    pending_ss["description"] = description
                    pending_ss["step"] = 4
                    context.user_data["pending_ss_create"] = pending_ss
                    await update.message.reply_text(
                        "Description retenue.\n\n"
                        "✏️ Étape 4/4 : Entrez l'<b>ordre d'exécution</b> (un nombre entier >= 1, ex: 1, 2, 3).",
                        parse_mode="HTML"
                    )
                    db.close()
                    return
                    
                elif step == 4:
                    try:
                        execution_order = int(text.strip())
                        if execution_order < 1:
                            raise ValueError()
                    except ValueError:
                        await update.message.reply_text("❌ Ordre invalide. Veuillez entrer un nombre entier supérieur ou égal à 1.")
                        db.close()
                        return
                    
                    try:
                        new_skill = create_skill({
                            "id": pending_ss["id"],
                            "name": pending_ss["name"],
                            "description": pending_ss["description"],
                            "branch": branch,
                            "execution_order": execution_order
                        })
                        context.user_data.pop("pending_ss_create", None)
                        await update.message.reply_text(
                            f"✅ <b>Softskill créé avec succès !</b>\n\n"
                            f"• <b>ID</b> : <code>{new_skill['id']}</code>\n"
                            f"• <b>Nom</b> : {html.escape(new_skill['name'])}\n"
                            f"• <b>Description</b> : {html.escape(new_skill['description'])}\n"
                            f"• <b>Branche</b> : {html.escape(new_skill['branch'])}\n"
                            f"• <b>Ordre</b> : {new_skill['execution_order']}\n"
                            f"• <b>Position</b> : (x={new_skill['x']}, y={new_skill['y']})",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        context.user_data.pop("pending_ss_create", None)
                        await update.message.reply_text(f"❌ Erreur lors de la création du softskill : {e}")
                    db.close()
                    return

        # Parse command
        try:
            parsed = parse_command(text)
        except ParserError as pe:
            await update.message.reply_text(f"⚠️ {pe}")
            return

        cmd = parsed["command"]

        if cmd == "done":
            habit_name = parsed["habit_name"]
            habit = db.query(Habit).filter_by(name=habit_name, user_id=user.id, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            if habit.type != "binary":
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" est quantitative. Utilisez : /log {habit_name} [valeur][unité]")
                return

            # Check if already logged today
            today = datetime.date.today()
            start_dt = datetime.datetime.combine(today, datetime.time.min)
            end_dt = datetime.datetime.combine(today, datetime.time.max)
            
            existing = db.query(HabitLog).filter(
                HabitLog.user_id == user.id,
                HabitLog.habit_id == habit.id,
                HabitLog.log_type == "done",
                HabitLog.timestamp >= start_dt,
                HabitLog.timestamp <= end_dt
            ).first()

            if existing:
                await update.message.reply_text(f"🎯 L'habitude \"{habit_name}\" a déjà été complétée aujourd'hui !")
                return

            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="done"
            )
            db.add(log)
            db.commit()

            # Recalculate daily stats
            score = calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            rewards_str = format_stat_rewards(habit.point_rewards)
            await update.message.reply_text(
                f"✅ {username} a complété la routine \"{habit_name}\" !\n"
                f"✨ Stats obtenues : {rewards_str}"
            )

        elif cmd == "log":
            habit_name = parsed["habit_name"]
            val = parsed["value"]
            unit = parsed["unit"]

            habit = db.query(Habit).filter_by(name=habit_name, user_id=user.id, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            if habit.type != "quantitative":
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" est binaire. Utilisez : /done {habit_name}")
                return

            if habit.unit and unit.lower() != habit.unit.lower():
                await update.message.reply_text(f"❌ L'habitude attend l'unité \"{habit.unit}\" (ex : /log {habit_name} {val}{habit.unit})")
                return

            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="log",
                amount=val,
                unit=unit
            )
            db.add(log)
            db.commit()

            today = datetime.date.today()
            score = calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            rewards_str = format_stat_rewards(habit.point_rewards)
            cap_info = f" (Cap journalier : {habit.daily_cap}pts)" if habit.daily_cap else ""

            await update.message.reply_text(
                f"📚 {username} a loggé {val}{unit} pour la quête \"{habit_name}\" !\n"
                f"✨ Stats obtenues : {rewards_str}{cap_info}"
            )

        elif cmd == "skip":
            habit_name = parsed["habit_name"]
            reason = parsed["reason"]

            habit = db.query(Habit).filter_by(name=habit_name, user_id=user.id, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="skip",
                reason=reason
            )
            db.add(log)
            db.commit()

            today = datetime.date.today()
            calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            await update.message.reply_text(
                f"⏭️ {username} a skippé la tâche \"{habit_name}\" pour aujourd'hui.\n"
                f"📝 Raison : {reason} (Le streak est préservé !)"
            )

        elif cmd == "fail":
            notodo_name = parsed["notodo_name"]
            notodo = db.query(NoTodo).filter(NoTodo.user_id == user.id, NoTodo.title.ilike(f"%{notodo_name}%")).first()
            
            if not notodo:
                await update.message.reply_text(f"❌ La règle No-Todo \"{notodo_name}\" n'existe pas. Utilisez /liste notodo pour vérifier vos règles.")
                return
                
            notodo.failed_at = datetime.datetime.now()
            db.commit()
            
            await update.message.reply_text(f"⚠️ Aïe ! {username} a transgressé la règle No-Todo : \"{notodo.title}\".\nC'est noté pour aujourd'hui. Reprenez-vous !")

        elif cmd == "status":
            today = datetime.date.today()
            score = calculate_daily_score(db, user_id=user.id, date=today)
            
            # Fetch custom thresholds or defaults
            custom_template = db.query(PerfectDayTemplate).filter_by(user_id=user.id, template_name=score.template_used).first()
            thresholds = custom_template.thresholds_json if custom_template else DEFAULT_THRESHOLDS.get(score.template_used, {})

            perf_status = "🟩 Validé !" if score.status == "Perfect" else "🟥 En cours..."

            perf_details = []
            for stat, thresh in thresholds.items():
                actual = score.actual_stats.get(stat.lower(), 0)
                perf_details.append(f"{STAT_LABELS.get(stat.lower(), stat)} : {actual}/{thresh}")

            # Get completed habits list
            start_dt = datetime.datetime.combine(today, datetime.time.min)
            end_dt = datetime.datetime.combine(today, datetime.time.max)
            today_logs = db.query(HabitLog).filter(
                HabitLog.user_id == user.id,
                HabitLog.timestamp >= start_dt,
                HabitLog.timestamp <= end_dt
            ).all()

            completed_lines = []
            skipped_lines = []
            logged_habit_ids = set()

            for log_entry in today_logs:
                habit = db.query(Habit).filter_by(id=log_entry.habit_id, user_id=user.id).first()
                if not habit:
                    continue
                logged_habit_ids.add(habit.id)
                display_name = "Chose secrète 🔒" if habit.is_private else html.escape(habit.name)

                if log_entry.log_type == "done":
                    completed_lines.append(f"- {display_name} (done)")
                elif log_entry.log_type == "log":
                    completed_lines.append(f"- {display_name} ({log_entry.amount}{log_entry.unit})")
                elif log_entry.log_type == "skip":
                    skipped_lines.append(f"- {display_name} (skippé, raison : {html.escape(log_entry.reason or '')})")

            # Get completed Todos for today
            completed_todos = db.query(Todo).filter(
                Todo.user_id == user.id,
                Todo.is_completed == True,
                Todo.completed_at >= start_dt,
                Todo.completed_at <= end_dt
            ).all()
            for t in completed_todos:
                completed_lines.append(f"- Todo : {html.escape(t.title)} (+{t.xp_reward} XP)")

            # Get remaining scheduled habits
            weekday = today.weekday()
            model_day_idx = (weekday + 1) % 7
            all_habits = db.query(Habit).filter_by(user_id=user.id, is_active=True).all()
            
            remaining_lines = []
            for habit in all_habits:
                scheduled = str(model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]
                if not scheduled or habit.id in logged_habit_ids:
                    continue
                display_name = "Chose secrète 🔒" if habit.is_private else html.escape(habit.name)
                desc = "quantitative" if habit.type == "quantitative" else "binary"
                remaining_lines.append(f"- {display_name} ({desc})")

            # Streaks
            perf_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Perfect").first()
            perf_streak_val = perf_streak.current_streak if perf_streak else 0

            msg = (
                f"⚔️ <b>{html.escape(username)}</b> — Statut de la journée (Template : {score.template_used.upper()})\n\n"
                f"Perfect Day : {perf_status}\n"
                f"🎯 Seuils à atteindre : {', '.join(perf_details) if perf_details else 'Aucun'}\n\n"
                f"🔥 Streak Perfect Day : {perf_streak_val} jours\n"
                f"💰 Or accumulé : {user.gold} Gold\n"
                f"⭐ Niveau {user.level} (XP : {user.xp})\n\n"
            )

            # Get failed NoTodos for today
            failed_notodos = db.query(NoTodo).filter(
                NoTodo.user_id == user.id,
                NoTodo.failed_at >= start_dt,
                NoTodo.failed_at <= end_dt
            ).all()
            
            failed_notodo_lines = []
            for n in failed_notodos:
                failed_notodo_lines.append(f"- 🚫 {html.escape(n.title)}")

            if completed_lines:
                msg += "<b>Quêtes accomplies :</b>\n" + "\n".join(completed_lines) + "\n\n"
            if skipped_lines:
                msg += "<b>Quêtes skippées :</b>\n" + "\n".join(skipped_lines) + "\n\n"
            if remaining_lines:
                msg += "<b>Quêtes restantes :</b>\n" + "\n".join(remaining_lines) + "\n\n"
            else:
                msg += "🎉 Toutes les quêtes d'aujourd'hui sont terminées !\n\n"
                
            if failed_notodo_lines:
                msg += "<b>Règles No-Todo brisées aujourd'hui :</b>\n" + "\n".join(failed_notodo_lines) + "\n"

            await update.message.reply_text(msg, parse_mode="HTML")

        elif cmd == "set-day":
            t_name = parsed["template_name"]
            if t_name is None:
                keyboard = [
                    [InlineKeyboardButton("📅 Semaine", callback_data="setday:week"),
                     InlineKeyboardButton("🌴 Weekend", callback_data="setday:weekend")],
                    [InlineKeyboardButton("🛟 Recovery", callback_data="setday:recup"),
                     InlineKeyboardButton("🤒 Sick", callback_data="setday:malade")],
                ]
                await update.message.reply_text(
                    "Quel type de journée veux-tu ?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return

            matched_name = TEMPLATE_WORD_MAP.get(t_name.lower())
            if not matched_name:
                await update.message.reply_text(
                    "❌ Template inconnu. Choisissez parmi : semaine, weekend, recovery, sick"
                )
                return

            await update.message.reply_text(_apply_set_day(db, user.id, matched_name))

        elif cmd == "liste":
            l_type = parsed["type"]
            if l_type is None:
                keyboard = [[
                    InlineKeyboardButton("📝 Todos", callback_data="liste:todo"),
                    InlineKeyboardButton("🎯 Habitudes", callback_data="liste:habit"),
                    InlineKeyboardButton("🚫 No-Todos", callback_data="liste:notodo"),
                ]]
                await update.message.reply_text(
                    "Quelle liste afficher ?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await update.message.reply_text(_render_liste(db, user.id, l_type), parse_mode="HTML")

        elif cmd == "motivation":
            from src.database.models import Goal
            goals = db.query(Goal).filter_by(user_id=user.id, completed=False).all()
            if not goals:
                await update.message.reply_text("Tu n'as pas encore d'objectifs en cours. Utilise le tableau de bord pour en définir !")
            else:
                lines = []
                for g in goals:
                    desc = f" - <i>{html.escape(g.description)}</i>" if g.description else ""
                    lines.append(f"🌟 <b>{html.escape(g.title)}</b>{desc}")
                
                msg = f"🔥 <b>Objectifs de {html.escape(username)}</b> 🔥\nNe perds pas le cap :\n\n" + "\n".join(lines)
                await update.message.reply_text(msg, parse_mode="HTML")

        elif cmd == "add":
            a_type = parsed["type"]
            title = parsed["title"]
            if a_type is None:
                keyboard = [
                    [InlineKeyboardButton("📝 Todo", callback_data="add:todo"),
                     InlineKeyboardButton("🚫 No-Todo", callback_data="add:notodo")],
                    [InlineKeyboardButton("🎯 Habitude", callback_data="add:habit")],
                ]
                await update.message.reply_text(
                    "Qu'est-ce que tu veux ajouter ?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return
            if a_type == "todo":
                todo = Todo(user_id=user.id, title=title, xp_reward=10)
                db.add(todo)
                db.commit()
                await update.message.reply_text(f"✅ Todo ajouté : {title}")
            elif a_type == "notodo":
                notodo = NoTodo(user_id=user.id, title=title)
                db.add(notodo)
                db.commit()
                await update.message.reply_text(f"🚫 No-Todo ajouté : {title}")
            elif a_type == "habit":
                # Respond with helper to add habit
                msg = (
                    "Pour créer une habitude, copiez-collez l'une des commandes ci-dessous et complétez-la :\n\n"
                    "<b>Habitude Binaire (Oui/Non) :</b>\n"
                    f"<code>/add_habit binary {title or 'Nom_Habitude'}</code>\n\n"
                    "<b>Habitude Quantitative (avec log) :</b>\n"
                    f"<code>/add_habit quant {title or 'Nom_Habitude'} min</code>"
                )
                await update.message.reply_text(msg, parse_mode="HTML")

        elif cmd == "add_habit":
            h_type = parsed["habit_type"]
            title = parsed["title"]
            unit = parsed.get("unit", "")
            
            # Default points for habit creation via bot
            default_points = {"discipline": 1}
            habit_type_db = "binary" if h_type == "binary" else "quantitative"
            
            habit = Habit(
                user_id=user.id,
                name=title,
                type=habit_type_db,
                point_rewards=default_points,
                unit=unit if habit_type_db == "quantitative" else None
            )
            db.add(habit)
            db.commit()
            
            await update.message.reply_text(f"✨ Habitude créée : {title} ({habit_type_db})")

        elif cmd == "shop":
            filter_val = parsed.get("filter", "toutes")
            rewards = db.query(Reward).filter_by(user_id=user.id).all()
            
            if not rewards:
                await update.message.reply_text("🏪 La boutique est vide. Créez des récompenses sur le dashboard !")
                return

            daily_items = []
            weekly_items = []
            regular_items = []
            
            for r in rewards:
                unlocked, reason = check_reward_lock(db, user.id, r)
                
                is_available = True
                if r.category in ["allostasis_daily", "allostasis_weekly"]:
                    is_available = is_allostasis_available(r)
                    
                is_owned = r.is_one_time and r.purchased_count > 0
                
                # Apply filters
                if filter_val in ["dispos", "unlocked"]:
                    if not unlocked:
                        continue
                    if is_owned:
                        continue
                    if r.category in ["allostasis_daily", "allostasis_weekly"] and not is_available:
                        continue
                if filter_val in ["verrouillees", "locked"] and unlocked:
                    continue
                    
                desc_str = f" - <i>{html.escape(r.description)}</i>" if r.description else ""
                
                if r.category in ["allostasis_daily", "allostasis_weekly"]:
                    if not unlocked:
                        status = f" [🔒 Verrouillé: {reason}]"
                    elif not is_available:
                        status = " [✓ Validé]"
                    else:
                        status = " [🔄 A valider]"
                    line = f"• <b>{html.escape(r.title)}</b>{desc_str}\n  Prix: <b>Gratuit</b>{status}"
                    if r.category == "allostasis_daily":
                        daily_items.append(line)
                    else:
                        weekly_items.append(line)
                else:
                    if is_owned:
                        status = " [👑 Acquis]"
                    elif not unlocked:
                        status = f" [🔒 Verrouillé: {reason}]"
                    else:
                        status = " [🛒 Achetable]"
                    line = f"• <b>{html.escape(r.title)}</b>{desc_str}\n  Prix: 💰 <b>{r.gold_cost} Or</b>{status}"
                    regular_items.append(line)
                    
            lines = [f"🏪 <b>Boutique de {username}</b> (Solde : 💰 <b>{user.gold} Or</b>)\n"]
            
            if daily_items:
                lines.append("🔄 <b>Allostasie Daily :</b>")
                lines.extend(daily_items)
                lines.append("")
                
            if weekly_items:
                lines.append("📅 <b>Allostasie Weekly :</b>")
                lines.extend(weekly_items)
                lines.append("")
                
            if regular_items:
                lines.append("💎 <b>Récompenses Classiques :</b>")
                lines.extend(regular_items)

            if len(daily_items) == 0 and len(weekly_items) == 0 and len(regular_items) == 0:
                await update.message.reply_text("Aucune récompense ne correspond à ce filtre.")
                return
                
            await update.message.reply_text("\n".join(lines).strip(), parse_mode="HTML")

        elif cmd == "buy":
            reward_name = parsed["reward_name"]
            if reward_name is None:
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Allostasie Day", callback_data="buy_cat:allostasis_daily"),
                        InlineKeyboardButton("📅 Allostasie Week", callback_data="buy_cat:allostasis_weekly")
                    ],
                    [
                        InlineKeyboardButton("💎 Shop Basic", callback_data="buy_cat:regular")
                    ]
                ]
                await update.message.reply_text(
                    "🛒 <b>Boutique — Choisissez une catégorie :</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                return

            matches = db.query(Reward).filter(
                Reward.user_id == user.id,
                Reward.title.ilike(f"%{reward_name}%")
            ).all()
            
            if not matches:
                await update.message.reply_text(f"❌ Aucune récompense ne correspond à \"{reward_name}\".")
                return
                
            if len(matches) > 1:
                options_str = ", ".join(f"\"{r.title}\"" for r in matches)
                await update.message.reply_text(
                    f"❌ Plusieurs récompenses correspondent : {options_str}. Soyez plus précis."
                )
                return
                
            reward_to_buy = matches[0]
            try:
                res = purchase_reward(db, user.id, reward_to_buy.id)
                if reward_to_buy.category in ["allostasis_daily", "allostasis_weekly"]:
                    await update.message.reply_text(
                        f"✅ Allostasie validée ! Vous avez validé <b>{html.escape(reward_to_buy.title)}</b>.\n"
                        f"Solde actuel : 💰 <b>{res['new_gold']} Or</b>.",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(
                        f"💸 Achat réussi ! Vous avez acheté <b>{html.escape(reward_to_buy.title)}</b> pour 💰 <b>{res['gold_spent']} Or</b>.\n"
                        f"Nouveau solde : 💰 <b>{res['new_gold']} Or</b>.",
                        parse_mode="HTML"
                    )
            except HTTPException as he:
                await update.message.reply_text(f"⚠️ {he.detail}")
            except Exception as e:
                await update.message.reply_text(f"❌ Erreur lors de l'achat : {e}")

        elif cmd == "softskill":
            config = load_tree_config()
            branches = config.get("branches", {})
            if not branches:
                await update.message.reply_text("Aucune branche de softskills configurée dans le système.")
                return
            
            keyboard = []
            row = []
            for b_key in branches.keys():
                row.append(InlineKeyboardButton(b_key, callback_data=f"ss_branch:{b_key}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
                
            await update.message.reply_text(
                "🧠 <b>Arbre des Softskills</b>\nChoisissez une catégorie de compétence :",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

        elif cmd == "aide":
            keyboard = [
                [InlineKeyboardButton("Aide Documentation", callback_data="help_doc")],
                [InlineKeyboardButton("Liste des commandes", callback_data="help_cmds")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Besoin d'aide ? Choisissez une option :", reply_markup=reply_markup)

    except Exception as e:
        print(f"Error executing command router: {e}")
        await update.message.reply_text(f"❌ Une erreur interne est survenue : {e}")
    finally:
        db.close()

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    # --- Static help buttons -------------------------------------------------
    if data == "help_doc":
        await query.message.reply_text(
            "📖 Pour ouvrir le tableau de bord, va sur http://localhost:5000"
        )
        return

    if data == "help_cmds":
        cmds_text = (
            "📋 <b>Liste des commandes</b>\n\n"
            "<b>/done</b> [nom] — Valide une habitude binaire\n"
            "<b>/log</b> [nom] [valeur][unité] — Enregistre une habitude quantitative\n"
            "<b>/skip</b> [nom] raison: [texte] — Saute une habitude sans casser le streak\n"
            "<b>/status</b> — Affiche le statut du jour\n"
            "<b>/set-day</b> (alias <b>/template</b>) [template] — Change le type de journée (boutons si sans argument)\n"
            "<b>/liste</b> [todo|habit|notodo] — Liste tes éléments (boutons si sans argument)\n"
            "<b>/add</b> [todo|notodo|habit] [titre] — Ajoute une tâche ou une règle (boutons si sans argument)\n"
            "<b>/add_habit</b> [binary|quant] [titre] [unité] — Crée une habitude\n"
            "<b>/fail</b> [nom_notodo] — Marque une règle No-Todo comme transgressée\n"
            "<b>/shop</b> [filtre] — Affiche les récompenses de la boutique\n"
            "<b>/buy</b> [nom] — Achète une récompense de la boutique\n"
            "<b>/motivation</b> — Liste tes objectifs à long terme\n"
            "<b>/softskill</b> (alias <b>/skills</b>) — Gère tes softskills (branches, création, validation)\n"
            "<b>/aide</b> (alias <b>/help</b>) — Affiche ce menu d'aide"
        )
        await query.message.reply_text(cmds_text, parse_mode="HTML")
        return

    # --- /add flow: type choice ---------------------------------------------
    if data == "add:habit":
        keyboard = [[
            InlineKeyboardButton("✅ Oui/Non (binaire)", callback_data="addhabit:binary"),
            InlineKeyboardButton("📊 Quantitatif (log)", callback_data="addhabit:quant"),
        ]]
        await query.message.reply_text(
            "Quel type d'habitude ?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # --- /add flow: a choice was made → await the title in the next message --
    pending_prompts = {
        "add:todo": ("todo", "✏️ Envoie le titre du Todo."),
        "add:notodo": ("notodo", "✏️ Envoie le titre de la règle No-Todo."),
        "addhabit:binary": ("habit_binary", "✏️ Envoie le nom de l'habitude (Oui/Non)."),
        "addhabit:quant": ("habit_quant", "✏️ Envoie : nom unité — ex : lecture min (l'unité est optionnelle)."),
    }
    if data in pending_prompts:
        state, prompt = pending_prompts[data]
        context.user_data["pending_add"] = state
        await query.message.reply_text(prompt)
        return

    # --- Softskill callback actions ------------------------------------------
    if data.startswith("ss_"):
        db = SessionLocal()
        try:
            user = _resolve_user(db, query.from_user)
            
            if data == "ss_back_main":
                config = load_tree_config()
                branches = config.get("branches", {})
                keyboard = []
                row = []
                for b_key in branches.keys():
                    row.append(InlineKeyboardButton(b_key, callback_data=f"ss_branch:{b_key}"))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                await query.edit_message_text(
                    "🧠 <b>Arbre des Softskills</b>\nChoisissez une catégorie de compétence :",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
            elif data.startswith("ss_branch:"):
                branch_key = data.split(":", 1)[1]
                config = load_tree_config()
                skills = [s for s in config.get("skills", []) if s.get("branch") == branch_key]
                progress = get_user_progress(db, user.id)
                
                lines = [f"🧠 <b>Branche : {html.escape(branch_key)}</b>\n"]
                if not skills:
                    lines.append("Aucun softskill dans cette branche.")
                else:
                    # Sort by execution_order
                    skills.sort(key=lambda s: s.get("execution_order", 1))
                    for s in skills:
                        prog = progress.get(s["id"], {})
                        status = "✅ Complété" if prog.get("completed") else "⏳ En cours"
                        lines.append(f"• <b>{html.escape(s['name'])}</b> (Ordre: {s.get('execution_order')}) - <i>{status}</i>")
                        if s.get("description"):
                            lines.append(f"  <i>{html.escape(s['description'])}</i>")
                            
                keyboard = [
                    [
                        InlineKeyboardButton("➕ Ajouter un Softskill", callback_data=f"ss_add_select:{branch_key}"),
                        InlineKeyboardButton("✅ Valider un Softskill", callback_data=f"ss_val_select:{branch_key}")
                    ],
                    [
                        InlineKeyboardButton("⬅️ Retour", callback_data="ss_back_main")
                    ]
                ]
                await query.edit_message_text(
                    "\n".join(lines),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
            elif data.startswith("ss_add_select:"):
                branch_key = data.split(":", 1)[1]
                context.user_data["pending_ss_create"] = {"step": 1, "branch": branch_key}
                await query.message.reply_text(
                    f"➕ <b>Création d'un Softskill dans {html.escape(branch_key)}</b>\n\n"
                    f"✏️ Étape 1/4 : Entrez l'identifiant unique (ID) du softskill (en minuscules, sans espace, ex: <code>ecoute_active</code>)."
                )
                
            elif data.startswith("ss_val_select:"):
                branch_key = data.split(":", 1)[1]
                config = load_tree_config()
                skills = [s for s in config.get("skills", []) if s.get("branch") == branch_key]
                progress = get_user_progress(db, user.id)
                
                keyboard = []
                for s in skills:
                    prog = progress.get(s["id"], {})
                    status_emoji = "✅" if prog.get("completed") else "⏳"
                    keyboard.append([InlineKeyboardButton(f"{status_emoji} {s['name']}", callback_data=f"ss_test_val:{s['id']}")])
                    
                keyboard.append([InlineKeyboardButton("⬅️ Retour", callback_data=f"ss_branch:{branch_key}")])
                
                await query.edit_message_text(
                    f"✅ <b>Validation — {html.escape(branch_key)}</b>\nChoisissez le softskill à valider :",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
            elif data.startswith("ss_test_val:"):
                skill_id = data.split(":", 1)[1]
                config = load_tree_config()
                skill = next((s for s in config.get("skills", []) if s["id"] == skill_id), None)
                if not skill:
                    await query.edit_message_text("❌ Softskill introuvable.")
                    db.close()
                    return
                    
                progress = get_user_progress(db, user.id)
                prog = progress.get(skill_id, {})
                test_text = prog.get("success_criteria_test") or "Aucun critère/test de validation défini pour ce softskill."
                
                lines = [
                    f"📋 <b>Validation — {html.escape(skill['name'])}</b>\n",
                    f"<b>Description</b> : <i>{html.escape(skill.get('description', 'Aucune description.'))}</i>\n",
                    f"<b>Critères / Test de validation</b> :",
                    f"<pre>{html.escape(test_text)}</pre>\n",
                    "Voulez-vous valider ce softskill ?"
                ]
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Valider", callback_data=f"ss_confirm_val:{skill_id}"),
                        InlineKeyboardButton("❌ Annuler", callback_data=f"ss_branch:{skill['branch']}")
                    ]
                ]
                
                await query.edit_message_text(
                    "\n".join(lines),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
            elif data.startswith("ss_confirm_val:"):
                skill_id = data.split(":", 1)[1]
                config = load_tree_config()
                skill = next((s for s in config.get("skills", []) if s["id"] == skill_id), None)
                if not skill:
                    await query.edit_message_text("❌ Softskill introuvable.")
                    db.close()
                    return
                    
                res = toggle_completion(db, user.id, skill_id, True)
                if "error" in res:
                    await query.edit_message_text(
                        f"⚠️ <b>Impossible de valider :</b>\n{html.escape(res['error'])}\n\n"
                        f"Vous devez d'abord compléter les prérequis.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Retour", callback_data=f"ss_branch:{skill['branch']}")
                        ]]),
                        parse_mode="HTML"
                    )
                else:
                    await query.edit_message_text(
                        f"🎉 <b>Félicitations !</b>\nLe softskill <b>{html.escape(skill['name'])}</b> a été validé avec succès !",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Retour à la branche", callback_data=f"ss_branch:{skill['branch']}")
                        ]]),
                        parse_mode="HTML"
                    )
        except Exception as e:
            print(f"Error handling softskill callback {data}: {e}")
            await query.message.reply_text(f"❌ Une erreur est survenue : {e}")
        finally:
            db.close()
        return

    # --- Data-backed buttons (need a DB session + the user) ------------------
    if data.startswith("liste:") or data.startswith("setday:"):
        db = SessionLocal()
        try:
            user = _resolve_user(db, query.from_user)
            key = data.split(":", 1)[1]
            if data.startswith("liste:"):
                await query.message.reply_text(_render_liste(db, user.id, key), parse_mode="HTML")
            else:
                await query.message.reply_text(_apply_set_day(db, user.id, key))
        except Exception as e:
            print(f"Error handling callback {data}: {e}")
            await query.message.reply_text(f"❌ Une erreur est survenue : {e}")
        finally:
            db.close()
        return

    if data.startswith("buy_cat:") or data.startswith("buy_item:"):
        db = SessionLocal()
        try:
            user = _resolve_user(db, query.from_user)
            if data.startswith("buy_cat:"):
                category = data.split(":", 1)[1]
                
                # Fetch all rewards for this user and this category
                rewards = db.query(Reward).filter_by(user_id=user.id, category=category).all()
                
                available_rewards = []
                for r in rewards:
                    # Check locks
                    unlocked, _ = check_reward_lock(db, user.id, r)
                    if not unlocked:
                        continue
                    
                    # Check category specific availability
                    if category in ["allostasis_daily", "allostasis_weekly"]:
                        if not is_allostasis_available(r):
                            continue
                    else: # regular
                        # Check one-time limit
                        if r.is_one_time and r.purchased_count > 0:
                            continue
                        # Check gold limit
                        if user.gold < r.gold_cost:
                            continue
                    
                    available_rewards.append(r)
                
                category_label = "Allostasie Day" if category == "allostasis_daily" else "Allostasie Week" if category == "allostasis_weekly" else "Boutique Classique"
                
                if not available_rewards:
                    await query.edit_message_text(
                        f"❌ Aucun item disponible ou achetable dans la catégorie <b>{category_label}</b>.",
                        parse_mode="HTML"
                    )
                    return
                
                # Construct inline keyboard buttons for available rewards
                keyboard = []
                for r in available_rewards:
                    if category in ["allostasis_daily", "allostasis_weekly"]:
                        btn_text = f"✨ {r.title}"
                    else:
                        btn_text = f"💰 {r.title} ({r.gold_cost} Or)"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"buy_item:{r.id}")])
                
                await query.edit_message_text(
                    f"🛒 <b>Items disponibles — {category_label} :</b>\nSélectionnez un item à acheter ou valider :",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
            else: # buy_item
                reward_id = int(data.split(":", 1)[1])
                reward_to_buy = db.query(Reward).filter_by(id=reward_id, user_id=user.id).first()
                
                if not reward_to_buy:
                    await query.edit_message_text("❌ Récompense introuvable.")
                    return
                    
                # Perform purchase
                res = purchase_reward(db, user.id, reward_to_buy.id)
                if reward_to_buy.category in ["allostasis_daily", "allostasis_weekly"]:
                    msg = (
                        f"✅ Allostasie validée ! Vous avez validé <b>{html.escape(reward_to_buy.title)}</b>.\n"
                        f"Solde actuel : 💰 <b>{res['new_gold']} Or</b>."
                    )
                else:
                    msg = (
                        f"💸 Achat réussi ! Vous avez acheté <b>{html.escape(reward_to_buy.title)}</b> pour 💰 <b>{res['gold_spent']} Or</b>.\n"
                        f"Nouveau solde : 💰 <b>{res['new_gold']} Or</b>."
                    )
                
                await query.edit_message_text(msg, parse_mode="HTML")
                
        except HTTPException as he:
            await query.edit_message_text(f"⚠️ {he.detail}")
        except Exception as e:
            print(f"Error handling callback {data}: {e}")
            await query.edit_message_text(f"❌ Une erreur est survenue : {e}")
        finally:
            db.close()
        return

async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ WARNING: TELEGRAM_BOT_TOKEN environment variable is not defined.")
        print("The Telegram Bot Listener will run in standby mode.")
        while True:
            await asyncio.sleep(3600)

    print(f"Starting Telegram Bot polling listener on Group ID: {TELEGRAM_GROUP_ID}...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, route_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, route_command))
    application.add_handler(CallbackQueryHandler(handle_callback))

    await application.initialize()

    # Define and register bot commands for Telegram autocomplete
    commands = [
        BotCommand("done", "Valider une habitude binaire (oui/non)"),
        BotCommand("log", "Enregistrer une habitude quantitative (ex: /log lecture 30)"),
        BotCommand("skip", "Passer une habitude pour aujourd'hui (sans casser le streak)"),
        BotCommand("status", "Afficher ton résumé et statut de la journée"),
        BotCommand("template", "Changer le type de journée (Perfect Day template)"),
        BotCommand("liste", "Lister tes todos, habitudes ou no-todos"),
        BotCommand("add", "Ajouter un todo, un no-todo ou une habitude"),
        BotCommand("add_habit", "Créer une nouvelle habitude (binaire ou quantitative)"),
        BotCommand("fail", "Signaler la transgression d'une règle No-Todo"),
        BotCommand("shop", "Consulter les récompenses de la boutique"),
        BotCommand("buy", "Acheter un item ou valider une allostasie"),
        BotCommand("motivation", "Afficher tes objectifs de vie à long terme"),
        BotCommand("softskill", "Gérer et valider tes softskills"),
        BotCommand("aide", "Afficher la liste d'aide et des commandes")
    ]
    try:
        await application.bot.set_my_commands(commands)
        print("Telegram bot autocomplete commands registered successfully.")
    except Exception as e:
        print(f"Failed to register Telegram bot autocomplete commands: {e}")

    await application.start()

    # Start the daily recap scheduler
    start_scheduler()

    # allowed_updates=ALL_TYPES is required so Telegram delivers callback_query
    # (inline button clicks). A previous restricted getUpdates call persists its
    # allowed_updates server-side, so we must override it explicitly here.
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
