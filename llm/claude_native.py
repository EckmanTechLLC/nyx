"""
Claude API Integration with Native Prompt Caching for NYX
Provides async Claude API wrapper with server-side prompt caching for cost optimization
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
import anthropic
from anthropic import AsyncAnthropic
import httpx
import uuid

from llm.models import (
    LLMRequest, LLMResponse, LLMUsage, LLMTiming, 
    LLMProvider, LLMModel, calculate_cost, estimate_tokens
)
from llm.native_cache import NativePromptCache
from database.connection import db_manager
from database.models import LLMInteraction
from config.settings import settings
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ClaudeAPIError(Exception):
    """Custom exception for Claude API errors"""
    pass

class ClaudeNativeAPI:
    """
    Async Claude API wrapper with native prompt caching
    
    Features:
    - Server-side prompt caching using Anthropic's cache_control
    - Fresh response generation with reduced input token costs
    - Complete database logging of interactions
    - Intelligent retry logic with exponential backoff
    - Council session context optimization
    - Real cost tracking with cache savings analysis
    """
    
    def __init__(self, native_cache: Optional[NativePromptCache] = None):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.cache = native_cache or NativePromptCache()
        
        # Configuration
        self.config = {
            "max_retries": 3,
            "base_delay": 1.0,
            "backoff_factor": 2.0,
            "max_delay": 60.0,
            "timeout_seconds": settings.llm_timeout_seconds,
            "enable_circuit_breaker": True,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_reset_time": 300  # 5 minutes
        }
        
        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        self._circuit_breaker_open = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "total_cost_usd": Decimal('0'),
            "native_cache_hits": 0,
            "input_tokens_saved": 0,
            "cost_saved_by_caching": Decimal('0')
        }
    
    async def call_claude(
        self,
        system_prompt: str = None,
        user_prompt: str = None,
        model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thought_tree_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        use_native_caching: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Main entry point for Claude API calls with native prompt caching
        
        Args:
            system_prompt: System/context prompt for Claude
            user_prompt: User input prompt  
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            thought_tree_id: Associated thought tree ID for logging
            session_id: Session ID for council sessions
            agent_id: Agent ID for tracking
            use_native_caching: Whether to use Anthropic's native caching
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with complete metadata including cache usage
        """
        request_start = datetime.now()
        
        # Create structured request
        request = LLMRequest(
            system_prompt=system_prompt or "",
            user_prompt=user_prompt or "",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thought_tree_id=thought_tree_id,
            session_id=session_id,
            agent_id=agent_id,
            use_cache=use_native_caching,
            metadata=kwargs
        )
        
        self.stats["total_requests"] += 1
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                raise ClaudeAPIError("Circuit breaker is open - API temporarily unavailable")
            
            # Prepare system prompt with native caching if enabled
            system_messages = []
            if system_prompt and use_native_caching:
                system_messages = self.cache.create_cached_system_prompt(
                    system_prompt, model.value
                )
            elif system_prompt:
                system_messages = [{"type": "text", "text": system_prompt}]
            
            # Prepare user messages
            messages = [{"role": "user", "content": user_prompt or ""}]
            
            # Add cache breakpoints to messages if using caching
            if use_native_caching:
                messages = self.cache.create_cached_messages(messages, model.value)
            
            # Generate cache key for tracking
            cache_key = ""
            if system_prompt or user_prompt:
                import hashlib
                content = f"{system_prompt}||{user_prompt}||{model.value}"
                cache_key = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Determine if this is likely a cache hit
            is_likely_cache_hit = self.cache.is_known_cache_key(cache_key)
            
            # Make the API call
            api_call_start = datetime.now()
            claude_response = await self._make_api_call_with_retries(
                request, system_messages, messages
            )
            api_call_end = datetime.now()
            api_call_ms = int((api_call_end - api_call_start).total_seconds() * 1000)
            
            request_end = datetime.now()
            
            # Extract usage information from Claude's response
            input_tokens = claude_response.usage.input_tokens
            output_tokens = claude_response.usage.output_tokens
            
            # Extract real cache usage from Claude's API response
            cached_tokens = getattr(claude_response.usage, 'cache_creation_input_tokens', 0)
            cache_read_tokens = getattr(claude_response.usage, 'cache_read_input_tokens', 0)
            
            # Determine if this was actually a cache hit based on Claude's response
            is_actual_cache_hit = cache_read_tokens > 0
            
            if is_actual_cache_hit:
                self.stats["native_cache_hits"] += 1
            
            # Calculate costs
            cost_usd = calculate_cost(model, input_tokens, output_tokens)
            
            # Estimate cost without caching (if we had cached content)
            cost_without_cache = cost_usd
            if cache_read_tokens > 0:
                # Cache read tokens cost ~10% of normal input tokens
                normal_cost = calculate_cost(model, cache_read_tokens, 0)
                cache_cost = normal_cost * Decimal('0.1')  # 10% cost for cache reads
                cost_without_cache = cost_usd + normal_cost - cache_cost
                self.stats["cost_saved_by_caching"] += cost_without_cache - cost_usd
                self.stats["input_tokens_saved"] += cache_read_tokens
            
            usage = LLMUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=cost_usd
            )
            
            timing = LLMTiming(
                request_start=request_start,
                request_end=request_end,
                response_time_ms=api_call_ms,
                cache_lookup_ms=None,  # Not applicable for native caching
                api_call_ms=api_call_ms
            )
            
            response = LLMResponse(
                request=request,
                content=claude_response.content[0].text,
                usage=usage,
                timing=timing,
                provider=LLMProvider.CLAUDE,
                cached=False,  # Always fresh responses with native caching
                cache_source="none",  # Native caching is transparent
                success=True
            )
            
            # Record cache usage statistics with real data from Claude
            if use_native_caching:
                self.cache.record_cache_usage(
                    prompt_cache_key=cache_key,
                    is_cache_hit=is_actual_cache_hit,
                    input_tokens=input_tokens,
                    cached_tokens=cached_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cost=cost_usd,
                    cost_without_cache=cost_without_cache
                )
            
            # Update statistics
            self.stats["successful_requests"] += 1
            self.stats["total_tokens_used"] += usage.total_tokens
            self.stats["total_cost_usd"] += Decimal(str(cost_usd))
            
            # Log to database (async, non-blocking)
            asyncio.create_task(self._log_interaction(
                response, cached_tokens, cache_read_tokens, cost_without_cache, is_actual_cache_hit
            ))
            
            # Reset circuit breaker on success
            self._circuit_breaker_failures = 0
            
            return response
            
        except Exception as e:
            # Handle failures
            request_end = datetime.now()
            timing = LLMTiming(
                request_start=request_start,
                request_end=request_end,
                response_time_ms=0
            )
            
            # Estimate usage for failed requests
            estimated_input_tokens = estimate_tokens((system_prompt or "") + (user_prompt or ""))
            usage = LLMUsage(
                input_tokens=estimated_input_tokens,
                output_tokens=0,
                total_tokens=estimated_input_tokens,
                cost_usd=Decimal('0')
            )
            
            response = LLMResponse(
                request=request,
                content="",
                usage=usage,
                timing=timing,
                provider=LLMProvider.CLAUDE,
                cached=False,
                cache_source="none",
                success=False,
                error_message=str(e)
            )
            
            self.stats["failed_requests"] += 1
            self._handle_circuit_breaker_failure()
            
            # Log failed interaction
            asyncio.create_task(self._log_interaction(response, 0, 0, Decimal('0'), False))
            
            # Re-raise the exception
            raise ClaudeAPIError(f"Claude API call failed: {str(e)}") from e
    
    async def _make_api_call_with_retries(self, request: LLMRequest, system_messages: List[Dict], messages: List[Dict]):
        """Make Claude API call with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.config["max_retries"] + 1):
            try:
                # Make the actual API call with native caching support
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=request.model.value,
                        max_tokens=request.max_tokens,
                        temperature=request.temperature,
                        system=system_messages,
                        messages=messages,
                        extra_headers={
                            "anthropic-version": "2023-06-01",
                            "anthropic-beta": "prompt-caching-2024-07-31"
                        }
                    ),
                    timeout=self.config["timeout_seconds"]
                )
                return response
                
            except anthropic.RateLimitError as e:
                # Handle rate limiting specifically
                if attempt < self.config["max_retries"]:
                    delay = min(
                        self.config["base_delay"] * (self.config["backoff_factor"] ** attempt),
                        self.config["max_delay"]
                    )
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                else:
                    raise ClaudeAPIError(f"Rate limit exceeded after {self.config['max_retries']} retries") from e
            
            except (anthropic.APIConnectionError, httpx.TimeoutException) as e:
                # Handle connection errors and timeouts
                if attempt < self.config["max_retries"]:
                    delay = min(
                        self.config["base_delay"] * (self.config["backoff_factor"] ** attempt),
                        self.config["max_delay"]
                    )
                    logger.warning(f"Connection error, retrying in {delay}s (attempt {attempt + 1}): {str(e)}")
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                else:
                    raise ClaudeAPIError(f"Connection failed after {self.config['max_retries']} retries") from e
            
            except anthropic.APIError as e:
                # Handle other API errors (usually don't retry these)
                raise ClaudeAPIError(f"Claude API error: {str(e)}") from e
            
            except Exception as e:
                # Handle unexpected errors
                if attempt < self.config["max_retries"]:
                    delay = min(
                        self.config["base_delay"] * (self.config["backoff_factor"] ** attempt),
                        self.config["max_delay"]
                    )
                    logger.error(f"Unexpected error, retrying in {delay}s (attempt {attempt + 1}): {str(e)}")
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                else:
                    raise ClaudeAPIError(f"Unexpected error after {self.config['max_retries']} retries") from e
        
        # This should never be reached, but just in case
        raise ClaudeAPIError(f"Max retries exceeded") from last_exception
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.config["enable_circuit_breaker"]:
            return False
        
        if not self._circuit_breaker_open:
            return False
        
        # Check if we should try to reset
        if self._circuit_breaker_last_failure:
            time_since_failure = (datetime.now() - self._circuit_breaker_last_failure).total_seconds()
            if time_since_failure > self.config["circuit_breaker_reset_time"]:
                self._circuit_breaker_open = False
                self._circuit_breaker_failures = 0
                logger.info("Circuit breaker reset - attempting API calls again")
                return False
        
        return True
    
    def _handle_circuit_breaker_failure(self):
        """Handle circuit breaker failure logic"""
        if not self.config["enable_circuit_breaker"]:
            return
        
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = datetime.now()
        
        if self._circuit_breaker_failures >= self.config["circuit_breaker_threshold"]:
            self._circuit_breaker_open = True
            logger.error(f"Circuit breaker opened after {self._circuit_breaker_failures} failures")
    
    async def _log_interaction(self, response: LLMResponse, cached_tokens: int, cache_read_tokens: int, cost_without_cache: Decimal, cache_hit: bool):
        """Log LLM interaction to database with native caching details"""
        try:
            # Ensure thought tree exists if provided
            thought_tree_id = response.request.thought_tree_id
            if thought_tree_id:
                thought_tree_id = await self._ensure_thought_tree_exists(
                    thought_tree_id, response.request.session_id
                )
            
            async with db_manager.get_async_session() as session:
                interaction = LLMInteraction(
                    id=uuid.uuid4(),
                    agent_id=response.request.agent_id,
                    thought_tree_id=thought_tree_id,
                    provider=response.provider.value,
                    model=response.request.model.value,
                    prompt_text=response.request.user_prompt,
                    system_prompt=response.request.system_prompt,
                    response_text=response.content if response.success else None,
                    request_timestamp=response.timing.request_start,
                    response_timestamp=response.timing.request_end if response.success else None,
                    token_count_input=response.usage.input_tokens,
                    token_count_output=response.usage.output_tokens,
                    cached_token_count=cached_tokens,
                    cache_creation_input_tokens=cached_tokens if not cache_hit else 0,
                    cache_read_input_tokens=cache_read_tokens,
                    latency_ms=response.timing.response_time_ms,
                    cost_usd=response.usage.cost_usd,
                    cost_without_cache_usd=cost_without_cache,
                    uses_prompt_caching=response.request.use_cache,
                    cache_ttl_seconds=self.cache.config["cache_ttl_seconds"],
                    cache_hit=cache_hit,
                    success=response.success,
                    error_message=response.error_message,
                    retry_count=response.retry_count
                )
                
                session.add(interaction)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log LLM interaction to database: {str(e)}")
    
    async def _ensure_thought_tree_exists(self, thought_tree_id: str, session_id: str = None) -> str:
        """Ensure a thought tree exists for logging, create if needed"""
        if not thought_tree_id:
            return None
            
        try:
            from database.models import ThoughtTree
            from sqlalchemy import select
            
            async with db_manager.get_async_session() as session:
                # Check if thought tree exists
                result = await session.execute(
                    select(ThoughtTree).filter(ThoughtTree.id == thought_tree_id)
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    # Create new thought tree
                    new_tree = ThoughtTree(
                        id=thought_tree_id,
                        goal="LLM Interaction",
                        status="in_progress",
                        metadata_={"session_id": session_id} if session_id else {},
                        depth=1
                    )
                    session.add(new_tree)
                    await session.commit()
                    
                return thought_tree_id
                
        except Exception as e:
            logger.warning(f"Failed to ensure thought tree exists: {str(e)}")
            return None
    
    @asynccontextmanager
    async def council_session(self, session_id: str, base_context: str = None):
        """
        Context manager for council sessions with native prompt caching
        
        Usage:
            async with claude_api.council_session("council_123", large_context) as session:
                # All calls in this block will reuse cached context
                response1 = await claude_api.call_claude("Engineer perspective", session_id=session)
                response2 = await claude_api.call_claude("Strategist view", session_id=session)
        """
        try:
            yield session_id
        finally:
            # Clean up any tracking (native caching is handled server-side by Anthropic)
            pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive API and caching statistics"""
        total_requests = self.stats["total_requests"]
        success_rate = self.stats["successful_requests"] / total_requests if total_requests > 0 else 0
        cache_hit_rate = self.stats["native_cache_hits"] / total_requests if total_requests > 0 else 0
        
        # Get cache statistics
        cache_stats = self.cache.get_statistics()
        
        return {
            # API Statistics
            "total_requests": total_requests,
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": round(success_rate, 4),
            
            # Cost Statistics
            "total_tokens_used": self.stats["total_tokens_used"],
            "total_cost_usd": float(self.stats["total_cost_usd"]),
            "input_tokens_saved": self.stats["input_tokens_saved"],
            "cost_saved_by_caching": float(self.stats["cost_saved_by_caching"]),
            
            # Native Caching Statistics
            "native_cache_hits": self.stats["native_cache_hits"],
            "cache_hit_rate": round(cache_hit_rate, 4),
            
            # Circuit Breaker
            "circuit_breaker_open": self._circuit_breaker_open,
            "circuit_breaker_failures": self._circuit_breaker_failures,
            
            # Detailed Cache Statistics
            "native_cache_stats": cache_stats
        }
    
    async def health_check(self) -> bool:
        """Check if Claude API is accessible"""
        try:
            # Make a minimal API call to test connectivity
            response = await self.call_claude(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say 'OK' if you can respond.",
                max_tokens=10,
                use_native_caching=False  # Don't cache health checks
            )
            return response.success and "OK" in response.content.upper()
        except Exception as e:
            logger.error(f"Claude API health check failed: {str(e)}")
            return False