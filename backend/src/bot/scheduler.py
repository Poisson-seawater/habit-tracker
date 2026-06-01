import os
import datetime
import asyncio
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config import TELEGRAM_BOT_TOKEN
from src.database.session import SessionLocal
from src.database.models import User, Habit, HabitLog, DayTemplate, DailyScore, Streak
from src.services.score_service import calculate_daily_score, update_streaks, ALL_12_STATS, STAT_LABELS

async def publish_daily_recap():
    """
    Triggered at 23:59 daily. Calculates the day's final score for each user, 
    updates streaks, and broadcasts an RPG character-sheet recap to the Telegram group chat.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Scheduler: TELEGRAM_BOT_TOKEN is missing. Recap broadcast aborted.")
        return

    print("Scheduler: Starting 23:59 daily RPG recap publisher...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        for user in users:
            if not user.chat_id:
                print(f"Skipping user {user.username} (no chat_id configured).")
                continue

            today = datetime.date.today()
            
            # 1. Finalize daily score and streaks
            score = calculate_daily_score(db, user_id=user.id, date=today)
            update_streaks(db, user_id=user.id, date=today)

            template = db.query(DayTemplate).filter_by(id=score.active_template_id).first()
            template_name = template.name if template else "Semaine"

            # 2. Get today's logs and split by public / private
            start_dt = datetime.datetime.combine(today, datetime.time.min)
            end_dt = datetime.datetime.combine(today, datetime.time.max)
            logs = db.query(HabitLog).filter(
                HabitLog.user_id == user.id,
                HabitLog.timestamp >= start_dt,
                HabitLog.timestamp <= end_dt
            ).all()

            public_actions = []
            private_completed_count = 0

            for log in logs:
                habit = db.query(Habit).filter_by(id=log.habit_id).first()
                if not habit:
                    continue
                
                if log.log_type in ["done", "log"]:
                    if habit.is_private:
                        private_completed_count += 1
                    else:
                        if log.log_type == "done":
                            public_actions.append(f"- {habit.name} (completé ✅)")
                        else:
                            public_actions.append(f"- {habit.name} ({log.amount}{log.unit} 📊)")
                elif log.log_type == "skip":
                    # Skips are public, show reason
                    if habit.is_private:
                        public_actions.append(f"- Chose secrète 🔒 (skippée ⏭️, raison: {log.reason})")
                    else:
                        public_actions.append(f"- {habit.name} (skippé ⏭️, raison: {log.reason})")

            # 3. Format streaks
            acc_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Acceptable").first()
            perf_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Perfect").first()

            acc_streak_val = acc_streak.current_streak if acc_streak else 0
            perf_streak_val = perf_streak.current_streak if perf_streak else 0

            # Determine daily status string
            if score.status == "Perfect":
                status_emoji = "🏆 PERFECT DAY!"
                status_desc = "Gabriel a transcendé ses limites aujourd'hui !"
            elif score.status == "Acceptable":
                status_emoji = "🟩 JOURNÉE ACCEPTABLE"
                status_desc = "Gabriel a validé ses quêtes indispensables."
            else:
                status_emoji = "🟥 JOURNÉE RATÉE"
                status_desc = "Le boss a triomphé aujourd'hui. On fera mieux demain !"

            # Format stat progression lines for non-zero points earned today
            stat_earned_lines = []
            for stat in ALL_12_STATS:
                val = score.actual_stats.get(stat, 0)
                if val > 0:
                    label = STAT_LABELS.get(stat, stat.capitalize())
                    stat_earned_lines.append(f"  • {label} : +{val} pts")

            stat_progression_block = "\n".join(stat_earned_lines) if stat_earned_lines else "  • Aucune stat obtenue"

            # 4. Construct beautiful public RPG message
            msg = (
                f"🔔 *RAPPORT RPG JOURNALIER — 23:59*\n"
                f"👤 Aventurier : *{user.username}* | Template : *{template_name}*\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"🛡️ *Statut Final :* {status_emoji}\n"
                f"💬 _\"{status_desc}\"_\n\n"
                f"🔥 Streak Acceptable : *{acc_streak_val} jours*\n"
                f"⭐ Streak Perfect : *{perf_streak_val} jours*\n\n"
                f"📈 *Stats obtenues aujourd'hui :*\n"
                f"{stat_progression_block}\n\n"
                f"⚔️ *Quêtes Accomplies :*\n"
            )

            if public_actions:
                msg += "\n".join(public_actions) + "\n"
            else:
                msg += "- Aucune quête publique enregistrée.\n"

            if private_completed_count > 0:
                msg += f"\n🔒 *Actions privées complétées :* {private_completed_count}\n"

            msg += "\n━━━━━━━━━━━━━━━━━━━\n"
            msg += "💪 Demain est une nouvelle journée d'entraînement. Préparez-vous !"

            # 5. Broadcast to Telegram chat
            await bot.send_message(chat_id=user.chat_id, text=msg, parse_mode="Markdown")
            print(f"Scheduler: Successfully broadcast daily recap for {user.username} to chat ID {user.chat_id}")

    except Exception as e:
        print(f"Scheduler: Error publishing daily recap: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Schedule daily recap at 23:59
    scheduler.add_job(publish_daily_recap, 'cron', hour=23, minute=59)
    scheduler.start()
    print("Scheduler: Daily RPG recap scheduled at 23:59.")

if __name__ == "__main__":
    # Test script locally by running the task directly
    asyncio.run(publish_daily_recap())
