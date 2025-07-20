from sqlalchemy import Column, String, Integer, Text, Boolean, DECIMAL, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class ThoughtTree(Base):
    __tablename__ = "thought_trees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=True)
    root_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=True)
    goal = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    depth = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, default={})
    
    # Reinforcement Learning Metrics
    success_score = Column(DECIMAL(5,4), default=0.0)
    quality_score = Column(DECIMAL(5,4), default=0.0)
    speed_score = Column(DECIMAL(5,4), default=0.0)
    usefulness_score = Column(DECIMAL(5,4), default=0.0)
    overall_weight = Column(DECIMAL(5,4), default=0.5)
    importance_level = Column(String(10), default="medium")
    
    # Relationships
    parent = relationship("ThoughtTree", remote_side=[id], foreign_keys=[parent_id], backref="children")
    root = relationship("ThoughtTree", remote_side=[id], foreign_keys=[root_id])
    agents = relationship("Agent", back_populates="thought_tree")
    orchestrators = relationship("Orchestrator", back_populates="thought_tree")
    llm_interactions = relationship("LLMInteraction", back_populates="thought_tree")
    tool_executions = relationship("ToolExecution", back_populates="thought_tree")
    communications = relationship("AgentCommunication", back_populates="thought_tree")
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')", 
                       name="check_thought_trees_status"),
        CheckConstraint("importance_level IN ('low', 'medium', 'high')", 
                       name="check_thought_trees_importance_level"),
        Index("idx_thought_trees_parent_id", "parent_id"),
        Index("idx_thought_trees_root_id", "root_id"),
        Index("idx_thought_trees_status", "status"),
        Index("idx_thought_trees_depth", "depth"),
        Index("idx_thought_trees_overall_weight", "overall_weight"),
    )

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thought_tree_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=False)
    agent_type = Column(String(20), nullable=False)
    agent_class = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="spawned")
    spawned_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Resource tracking
    max_recursion_depth = Column(Integer, default=5)
    current_recursion_depth = Column(Integer, default=0)
    
    # Context and state
    context = Column(JSONB, default={})
    state = Column(JSONB, default={})
    
    # Relationships
    thought_tree = relationship("ThoughtTree", back_populates="agents")
    spawner = relationship("Agent", remote_side=[id], backref="spawned_agents")
    llm_interactions = relationship("LLMInteraction", back_populates="agent")
    tool_executions = relationship("ToolExecution", back_populates="agent")
    sent_communications = relationship("AgentCommunication", foreign_keys="AgentCommunication.sender_agent_id", back_populates="sender")
    received_communications = relationship("AgentCommunication", foreign_keys="AgentCommunication.receiver_agent_id", back_populates="receiver")
    
    __table_args__ = (
        CheckConstraint("agent_type IN ('task', 'council', 'validator', 'memory')", 
                       name="check_agents_agent_type"),
        CheckConstraint("status IN ('spawned', 'active', 'waiting', 'coordinating', 'completed', 'failed', 'terminated')", 
                       name="check_agents_status"),
        Index("idx_agents_thought_tree_id", "thought_tree_id"),
        Index("idx_agents_type_status", "agent_type", "status"),
        Index("idx_agents_spawned_by", "spawned_by"),
    )

class Orchestrator(Base):
    __tablename__ = "orchestrators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_orchestrator_id = Column(UUID(as_uuid=True), ForeignKey("orchestrators.id"), nullable=True)
    thought_tree_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=False)
    orchestrator_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    max_concurrent_agents = Column(Integer, default=10)
    current_active_agents = Column(Integer, default=0)
    
    # Context
    global_context = Column(JSONB, default={})
    
    # Relationships
    parent_orchestrator = relationship("Orchestrator", remote_side=[id], backref="sub_orchestrators")
    thought_tree = relationship("ThoughtTree", back_populates="orchestrators")
    
    __table_args__ = (
        CheckConstraint("orchestrator_type IN ('top_level', 'sub', 'test')", 
                       name="check_orchestrators_orchestrator_type"),
        CheckConstraint("status IN ('initializing', 'active', 'completed', 'failed', 'paused', 'terminated')", 
                       name="check_orchestrators_status"),
        Index("idx_orchestrators_parent_id", "parent_orchestrator_id"),
        Index("idx_orchestrators_thought_tree_id", "thought_tree_id"),
        Index("idx_orchestrators_status", "status"),
    )

class LLMInteraction(Base):
    __tablename__ = "llm_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    thought_tree_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=True)
    
    # API Details
    provider = Column(String(20), nullable=False, default="claude")
    model = Column(String(50), nullable=False)
    
    # Request/Response
    prompt_text = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    
    # Metadata
    request_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    response_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Metrics
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    cached_token_count = Column(Integer, default=0)  # Tokens saved by native caching
    cache_creation_input_tokens = Column(Integer, default=0)  # Tokens used to create cache
    cache_read_input_tokens = Column(Integer, default=0)      # Reduced tokens from cache usage
    latency_ms = Column(Integer, nullable=True)
    cost_usd = Column(DECIMAL(10,6), nullable=True)
    cost_without_cache_usd = Column(DECIMAL(10,6), nullable=True)  # What cost would have been without caching
    
    # Native Caching Details
    uses_prompt_caching = Column(Boolean, default=False)
    cache_ttl_seconds = Column(Integer, nullable=True)  # TTL for cached prompts
    cache_hit = Column(Boolean, default=False)  # Whether this call used cached prompts
    
    # Status
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    agent = relationship("Agent", back_populates="llm_interactions")
    thought_tree = relationship("ThoughtTree", back_populates="llm_interactions")
    
    __table_args__ = (
        Index("idx_llm_interactions_agent_id", "agent_id"),
        Index("idx_llm_interactions_thought_tree_id", "thought_tree_id"),
        Index("idx_llm_interactions_timestamp", "request_timestamp"),
        Index("idx_llm_interactions_provider_model", "provider", "model"),
    )

class ToolExecution(Base):
    __tablename__ = "tool_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    thought_tree_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=False)
    
    # Tool Details
    tool_name = Column(String(50), nullable=False)
    tool_class = Column(String(100), nullable=False)
    
    # Execution
    input_parameters = Column(JSONB, nullable=False)
    output_result = Column(JSONB, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Status
    success = Column(Boolean, default=False)
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    agent = relationship("Agent", back_populates="tool_executions")
    thought_tree = relationship("ThoughtTree", back_populates="tool_executions")
    
    __table_args__ = (
        Index("idx_tool_executions_agent_id", "agent_id"),
        Index("idx_tool_executions_thought_tree_id", "thought_tree_id"),
        Index("idx_tool_executions_tool_name", "tool_name"),
        Index("idx_tool_executions_started_at", "started_at"),
    )

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    template_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSONB, default=[])
    
    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    success_rate = Column(DECIMAL(5,4), default=0.0)
    
    __table_args__ = (
        CheckConstraint("template_type IN ('system', 'user', 'assistant')", 
                       name="check_prompt_templates_template_type"),
        # Only one active version per name allowed
        Index("idx_prompt_templates_name_version", "name", "version", unique=True),
        Index("idx_prompt_templates_name", "name"),
        Index("idx_prompt_templates_type_active", "template_type", "is_active"),
    )

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(JSONB, nullable=False)
    config_type = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("config_type IN ('limit', 'setting', 'credential')", 
                       name="check_system_config_config_type"),
        Index("idx_system_config_key", "config_key"),
        Index("idx_system_config_type", "config_type"),
    )

class AgentCommunication(Base):
    __tablename__ = "agent_communications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    receiver_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    thought_tree_id = Column(UUID(as_uuid=True), ForeignKey("thought_trees.id"), nullable=False)
    
    # Message
    message_type = Column(String(20), nullable=False)
    content = Column(JSONB, nullable=False)
    
    # Timing
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    received_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    delivered = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    
    # Relationships
    sender = relationship("Agent", foreign_keys=[sender_agent_id], back_populates="sent_communications")
    receiver = relationship("Agent", foreign_keys=[receiver_agent_id], back_populates="received_communications")
    thought_tree = relationship("ThoughtTree", back_populates="communications")
    
    __table_args__ = (
        CheckConstraint("message_type IN ('context_share', 'request', 'response', 'notification')", 
                       name="check_agent_communications_message_type"),
        Index("idx_agent_communications_sender", "sender_agent_id"),
        Index("idx_agent_communications_receiver", "receiver_agent_id"),
        Index("idx_agent_communications_thought_tree", "thought_tree_id"),
        Index("idx_agent_communications_sent_at", "sent_at"),
    )