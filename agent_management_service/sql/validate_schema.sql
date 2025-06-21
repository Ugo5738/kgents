-- Schema validation script for agent_management_service
-- This script validates that all required tables and columns exist

DO $$
BEGIN
    -- Check if agents table exists
    IF NOT EXISTS (
        SELECT FROM pg_tables
        WHERE schemaname = 'agent_management_service' AND tablename = 'agents'
    ) THEN
        RAISE EXCEPTION 'Required table agent_management_service.agents does not exist';
    END IF;

    -- Check if agent_versions table exists
    IF NOT EXISTS (
        SELECT FROM pg_tables
        WHERE schemaname = 'agent_management_service' AND tablename = 'agent_versions'
    ) THEN
        RAISE EXCEPTION 'Required table agent_management_service.agent_versions does not exist';
    END IF;

    -- Validate required columns in agents table
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'agent_management_service' 
        AND table_name = 'agents'
        AND column_name = 'id'
    ) THEN
        RAISE EXCEPTION 'Required column agent_management_service.agents.id does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'agent_management_service'
        AND table_name = 'agents'
        AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'Required column agent_management_service.agents.user_id does not exist';
    END IF;

    -- Validate agent_versions columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'agent_management_service'
        AND table_name = 'agent_versions'
        AND column_name = 'agent_id'
    ) THEN
        RAISE EXCEPTION 'Required column agent_management_service.agent_versions.agent_id does not exist';
    END IF;

    RAISE NOTICE 'Schema validation completed successfully';
END $$;
