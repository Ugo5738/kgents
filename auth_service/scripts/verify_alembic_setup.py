import os
import sys
from pathlib import Path

print("--- Starting Alembic Setup Verification ---")

# --- Step 1: Replicate the PYTHONPATH setup from alembic/env.py ---
# This is the most critical part. We are making sure this script can find
# your project's source code in the same way alembic will.

try:
    service_dir = Path(__file__).parent.parent.absolute()
    project_root = service_dir.parent

    print(f"Service Directory: {service_dir}")
    print(f"Project Root: {project_root}")

    # Add the service's own source code to the path
    src_path = str(service_dir / "src")
    sys.path.insert(0, src_path)
    print(f"Added to sys.path: {src_path}")

    # Add the shared library to the path
    shared_path = str(project_root)
    sys.path.insert(0, shared_path)
    print(f"Added to sys.path: {shared_path}")

    print("\n--- Step 2: Attempting to import models ---")

    # --- Step 2: Attempt to import the Base object and all models ---
    # This will fail with a ModuleNotFoundError if the path is wrong.

    from auth_service.db import Base

    print("Successfully imported 'Base' from auth_service.db")

    from auth_service.models import *

    print("Successfully imported all models from auth_service.models")

    print("\n--- Step 3: Listing all tables discovered by SQLAlchemy ---")

    # --- Step 3: Print all tables registered with SQLAlchemy's metadata ---
    # This is the definitive proof. If your tables are listed here, Alembic can see them.

    discovered_tables = Base.metadata.tables.keys()

    if not discovered_tables:
        print(
            "\nERROR: No tables were found in the SQLAlchemy metadata. Imports might have failed silently."
        )
    else:
        print("\nSUCCESS! Alembic can see the following tables:")
        for table_name in sorted(discovered_tables):
            print(f"  - {table_name}")

    print("\n--- Verification Complete ---")

except ImportError as e:
    print(f"\n--- VERIFICATION FAILED ---")
    print(f"An ImportError occurred: {e}")
    print("This means the PYTHONPATH is likely incorrect in alembic/env.py.")
    print("Please ensure the `sys.path.insert` lines in `alembic/env.py` are correct.")
    sys.exit(1)
except Exception as e:
    print(f"\n--- VERIFICATION FAILED ---")
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
