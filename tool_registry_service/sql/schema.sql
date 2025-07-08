-- Tool Registry Service Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tool_categories table
CREATE TABLE IF NOT EXISTS tool_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(255),
    color VARCHAR(50),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create tools table
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE,
    description TEXT,
    category_id UUID REFERENCES tool_categories(id) ON DELETE SET NULL,
    owner_id UUID NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    tool_type VARCHAR(50) NOT NULL,
    execution_env VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    input_schema JSONB,
    output_schema JSONB,
    authentication_config JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Create an index on owner_id for performance
    INDEX idx_tools_owner_id (owner_id),
    -- Create index on category for filtering
    INDEX idx_tools_category_id (category_id),
    -- Create index on public/approved tools
    INDEX idx_tools_public_approved ((is_public AND is_approved)),
    -- Add constraint for tool type
    CONSTRAINT valid_tool_type CHECK (tool_type IN ('http', 'python', 'javascript', 'command'))
);

-- Create tool_executions table to track execution history
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,
    inputs JSONB,
    outputs JSONB,
    error TEXT,
    metadata JSONB,
    
    -- Add indices for common queries
    INDEX idx_tool_executions_tool_id (tool_id),
    INDEX idx_tool_executions_user_id (user_id),
    INDEX idx_tool_executions_status (status)
);

-- Add triggers for updated_at timestamp management
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to tool_categories
CREATE TRIGGER set_tool_categories_updated_at
BEFORE UPDATE ON tool_categories
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- Add trigger to tools
CREATE TRIGGER set_tools_updated_at
BEFORE UPDATE ON tools
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();
