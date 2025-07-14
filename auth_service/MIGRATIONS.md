# Auth Service: Database Migration Guide

This document outlines the standard workflow for managing database schema changes for the `auth_service`.

## Core Architecture

The `auth_service` database is structured into two primary schemas:

1.  **`auth` schema:** This is managed exclusively by the Supabase GoTrue service. It contains core authentication tables like `auth.users`. **We never modify this schema with Alembic.** We only link to it (e.g., via Foreign Keys from our `profiles` table).
2.  **`auth_service_data` schema:** This is our application-specific schema. All of our custom tables (`profiles`, `roles`, `permissions`, `app_clients`, etc.) reside here. **This schema is 100% managed by our SQLAlchemy models and Alembic migrations.**

Our primary tool for all database operations is the `scripts/manage_db.py` script. Please use this script instead of running `alembic` or `psql` commands directly to ensure a consistent and reliable environment.

## Initial Developer Setup

For a new developer setting up the project, or for anyone needing a completely fresh environment, the process is a single command:

````bash
# From within the auth_service/ directory
python scripts/manage_db.py recreate```

This command fully automates the following steps:
1.  Stops the entire local Supabase stack to ensure a clean state.
2.  Starts a fresh, new Supabase stack (including database and auth services).
3.  Creates the `auth_dev_db` database and our custom `auth_service_data` schema within it.
4.  Resets and generates a fresh Alembic migration based on the current state of your models.
5.  Applies the migration to create all necessary tables.
6.  Runs the bootstrap process to seed the database with initial roles, permissions, and the admin user.

## Daily Development Workflow

When you need to make a change to the database schema (e.g., add a column or a new table), follow this process:

#### Step 1: Modify Your SQLAlchemy Models
Make the necessary changes to your model files located in `src/auth_service/models/`.

#### Step 2: Generate a New Migration
Run the `create-migration` command, providing a short, descriptive message about the change.

```bash
# Use a descriptive message in the imperative mood
python scripts/manage_db.py create-migration -m "Add description column to roles table"
````
