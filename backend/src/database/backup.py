import os
import shutil
import datetime
import glob

def rotate_backups(db_path: str = "/data/habit_tracker.db", backup_dir: str = "/data/backups", max_backups: int = 5):
    """
    Creates a timestamped backup of the SQLite database file and rotates older backups, 
    preserving only the latest `max_backups` copies to prevent disk saturation.
    """
    # Fallback to local paths if in local dev
    if not os.path.exists(os.path.dirname(db_path)):
        # If /data does not exist, use relative workspace path ./data
        db_path = "./data/habit_tracker.db"
        backup_dir = "./data/backups"

    if not os.path.exists(db_path):
        print(f"Backup Error: Source database not found at '{db_path}'.")
        return False

    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"habit_tracker_backup_{timestamp}.db"
    dest_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(db_path, dest_path)
        print(f"Backup Success: Created database copy at '{dest_path}'")
    except Exception as e:
        print(f"Backup Error: Failed to copy database file: {e}")
        return False

    # Perform rotation (keep only latest max_backups)
    backup_pattern = os.path.join(backup_dir, "habit_tracker_backup_*.db")
    existing_backups = glob.glob(backup_pattern)
    
    # Sort backups by modification time (oldest first)
    existing_backups.sort(key=os.path.getmtime)

    if len(existing_backups) > max_backups:
        to_delete = existing_backups[:-max_backups]
        for old_backup in to_delete:
            try:
                os.remove(old_backup)
                print(f"Backup Rotation: Deleted obsolete backup file '{old_backup}'")
            except Exception as e:
                print(f"Backup Rotation Error: Failed to remove old file '{old_backup}': {e}")

    return True

if __name__ == "__main__":
    rotate_backups()
