import sys
import os

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.database.session import SessionLocal
from src.database.models import Habit, PerfectDayTemplate, DailyScore, Todo, SubStep

MAPPING = {
    "force": "forme_physique",
    "endurance": "forme_physique",
    "mobilite": "forme_physique",
    "discipline": "discipline",
    "creativite": "apprendre",
    "connaissance": "apprendre",
    "sociabilite": "social",
    "sante_mentale": "sante",
    "finance": "finance",
    "organisation": "discipline",
    "spiritualite": "sante",
    "repos": "sante"
}

def map_stat(stat):
    if not stat:
        return stat
    return MAPPING.get(stat.lower(), stat)

def map_dict(d):
    if not d:
        return d
    new_d = {}
    for k, v in d.items():
        new_k = map_stat(k)
        new_d[new_k] = new_d.get(new_k, 0) + v
    return new_d

def map_list(lst):
    if not lst:
        return lst
    new_lst = []
    for item in lst:
        new_item = map_stat(item)
        if new_item not in new_lst:
            new_lst.append(new_item)
    return new_lst

def run_migration():
    db = SessionLocal()
    try:
        print("Starting stats migration from 12 to 6 stats...")

        # 1. Migrate Habits
        habits = db.query(Habit).all()
        print(f"Migrating {len(habits)} Habits...")
        for habit in habits:
            if habit.point_rewards:
                habit.point_rewards = map_dict(habit.point_rewards)
        
        # 2. Migrate Perfect Day Templates
        templates = db.query(PerfectDayTemplate).all()
        print(f"Migrating {len(templates)} Perfect Day Templates...")
        for temp in templates:
            if temp.thresholds_json:
                temp.thresholds_json = map_dict(temp.thresholds_json)

        # 3. Migrate Daily Scores
        scores = db.query(DailyScore).all()
        print(f"Migrating {len(scores)} Daily Scores...")
        for score in scores:
            if score.actual_stats:
                score.actual_stats = map_dict(score.actual_stats)

        # 4. Migrate SubSteps
        substeps = db.query(SubStep).all()
        print(f"Migrating {len(substeps)} SubSteps...")
        for ss in substeps:
            if ss.stats_json:
                ss.stats_json = map_list(ss.stats_json)

        # 5. Migrate Todos
        todos = db.query(Todo).all()
        print(f"Migrating {len(todos)} Todos...")
        for todo in todos:
            if todo.stat_reward_1:
                todo.stat_reward_1 = map_stat(todo.stat_reward_1)
            if todo.stat_reward_2:
                todo.stat_reward_2 = map_stat(todo.stat_reward_2)

        db.commit()
        print("Database migration completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
