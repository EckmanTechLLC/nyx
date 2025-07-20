"""
LLM Response Models and Data Structures for NYX
Provides structured data models for LLM interactions and responses
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid

class LLMProvider(str, Enum):
    CLAUDE = "claude"
    GPT = "gpt"  # Future support
    GEMINI = "gemini"  # Future support

class LLMModel(str, Enum):
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229" 
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"  # Keep for backward compatibility

class CacheSource(str, Enum):
    NONE = "none"           # No cache, fresh API call
    EPHEMERAL = "ephemeral" # In-memory cache hit
    SHARED = "shared"       # Shared context cache hit
    PERSISTENT = "persistent" # Database cache hit

@dataclass
class LLMUsage:
    """Token usage and cost information"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    
    def __post_init__(self):
        if self.total_tokens != self.input_tokens + self.output_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens

@dataclass 
class LLMTiming:
    """Timing information for LLM interactions"""
    request_start: datetime
    request_end: datetime
    response_time_ms: int
    cache_lookup_ms: Optional[int] = None
    api_call_ms: Optional[int] = None
    
    def __post_init__(self):
        if self.response_time_ms == 0:
            delta = self.request_end - self.request_start
            self.response_time_ms = int(delta.total_seconds() * 1000)

@dataclass
class LLMRequest:
    """Structured LLM request with all parameters"""
    system_prompt: str
    user_prompt: str
    model: LLMModel
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    thought_tree_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    use_cache: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Generate unique request ID
        if 'request_id' not in self.metadata:
            self.metadata['request_id'] = str(uuid.uuid4())
    
    @property
    def cache_key_content(self) -> str:
        """Content used for cache key generation"""
        return f"{self.system_prompt}||{self.user_prompt}||{self.model.value}"
    
    @property
    def total_prompt_length(self) -> int:
        """Total character length of prompts"""
        return len(self.system_prompt) + len(self.user_prompt)

@dataclass
class LLMResponse:
    """Complete LLM response with metadata"""
    request: LLMRequest
    content: str
    usage: LLMUsage
    timing: LLMTiming
    provider: LLMProvider
    cached: bool
    cache_source: CacheSource
    success: bool = True
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Generate unique response ID
        if 'response_id' not in self.metadata:
            self.metadata['response_id'] = str(uuid.uuid4())
        
        # Set cache status based on source
        self.cached = self.cache_source != CacheSource.NONE
    
    @property
    def request_id(self) -> str:
        """Get request ID from request metadata"""
        return self.request.metadata.get('request_id', '')
    
    @property
    def response_id(self) -> str:
        """Get response ID from metadata"""
        return self.metadata.get('response_id', '')
    
    @property
    def cost_per_token(self) -> Decimal:
        """Calculate cost per token"""
        if self.usage.total_tokens == 0:
            return Decimal('0')
        return self.usage.cost_usd / self.usage.total_tokens
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate generation speed"""
        if self.timing.response_time_ms == 0:
            return 0.0
        return (self.usage.output_tokens / self.timing.response_time_ms) * 1000

@dataclass
class CacheStatistics:
    """Cache performance statistics"""
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    cost_saved_usd: Decimal = Decimal('0')
    ephemeral_hits: int = 0
    shared_context_hits: int = 0
    persistent_hits: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def total_requests(self) -> int:
        """Total number of requests processed"""
        return self.cache_hits + self.cache_misses

@dataclass
class PromptTemplate:
    """Database-backed prompt template"""
    id: str
    name: str
    template_type: str  # 'system', 'user', 'assistant'
    content: str
    variables: List[str]
    version: int = 1
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    usage_count: int = 0
    success_rate: Decimal = Decimal('0.0')
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        try:
            return self.content.format(**variables)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(f"Missing required template variable: {missing_var}")
        except Exception as e:
            raise ValueError(f"Template rendering error: {str(e)}")
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided"""
        missing = []
        for required_var in self.variables:
            if required_var not in variables:
                missing.append(required_var)
        return missing

@dataclass
class CouncilSession:
    """Council session tracking for shared context caching"""
    session_id: str
    topic: str
    participants: List[str]
    base_context: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    shared_cache_hits: int = 0
    total_interactions: int = 0
    tokens_saved: int = 0
    cost_saved_usd: Decimal = Decimal('0')
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate session duration in seconds"""
        if self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds())
        return None
    
    @property
    def cache_efficiency(self) -> float:
        """Calculate cache efficiency for this session"""
        if self.total_interactions == 0:
            return 0.0
        return self.shared_cache_hits / self.total_interactions

# Token pricing for cost calculation (as of 2024)
CLAUDE_PRICING = {
    LLMModel.CLAUDE_3_5_SONNET: {
        'input_per_token': Decimal('0.000003'),   # $3 per 1M input tokens
        'output_per_token': Decimal('0.000015'),  # $15 per 1M output tokens
    },
    LLMModel.CLAUDE_3_5_HAIKU: {
        'input_per_token': Decimal('0.000001'),   # $1 per 1M input tokens
        'output_per_token': Decimal('0.000005'),  # $5 per 1M output tokens
    },
    LLMModel.CLAUDE_3_OPUS: {
        'input_per_token': Decimal('0.000015'),   # $15 per 1M input tokens  
        'output_per_token': Decimal('0.000075'),  # $75 per 1M output tokens
    },
    LLMModel.CLAUDE_3_HAIKU: {
        'input_per_token': Decimal('0.00000025'), # $0.25 per 1M input tokens
        'output_per_token': Decimal('0.00000125'), # $1.25 per 1M output tokens
    }
}

def calculate_cost(model: LLMModel, input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost for LLM usage"""
    if model not in CLAUDE_PRICING:
        return Decimal('0')
    
    pricing = CLAUDE_PRICING[model]
    input_cost = pricing['input_per_token'] * input_tokens
    output_cost = pricing['output_per_token'] * output_tokens
    
    return input_cost + output_cost

def estimate_tokens(text: str) -> int:
    """Rough token estimation for text (approximate 4 chars per token)"""
    return max(1, len(text) // 4)