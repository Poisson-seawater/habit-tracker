import os
import pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def configure_static_serving(app: FastAPI):
    """
    Finds and mounts the frontend static directory to the FastAPI app at root '/'
    after all REST routes have been registered.
    """
    # In Docker container, the static assets are copied to /app/frontend
    frontend_dir = "/app/frontend"
    
    if not os.path.exists(frontend_dir):
        # Locally, they are situated in habit-tracker/frontend
        frontend_dir = str(pathlib.Path(__file__).resolve().parent.parent.parent / "frontend")

    if os.path.exists(frontend_dir):
        # Make sure directory is not empty
        try:
            files = os.listdir(frontend_dir)
            if files:
                app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
                print(f"Static Serving: Successfully mounted frontend static assets from '{frontend_dir}'")
                return
        except Exception as e:
            print(f"Static Serving Error: Failed to read directory: {e}")
            
    print(f"Static Serving Warning: Frontend static files not found at '{frontend_dir}'. Localhost dashboard serving will be unavailable.")
