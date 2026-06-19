import os
import pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def configure_static_serving(app: FastAPI):
    """
    Finds and mounts the frontend static directory to the FastAPI app at root '/'
    after all REST routes have been registered. Also mounts the documentation
    wiki at '/docs'.
    """
    # Mount docs/wiki at /docs
    docs_dir = "/app/docs/wiki"

    if not os.path.exists(docs_dir):
        current_file = pathlib.Path(__file__).resolve()
        docs_candidates = [
            current_file.parent.parent.parent / "docs" / "wiki",
            current_file.parent.parent.parent.parent / "docs" / "wiki",
        ]
        for candidate in docs_candidates:
            if candidate.exists():
                docs_dir = str(candidate)
                break

    if os.path.exists(docs_dir):
        try:
            files = os.listdir(docs_dir)
            if files:
                app.mount(
                    "/docs", StaticFiles(directory=docs_dir, html=True), name="docs"
                )
                print(
                    f"Static Serving: Successfully mounted docs from "
                    f"'{docs_dir}' at '/docs'"
                )
        except Exception as e:
            print(f"Static Serving Error: Failed to read docs directory: {e}")

    # In Docker container, the static assets are copied to /app/frontend
    frontend_dir = "/app/frontend"

    if not os.path.exists(frontend_dir):
        current_file = pathlib.Path(__file__).resolve()
        frontend_candidates = [
            current_file.parent.parent.parent / "frontend",
            current_file.parent.parent.parent.parent / "frontend",
        ]
        for candidate in frontend_candidates:
            if candidate.exists():
                frontend_dir = str(candidate)
                break

    if os.path.exists(frontend_dir):
        # Make sure directory is not empty
        try:
            files = os.listdir(frontend_dir)
            if files:
                app.mount(
                    "/", StaticFiles(directory=frontend_dir, html=True), name="frontend"
                )
                print(
                    "Static Serving: Successfully mounted frontend static assets "
                    f"from '{frontend_dir}'"
                )
                return
        except Exception as e:
            print(f"Static Serving Error: Failed to read directory: {e}")

    print(
        f"Static Serving Warning: Frontend static files not found at "
        f"'{frontend_dir}'. Localhost dashboard serving will be unavailable."
    )
