from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

class StatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentTypeEnum(str, Enum):
    TASK = "task"
    COUNCIL = "council"
    VALIDATOR = "validator"
    MEMORY = "memory"

class AgentStatusEnum(str, Enum):
    SPAWNED = "spawned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

class OrchestratorTypeEnum(str, Enum):
    TOP_LEVEL = "top_level"
    SUB = "sub"

class OrchestratorStatusEnum(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class ImportanceLevelEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TemplateTypeEnum(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ConfigTypeEnum(str, Enum):
    LIMIT = "limit"
    SETTING = "setting"
    CREDENTIAL = "credential"

class MessageTypeEnum(str, Enum):
    CONTEXT_SHARE = "context_share"
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampMixin(BaseSchema):
    created_at: datetime
    updated_at: datetime

# ThoughtTree schemas
class ThoughtTreeBase(BaseSchema):
    goal: str
    status: StatusEnum = StatusEnum.PENDING
    depth: int = 0
    metadata: Dict[str, Any] = {}
    success_score: Decimal = Decimal("0.0")
    quality_score: Decimal = Decimal("0.0")
    speed_score: Decimal = Decimal("0.0")
    usefulness_score: Decimal = Decimal("0.0")
    overall_weight: Decimal = Decimal("0.5")
    importance_level: ImportanceLevelEnum = ImportanceLevelEnum.MEDIUM

class ThoughtTreeCreate(ThoughtTreeBase):
    parent_id: Optional[UUID] = None
    root_id: Optional[UUID] = None

class ThoughtTreeUpdate(BaseSchema):
    goal: Optional[str] = None
    status: Optional[StatusEnum] = None
    metadata: Optional[Dict[str, Any]] = None
    success_score: Optional[Decimal] = None
    quality_score: Optional[Decimal] = None
    speed_score: Optional[Decimal] = None
    usefulness_score: Optional[Decimal] = None
    overall_weight: Optional[Decimal] = None
    importance_level: Optional[ImportanceLevelEnum] = None
    completed_at: Optional[datetime] = None

class ThoughtTree(ThoughtTreeBase, TimestampMixin):
    id: UUID
    parent_id: Optional[UUID] = None
    root_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None

# Agent schemas
class AgentBase(BaseSchema):
    agent_type: AgentTypeEnum
    agent_class: str
    status: AgentStatusEnum = AgentStatusEnum.SPAWNED
    max_recursion_depth: int = 5
    current_recursion_depth: int = 0
    context: Dict[str, Any] = {}
    state: Dict[str, Any] = {}

class AgentCreate(AgentBase):
    thought_tree_id: UUID
    spawned_by: Optional[UUID] = None

class AgentUpdate(BaseSchema):
    status: Optional[AgentStatusEnum] = None
    context: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None
    current_recursion_depth: Optional[int] = None
    completed_at: Optional[datetime] = None

class Agent(AgentBase):
    id: UUID
    thought_tree_id: UUID
    spawned_by: Optional[UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# Orchestrator schemas
class OrchestratorBase(BaseSchema):
    orchestrator_type: OrchestratorTypeEnum
    status: OrchestratorStatusEnum = OrchestratorStatusEnum.ACTIVE
    max_concurrent_agents: int = 10
    current_active_agents: int = 0
    global_context: Dict[str, Any] = {}

class OrchestratorCreate(OrchestratorBase):
    thought_tree_id: UUID
    parent_orchestrator_id: Optional[UUID] = None

class OrchestratorUpdate(BaseSchema):
    status: Optional[OrchestratorStatusEnum] = None
    max_concurrent_agents: Optional[int] = None
    current_active_agents: Optional[int] = None
    global_context: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

class Orchestrator(OrchestratorBase):
    id: UUID
    thought_tree_id: UUID
    parent_orchestrator_id: Optional[UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# LLM Interaction schemas
class LLMInteractionBase(BaseSchema):
    provider: str = "claude"
    model: str
    prompt_text: str
    system_prompt: Optional[str] = None
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    success: bool = False
    retry_count: int = 0

class LLMInteractionCreate(LLMInteractionBase):
    thought_tree_id: UUID
    agent_id: Optional[UUID] = None

class LLMInteractionUpdate(BaseSchema):
    response_text: Optional[str] = None
    response_timestamp: Optional[datetime] = None
    token_count_output: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None

class LLMInteraction(LLMInteractionBase):
    id: UUID
    thought_tree_id: UUID
    agent_id: Optional[UUID] = None
    response_text: Optional[str] = None
    request_timestamp: datetime
    response_timestamp: Optional[datetime] = None
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None

# Tool Execution schemas
class ToolExecutionBase(BaseSchema):
    tool_name: str
    tool_class: str
    input_parameters: Dict[str, Any]
    success: bool = False
    retry_count: int = 0

class ToolExecutionCreate(ToolExecutionBase):
    agent_id: UUID
    thought_tree_id: UUID

class ToolExecutionUpdate(BaseSchema):
    output_result: Optional[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    success: Optional[bool] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None

class ToolExecution(ToolExecutionBase):
    id: UUID
    agent_id: UUID
    thought_tree_id: UUID
    output_result: Optional[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

# Prompt Template schemas
class PromptTemplateBase(BaseSchema):
    name: str
    template_type: TemplateTypeEnum
    content: str
    variables: List[str] = []
    version: int = 1
    is_active: bool = True
    created_by: Optional[str] = None
    usage_count: int = 0
    success_rate: Decimal = Decimal("0.0")

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplateUpdate(BaseSchema):
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None
    usage_count: Optional[int] = None
    success_rate: Optional[Decimal] = None

class PromptTemplate(PromptTemplateBase, TimestampMixin):
    id: UUID

# System Config schemas
class SystemConfigBase(BaseSchema):
    config_key: str
    config_value: Dict[str, Any]
    config_type: ConfigTypeEnum
    description: Optional[str] = None

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfigUpdate(BaseSchema):
    config_value: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

class SystemConfig(SystemConfigBase, TimestampMixin):
    id: UUID

# Agent Communication schemas
class AgentCommunicationBase(BaseSchema):
    message_type: MessageTypeEnum
    content: Dict[str, Any]
    delivered: bool = False
    processed: bool = False

class AgentCommunicationCreate(AgentCommunicationBase):
    sender_agent_id: UUID
    receiver_agent_id: Optional[UUID] = None  # None for broadcast
    thought_tree_id: UUID

class AgentCommunicationUpdate(BaseSchema):
    received_at: Optional[datetime] = None
    delivered: Optional[bool] = None
    processed: Optional[bool] = None

class AgentCommunication(AgentCommunicationBase):
    id: UUID
    sender_agent_id: UUID
    receiver_agent_id: Optional[UUID] = None
    thought_tree_id: UUID
    sent_at: datetime
    received_at: Optional[datetime] = None