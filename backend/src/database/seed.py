import os
from src.database.session import SessionLocal, engine, Base
from src.database.models import User, Habit, DayTemplate
from src.config import TELEGRAM_GROUP_ID

def seed_db():
    # Make sure all tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Seed Default User (Gabriel)
        # Check if user already exists
        user = db.query(User).filter_by(id=1).first()
        if not user:
            # Fallback chat ID if env is empty
            chat_id = TELEGRAM_GROUP_ID if TELEGRAM_GROUP_ID else "12345678"
            user = User(
                id=1,
                username="Gabriel",
                chat_id=str(chat_id)
            )
            db.add(user)
            print("Seeded default user: Gabriel")
        else:
            # Update chat ID if it changed in env
            if TELEGRAM_GROUP_ID and user.chat_id != str(TELEGRAM_GROUP_ID):
                user.chat_id = str(TELEGRAM_GROUP_ID)
                print(f"Updated user Gabriel chat_id to: {TELEGRAM_GROUP_ID}")
        
        # 2. Seed Default Templates
        templates_data = [
            {
                "id": 1,
                "name": "Semaine",
                "acceptable_thresholds": {"discipline": 4, "organisation": 1},
                "perfect_thresholds": {"discipline": 8, "organisation": 3, "creativite": 3, "connaissance": 3}
            },
            {
                "id": 2,
                "name": "Weekend",
                "acceptable_thresholds": {"repos": 4, "sociabilite": 1},
                "perfect_thresholds": {"repos": 8, "sociabilite": 4, "creativite": 3}
            },
            {
                "id": 3,
                "name": "Récupération",
                "acceptable_thresholds": {"repos": 5, "sante_mentale": 2},
                "perfect_thresholds": {"repos": 8, "sante_mentale": 5, "spiritualite": 3}
            },
            {
                "id": 4,
                "name": "Malade",
                "acceptable_thresholds": {"repos": 3},
                "perfect_thresholds": {"repos": 6, "sante_mentale": 3}
            }
        ]
        
        for t_info in templates_data:
            existing = db.query(DayTemplate).filter_by(id=t_info["id"]).first()
            if not existing:
                template = DayTemplate(
                    id=t_info["id"],
                    name=t_info["name"],
                    acceptable_thresholds=t_info["acceptable_thresholds"],
                    perfect_thresholds=t_info["perfect_thresholds"]
                )
                db.add(template)
                print(f"Seeded template: {t_info['name']}")
        
        # 3. Seed Default Habits
        habits_data = [
            {
                "id": 1,
                "name": "routine_matin",
                "description": "Faire son lit, boire de l'eau, méditation rapide et étirements.",
                "type": "binary",
                "frequency": "daily",
                "scheduled_days": "0,1,2,3,4,5,6",
                "reminder_time": "08:00",
                "is_private": False,
                "is_reportable": False,
                "is_mandatory": True,
                "point_rewards": {"discipline": 2, "organisation": 1},
                "daily_cap": None,
                "unit": None,
                "is_active": True
            },
            {
                "id": 2,
                "name": "lecture",
                "description": "Lecture active de livres techniques, de fiction ou de philosophie.",
                "type": "quantitative",
                "frequency": "daily",
                "scheduled_days": "0,1,2,3,4,5,6",
                "reminder_time": "21:00",
                "is_private": False,
                "is_reportable": True,
                "is_mandatory": False,
                "point_rewards": {"creativite": 5, "discipline": 2, "connaissance": 3},
                "daily_cap": 8,  # Cap points per day
                "unit": "min",
                "is_active": True
            },
            {
                "id": 3,
                "name": "ukulele",
                "description": "Pratique instrumentale pour la créativité et la coordination.",
                "type": "binary",
                "frequency": "custom",
                "scheduled_days": "1,3,5",  # Mon, Wed, Fri
                "reminder_time": "18:00",
                "is_private": False,
                "is_reportable": True,
                "is_mandatory": False,
                "point_rewards": {"creativite": 5, "discipline": 2},
                "daily_cap": None,
                "unit": None,
                "is_active": True
            },
            {
                "id": 4,
                "name": "nage",
                "description": "Session piscine ou natation cardio.",
                "type": "quantitative",
                "frequency": "weekly",
                "scheduled_days": "2,4",  # Tue, Thu
                "reminder_time": "12:00",
                "is_private": False,
                "is_reportable": True,
                "is_mandatory": False,
                "point_rewards": {"force": 8, "endurance": 5, "mobilite": 3},
                "daily_cap": 15,
                "unit": "km",
                "is_active": True
            },
            {
                "id": 5,
                "name": "meditation",
                "description": "Méditation pleine conscience (gardé privé).",
                "type": "binary",
                "frequency": "daily",
                "scheduled_days": "0,1,2,3,4,5,6",
                "reminder_time": "07:00",
                "is_private": True,
                "is_reportable": False,
                "is_mandatory": False,
                "point_rewards": {"sante_mentale": 3, "repos": 2},
                "daily_cap": None,
                "unit": None,
                "is_active": True
            }
        ]
        
        for h_info in habits_data:
            existing = db.query(Habit).filter_by(id=h_info["id"]).first()
            if not existing:
                habit = Habit(
                    id=h_info["id"],
                    name=h_info["name"],
                    description=h_info["description"],
                    type=h_info["type"],
                    frequency=h_info["frequency"],
                    scheduled_days=h_info["scheduled_days"],
                    reminder_time=h_info["reminder_time"],
                    is_private=h_info["is_private"],
                    is_reportable=h_info["is_reportable"],
                    is_mandatory=h_info["is_mandatory"],
                    point_rewards=h_info["point_rewards"],
                    daily_cap=h_info["daily_cap"],
                    unit=h_info["unit"],
                    is_active=h_info["is_active"]
                )
                db.add(habit)
                print(f"Seeded habit: {h_info['name']}")
                
        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
