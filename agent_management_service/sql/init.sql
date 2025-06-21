-- Initial database setup for agent_management_service

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS agent_management_service;

-- Set search path to our schema
SET search_path TO agent_management_service, public;

-- Create extension for UUID generation if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable Row Level Security for all tables
ALTER DEFAULT PRIVILEGES IN SCHEMA agent_management_service 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO postgres;

-- Create RLS policies for agent_management_service tables
-- Note: The actual RLS policies will be created after table creation in migrations
