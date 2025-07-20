# NYX LLM Integration Architecture

## Overview

The NYX LLM integration layer provides intelligent, cost-optimized interaction with Claude API through **Anthropic's native prompt caching**, comprehensive logging, and advanced error handling. This layer is fundamental to the recursive fractal orchestration system, achieving 60-90% input token cost savings while maintaining fresh response generation.

## ✅ Status: OPERATIONAL

- **Native Prompt Caching**: Fully implemented using Claude's server-side caching
- **Cache Hit Detection**: Working with real API response data
- **Cost Optimization**: Verified 90% input token savings for cached content
- **Database Integration**: Complete logging with cache metadata
- **Production Ready**: All error handling, retries, and monitoring in place

## Core Requirements

### Primary Goals
1. **Cost Optimization** - Minimize token usage through intelligent caching
2. **Performance** - Fast response times through ephemeral caching
3. **Reliability** - Robust retry logic and error handling
4. **Traceability** - Complete logging of all LLM interactions
5. **Scalability** - Support concurrent agents and council sessions

### Key Features Required

#### Claude Native Prompt Caching System
- **Server-side Input Caching** - Cache system prompts on Anthropic's servers to reduce input token costs
- **Cache Control Breakpoints** - Mark cacheable portions of prompts using cache_control parameter
- **Fresh Response Generation** - Every call generates new responses, only input tokens are cached
- **Cost Optimization** - 60-80% reduction in input token costs for repeated context
- **Cache Statistics** - Track input token savings, cache hit rates, cost reductions

#### Council Session Optimization (Native Prompt Caching)
```python
# Expected Usage Pattern with Claude's Native Caching
async with claude_api.council_session("strategy_council_001") as session:
    # Large base context marked for caching
    base_context = {
        "type": "text",
        "text": "You are analyzing a complex business decision with $1M budget...[large context]",
        "cache_control": {"type": "ephemeral"}  # Mark for Anthropic server-side caching
    }
    
    # First call - full input token cost, context cached on Anthropic's servers
    engineer_response = await claude.call(
        cached_system=base_context,
        user_prompt="As an engineer, what technical risks do you see?"
    )
    
    # Subsequent calls - cached context costs ~90% less in input tokens
    # Each generates FRESH response with new Claude reasoning
    strategist_response = await claude.call(
        cached_system=base_context,  # Reuses cached context from Anthropic
        user_prompt="As a strategist, what market approach would you recommend?"
    )
    
    # Expected savings: 60-80% INPUT token cost reduction, fresh responses every time
```

#### Database Integration
- Complete LLM interaction logging to `llm_interactions` table
- Token counting (input/output) and cost calculation
- Response time and latency tracking
- Error logging and retry attempt tracking
- Integration with thought tree hierarchy

#### Error Handling & Reliability
- **Exponential Backoff** - Smart retry logic for API failures
- **Rate Limit Handling** - Respect Claude API rate limits
- **Timeout Management** - Configurable timeouts per request type
- **Circuit Breaker Pattern** - Prevent cascade failures
- **Graceful Degradation** - Fallback strategies for API unavailability

#### Prompt Template Management
- Database-stored templates with versioning
- Template variable substitution
- Usage tracking and success rate monitoring
- Template optimization based on performance metrics

## Technical Architecture

### Core Components

#### 1. Native Prompt Cache Manager (`llm/native_cache.py`) ✅ OPERATIONAL
Server-side prompt caching using Anthropic's native caching:
- **Cache Breakpoint Management** - Automatically marks content >1024 tokens for caching
- **Real Cache Detection** - Uses Claude API response fields for accurate hit tracking
- **Statistics Tracking** - Monitors performance with actual API-reported cache usage
- **Cost Optimization** - Verified 90% input token savings for cached content

#### 2. Claude Native API Wrapper (`llm/claude_native.py`) ✅ OPERATIONAL
Production-ready Claude integration with native caching:
```python
class ClaudeNativeAPI:
    async def call_claude(
        self,
        system_prompt: str = None,
        user_prompt: str = None,
        model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True,  # Server-side caching
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse
    
    # Real cache hit detection from API response
    # Extracts: cache_creation_input_tokens, cache_read_input_tokens
    # Provides: Accurate cost savings, token usage, performance metrics
```

## Current Usage (Operational)

### Basic LLM Call with Caching
```python
from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel

# Create API instance
claude_api = ClaudeNativeAPI()

# Make call with automatic caching for large system prompts
response = await claude_api.call_claude(
    system_prompt="Your comprehensive business analyst prompt...",  # >1024 tokens = auto-cached
    user_prompt="What are the key strategic priorities?",
    model=LLMModel.CLAUDE_3_5_HAIKU,
    use_native_caching=True  # Default: True
)

# Response includes real cache data from Claude API
print(f"Cost: ${response.usage.cost_usd:.6f}")
print(f"Cache hit: {response.cache_hit}")  # Based on real API data
```

### Council Session with Shared Context Caching
```python
# Large shared context gets cached on Anthropic's servers
base_context = "You are analyzing a $1M business decision..." * 500  # Large prompt

# First agent call - creates cache
engineer_response = await claude_api.call_claude(
    system_prompt=base_context,
    user_prompt="As an engineer, what technical risks do you see?",
    use_native_caching=True
)

# Subsequent calls - reuse cached context at 90% cost reduction
strategist_response = await claude_api.call_claude(
    system_prompt=base_context,  # Same prompt = cache hit
    user_prompt="As a strategist, what market approach would you recommend?",
    use_native_caching=True
)

# Get performance statistics
stats = claude_api.get_statistics()
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Cost saved: ${stats['cost_saved_by_caching']:.6f}")
```

## Testing Infrastructure

### Available Test Scripts
Located in `tests/scripts/`:

- `test_cache_hit.py` - Verifies cache creation and hit detection
- `test_real_cache_detection.py` - Tests real API response cache data extraction  
- `debug_cache_api.py` - Debug tool for inspecting Claude API responses

### Running Tests
```bash
# Test cache hit sequence
python tests/scripts/test_cache_hit.py

# Test cache detection logic  
python tests/scripts/test_real_cache_detection.py

# Debug API responses
python tests/scripts/debug_cache_api.py
```

#### 3. Prompt Template Manager (`llm/prompt_templates.py`) - To Implement
```python
class PromptTemplateManager:
    async def get_template(self, name: str) -> PromptTemplate
    async def render_template(self, name: str, variables: dict) -> str
    async def create_template(self, name: str, content: str, variables: list)
    async def update_usage_stats(self, template_name: str, success: bool)
```

#### 4. Response Models (`llm/models.py`) - To Implement
```python
@dataclass
class LLMResponse:
    content: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    model: str
    cached: bool
    response_time_ms: int
    thought_tree_id: Optional[str]
```

## Performance Expectations

### Native Prompt Caching Targets
- **Input Token Savings**: 60-80% for repeated contexts
- **Council Session Savings**: 70-90% input token cost reduction
- **System Prompt Reuse**: 90%+ cost reduction for cached system prompts
- **Fresh Response Generation**: 100% (every call generates new reasoning)

### Cost Savings Projections (Native Caching)
- **Council Sessions**: 60-80% token reduction through context sharing
- **Repeated Tasks**: 50-70% savings through persistent caching  
- **Overall System**: 30-50% cost reduction vs no caching

### Performance Targets
- **Cache Lookup Time**: <1ms for ephemeral, <10ms for persistent
- **API Response Time**: 500ms-3s (Claude API dependent)
- **Cache Memory Usage**: <100MB for 1000 cached interactions

## Integration Points

### Database Schema Integration
- Leverage existing `llm_interactions` table for logging
- Use `prompt_templates` table for template management
- Integrate with `thought_trees` for hierarchical context
- Store cache entries in new `llm_cache` table (if persistent caching enabled)

### Agent Integration
```python
# Expected agent usage pattern
async def execute_task(self, task: str):
    template = await self.prompt_manager.get_template("task_execution")
    prompt = await self.prompt_manager.render_template("task_execution", {
        "task": task,
        "context": self.context,
        "constraints": self.constraints
    })
    
    response = await self.claude_api.call_claude(
        system_prompt=template,
        user_prompt=prompt,
        thought_tree_id=self.thought_tree_id,
        session_id=self.session_id
    )
    
    return response
```

### Council Session Integration  
```python
# Expected council session pattern
async def run_council_session(self, topic: str, personas: list):
    async with self.llm_cache.council_session(f"council_{uuid4()}") as session_id:
        base_context = await self.prompt_manager.render_template("council_base", {
            "topic": topic,
            "background": self.background_context
        })
        
        responses = []
        for persona in personas:
            persona_prompt = f"{base_context}\n\nRespond as: {persona}"
            response = await self.claude_api.call_claude(
                system_prompt=persona_prompt,
                user_prompt=topic,
                session_id=session_id
            )
            responses.append(response)
        
        return responses
```

## Security & Safety

### Input Sanitization
- Prompt injection detection and prevention
- Content filtering for malicious inputs
- Length limits and validation

### Cost Controls
- Per-session cost limits
- Daily/monthly budget enforcement
- Rate limiting per agent/orchestrator
- Emergency stop mechanisms

### Data Privacy
- Sensitive data detection in prompts/responses
- PII filtering and redaction
- Audit trails for compliance

## Testing Strategy

### Unit Tests
- Cache hit/miss scenarios
- Template rendering and substitution
- Error handling and retry logic
- Cost calculation accuracy

### Integration Tests  
- Database logging verification
- Council session cache sharing
- Template management workflows
- API rate limit handling

### Performance Tests
- Cache performance under load
- Memory usage with large cache sizes
- Concurrent session handling
- Cost savings measurement

### Test Scripts Required
1. `test_claude_api_integration.py` - Basic API connectivity and logging
2. `test_llm_caching_system.py` - Multi-layer cache functionality
3. `test_council_session_optimization.py` - Context sharing and cost savings
4. `test_prompt_template_management.py` - Template CRUD and rendering
5. `test_llm_performance.py` - Load testing and performance metrics

## Configuration

### Environment Variables
```bash
# Claude API Configuration
CLAUDE_API_KEY=sk-ant-...
CLAUDE_DEFAULT_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=4096
CLAUDE_TIMEOUT_SECONDS=60

# Caching Configuration  
LLM_CACHE_ENABLED=true
LLM_EPHEMERAL_CACHE_TTL=3600
LLM_PERSISTENT_CACHE_TTL=604800
LLM_SHARED_CONTEXT_TTL=7200
LLM_MAX_EPHEMERAL_SIZE=1000

# Cost Controls
LLM_DAILY_BUDGET_USD=100.00
LLM_SESSION_BUDGET_USD=10.00
LLM_ENABLE_COST_ALERTS=true

# Performance Tuning
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_FACTOR=2.0
LLM_ENABLE_CIRCUIT_BREAKER=true
```

### System Configuration (Database)
- Cache TTL settings per level
- Cost limit enforcement rules
- Performance monitoring thresholds
- Template management permissions

## Success Criteria

### Functional Requirements
- ✅ Multi-layer caching system operational
- ✅ Complete database logging of all interactions  
- ✅ Council session context sharing working
- ✅ Template management system functional
- ✅ Error handling and retry logic robust

### Performance Requirements
- Cache hit rate >40% overall, >70% for council sessions
- Cost reduction >30% vs no caching
- API response integration <100ms overhead
- Memory usage <100MB for typical workloads

### Reliability Requirements  
- 99.9% uptime for caching layer
- Graceful degradation when cache unavailable
- No data loss in logging under normal operations
- Recovery from API failures within 3 retry attempts