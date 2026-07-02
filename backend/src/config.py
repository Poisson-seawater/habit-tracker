import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Env settings
ENV = os.getenv("ENV", "development")

# API Configuration
API_PORT = int(os.getenv("API_PORT", 5000))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID", "")

# Database Configuration
# In docker container, we want /data/habit_tracker.db
# Locally, we want backend/data/habit_tracker.db or project_root/data/habit_tracker.db
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Check if /data is writeable/exists
    if os.path.exists("/data"):
        DATABASE_URL = "sqlite:////data/habit_tracker.db"
    else:
        # Create a local data directory inside backend/ if it doesn't exist
        local_data_dir = BASE_DIR / "data"
        local_data_dir.mkdir(parents=True, exist_ok=True)
        DATABASE_URL = f"sqlite:///{local_data_dir}/habit_tracker.db"

# Ensure SQLite URL is formatted correctly for SQLAlchemy (sqlite:///...)
if DATABASE_URL.startswith("sqlite://") and not DATABASE_URL.startswith("sqlite:///"):
    # Fix potential double/triple slash issues from env
    db_path = DATABASE_URL.replace("sqlite://", "").lstrip("/")
    # If absolute path (starts with / after lstrip), we need 4 slashes total: sqlite:////...
    if db_path.startswith("/"):
        DATABASE_URL = f"sqlite:////{db_path}"
    else:
        DATABASE_URL = f"sqlite:///{db_path}"

# Timezone Configuration
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

# Google Calendar & Tasks Integration Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:5000/api/v1/auth/google/callback"
)
GOOGLE_ENCRYPTION_KEY = os.getenv("GOOGLE_ENCRYPTION_KEY", "default-habit-tracker-key-12345")

# Web/API Authentication Configuration
AUTH_BOOTSTRAP_CODE = os.getenv("AUTH_BOOTSTRAP_CODE", "")
HABIT_API_TOKEN = os.getenv("HABIT_API_TOKEN", "")
AUTH_SESSION_DAYS = int(os.getenv("AUTH_SESSION_DAYS", "30"))
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
}
