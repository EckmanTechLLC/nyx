"""
Memory Agent Implementation for NYX System

Memory agents handle context persistence, feedback integration, retrieval from
thought trees, and cross-agent context sharing for the NYX system.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .base import BaseAgent, AgentResult
from llm.models import LLMModel
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, AgentCommunication

logger = logging.getLogger(__name__)

class MemoryScope(Enum):
    """Scope of memory operations"""
    AGENT = "agent"           # Single agent memory
    SESSION = "session"       # Session-specific memory
    THOUGHT_TREE = "thought_tree"  # Thought tree memory
    GLOBAL = "global"         # Cross-agent global memory

class MemoryType(Enum):
    """Types of memory content"""
    CONTEXT = "context"       # Contextual information
    LEARNING = "learning"     # Learning and feedback
    COMMUNICATION = "communication"  # Inter-agent communications
    DECISION = "decision"     # Decision history and rationale
    PERFORMANCE = "performance"  # Performance metrics and feedback

@dataclass
class MemoryEntry:
    """Represents a memory entry"""
    id: str
    memory_type: MemoryType
    scope: MemoryScope
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    relevance_score: float = 1.0
    access_count: int = 0

@dataclass
class MemoryQuery:
    """Query for memory retrieval"""
    query_text: str
    memory_types: List[MemoryType] = None
    scopes: List[MemoryScope] = None
    time_range: Tuple[datetime, datetime] = None
    max_results: int = 10
    min_relevance_score: float = 0.5

class MemoryAgent(BaseAgent):
    """
    Memory Agent for context management and persistence
    
    Features:
    - Context persistence across sessions and agents
    - Intelligent memory retrieval with relevance scoring
    - Cross-agent context sharing and communication
    - Learning integration and feedback processing
    - Memory optimization and pruning
    - Thought tree integration for hierarchical memory
    """
    
    def __init__(
        self,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 2,
        timeout_seconds: int = 240,
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True,
        memory_retention_days: int = 30,
        max_memory_entries: int = 1000
    ):
        super().__init__(
            agent_type="memory",
            thought_tree_id=thought_tree_id,
            parent_agent_id=parent_agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            llm_model=llm_model,
            use_native_caching=use_native_caching
        )
        
        # Memory-specific configuration
        self.memory_retention_days = memory_retention_days
        self.max_memory_entries = max_memory_entries
        
        # In-memory cache for frequently accessed memories
        self.memory_cache: Dict[str, MemoryEntry] = {}
        self.cache_max_size = 100
        
        # Memory operation tracking
        self.operation_history: List[Dict[str, Any]] = []
    
    async def _agent_specific_initialization(self) -> bool:
        """Initialize memory agent"""
        try:
            logger.info(f"MemoryAgent {self.id} initializing with retention: {self.memory_retention_days} days, max entries: {self.max_memory_entries}")
            
            # Initialize memory structures if needed
            await self._ensure_thought_tree_exists()
            
            return True
        except Exception as e:
            logger.error(f"MemoryAgent {self.id} initialization failed: {str(e)}")
            return False
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input for memory operations"""
        operation = input_data.get('operation')
        if not operation:
            logger.error(f"MemoryAgent {self.id}: No operation specified")
            return False
        
        valid_operations = ['store', 'retrieve', 'update', 'delete', 'search', 'summarize']
        if operation not in valid_operations:
            logger.error(f"MemoryAgent {self.id}: Invalid operation '{operation}'. Valid: {valid_operations}")
            return False
        
        return True
    
    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute memory operation"""
        operation = input_data['operation']
        
        # Route to specific operation handler
        operation_handlers = {
            'store': self._handle_store_memory,
            'retrieve': self._handle_retrieve_memory,
            'update': self._handle_update_memory,
            'delete': self._handle_delete_memory,
            'search': self._handle_search_memory,
            'summarize': self._handle_summarize_memory
        }
        
        handler = operation_handlers.get(operation)
        if not handler:
            return AgentResult(
                success=False,
                content="",
                error_message=f"No handler found for operation: {operation}"
            )
        
        return await handler(input_data)
    
    async def _handle_store_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Store memory entry"""
        try:
            required_fields = ['content', 'memory_type', 'scope']
            for field in required_fields:
                if field not in input_data:
                    return AgentResult(
                        success=False,
                        content="",
                        error_message=f"Missing required field for store operation: {field}"
                    )
            
            # Create memory entry
            import uuid
            memory_entry = MemoryEntry(
                id=str(uuid.uuid4()),
                memory_type=MemoryType(input_data['memory_type']),
                scope=MemoryScope(input_data['scope']),
                content=input_data['content'],
                metadata=input_data.get('metadata', {}),
                timestamp=datetime.now(),
                relevance_score=input_data.get('relevance_score', 1.0)
            )
            
            # Store in database
            await self._persist_memory_entry(memory_entry)
            
            # Add to cache if high relevance
            if memory_entry.relevance_score > 0.7:
                self._add_to_cache(memory_entry)
            
            # Track operation
            self.operation_history.append({
                'operation': 'store',
                'timestamp': datetime.now(),
                'memory_id': memory_entry.id,
                'success': True
            })
            
            return AgentResult(
                success=True,
                content=f"Memory stored successfully with ID: {memory_entry.id}",
                metadata={
                    'memory_id': memory_entry.id,
                    'memory_type': memory_entry.memory_type.value,
                    'scope': memory_entry.scope.value,
                    'relevance_score': memory_entry.relevance_score
                }
            )
            
        except Exception as e:
            logger.error(f"MemoryAgent {self.id} store operation error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Store operation failed: {str(e)}"
            )
    
    async def _handle_retrieve_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Retrieve specific memory entry"""
        try:
            memory_id = input_data.get('memory_id')
            if not memory_id:
                return AgentResult(
                    success=False,
                    content="",
                    error_message="Memory ID required for retrieve operation"
                )
            
            # Check cache first
            if memory_id in self.memory_cache:
                memory_entry = self.memory_cache[memory_id]
                memory_entry.access_count += 1
                
                return AgentResult(
                    success=True,
                    content=memory_entry.content,
                    metadata={
                        'memory_id': memory_entry.id,
                        'memory_type': memory_entry.memory_type.value,
                        'scope': memory_entry.scope.value,
                        'timestamp': memory_entry.timestamp.isoformat(),
                        'relevance_score': memory_entry.relevance_score,
                        'access_count': memory_entry.access_count,
                        'source': 'cache'
                    }
                )
            
            # Retrieve from database
            memory_entry = await self._load_memory_entry(memory_id)
            if memory_entry:
                memory_entry.access_count += 1
                self._add_to_cache(memory_entry)
                
                return AgentResult(
                    success=True,
                    content=memory_entry.content,
                    metadata={
                        'memory_id': memory_entry.id,
                        'memory_type': memory_entry.memory_type.value,
                        'scope': memory_entry.scope.value,
                        'timestamp': memory_entry.timestamp.isoformat(),
                        'relevance_score': memory_entry.relevance_score,
                        'access_count': memory_entry.access_count,
                        'source': 'database'
                    }
                )
            else:
                return AgentResult(
                    success=False,
                    content="",
                    error_message=f"Memory entry not found: {memory_id}"
                )
                
        except Exception as e:
            logger.error(f"MemoryAgent {self.id} retrieve operation error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Retrieve operation failed: {str(e)}"
            )
    
    async def _handle_search_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Search memories using intelligent matching"""
        try:
            query_text = input_data.get('query_text')
            if not query_text:
                return AgentResult(
                    success=False,
                    content="",
                    error_message="Query text required for search operation"
                )
            
            # Create memory query
            memory_query = MemoryQuery(
                query_text=query_text,
                memory_types=[MemoryType(t) for t in input_data.get('memory_types', [])] if input_data.get('memory_types') else None,
                scopes=[MemoryScope(s) for s in input_data.get('scopes', [])] if input_data.get('scopes') else None,
                max_results=input_data.get('max_results', 10),
                min_relevance_score=input_data.get('min_relevance_score', 0.5)
            )
            
            # Perform search
            search_results = await self._search_memories(memory_query)
            
            if search_results:
                # Format results
                formatted_results = []
                for memory_entry, relevance_score in search_results:
                    formatted_results.append({
                        'memory_id': memory_entry.id,
                        'content': memory_entry.content,
                        'memory_type': memory_entry.memory_type.value,
                        'scope': memory_entry.scope.value,
                        'timestamp': memory_entry.timestamp.isoformat(),
                        'relevance_score': relevance_score
                    })
                
                return AgentResult(
                    success=True,
                    content=json.dumps(formatted_results, indent=2),
                    metadata={
                        'query_text': query_text,
                        'results_count': len(formatted_results),
                        'search_parameters': {
                            'memory_types': [t.value for t in memory_query.memory_types] if memory_query.memory_types else None,
                            'scopes': [s.value for s in memory_query.scopes] if memory_query.scopes else None,
                            'max_results': memory_query.max_results,
                            'min_relevance_score': memory_query.min_relevance_score
                        }
                    }
                )
            else:
                return AgentResult(
                    success=True,
                    content="No matching memories found",
                    metadata={'query_text': query_text, 'results_count': 0}
                )
                
        except Exception as e:
            logger.error(f"MemoryAgent {self.id} search operation error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Search operation failed: {str(e)}"
            )
    
    async def _handle_summarize_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Summarize memories using LLM"""
        try:
            # Get memories to summarize
            scope = input_data.get('scope', 'thought_tree')
            memory_types = input_data.get('memory_types', ['context', 'decision', 'learning'])
            time_range_days = input_data.get('time_range_days', 7)
            
            # Search for relevant memories
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_range_days)
            
            search_query = MemoryQuery(
                query_text=input_data.get('summary_focus', 'all activities and decisions'),
                memory_types=[MemoryType(t) for t in memory_types],
                scopes=[MemoryScope(scope)],
                time_range=(start_time, end_time),
                max_results=input_data.get('max_memories', 20),
                min_relevance_score=0.3
            )
            
            memories = await self._search_memories(search_query)
            
            if not memories:
                return AgentResult(
                    success=True,
                    content="No memories found in the specified time range for summarization.",
                    metadata={'time_range_days': time_range_days, 'memories_found': 0}
                )
            
            # Prepare memories for LLM summarization
            memory_content = []
            for memory_entry, _ in memories:
                memory_content.append({
                    'timestamp': memory_entry.timestamp.isoformat(),
                    'type': memory_entry.memory_type.value,
                    'scope': memory_entry.scope.value,
                    'content': memory_entry.content
                })
            
            # Generate summary using LLM
            system_prompt = """You are an expert memory analyst specializing in creating concise, actionable summaries of agent activities and learnings.

Your task is to analyze memory entries and create a comprehensive summary that highlights:
1. Key decisions and their outcomes
2. Important context and learnings
3. Patterns and trends
4. Notable successes and failures
5. Actionable insights for future operations

Focus on extracting the most valuable information and presenting it in a clear, organized manner."""

            user_prompt = f"""Analyze and summarize the following memory entries from the past {time_range_days} days:

MEMORIES TO SUMMARIZE:
{json.dumps(memory_content, indent=2)}

SUMMARY PARAMETERS:
- Scope: {scope}
- Memory Types: {memory_types}
- Total Memories: {len(memories)}
- Time Range: {time_range_days} days

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Decisions and Actions
3. Important Learnings and Context
4. Performance Insights
5. Recommendations for Future Operations

Structure the summary for clarity and actionability."""

            llm_result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=input_data.get('max_tokens', 2048),
                temperature=0.5
            )
            
            if llm_result.success:
                return AgentResult(
                    success=True,
                    content=llm_result.content,
                    tokens_used=llm_result.tokens_used,
                    cost_usd=llm_result.cost_usd,
                    metadata={
                        'summarized_memories': len(memories),
                        'time_range_days': time_range_days,
                        'memory_types': memory_types,
                        'scope': scope
                    }
                )
            else:
                return AgentResult(
                    success=False,
                    content="",
                    error_message=f"LLM summarization failed: {llm_result.error_message}"
                )
                
        except Exception as e:
            logger.error(f"MemoryAgent {self.id} summarize operation error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Summarize operation failed: {str(e)}"
            )
    
    async def _handle_update_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Update existing memory entry"""
        # Implementation for updating memory entries
        return AgentResult(
            success=False,
            content="",
            error_message="Update operation not yet implemented"
        )
    
    async def _handle_delete_memory(self, input_data: Dict[str, Any]) -> AgentResult:
        """Delete memory entry"""
        # Implementation for deleting memory entries
        return AgentResult(
            success=False,
            content="",
            error_message="Delete operation not yet implemented"
        )
    
    async def _search_memories(self, query: MemoryQuery) -> List[Tuple[MemoryEntry, float]]:
        """Search memories and return results with relevance scores"""
        # For now, return empty list - full implementation would involve:
        # 1. Database query based on filters
        # 2. LLM-based semantic similarity scoring
        # 3. Ranking and filtering by relevance
        return []
    
    async def _persist_memory_entry(self, memory_entry: MemoryEntry):
        """Persist memory entry to database"""
        try:
            async with db_manager.get_async_session() as session:
                # Store memory as agent communication for now
                # (In production, you might want a dedicated memory table)
                communication = AgentCommunication(
                    id=memory_entry.id,
                    sender_agent_id=self.id,
                    receiver_agent_id=None,  # Null for memory entries
                    thought_tree_id=self.thought_tree_id,
                    message_type="context_share",
                    content={
                        'text': memory_entry.content,
                        'memory_type': memory_entry.memory_type.value,
                        'scope': memory_entry.scope.value,
                        'relevance_score': memory_entry.relevance_score,
                        'access_count': memory_entry.access_count,
                        'memory_metadata': memory_entry.metadata
                    }
                )
                
                session.add(communication)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to persist memory entry {memory_entry.id}: {str(e)}")
            raise
    
    async def _load_memory_entry(self, memory_id: str) -> Optional[MemoryEntry]:
        """Load memory entry from database"""
        try:
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                
                result = await session.execute(
                    select(AgentCommunication)
                    .filter(AgentCommunication.id == memory_id)
                    .filter(AgentCommunication.message_type == "memory")
                )
                
                communication = result.scalar_one_or_none()
                
                if communication and communication.metadata_:
                    return MemoryEntry(
                        id=communication.id,
                        memory_type=MemoryType(communication.metadata_.get('memory_type', 'context')),
                        scope=MemoryScope(communication.metadata_.get('scope', 'agent')),
                        content=communication.content,
                        metadata=communication.metadata_.get('memory_metadata', {}),
                        timestamp=communication.timestamp,
                        relevance_score=communication.metadata_.get('relevance_score', 1.0),
                        access_count=communication.metadata_.get('access_count', 0)
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to load memory entry {memory_id}: {str(e)}")
            return None
    
    def _add_to_cache(self, memory_entry: MemoryEntry):
        """Add memory entry to cache"""
        if len(self.memory_cache) >= self.cache_max_size:
            # Remove least recently used entry
            lru_key = min(self.memory_cache.keys(), 
                         key=lambda k: self.memory_cache[k].access_count)
            del self.memory_cache[lru_key]
        
        self.memory_cache[memory_entry.id] = memory_entry
    
    async def _ensure_thought_tree_exists(self):
        """Ensure thought tree exists for memory operations"""
        if not self.thought_tree_id:
            return
            
        try:
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                
                result = await session.execute(
                    select(ThoughtTree).filter(ThoughtTree.id == self.thought_tree_id)
                )
                existing_tree = result.scalar_one_or_none()
                
                if not existing_tree:
                    new_tree = ThoughtTree(
                        id=self.thought_tree_id,
                        goal="Memory Management",
                        status="active",
                        metadata_={'managed_by_memory_agent': self.id},
                        depth=1
                    )
                    session.add(new_tree)
                    await session.commit()
                    
        except Exception as e:
            logger.warning(f"Failed to ensure thought tree exists: {str(e)}")
    
    # Convenience methods for common memory operations
    
    async def store_context(self, content: str, metadata: Dict[str, Any] = None) -> AgentResult:
        """Store contextual information"""
        return await self.execute({
            'operation': 'store',
            'content': content,
            'memory_type': 'context',
            'scope': 'thought_tree',
            'metadata': metadata or {}
        })
    
    async def store_learning(self, content: str, relevance_score: float = 0.8, metadata: Dict[str, Any] = None) -> AgentResult:
        """Store learning or feedback information"""
        return await self.execute({
            'operation': 'store',
            'content': content,
            'memory_type': 'learning',
            'scope': 'global',
            'relevance_score': relevance_score,
            'metadata': metadata or {}
        })
    
    async def search_context(self, query: str, max_results: int = 5) -> AgentResult:
        """Search for relevant context"""
        return await self.execute({
            'operation': 'search',
            'query_text': query,
            'memory_types': ['context'],
            'scopes': ['thought_tree', 'session'],
            'max_results': max_results
        })
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory agent statistics"""
        base_stats = await self.get_statistics()
        
        memory_stats = {
            'memory_retention_days': self.memory_retention_days,
            'max_memory_entries': self.max_memory_entries,
            'cache_size': len(self.memory_cache),
            'cache_max_size': self.cache_max_size,
            'total_operations': len(self.operation_history),
            'successful_operations': len([op for op in self.operation_history if op.get('success', False)])
        }
        
        return {**base_stats, **memory_stats}