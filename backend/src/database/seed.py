import os
import datetime
from src.database.session import SessionLocal, engine, Base
from src.database.models import (
    User,
    Habit,
    PerfectDayTemplate,
    BiologicalZone,
    Todo,
    Goal,
    SubStep,
    GoalSubStepLink,
    NoTodo,
)

DEFAULT_BIOLOGICAL_ZONES = [
    {
        "zone_name": "Sommeil",
        "zone_type": "sleep",
        "start_time": "23:00",
        "end_time": "07:00",
        "color": None,
        "display_order": 1,
    },
    {
        "zone_name": "Focus Profond Matin",
        "zone_type": "deep_focus",
        "start_time": "08:00",
        "end_time": "12:00",
        "color": None,
        "display_order": 2,
    },
    {
        "zone_name": "Repos / Dejeuner",
        "zone_type": "rest",
        "start_time": "12:00",
        "end_time": "13:00",
        "color": None,
        "display_order": 3,
    },
    {
        "zone_name": "Pic Physique",
        "zone_type": "physical_peak",
        "start_time": "14:00",
        "end_time": "17:00",
        "color": None,
        "display_order": 4,
    },
    {
        "zone_name": "Zone Creative",
        "zone_type": "creative",
        "start_time": "20:00",
        "end_time": "22:00",
        "color": None,
        "display_order": 5,
    },
]


def seed_default_biological_zones(db, user_id=None):
    if user_id is not None:
        if db.query(BiologicalZone).filter_by(user_id=user_id).first() is not None:
            return
        user_ids = [user_id]
    elif db.query(BiologicalZone).first() is not None:
        return
    else:
        user_ids = [row[0] for row in db.query(User.id).all()]

    for user_id in user_ids:
        for zone in DEFAULT_BIOLOGICAL_ZONES:
            db.add(BiologicalZone(user_id=user_id, **zone))


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
                "gold": 0,
            }
        ]
        for u_info in users_data:
            user = User(
                id=u_info["id"],
                username=u_info["username"],
                chat_id=str(u_info["chat_id"]) if u_info["chat_id"] else None,
                xp=u_info["xp"],
                level=u_info["level"],
                gold=u_info["gold"],
            )
            db.add(user)
        db.flush()  # Make sure users are created to get foreign keys

        # 2. Seed Default Templates per User
        for user_id in [1]:
            templates_data = [
                {
                    "template_name": "rest",
                    "focus_hours": 2.0,
                    "min_rest_hours": 10.0,
                    "ceilings_json": {"musculaire": 1.0, "cerveau": 1.0, "emotionnel_social": 1.0, "creatif_divergent": 1.0, "total": 4.0},
                    "thresholds_json": None,
                },
                {
                    "template_name": "regular",
                    "focus_hours": 6.0,
                    "min_rest_hours": 8.0,
                    "ceilings_json": {"musculaire": 2.0, "cerveau": 2.0, "emotionnel_social": 2.0, "creatif_divergent": 2.0, "total": 8.0},
                    "thresholds_json": None,
                },
                {
                    "template_name": "hustle",
                    "focus_hours": 9.0,
                    "min_rest_hours": 7.0,
                    "ceilings_json": {"musculaire": 4.0, "cerveau": 4.0, "emotionnel_social": 4.0, "creatif_divergent": 4.0, "total": 10.0},
                    "thresholds_json": None,
                },
            ]
            for t_info in templates_data:
                template = PerfectDayTemplate(
                    user_id=user_id,
                    template_name=t_info["template_name"],
                    focus_hours=t_info["focus_hours"],
                    min_rest_hours=t_info["min_rest_hours"],
                    ceilings_json=t_info["ceilings_json"],
                    thresholds_json=t_info["thresholds_json"],
                )
                db.add(template)

        seed_default_biological_zones(db)

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
                "is_active": True,
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
                "is_active": True,
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
                "is_active": True,
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
                "is_active": True,
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
                "is_active": True,
            },
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
                is_active=h_info["is_active"],
            )
            db.add(habit)

        # 4. Seed Goals (Objectifs Long Terme) for Gabriel (User 1)
        goals_data = [
            {
                "id": 1,
                "user_id": 1,
                "title": "Devenir Millionnaire",
                "description": "Atteindre la liberté financière absolue",
            },
            {
                "id": 2,
                "user_id": 1,
                "title": "Faire le tour du monde",
                "description": "Explorer toutes les merveilles de la Terre",
            },
            {
                "id": 3,
                "user_id": 1,
                "title": "Avoir des enfants",
                "description": "Fonder une famille aimante et stable",
            },
        ]
        for g_info in goals_data:
            goal = Goal(
                id=g_info["id"],
                user_id=g_info["user_id"],
                title=g_info["title"],
                description=g_info["description"],
            )
            db.add(goal)
        db.flush()

        # 5. Seed SubSteps for Gabriel (User 1)
        substeps_data = [
            {
                "id": 1,
                "user_id": 1,
                "title": "Avoir 500k en actif",
                "gold_reward": 500,
                "stats_json": ["finance"],
                "description": "Accumuler 500k d'actifs nets",
            },
            {
                "id": 2,
                "user_id": 1,
                "title": "Acheter un immeuble locatif",
                "gold_reward": 300,
                "stats_json": ["finance", "discipline"],
                "description": "Trouver et acquérir un premier bien de rendement",
            },
            {
                "id": 3,
                "user_id": 1,
                "title": "Trouver un bon avocat",
                "gold_reward": 100,
                "stats_json": ["discipline"],
                "description": "Réseauter pour s'entourer d'un expert juridique",
            },
            {
                "id": 4,
                "user_id": 1,
                "title": "Avoir de l'argent",
                "gold_reward": 150,
                "stats_json": ["finance"],
                "description": "Constituer une épargne de voyage",
            },
            {
                "id": 5,
                "user_id": 1,
                "title": "Avoir un passeport",
                "gold_reward": 50,
                "stats_json": ["discipline"],
                "description": "Faire les démarches à la mairie",
            },
            {
                "id": 6,
                "user_id": 1,
                "title": "Créer une feuille de budget",
                "gold_reward": 75,
                "stats_json": ["finance", "discipline"],
                "description": "Suivre ses dépenses mensuelles",
            },
            {
                "id": 7,
                "user_id": 1,
                "title": "Achat assurance vie",
                "gold_reward": 100,
                "stats_json": ["finance"],
                "description": "Sécuriser un contrat d'assurance vie",
            },
            {
                "id": 8,
                "user_id": 1,
                "title": "Avoir une entrée d'argent stable",
                "gold_reward": 200,
                "stats_json": ["finance"],
                "description": "Garantir un flux financier mensuel régulier",
            },
            {
                "id": 9,
                "user_id": 1,
                "title": "Trouver une femme",
                "gold_reward": 150,
                "stats_json": ["social"],
                "description": "Rencontrer sa partenaire de vie idéale",
            },
            {
                "id": 10,
                "user_id": 1,
                "title": "La marier",
                "gold_reward": 250,
                "stats_json": ["social", "sante"],
                "description": "Célébrer notre union",
            },
        ]
        for s_info in substeps_data:
            substep = SubStep(
                id=s_info["id"],
                user_id=s_info["user_id"],
                title=s_info["title"],
                description=s_info["description"],
                gold_reward=s_info["gold_reward"],
                stats_json=s_info["stats_json"],
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
            {"goal_id": 3, "substep_id": 10},
        ]
        for l_info in links_data:
            link = GoalSubStepLink(
                goal_id=l_info["goal_id"], substep_id=l_info["substep_id"]
            )
            db.add(link)

        # 8. Seed Todos (Primes)
        todos_data = [
            {
                "user_id": 1,
                "title": "⚔️ Dompter le Dragon de Fer (Séance Jambes)",
                "stat_reward_1": "forme_physique",
                "points_reward_1": 16,
                "xp_reward": 20,
            },
            {
                "user_id": 1,
                "title": "📚 Décoder les Runes (Lire 20 pages de doc)",
                "stat_reward_1": "apprendre",
                "points_reward_1": 3,
                "xp_reward": 10,
            },
        ]
        for t_info in todos_data:
            todo = Todo(
                user_id=t_info["user_id"],
                title=t_info["title"],
                stat_reward_1=t_info["stat_reward_1"],
                points_reward_1=t_info["points_reward_1"],
                xp_reward=t_info["xp_reward"],
            )
            db.add(todo)

        # 9. Seed NoTodos
        gabriel_notodos = [
            "Scroller sur les réseaux sociaux le matin",
            "Repousser le réveil (Snooze)",
            "Manger de la junk food en semaine",
            "Se plaindre sans chercher de solution",
            "Boire de l'alcool en semaine",
            "Regarder la TV avant de dormir",
        ]

        notodos_data = []
        for t in gabriel_notodos:
            notodos_data.append({"user_id": 1, "title": t})
        for n_info in notodos_data:
            notodo = NoTodo(user_id=n_info["user_id"], title=n_info["title"])
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

    # Run lightweight migrations for existing databases
    _run_migrations()

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


def _run_migrations():
    """
    Run idempotent ALTER-based migrations for schema changes that
    create_all() cannot handle on existing tables.
    """
    from sqlalchemy import text, inspect

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        # v12: Add execution_order to goal_substep_links
        if "goal_substep_links" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("goal_substep_links")]
            if "execution_order" not in columns:
                print(
                    "Running migration v12: adding execution_order to goal_substep_links..."
                )
                db.execute(
                    text(
                        "ALTER TABLE goal_substep_links ADD COLUMN execution_order INTEGER DEFAULT 1"
                    )
                )
                db.execute(
                    text(
                        "UPDATE goal_substep_links SET execution_order = "
                        "(SELECT execution_order FROM substeps WHERE substeps.id = goal_substep_links.substep_id)"
                    )
                )
                db.commit()
                print("Migration v12 applied successfully.")

        # v13: Add is_life_lore to substeps
        if "substeps" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("substeps")]
            if "is_life_lore" not in columns:
                print("Running migration v13: adding is_life_lore to substeps...")
                db.execute(
                    text(
                        "ALTER TABLE substeps ADD COLUMN is_life_lore BOOLEAN DEFAULT 0"
                    )
                )
                db.commit()
                print("Migration v13 applied successfully.")

        # v14: Add do_date and due_date to todos
        if "todos" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("todos")]
            if "do_date" not in columns:
                print("Running migration v14: adding do_date and due_date to todos...")
                db.execute(text("ALTER TABLE todos ADD COLUMN do_date DATE"))
                db.execute(text("ALTER TABLE todos ADD COLUMN due_date DATE"))
                db.commit()
                print("Migration v14 applied successfully.")

        # v15: Add pinned_goals to users
        if "users" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("users")]
            if "pinned_goals" not in columns:
                print("Running migration v15: adding pinned_goals to users...")
                db.execute(
                    text("ALTER TABLE users ADD COLUMN pinned_goals TEXT DEFAULT '[]'")
                )
                db.commit()
                print("Migration v15 applied successfully.")

        # v16: Add effort budget columns to perfect_day_templates, habits, substeps
        if "perfect_day_templates" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("perfect_day_templates")]
            if "focus_hours" not in columns:
                print("Running migration v16: adding focus_hours, ceilings_json, min_rest_hours to perfect_day_templates...")
                db.execute(text("ALTER TABLE perfect_day_templates ADD COLUMN focus_hours REAL DEFAULT 6.0"))
                db.execute(text("ALTER TABLE perfect_day_templates ADD COLUMN ceilings_json TEXT"))
                db.execute(text("ALTER TABLE perfect_day_templates ADD COLUMN min_rest_hours REAL DEFAULT 8.0"))
                db.commit()
                print("Migration v16 (perfect_day_templates) applied successfully.")
            
            # v17: Add agenda_json to perfect_day_templates
            if "agenda_json" not in columns:
                print("Running migration v17: adding agenda_json to perfect_day_templates...")
                db.execute(text("ALTER TABLE perfect_day_templates ADD COLUMN agenda_json TEXT"))
                db.commit()
                print("Migration v17 (agenda_json) applied successfully.")

        if "habits" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("habits")]
            if "effort_type" not in columns:
                print("Running migration v16: adding effort_type, effort_duration to habits...")
                db.execute(text("ALTER TABLE habits ADD COLUMN effort_type TEXT"))
                db.execute(text("ALTER TABLE habits ADD COLUMN effort_duration REAL DEFAULT 1.0"))
                db.commit()
                print("Migration v16 (habits) applied successfully.")

        if "substeps" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("substeps")]
            if "effort_type" not in columns:
                print("Running migration v16: adding effort_type, effort_duration to substeps...")
                db.execute(text("ALTER TABLE substeps ADD COLUMN effort_type TEXT"))
                db.execute(text("ALTER TABLE substeps ADD COLUMN effort_duration REAL DEFAULT 1.0"))
                db.commit()
                print("Migration v16 (substeps) applied successfully.")

        # v18: Add biological_zones table and default biological day
        if "biological_zones" not in inspector.get_table_names():
            print("Running migration v18: creating biological_zones table...")
            db.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS biological_zones (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        zone_name VARCHAR NOT NULL,
                        zone_type VARCHAR NOT NULL,
                        start_time VARCHAR NOT NULL,
                        end_time VARCHAR NOT NULL,
                        color VARCHAR,
                        display_order INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            db.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_biological_zones_user_id "
                    "ON biological_zones (user_id)"
                )
            )
            db.commit()
            print("Migration v18 (biological_zones table) applied successfully.")

        if "users" in inspector.get_table_names():
            seed_default_biological_zones(db)
            db.commit()

        # Check if rest, regular, hustle templates exist for each user
        # If not, create them
        if "perfect_day_templates" in inspector.get_table_names() and "users" in inspector.get_table_names():
            # Get all user IDs
            user_ids = [r[0] for r in db.execute(text("SELECT id FROM users")).fetchall()]
            
            # Default agendas
            default_rest_agenda = '[{"id": 1, "title": "Sommeil / Repos", "start": "00:00", "end": "08:00", "category": "sleep"}, {"id": 2, "title": "Méditation / Relaxation", "start": "09:00", "end": "10:00", "category": "relax"}, {"id": 3, "title": "Marche & Étirements", "start": "12:00", "end": "13:00", "category": "routine"}, {"id": 4, "title": "Lecture & Repos mental", "start": "14:00", "end": "17:00", "category": "relax"}, {"id": 5, "title": "Sommeil", "start": "21:30", "end": "24:00", "category": "sleep"}]'
            default_regular_agenda = '[{"id": 1, "title": "Sommeil / Récupération", "start": "00:00", "end": "07:00", "category": "sleep"}, {"id": 2, "title": "Routine matinale & Cardio", "start": "07:00", "end": "08:00", "category": "routine"}, {"id": 3, "title": "Focus Deep Work (Projet principal)", "start": "08:30", "end": "12:00", "category": "focus"}, {"id": 4, "title": "Gestion administrative / Travail", "start": "13:00", "end": "15:00", "category": "focus"}, {"id": 5, "title": "Entraînement physique", "start": "17:30", "end": "19:00", "category": "routine"}, {"id": 6, "title": "Détente / Social", "start": "19:00", "end": "22:00", "category": "relax"}, {"id": 7, "title": "Sommeil / Couché", "start": "22:00", "end": "24:00", "category": "sleep"}]'
            default_hustle_agenda = '[{"id": 1, "title": "Sommeil court", "start": "00:00", "end": "06:00", "category": "sleep"}, {"id": 2, "title": "Cardio & Routine active", "start": "06:00", "end": "07:00", "category": "routine"}, {"id": 3, "title": "Deep Work", "start": "07:30", "end": "12:00", "category": "focus"}, {"id": 4, "title": "Focus Code / Projet", "start": "13:00", "end": "18:00", "category": "focus"}, {"id": 5, "title": "Musculation / Sport", "start": "18:30", "end": "20:00", "category": "routine"}, {"id": 6, "title": "Veille / Apprentissage", "start": "20:00", "end": "22:30", "category": "focus"}, {"id": 7, "title": "Récupération & Couché", "start": "22:30", "end": "24:00", "category": "sleep"}]'

            for uid in user_ids:
                existing_templates = [r[0] for r in db.execute(
                    text("SELECT template_name FROM perfect_day_templates WHERE user_id = :uid"),
                    {"uid": uid}
                ).fetchall()]
                
                # Check rest
                if "rest" not in existing_templates:
                    db.execute(
                        text("INSERT INTO perfect_day_templates (user_id, template_name, focus_hours, min_rest_hours, ceilings_json, thresholds_json, agenda_json) VALUES (:uid, 'rest', 2.0, 10.0, :ceilings, 'null', :agenda)"),
                        {"uid": uid, "ceilings": '{"musculaire": 1.0, "cerveau": 1.0, "emotionnel_social": 1.0, "creatif_divergent": 1.0, "total": 4.0}', "agenda": default_rest_agenda}
                    )
                else:
                    db.execute(
                        text("UPDATE perfect_day_templates SET agenda_json = :agenda WHERE user_id = :uid AND template_name = 'rest' AND (agenda_json IS NULL OR agenda_json = '[]' OR agenda_json = '')"),
                        {"uid": uid, "agenda": default_rest_agenda}
                    )
                
                # Check regular
                if "regular" not in existing_templates:
                    db.execute(
                        text("INSERT INTO perfect_day_templates (user_id, template_name, focus_hours, min_rest_hours, ceilings_json, thresholds_json, agenda_json) VALUES (:uid, 'regular', 6.0, 8.0, :ceilings, 'null', :agenda)"),
                        {"uid": uid, "ceilings": '{"musculaire": 2.0, "cerveau": 2.0, "emotionnel_social": 2.0, "creatif_divergent": 2.0, "total": 8.0}', "agenda": default_regular_agenda}
                    )
                else:
                    db.execute(
                        text("UPDATE perfect_day_templates SET agenda_json = :agenda WHERE user_id = :uid AND template_name = 'regular' AND (agenda_json IS NULL OR agenda_json = '[]' OR agenda_json = '')"),
                        {"uid": uid, "agenda": default_regular_agenda}
                    )
                
                # Check hustle
                if "hustle" not in existing_templates:
                    db.execute(
                        text("INSERT INTO perfect_day_templates (user_id, template_name, focus_hours, min_rest_hours, ceilings_json, thresholds_json, agenda_json) VALUES (:uid, 'hustle', 9.0, 7.0, :ceilings, 'null', :agenda)"),
                        {"uid": uid, "ceilings": '{"musculaire": 4.0, "cerveau": 4.0, "emotionnel_social": 4.0, "creatif_divergent": 4.0, "total": 10.0}', "agenda": default_hustle_agenda}
                    )
                else:
                    db.execute(
                        text("UPDATE perfect_day_templates SET agenda_json = :agenda WHERE user_id = :uid AND template_name = 'hustle' AND (agenda_json IS NULL OR agenda_json = '[]' OR agenda_json = '')"),
                        {"uid": uid, "agenda": default_hustle_agenda}
                    )
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Migration error (non-fatal): {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
