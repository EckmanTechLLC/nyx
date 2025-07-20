"""
Claude Native Prompt Caching for NYX
Implements Anthropic's server-side prompt caching for input token cost reduction
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class CacheBreakpoint:
    """Represents a cache breakpoint in a prompt"""
    content: str
    cache_type: str = "ephemeral"
    estimated_tokens: int = 0
    
    def to_cache_control(self) -> Dict[str, str]:
        """Convert to Anthropic cache_control format"""
        return {"type": self.cache_type}

@dataclass
class CachedPrompt:
    """Represents a prompt with cache breakpoints"""
    system_parts: List[Dict[str, Any]]
    user_content: str
    cache_breakpoints: List[int]  # Indices where caching is enabled
    estimated_cached_tokens: int = 0
    
    def get_cache_key(self) -> str:
        """Generate cache key for tracking purposes"""
        content = json.dumps(self.system_parts, sort_keys=True) + self.user_content
        return hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class CacheStatistics:
    """Native prompt caching statistics"""
    total_requests: int = 0
    cache_creation_requests: int = 0  # First time seeing this prompt
    cache_hit_requests: int = 0       # Subsequent uses of cached prompt
    
    # Token tracking
    total_input_tokens: int = 0
    cached_tokens: int = 0            # Tokens that were cached
    cache_read_tokens: int = 0        # Reduced-cost tokens from cache hits
    
    # Cost tracking  
    total_cost: Decimal = Decimal('0')
    cost_without_cache: Decimal = Decimal('0')  # What it would have cost
    cost_saved: Decimal = Decimal('0')
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hit_requests / self.total_requests
    
    @property
    def token_savings_rate(self) -> float:
        """Calculate percentage of tokens saved through caching"""
        if self.total_input_tokens == 0:
            return 0.0
        return self.cached_tokens / self.total_input_tokens
    
    @property
    def cost_savings_rate(self) -> float:
        """Calculate percentage of cost saved"""
        if self.cost_without_cache == 0:
            return 0.0
        return float(self.cost_saved / self.cost_without_cache)

class NativePromptCache:
    """
    Claude Native Prompt Caching Manager
    
    Handles server-side prompt caching using Anthropic's cache_control parameter
    to reduce input token costs while maintaining fresh response generation.
    """
    
    def __init__(self):
        # Cache configuration
        self.config = {
            "min_cacheable_tokens": 1024,        # Minimum tokens for caching
            "haiku_min_tokens": 2048,            # Higher minimum for Haiku models
            "cache_ttl_seconds": 300,            # 5 minutes cache lifetime
            "max_cache_breakpoints": 4,          # Max breakpoints per request
            "auto_cache_system_prompts": True    # Automatically cache large system prompts
        }
        
        # Statistics tracking
        self.stats = CacheStatistics()
        
        # Cache key tracking (for our internal statistics)
        self._known_cache_keys: Dict[str, datetime] = {}
    
    def should_cache_content(self, content: str, model: str = None) -> bool:
        """Determine if content should be cached based on token threshold"""
        estimated_tokens = len(content) // 4  # Rough approximation
        
        # Use higher threshold for Haiku models
        min_tokens = self.config["haiku_min_tokens"] if model and "haiku" in model.lower() else self.config["min_cacheable_tokens"]
        
        return estimated_tokens >= min_tokens
    
    def create_cached_system_prompt(self, system_content: str, model: str = None) -> List[Dict[str, Any]]:
        """
        Create a system prompt with caching enabled if content is large enough
        
        Returns:
            List of system message parts with cache_control where appropriate
        """
        if not self.should_cache_content(system_content, model):
            # Content too small for caching, return as regular system prompt
            return [{
                "type": "text",
                "text": system_content
            }]
        
        # Enable caching for large system prompt
        return [{
            "type": "text", 
            "text": system_content,
            "cache_control": {"type": "ephemeral"}
        }]
    
    def create_cached_messages(self, messages: List[Dict[str, Any]], model: str = None) -> List[Dict[str, Any]]:
        """
        Process messages and add cache breakpoints for large content
        
        Args:
            messages: List of message dicts with role/content
            model: Model name for token threshold determination
            
        Returns:
            Messages with cache_control added where appropriate
        """
        processed_messages = []
        
        for message in messages:
            content = message.get("content", "")
            
            if isinstance(content, str) and self.should_cache_content(content, model):
                # Add cache control to large message content
                processed_message = message.copy()
                processed_message["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                processed_messages.append(processed_message)
            else:
                # Keep message as-is
                processed_messages.append(message)
        
        return processed_messages
    
    def create_council_session_prompt(self, base_context: str, model: str = None) -> List[Dict[str, Any]]:
        """
        Create a cached system prompt optimized for council sessions
        
        For council sessions, we want to cache the large base context so that
        each agent's query reuses the cached context with minimal input token cost.
        """
        if not base_context:
            return []
        
        # Always cache council session context (likely to be reused)
        return [{
            "type": "text",
            "text": base_context,
            "cache_control": {"type": "ephemeral"}
        }]
    
    def record_cache_usage(self, 
                          prompt_cache_key: str, 
                          is_cache_hit: bool,
                          input_tokens: int,
                          cached_tokens: int = 0,
                          cache_read_tokens: int = 0,
                          cost: Decimal = None,
                          cost_without_cache: Decimal = None):
        """
        Record cache usage statistics
        
        Args:
            prompt_cache_key: Internal cache key for tracking
            is_cache_hit: Whether this was a cache hit
            input_tokens: Total input tokens for this request
            cached_tokens: Number of tokens that were cached
            cache_read_tokens: Number of tokens read from cache at reduced cost
            cost: Actual cost paid
            cost_without_cache: What the cost would have been without caching
        """
        self.stats.total_requests += 1
        self.stats.total_input_tokens += input_tokens
        
        if is_cache_hit:
            self.stats.cache_hit_requests += 1
            self.stats.cache_read_tokens += cache_read_tokens
        else:
            self.stats.cache_creation_requests += 1
            self.stats.cached_tokens += cached_tokens
        
        if cost:
            self.stats.total_cost += Decimal(str(cost))
        
        if cost_without_cache:
            self.stats.cost_without_cache += Decimal(str(cost_without_cache))
            if cost:
                self.stats.cost_saved += Decimal(str(cost_without_cache)) - Decimal(str(cost))
        
        # Track known cache keys
        self._known_cache_keys[prompt_cache_key] = datetime.now()
    
    def is_known_cache_key(self, cache_key: str) -> bool:
        """Check if we've seen this cache pattern before (for statistics)"""
        return cache_key in self._known_cache_keys
    
    def cleanup_expired_tracking(self):
        """Clean up expired cache key tracking"""
        cutoff = datetime.now() - timedelta(seconds=self.config["cache_ttl_seconds"])
        expired_keys = [
            key for key, timestamp in self._known_cache_keys.items() 
            if timestamp < cutoff
        ]
        
        for key in expired_keys:
            del self._known_cache_keys[key]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        self.cleanup_expired_tracking()
        
        return {
            "total_requests": self.stats.total_requests,
            "cache_creation_requests": self.stats.cache_creation_requests,
            "cache_hit_requests": self.stats.cache_hit_requests,
            "cache_hit_rate": round(self.stats.cache_hit_rate, 4),
            
            "total_input_tokens": self.stats.total_input_tokens,
            "cached_tokens": self.stats.cached_tokens,
            "cache_read_tokens": self.stats.cache_read_tokens,
            "token_savings_rate": round(self.stats.token_savings_rate, 4),
            
            "total_cost_usd": float(self.stats.total_cost),
            "cost_without_cache_usd": float(self.stats.cost_without_cache),
            "cost_saved_usd": float(self.stats.cost_saved),
            "cost_savings_rate": round(self.stats.cost_savings_rate, 4),
            
            "active_cache_keys": len(self._known_cache_keys),
            "cache_ttl_seconds": self.config["cache_ttl_seconds"]
        }
    
    def clear_statistics(self):
        """Reset all statistics"""
        self.stats = CacheStatistics()
        self._known_cache_keys.clear()