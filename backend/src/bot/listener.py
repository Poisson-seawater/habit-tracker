import os
import re
import asyncio
import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID
from src.database.session import SessionLocal
from src.database.models import User, Habit, HabitLog, DayTemplate, DailyScore, Streak
from src.bot.parser import parse_command, ParserError
from src.services.score_service import calculate_daily_score, update_streaks

# Mapping HSL-tailored stats to their French display labels
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

async def route_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text.startswith("/"):
        return

    chat_id = str(update.effective_chat.id)
    
    # In production, strictly restrict to target group chat
    if TELEGRAM_GROUP_ID and chat_id != str(TELEGRAM_GROUP_ID):
        print(f"Ignored message from unauthorized chat ID: {chat_id}")
        return

    db = SessionLocal()
    try:
        # Resolve Gabriel (User ID 1) and update his chat_id if necessary
        user = db.query(User).filter_by(id=1).first()
        if not user:
            # Fallback seed user
            user = User(id=1, username="Gabriel", chat_id=chat_id)
            db.add(user)
            db.commit()
        elif user.chat_id != chat_id:
            user.chat_id = chat_id
            db.commit()

        username = user.username

        # Parse command
        try:
            parsed = parse_command(text)
        except ParserError as pe:
            await update.message.reply_text(f"⚠️ {pe}")
            return

        cmd = parsed["command"]

        if cmd == "done":
            habit_name = parsed["habit_name"]
            habit = db.query(Habit).filter_by(name=habit_name, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            if habit.type != "binary":
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" est quantitative. Utilisez: /log {habit_name} [valeur][unité]")
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

            # Log habit
            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="done"
            )
            db.add(log)
            db.commit()

            # Recalculate points and streaks
            calculate_daily_score(db, user_id=user.id, date=today)
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

            habit = db.query(Habit).filter_by(name=habit_name, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            if habit.type != "quantitative":
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" est binaire. Utilisez: /done {habit_name}")
                return

            if habit.unit and unit.lower() != habit.unit.lower():
                await update.message.reply_text(f"❌ L'habitude attend l'unité \"{habit.unit}\" (ex: /log {habit_name} {val}{habit.unit})")
                return

            # Log habit
            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="log",
                amount=val,
                unit=unit
            )
            db.add(log)
            db.commit()

            # Recalculate
            today = datetime.date.today()
            calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            rewards_str = format_stat_rewards(habit.point_rewards)
            # Add indication if cap applies
            cap_info = ""
            if habit.daily_cap:
                cap_info = f" (Cap journalier: {habit.daily_cap}pts)"

            await update.message.reply_text(
                f"📚 {username} a loggé {val}{unit} pour la quête \"{habit_name}\" !\n"
                f"✨ Stats obtenues : {rewards_str}{cap_info}"
            )

        elif cmd == "skip":
            habit_name = parsed["habit_name"]
            reason = parsed["reason"]

            habit = db.query(Habit).filter_by(name=habit_name, is_active=True).first()
            if not habit:
                await update.message.reply_text(f"❌ L'habitude \"{habit_name}\" n'existe pas ou n'est pas active.")
                return

            # Log skip
            log = HabitLog(
                user_id=user.id,
                habit_id=habit.id,
                log_type="skip",
                reason=reason
            )
            db.add(log)
            db.commit()

            # Recalculate
            today = datetime.date.today()
            calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            await update.message.reply_text(
                f"⏭️ {username} a skippé la tâche \"{habit_name}\" pour aujourd'hui.\n"
                f"📝 Raison : {reason} (Le streak est préservé !)"
            )

        elif cmd == "status":
            today = datetime.date.today()
            score = calculate_daily_score(db, user_id=user.id, date=today)
            
            template = db.query(DayTemplate).filter_by(id=score.active_template_id).first()
            template_name = template.name if template else "Semaine"

            # Get acceptable thresholds string
            acc_status = "🟩 Validé" if score.status in ["Acceptable", "Perfect"] else "🟥 En cours"
            perf_status = "🟩 Validé" if score.status == "Perfect" else "🟥 En cours"

            acc_details = []
            if template:
                for stat, thresh in template.acceptable_thresholds.items():
                    actual = score.actual_stats.get(stat.lower(), 0)
                    acc_details.append(f"{STAT_LABELS.get(stat.lower(), stat)}: {actual}/{thresh}")

            perf_details = []
            if template:
                for stat, thresh in template.perfect_thresholds.items():
                    actual = score.actual_stats.get(stat.lower(), 0)
                    perf_details.append(f"{STAT_LABELS.get(stat.lower(), stat)}: {actual}/{thresh}")

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

            for log in today_logs:
                habit = db.query(Habit).filter_by(id=log.habit_id).first()
                if not habit:
                    continue
                logged_habit_ids.add(habit.id)
                
                # Check privacy
                display_name = "Chose secrète 🔒" if habit.is_private else habit.name

                if log.log_type == "done":
                    completed_lines.append(f"- {display_name} (done)")
                elif log.log_type == "log":
                    completed_lines.append(f"- {display_name} ({log.amount}{log.unit})")
                elif log.log_type == "skip":
                    skipped_lines.append(f"- {display_name} (skippé, raison: {log.reason})")

            # Get remaining scheduled habits
            weekday = today.weekday()
            model_day_idx = (weekday + 1) % 7
            all_habits = db.query(Habit).filter_by(is_active=True).all()
            
            remaining_lines = []
            for habit in all_habits:
                scheduled = str(model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]
                if not scheduled or habit.id in logged_habit_ids:
                    continue
                
                # Check privacy
                display_name = "Chose secrète 🔒" if habit.is_private else habit.name
                
                desc = "quantitative" if habit.type == "quantitative" else "binary"
                remaining_lines.append(f"- {display_name} ({desc})")

            # Get streaks
            acc_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Acceptable").first()
            perf_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Perfect").first()

            acc_streak_val = acc_streak.current_streak if acc_streak else 0
            perf_streak_val = perf_streak.current_streak if perf_streak else 0

            msg = (
                f"⚔️ *{username}* — Statut du Jour (Template : {template_name})\n\n"
                f"Acceptable Day : {acc_status} ({', '.join(acc_details)})\n"
                f"Perfect Day : {perf_status} ({', '.join(perf_details)})\n\n"
                f"🔥 Streak Acceptable : {acc_streak_val} jours\n"
                f"⭐ Streak Perfect : {perf_streak_val} jours\n\n"
            )

            if completed_lines:
                msg += "*Quêtes accomplies :*\n" + "\n".join(completed_lines) + "\n\n"
            if skipped_lines:
                msg += "*Quêtes skippées :*\n" + "\n".join(skipped_lines) + "\n\n"
            if remaining_lines:
                msg += "*Quêtes restantes :*\n" + "\n".join(remaining_lines) + "\n"
            else:
                msg += "🎉 Toutes les quêtes d'aujourd'hui sont terminées !"

            await update.message.reply_text(msg, parse_mode="Markdown")

        elif cmd == "set-day":
            t_name = parsed["template_name"].lower()
            
            # Map sick/semaine/recovery toseeded template names
            t_map = {
                "semaine": "Semaine",
                "weekend": "Weekend",
                "recovery": "Récupération",
                "sick": "Malade",
                "malade": "Malade",
                "récupération": "Récupération",
                "recuperation": "Récupération"
            }

            matched_name = t_map.get(t_name)
            if not matched_name:
                await update.message.reply_text(
                    f"❌ Template inconnu. Choisissez parmi : semaine, weekend, recovery, sick"
                )
                return

            template = db.query(DayTemplate).filter(DayTemplate.name.collate("NOCASE") == matched_name).first()
            if not template:
                await update.message.reply_text(f"❌ Template \"{matched_name}\" non trouvé dans la base.")
                return

            # Apply and recalculate
            today = datetime.date.today()
            score = calculate_daily_score(db, user_id=user.id, date=today, template_id=template.id)
            update_streaks(db, user_id=user.id, date=today)

            await update.message.reply_text(
                f"🩹 Template de journée mis à jour vers : \"{template.name}\".\n"
                f"✨ Les seuils de points ont été allégés pour aujourd'hui !"
            )

    except Exception as e:
        print(f"Error executing command router: {e}")
        await update.message.reply_text(f"❌ Une erreur interne est survenue : {e}")
    finally:
        db.close()

async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ WARNING: TELEGRAM_BOT_TOKEN environment variable is not defined.")
        print("The Telegram Bot Listener will run in standby mode. Define the token in your .env file to enable polling.")
        while True:
            await asyncio.sleep(3600)

    print(f"Starting Telegram Bot polling listener on Group ID: {TELEGRAM_GROUP_ID}...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Route all messages that look like commands
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, route_command))

    # Support direct private testing if group is not set up
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, route_command))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Run until cancelled
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
