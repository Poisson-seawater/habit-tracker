import os
import html
import datetime
import asyncio
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import TELEGRAM_BOT_TOKEN
from src.database.session import SessionLocal
from src.database.models import (
    User,
    Habit,
    HabitLog,
    DailyScore,
    Streak,
    Todo,
    NoTodo,
    SubStep,
)
from src.services.score_service import (
    calculate_daily_score,
    update_streaks,
    add_user_xp,
    ALL_6_STATS,
)
from src.services.reward_service import get_allostasis_purchases_on_date

STAT_LABELS = {
    "forme_physique": "Forme Physique 💪",
    "sante": "Santé 🧠",
    "social": "Social 🤝",
    "finance": "Finance 💰",
    "apprendre": "Apprendre 📚",
    "discipline": "Discipline ⚔️",
}


async def publish_daily_recap():
    """
    Triggered at 21:30 daily. Calculates the day's final score for all users,
    updates streaks, awards 5 XP for Perfect Days, and broadcasts a consolidated
    RPG guild recap to the Telegram group chat.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Scheduler: TELEGRAM_BOT_TOKEN is missing. Recap broadcast aborted.")
        return

    from src.config import TELEGRAM_GROUP_ID

    print("Scheduler: Starting 21:30 daily RPG guild recap publisher...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    db = SessionLocal()

    try:
        users = db.query(User).all()
        if not users:
            print("Scheduler: No adventurers found in database.")
            return

        import zoneinfo
        from src.config import TIMEZONE

        tz = zoneinfo.ZoneInfo(TIMEZONE)
        today = datetime.datetime.now(tz).date()
        user_blocks = []
        individual_reports = {}

        for user in users:
            # 1. Finalize daily score and streaks
            score = calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            # 2. Award 5 XP if Perfect Day achieved
            xp_gained = 0
            levels_gained = []
            if score.status == "Perfect":
                xp_gained = 5
                levels_gained = add_user_xp(user, 5)
                db.commit()

            # 3. Get today's logs and split by public / private
            start_dt = datetime.datetime.combine(today, datetime.time.min)
            end_dt = datetime.datetime.combine(today, datetime.time.max)
            logs = (
                db.query(HabitLog)
                .filter(
                    HabitLog.user_id == user.id,
                    HabitLog.timestamp >= start_dt,
                    HabitLog.timestamp <= end_dt,
                )
                .all()
            )

            completed_habits = []
            skipped_habits = []
            private_completed_count = 0

            # Group today's logs by habit so targeted habits show a single "X/N" line
            logs_by_habit = {}
            for log in logs:
                logs_by_habit.setdefault(log.habit_id, []).append(log)

            for habit_id, h_logs in logs_by_habit.items():
                habit = db.query(Habit).filter_by(id=habit_id, user_id=user.id).first()
                if not habit:
                    continue

                done_logs = [l for l in h_logs if l.log_type in ["done", "log"]]
                has_target = habit.daily_target is not None and habit.daily_target > 1

                if done_logs:
                    if habit.is_private:
                        private_completed_count += len(done_logs)
                    elif has_target:
                        completed_habits.append(
                            f"{html.escape(habit.name)} {len(done_logs)}/{habit.daily_target} ✅"
                        )
                    else:
                        for log in done_logs:
                            if log.log_type == "done":
                                completed_habits.append(f"{html.escape(habit.name)} ✅")
                            else:
                                completed_habits.append(
                                    f"{html.escape(habit.name)} ({log.amount}{html.escape(log.unit or '')})"
                                )
                elif any(l.log_type == "skip" for l in h_logs):
                    if habit.is_private:
                        skipped_habits.append("Chose secrète 🔒 (skippée ⏭️)")
                    else:
                        skipped_habits.append(f"{html.escape(habit.name)} (skippé ⏭️)")

            # Check completed Todos today
            completed_todos = (
                db.query(Todo)
                .filter(
                    Todo.user_id == user.id,
                    Todo.is_completed == True,
                    Todo.completed_at >= start_dt,
                    Todo.completed_at <= end_dt,
                )
                .all()
            )
            completed_todos_list = []
            for t in completed_todos:
                completed_todos_list.append(f"{html.escape(t.title)} 🌟")

            # Check failed NoTodos today
            failed_notodos = (
                db.query(NoTodo)
                .filter(
                    NoTodo.user_id == user.id,
                    NoTodo.failed_at >= start_dt,
                    NoTodo.failed_at <= end_dt,
                )
                .all()
            )
            failed_notodos_list = []
            for n in failed_notodos:
                failed_notodos_list.append(f"{html.escape(n.title)} 🚫")

            # 4. Format streaks
            perf_streak = (
                db.query(Streak)
                .filter_by(user_id=user.id, streak_type="Perfect")
                .first()
            )
            perf_streak_val = perf_streak.current_streak if perf_streak else 0

            # Determine daily status string
            if score.status == "Perfect":
                status_emoji = "🏆 PERFECT DAY (+5 XP)!"
            else:
                status_emoji = "🟥 JOURNÉE INCOMPLÈTE"

            # Format stat progression lines
            stat_earned_parts = []
            for stat in ALL_6_STATS:
                val = score.actual_stats.get(stat, 0)
                if val > 0:
                    label = STAT_LABELS.get(stat, stat.capitalize())
                    label_short = label.split(" ")[0] if " " in label else label
                    stat_earned_parts.append(f"{label_short} +{val}")

            stat_progression_str = (
                ", ".join(stat_earned_parts) if stat_earned_parts else "Aucune stat"
            )

            # Level up notification text
            lvl_info = (
                f" (LEVEL UP! Nouveau niveau: {user.level} 🎉)" if levels_gained else ""
            )

            # 5. Construct user block
            habits_str = ", ".join(completed_habits) if completed_habits else "Aucune"
            if private_completed_count > 0:
                if habits_str == "Aucune":
                    habits_str = f"+{private_completed_count} privées 🔒"
                else:
                    habits_str += f" (+{private_completed_count} privées 🔒)"

            skipped_line = (
                f"\n⏭️ <b>Habitudes skippées :</b> {', '.join(skipped_habits)}"
                if skipped_habits
                else ""
            )
            todos_str = (
                ", ".join(completed_todos_list) if completed_todos_list else "Aucun"
            )
            failed_notodos_str = (
                ", ".join(failed_notodos_list) if failed_notodos_list else "Aucun"
            )

            # Check completed Life Lore subgoals today
            completed_life_lore = (
                db.query(SubStep)
                .filter(
                    SubStep.user_id == user.id,
                    SubStep.is_life_lore == True,
                    SubStep.completed == True,
                    SubStep.completed_at >= start_dt,
                    SubStep.completed_at <= end_dt,
                )
                .all()
            )
            completed_life_lore_list = []
            for s in completed_life_lore:
                completed_life_lore_list.append(f"{html.escape(s.title)} 📖")
            life_lore_str = (
                ", ".join(completed_life_lore_list)
                if completed_life_lore_list
                else "Aucun"
            )

            # Fetch today's redeemed allostasis rewards
            allostasis_purchased = get_allostasis_purchases_on_date(db, user.id, today)
            allostasis_line = ""
            if allostasis_purchased:
                allostasis_items_str = ", ".join(
                    f"{html.escape(r.title)} ✅" for r in allostasis_purchased
                )
                allostasis_line = f"\n🧠 <b>Allostasie :</b> {allostasis_items_str}"

            user_block = (
                f"👤 Aventurier : <b>{html.escape(user.username)}</b> (Niveau {user.level}{lvl_info})\n"
                f"🛡️ <b>Statut :</b> {status_emoji} | Template : {score.template_used.upper()}\n"
                f"🔥 Streak Perfect : <b>{perf_streak_val}j</b> | 💰 Or : <b>{user.gold} Gold</b>\n"
                f"📈 <b>Stats du jour :</b> {stat_progression_str}\n"
                f"✅ <b>Habitudes faites :</b> {habits_str}"
                f"{skipped_line}\n"
                f"🌟 <b>To-Dos faits :</b> {todos_str}\n"
                f"📖 <b>Life Lore :</b> {life_lore_str}\n"
                f"⚠️ <b>No-To-Dos brisés :</b> {failed_notodos_str}"
                f"{allostasis_line}"
            )
            user_blocks.append(user_block)
            individual_reports[user.chat_id] = user_block

        # 6. Construct group or individual messages
        group_chat_id = TELEGRAM_GROUP_ID if TELEGRAM_GROUP_ID else None

        if group_chat_id:
            guild_msg = (
                f"🔔 <b>BILAN DE LA GUILDE — {today.strftime('%d/%m/%Y')}</b> ⚔\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(user_blocks) + "\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💪 Demain est une nouvelle journée d'entraînement. Soyez prêts !"
            )
            await bot.send_message(
                chat_id=group_chat_id, text=guild_msg, parse_mode="HTML"
            )
            print(
                f"Scheduler: Successfully broadcast daily guild recap to group chat ID {group_chat_id}"
            )
        else:
            # Fallback to individual DMs
            for chat_id, report_str in individual_reports.items():
                if not chat_id:
                    continue
                dm_msg = (
                    f"🔔 <b>VOTRE BILAN JOURNALIER — {today.strftime('%d/%m/%Y')}</b> ⚔\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{report_str}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"💪 Demain est une nouvelle journée d'entraînement. Soyez prêts !"
                )
                await bot.send_message(chat_id=chat_id, text=dm_msg, parse_mode="HTML")
                print(f"Scheduler: Successfully sent daily DM recap to {chat_id}")

    except Exception as e:
        print(f"Scheduler: Error publishing daily recap: {e}")
    finally:
        db.close()


def start_scheduler():
    import zoneinfo
    from src.config import TIMEZONE

    tz = zoneinfo.ZoneInfo(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(publish_daily_recap, "cron", hour=21, minute=30)
    scheduler.start()
    print(f"Scheduler: Daily RPG recap scheduled at 21:30 in timezone {TIMEZONE}.")


if __name__ == "__main__":
    asyncio.run(publish_daily_recap())
