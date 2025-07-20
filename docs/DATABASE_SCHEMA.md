# NYX Database Schema Documentation

## Overview

The NYX database schema is designed to support recursive fractal orchestration with complete traceability, thought tree management, and reinforcement learning metrics. All data is stored in PostgreSQL with no automatic cleanup policies.

## Core Tables

### thought_trees
Stores the hierarchical structure of goals, subtasks, and outcomes.

```sql
CREATE TABLE thought_trees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES thought_trees(id),
    root_id UUID REFERENCES thought_trees(id),
    goal TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
    depth INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    
    -- Reinforcement Learning Metrics
    success_score DECIMAL(5,4) DEFAULT 0.0,
    quality_score DECIMAL(5,4) DEFAULT 0.0,
    speed_score DECIMAL(5,4) DEFAULT 0.0,
    usefulness_score DECIMAL(5,4) DEFAULT 0.0,
    overall_weight DECIMAL(5,4) DEFAULT 0.5,
    importance_level VARCHAR(10) DEFAULT 'medium' CHECK (importance_level IN ('low', 'medium', 'high')),
    
    INDEX idx_thought_trees_parent_id (parent_id),
    INDEX idx_thought_trees_root_id (root_id),
    INDEX idx_thought_trees_status (status),
    INDEX idx_thought_trees_depth (depth),
    INDEX idx_thought_trees_overall_weight (overall_weight)
);
```

### agents
Tracks all agent instances and their lifecycle.

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thought_tree_id UUID NOT NULL REFERENCES thought_trees(id),
    agent_type VARCHAR(20) NOT NULL CHECK (agent_type IN ('task', 'council', 'validator', 'memory')),
    agent_class VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('spawned', 'active', 'completed', 'failed', 'terminated')),
    spawned_by UUID REFERENCES agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Resource tracking
    max_recursion_depth INTEGER DEFAULT 5,
    current_recursion_depth INTEGER DEFAULT 0,
    
    -- Context and state
    context JSONB DEFAULT '{}',
    state JSONB DEFAULT '{}',
    
    INDEX idx_agents_thought_tree_id (thought_tree_id),
    INDEX idx_agents_type_status (agent_type, status),
    INDEX idx_agents_spawned_by (spawned_by)
);
```

### orchestrators
Tracks orchestrator instances and their coordination activities.

```sql
CREATE TABLE orchestrators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_orchestrator_id UUID REFERENCES orchestrators(id),
    thought_tree_id UUID NOT NULL REFERENCES thought_trees(id),
    orchestrator_type VARCHAR(20) NOT NULL CHECK (orchestrator_type IN ('top_level', 'sub')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'completed', 'failed', 'paused')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Configuration
    max_concurrent_agents INTEGER DEFAULT 10,
    current_active_agents INTEGER DEFAULT 0,
    
    -- Context
    global_context JSONB DEFAULT '{}',
    
    INDEX idx_orchestrators_parent_id (parent_orchestrator_id),
    INDEX idx_orchestrators_thought_tree_id (thought_tree_id),
    INDEX idx_orchestrators_status (status)
);
```

### llm_interactions
Complete log of all LLM API calls with inputs, outputs, and metrics.

```sql
CREATE TABLE llm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    thought_tree_id UUID NOT NULL REFERENCES thought_trees(id),
    
    -- API Details
    provider VARCHAR(20) NOT NULL DEFAULT 'claude',
    model VARCHAR(50) NOT NULL,
    
    -- Request/Response
    prompt_text TEXT NOT NULL,
    system_prompt TEXT,
    response_text TEXT,
    
    -- Metadata
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Metrics
    token_count_input INTEGER,
    token_count_output INTEGER,
    cached_token_count INTEGER DEFAULT 0,  -- Tokens saved by native caching
    cache_creation_input_tokens INTEGER DEFAULT 0,  -- Tokens used to create cache
    cache_read_input_tokens INTEGER DEFAULT 0,      -- Reduced tokens from cache usage
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),
    cost_without_cache_usd DECIMAL(10,6),  -- What cost would have been without caching
    
    -- Native Caching Details
    uses_prompt_caching BOOLEAN DEFAULT FALSE,
    cache_ttl_seconds INTEGER,  -- TTL for cached prompts
    cache_hit BOOLEAN DEFAULT FALSE,  -- Whether this call used cached prompts
    
    -- Status
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    INDEX idx_llm_interactions_agent_id (agent_id),
    INDEX idx_llm_interactions_thought_tree_id (thought_tree_id),
    INDEX idx_llm_interactions_timestamp (request_timestamp),
    INDEX idx_llm_interactions_provider_model (provider, model)
);
```

### tool_executions
Logs all tool calls with complete traceability.

```sql
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    thought_tree_id UUID NOT NULL REFERENCES thought_trees(id),
    
    -- Tool Details
    tool_name VARCHAR(50) NOT NULL,
    tool_class VARCHAR(100) NOT NULL,
    
    -- Execution
    input_parameters JSONB NOT NULL,
    output_result JSONB,
    stdout TEXT,
    stderr TEXT,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Status
    success BOOLEAN DEFAULT FALSE,
    exit_code INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    INDEX idx_tool_executions_agent_id (agent_id),
    INDEX idx_tool_executions_thought_tree_id (thought_tree_id),
    INDEX idx_tool_executions_tool_name (tool_name),
    INDEX idx_tool_executions_started_at (started_at)
);
```

### prompt_templates
Database-stored prompt templates and schemas.

```sql
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    template_type VARCHAR(20) NOT NULL CHECK (template_type IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    variables JSONB DEFAULT '[]',  -- List of template variables
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,4) DEFAULT 0.0,
    
    INDEX idx_prompt_templates_name (name),
    INDEX idx_prompt_templates_type_active (template_type, is_active)
);
```

### system_config
Runtime configuration and limits.

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    config_type VARCHAR(20) NOT NULL CHECK (config_type IN ('limit', 'setting', 'credential')),
    description TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_system_config_key (config_key),
    INDEX idx_system_config_type (config_type)
);
```

### agent_communications
Cross-agent context sharing and communication log.

```sql
CREATE TABLE agent_communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_agent_id UUID NOT NULL REFERENCES agents(id),
    receiver_agent_id UUID REFERENCES agents(id), -- NULL for broadcast
    thought_tree_id UUID NOT NULL REFERENCES thought_trees(id),
    
    -- Message
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('context_share', 'request', 'response', 'notification')),
    content JSONB NOT NULL,
    
    -- Timing
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    delivered BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    
    INDEX idx_agent_communications_sender (sender_agent_id),
    INDEX idx_agent_communications_receiver (receiver_agent_id),
    INDEX idx_agent_communications_thought_tree (thought_tree_id),
    INDEX idx_agent_communications_sent_at (sent_at)
);
```

## Initial Configuration Data

The following system configurations should be inserted on database initialization:

```sql
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('max_recursion_depth', '{"value": 10}', 'limit', 'Maximum depth for recursive agent spawning'),
('max_concurrent_agents', '{"value": 50}', 'limit', 'Maximum number of concurrent agents system-wide'),
('max_thought_tree_age_days', '{"value": 365}', 'limit', 'Maximum age before thought trees marked as archival'),
('default_retry_attempts', '{"value": 3}', 'setting', 'Default number of retry attempts for failed operations'),
('llm_timeout_seconds', '{"value": 60}', 'setting', 'Default timeout for LLM API calls'),
('tool_timeout_seconds', '{"value": 30}', 'setting', 'Default timeout for tool executions');
```

## Indexing Strategy

- Primary keys use UUIDs for distributed scalability
- Composite indexes on frequently queried combinations
- Partial indexes on active/pending records
- Time-based indexes for audit trails and performance monitoring

## Data Retention Policy

- No automatic cleanup - all records preserved
- Low-value records marked with `importance_level = 'low'`
- Manual archival processes can be implemented later
- Thought trees maintain complete lineage indefinitely