import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.database.seed import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase
    print("Initializing SQLite tables and seeding default data...")
    try:
        init_db()
        print("Startup database check complete.")
    except Exception as e:
        print(f"Error initializing database on startup: {e}")
    yield
    # Shutdown phase
    print("Shutting down API server...")

app = FastAPI(
    title="Habit Tracker Bot API",
    description="Backend API and dashboard server for the RPG Accountability Habit Tracker",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local single-user development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root status healthcheck
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "habit-tracker-api"}

# We will register our api routes here (implemented in T017/T018)
from src.api.routes import router as api_router
app.include_router(api_router, prefix="/api/v1")

# Mount static files at root AFTER api routes
from src.api.static_config import configure_static_serving
configure_static_serving(app)
