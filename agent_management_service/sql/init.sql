-- Agent Management Service Database Schema
-- This file contains the complete schema for the agent_management_service

-- Create enum types
CREATE TYPE agent_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE agent_type AS ENUM ('langflow', 'custom', 'openai_assistant');

-- Create agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    status agent_status NOT NULL DEFAULT 'draft',
    agent_type agent_type NOT NULL DEFAULT 'langflow',
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create agent_versions table
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    config JSONB NOT NULL,
    changelog TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, version_number)
);

-- Create indexes
CREATE INDEX ix_agents_user_id ON agents(user_id);
CREATE INDEX ix_agents_id ON agents(id);
CREATE INDEX ix_agent_versions_agent_id ON agent_versions(agent_id);
CREATE INDEX ix_agent_versions_user_id ON agent_versions(user_id);
CREATE INDEX ix_agent_versions_id ON agent_versions(id);
CREATE INDEX ix_agent_versions_version_number ON agent_versions(version_number);

-- Add comments
COMMENT ON TABLE agents IS 'Stores agent definitions and metadata';
COMMENT ON TABLE agent_versions IS 'Stores versioned configurations of agents';
COMMENT ON COLUMN agents.config IS 'JSON configuration for the agent (Langflow flow, custom config, etc.)';
COMMENT ON COLUMN agent_versions.config IS 'Versioned agent configuration';

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE
    ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_versions_updated_at BEFORE UPDATE
    ON agent_versions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
