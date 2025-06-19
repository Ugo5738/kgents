# auth_service/debug_routes.py
import os
import sys

from dotenv import load_dotenv

# --- ARCHITECTURAL FIX: Explicitly load the correct .env file ---
# Determine the path to the .env file within the auth_service directory
# This makes the script runnable from any location.
auth_service_dir = os.path.dirname(__file__)
env_path = os.path.join(auth_service_dir, ".env")

# Load the environment variables from the file.
# This must happen *before* we import anything from our application that uses settings.
if os.path.exists(env_path):
    print(f"--- Loading environment from: {env_path} ---")
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"--- WARNING: .env file not found at {env_path}. Script may fail. ---")
# ----------------------------------------------------------------

# Add the 'src' directory to the Python path to allow imports from auth_service
sys.path.insert(0, os.path.abspath(os.path.join(auth_service_dir, "src")))

from fastapi.routing import APIRoute

from auth_service.main import app


def list_routes():
    """
    Lists all registered routes in the FastAPI application, including their
    path, name, and methods.
    """
    print("--- Registered Application Routes ---")
    print(f"{'Path':<50} {'Name':<30} {'Methods'}")
    print("-" * 100)

    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "name": route.name,
                    "methods": sorted(list(route.methods)),
                }
            )

    # Sort routes by path for readability
    sorted_routes = sorted(routes, key=lambda x: x["path"])

    for route in sorted_routes:
        print(f"{route['path']:<50} {route['name']:<30} {route['methods']}")

    print("-" * 100)


if __name__ == "__main__":
    list_routes()
