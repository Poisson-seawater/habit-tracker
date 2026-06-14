import os
import datetime
from src.database.session import SessionLocal, engine, Base
from src.database.models import User, Habit, PerfectDayTemplate, Todo, Goal, SubStep, GoalSubStepLink, NoTodo

def seed_db():
    # Drop all tables first to get a clean, updated schema for V2
    Base.metadata.drop_all(bind=engine)
    # Re-create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Seed Users
        users_data = [
            {
                "id": 1,
                "username": "Gabriel",
                "chat_id": os.getenv("TELEGRAM_DEFAULT_USER_ID"),
                "xp": 0,
                "level": 1,
                "gold": 0
            }
        ]
        for u_info in users_data:
            user = User(
                id=u_info["id"],
                username=u_info["username"],
                chat_id=str(u_info["chat_id"]) if u_info["chat_id"] else None,
                xp=u_info["xp"],
                level=u_info["level"],
                gold=u_info["gold"]
            )
            db.add(user)
        db.flush()  # Make sure users are created to get foreign keys

        # 2. Seed Default Templates per User
        for user_id in [1]:
            templates_data = [
                {
                    "template_name": "week",
                    "thresholds_json": {"discipline": 11, "apprendre": 6}
                },
                {
                    "template_name": "weekend",
                    "thresholds_json": {"sante": 8, "social": 4, "apprendre": 3}
                },
                {
                    "template_name": "recup",
                    "thresholds_json": {"sante": 8}
                },
                {
                    "template_name": "malade",
                    "thresholds_json": {"sante": 3}
                }
            ]
            for t_info in templates_data:
                template = PerfectDayTemplate(
                    user_id=user_id,
                    template_name=t_info["template_name"],
                    thresholds_json=t_info["thresholds_json"]
                )
                db.add(template)

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
                "point_rewards": {"discipline": 3},
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
                "point_rewards": {"apprendre": 8, "discipline": 2},
                "daily_cap": 8,
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
                "point_rewards": {"apprendre": 5, "discipline": 2},
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
                "point_rewards": {"forme_physique": 16},
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
                "point_rewards": {"sante": 5},
                "daily_cap": None,
                "unit": None,
                "is_active": True
            }
        ]
        for h_info in habits_data:
            habit = Habit(
                id=h_info["id"],
                user_id=1,
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

        # 4. Seed Goals (Objectifs Long Terme) for Gabriel (User 1)
        goals_data = [
            {"id": 1, "user_id": 1, "title": "Devenir Millionnaire", "description": "Atteindre la liberté financière absolue"},
            {"id": 2, "user_id": 1, "title": "Faire le tour du monde", "description": "Explorer toutes les merveilles de la Terre"},
            {"id": 3, "user_id": 1, "title": "Avoir des enfants", "description": "Fonder une famille aimante et stable"}
        ]
        for g_info in goals_data:
            goal = Goal(
                id=g_info["id"],
                user_id=g_info["user_id"],
                title=g_info["title"],
                description=g_info["description"]
            )
            db.add(goal)
        db.flush()

        # 5. Seed SubSteps for Gabriel (User 1)
        substeps_data = [
            {"id": 1, "user_id": 1, "title": "Avoir 500k en actif", "gold_reward": 500, "stats_json": ["finance"], "description": "Accumuler 500k d'actifs nets"},
            {"id": 2, "user_id": 1, "title": "Acheter un immeuble locatif", "gold_reward": 300, "stats_json": ["finance", "discipline"], "description": "Trouver et acquérir un premier bien de rendement"},
            {"id": 3, "user_id": 1, "title": "Trouver un bon avocat", "gold_reward": 100, "stats_json": ["discipline"], "description": "Réseauter pour s'entourer d'un expert juridique"},
            {"id": 4, "user_id": 1, "title": "Avoir de l'argent", "gold_reward": 150, "stats_json": ["finance"], "description": "Constituer une épargne de voyage"},
            {"id": 5, "user_id": 1, "title": "Avoir un passeport", "gold_reward": 50, "stats_json": ["discipline"], "description": "Faire les démarches à la mairie"},
            {"id": 6, "user_id": 1, "title": "Créer une feuille de budget", "gold_reward": 75, "stats_json": ["finance", "discipline"], "description": "Suivre ses dépenses mensuelles"},
            {"id": 7, "user_id": 1, "title": "Achat assurance vie", "gold_reward": 100, "stats_json": ["finance"], "description": "Sécuriser un contrat d'assurance vie"},
            {"id": 8, "user_id": 1, "title": "Avoir une entrée d'argent stable", "gold_reward": 200, "stats_json": ["finance"], "description": "Garantir un flux financier mensuel régulier"},
            {"id": 9, "user_id": 1, "title": "Trouver une femme", "gold_reward": 150, "stats_json": ["social"], "description": "Rencontrer sa partenaire de vie idéale"},
            {"id": 10, "user_id": 1, "title": "La marier", "gold_reward": 250, "stats_json": ["social", "sante"], "description": "Célébrer notre union"}
        ]
        for s_info in substeps_data:
            substep = SubStep(
                id=s_info["id"],
                user_id=s_info["user_id"],
                title=s_info["title"],
                description=s_info["description"],
                gold_reward=s_info["gold_reward"],
                stats_json=s_info["stats_json"]
            )
            db.add(substep)
        db.flush()

        # 6. Seed Goal-SubStep Links
        links_data = [
            # Devenir Millionnaire -> 500k, Immeuble, Avocat
            {"goal_id": 1, "substep_id": 1},
            {"goal_id": 1, "substep_id": 2},
            {"goal_id": 1, "substep_id": 3},
            # Faire le tour du monde -> Avoir de l'argent, Passeport, Budget, Assurance vie
            {"goal_id": 2, "substep_id": 4},
            {"goal_id": 2, "substep_id": 5},
            {"goal_id": 2, "substep_id": 6},
            {"goal_id": 2, "substep_id": 7},
            # Avoir des enfants -> Argent stable, Trouver femme, Marier
            {"goal_id": 3, "substep_id": 8},
            {"goal_id": 3, "substep_id": 9},
            {"goal_id": 3, "substep_id": 10}
        ]
        for l_info in links_data:
            link = GoalSubStepLink(
                goal_id=l_info["goal_id"],
                substep_id=l_info["substep_id"]
            )
            db.add(link)

        # 8. Seed Todos (Primes)
        todos_data = [
            {
                "user_id": 1,
                "title": "⚔️ Dompter le Dragon de Fer (Séance Jambes)",
                "stat_reward_1": "forme_physique",
                "points_reward_1": 16,
                "xp_reward": 20
            },
            {
                "user_id": 1,
                "title": "📚 Décoder les Runes (Lire 20 pages de doc)",
                "stat_reward_1": "apprendre",
                "points_reward_1": 3,
                "xp_reward": 10
            },
        ]
        for t_info in todos_data:
            todo = Todo(
                user_id=t_info["user_id"],
                title=t_info["title"],
                stat_reward_1=t_info["stat_reward_1"],
                points_reward_1=t_info["points_reward_1"],
                xp_reward=t_info["xp_reward"]
            )
            db.add(todo)
            
        # 9. Seed NoTodos
        gabriel_notodos = [
            "Scroller sur les réseaux sociaux le matin",
            "Repousser le réveil (Snooze)",
            "Manger de la junk food en semaine",
            "Se plaindre sans chercher de solution",
            "Boire de l'alcool en semaine",
            "Regarder la TV avant de dormir"
        ]
        
        notodos_data = []
        for t in gabriel_notodos:
            notodos_data.append({"user_id": 1, "title": t})
        for n_info in notodos_data:
            notodo = NoTodo(
                user_id=n_info["user_id"],
                title=n_info["title"]
            )
            db.add(notodo)
                
        db.commit()
        print("Database V2 seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database V2: {e}")
        raise e
    finally:
        db.close()

def init_db():
    """
    Idempotent startup initializer. Creates any missing tables and seeds the
    default data ONLY when the database is empty. Never drops existing data,
    so user accounts, logs, points and streaks survive container restarts.
    Use seed_db() directly (manually) for a full destructive reset.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        already_seeded = db.query(User).first() is not None
    finally:
        db.close()

    if already_seeded:
        print("Database already initialized — skipping seed (data preserved).")
        return

    print("Empty database detected — seeding default data...")
    seed_db()


if __name__ == "__main__":
    seed_db()
