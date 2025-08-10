-- Agent Deployment Service Database Schema
-- This file contains the complete schema for the agent_deployment_service

-- Create enum types
CREATE TYPE deployment_status AS ENUM ('pending', 'deploying', 'running', 'failed', 'stopped');
CREATE TYPE build_strategy AS ENUM ('cloud_build', 'github_actions');
CREATE TYPE deployment_strategy AS ENUM ('cloud_run', 'kubernetes');

-- Create deployments table
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    agent_version_id UUID NOT NULL,
    status deployment_status NOT NULL DEFAULT 'pending',
    endpoint_url VARCHAR,
    deployment_metadata JSONB,
    error_message TEXT,
    deployed_at TIMESTAMP WITH TIME ZONE,
    stopped_at TIMESTAMP WITH TIME ZONE,
    build_strategy build_strategy,
    deployment_strategy deployment_strategy,
    deploy_real_agent BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX ix_deployments_user_id ON deployments(user_id);
CREATE INDEX ix_deployments_agent_id ON deployments(agent_id);
CREATE INDEX ix_deployments_agent_version_id ON deployments(agent_version_id);
CREATE INDEX ix_deployments_status ON deployments(status);

-- Add comments
COMMENT ON TABLE deployments IS 'Tracks agent deployments and their lifecycle';
COMMENT ON COLUMN deployments.endpoint_url IS 'The URL where the deployed agent can be accessed';
COMMENT ON COLUMN deployments.deployment_metadata IS 'Platform-specific deployment details (Cloud Run service name, K8s deployment info, etc.)';
COMMENT ON COLUMN deployments.deploy_real_agent IS 'Whether to deploy the actual agent or just a test container';

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_deployments_updated_at BEFORE UPDATE
    ON deployments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();