"""
Main conftest file that imports and re-exports all fixtures from modular files.
This approach improves maintainability by organizing fixtures into logical modules.
"""

import asyncio
import os

from dotenv import load_dotenv

# Explicitly load the test environment variables before importing any app modules
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env.test")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print(f"Warning: .env.test file not found at {dotenv_path}")

# Now reload the config to ensure it picks up test settings
from importlib import reload

from agent_deployment_service import config

reload(config)

# Make seed_test_user available as a fixture as well for convenience
import pytest

# Import and re-export fixtures from modular files
# This keeps this file clean while allowing tests to import fixtures normally
