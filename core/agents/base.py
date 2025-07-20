"""
Base Agent Class for NYX System

Provides core agent functionality with LLM integration, database persistence,
and comprehensive execution tracking.
"""
import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel
from database.connection import db_manager
from database.models import Agent, LLMInteraction
from config.settings import settings

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent execution states - must match database constraint values"""
    SPAWNED = "spawned"
    ACTIVE = "active"
    WAITING = "waiting"
    COORDINATING = "coordinating"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

@dataclass
class AgentResult:
    """Result of agent execution"""
    success: bool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'success': self.success,
            'content': self.content,
            'metadata': self.metadata,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'tokens_used': self.tokens_used,
            'cost_usd': self.cost_usd
        }

class BaseAgent(ABC):
    """
    Base class for all NYX agents
    
    Provides:
    - LLM integration with native caching
    - Database persistence and state tracking
    - Error handling and retry logic
    - Resource management and limits
    - Comprehensive execution logging
    """
    
    def __init__(
        self,
        agent_type: str,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True
    ):
        # Core identifiers
        self.id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.thought_tree_id = thought_tree_id
        self.parent_agent_id = parent_agent_id
        
        # Execution configuration
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.llm_model = llm_model
        self.use_native_caching = use_native_caching
        
        # State management
        self.state = AgentState.SPAWNED
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.retry_count = 0
        
        # LLM integration
        self.claude_api = ClaudeNativeAPI()
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        
    async def initialize(self) -> bool:
        """
        Initialize agent and persist to database
        Returns True if successful, False otherwise
        """
        try:
            await self._persist_agent_state()
            
            # Run agent-specific initialization
            initialization_success = await self._agent_specific_initialization()
            
            if initialization_success:
                self.state = AgentState.ACTIVE
                await self._persist_agent_state()
                logger.info(f"Agent {self.id} ({self.agent_type}) initialized successfully")
                return True
            else:
                self.state = AgentState.FAILED
                await self._persist_agent_state()
                logger.error(f"Agent {self.id} initialization failed")
                return False
                
        except Exception as e:
            self.state = AgentState.FAILED
            await self._persist_agent_state()
            logger.error(f"Agent {self.id} initialization error: {str(e)}")
            return False
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute agent task with comprehensive error handling and logging
        """
        execution_start = datetime.now()
        
        try:
            # Validate input
            if not await self._validate_input(input_data):
                return AgentResult(
                    success=False,
                    content="",
                    error_message="Input validation failed",
                    execution_time_ms=0
                )
            
            # Check agent state
            if self.state not in [AgentState.ACTIVE, AgentState.WAITING, AgentState.COORDINATING]:
                return AgentResult(
                    success=False,
                    content="",
                    error_message=f"Agent not in executable state: {self.state.value}",
                    execution_time_ms=0
                )
            
            # Keep agent in ACTIVE state during execution
            await self._persist_agent_state()
            
            # Execute with retry logic
            result = await self._execute_with_retries(input_data)
            
            # Update state based on result
            if result.success:
                self.state = AgentState.COMPLETED
            else:
                self.state = AgentState.FAILED
            
            await self._persist_agent_state()
            
            # Calculate execution time
            execution_end = datetime.now()
            result.execution_time_ms = int((execution_end - execution_start).total_seconds() * 1000)
            
            # Update tracking
            self.total_tokens_used += result.tokens_used
            self.total_cost_usd += result.cost_usd
            self.execution_history.append({
                'timestamp': execution_start,
                'input_data': input_data,
                'result': result.to_dict()
            })
            
            logger.info(f"Agent {self.id} execution completed: success={result.success}, tokens={result.tokens_used}, cost=${result.cost_usd:.6f}")
            
            return result
            
        except Exception as e:
            execution_end = datetime.now()
            execution_time = int((execution_end - execution_start).total_seconds() * 1000)
            
            self.state = AgentState.FAILED
            await self._persist_agent_state()
            
            error_result = AgentResult(
                success=False,
                content="",
                error_message=f"Execution error: {str(e)}",
                execution_time_ms=execution_time
            )
            
            logger.error(f"Agent {self.id} execution error: {str(e)}")
            return error_result
    
    async def _execute_with_retries(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute agent task with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.retry_count = attempt
                result = await asyncio.wait_for(
                    self._agent_specific_execution(input_data),
                    timeout=self.timeout_seconds
                )
                
                if result.success:
                    return result
                    
                # If not successful, prepare for retry
                last_error = result.error_message
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** attempt, 30))  # Exponential backoff
                    
            except asyncio.TimeoutError:
                last_error = f"Execution timeout after {self.timeout_seconds} seconds"
                logger.warning(f"Agent {self.id} timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Agent {self.id} error on attempt {attempt + 1}: {str(e)}")
                
            if attempt < self.max_retries:
                await asyncio.sleep(min(2 ** attempt, 30))
        
        # All retries exhausted
        return AgentResult(
            success=False,
            content="",
            error_message=f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}",
            execution_time_ms=0
        )
    
    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AgentResult:
        """
        Make LLM call with proper integration to native caching system
        """
        try:
            response = await self.claude_api.call_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                thought_tree_id=self.thought_tree_id,
                agent_id=self.id,
                use_native_caching=self.use_native_caching
            )
            
            if response.success:
                return AgentResult(
                    success=True,
                    content=response.content,
                    tokens_used=response.usage.total_tokens,
                    cost_usd=float(response.usage.cost_usd),
                    metadata={
                        'model': self.llm_model.value,
                        'cache_hit': getattr(response, 'cache_hit', False),
                        'input_tokens': response.usage.input_tokens,
                        'output_tokens': response.usage.output_tokens
                    }
                )
            else:
                return AgentResult(
                    success=False,
                    content="",
                    error_message=response.error_message or "LLM call failed",
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                    cost_usd=float(response.usage.cost_usd) if response.usage else 0.0
                )
                
        except Exception as e:
            logger.error(f"Agent {self.id} LLM call error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"LLM integration error: {str(e)}",
                tokens_used=0,
                cost_usd=0.0
            )
    
    async def _persist_agent_state(self):
        """Persist current agent state to database"""
        try:
            async with db_manager.get_async_session() as session:
                # Check if agent exists
                from sqlalchemy import select
                result = await session.execute(
                    select(Agent).filter(Agent.id == self.id)
                )
                existing_agent = result.scalar_one_or_none()
                
                if existing_agent:
                    # Update existing agent
                    existing_agent.status = self.state.value
                    existing_agent.completed_at = datetime.now() if self.state.value in ['completed', 'failed', 'terminated'] else None
                    existing_agent.state = {'current_state': self.state.value, 'retry_count': self.retry_count}
                    existing_agent.context = {
                        'execution_history_count': len(self.execution_history),
                        'total_tokens_used': self.total_tokens_used,
                        'total_cost_usd': self.total_cost_usd,
                        'llm_model': self.llm_model.value,
                        'max_retries': self.max_retries,
                        'timeout_seconds': self.timeout_seconds,
                        'use_native_caching': self.use_native_caching
                    }
                else:
                    # Create new agent - must provide required fields
                    # Ensure we have a valid thought tree ID
                    if not self.thought_tree_id:
                        # Create a default thought tree for agent testing
                        from database.models import ThoughtTree
                        import uuid
                        self.thought_tree_id = str(uuid.uuid4())
                        
                        default_tree = ThoughtTree(
                            id=self.thought_tree_id,
                            goal=f"Agent {self.agent_type} operations",
                            status="in_progress",
                            depth=1
                        )
                        session.add(default_tree)
                        await session.flush()  # Ensure tree is created before agent
                    
                    new_agent = Agent(
                        id=self.id,
                        thought_tree_id=self.thought_tree_id,
                        agent_type=self.agent_type,
                        agent_class=self.__class__.__name__,
                        status=self.state.value,
                        spawned_by=self.parent_agent_id,
                        created_at=self.created_at,
                        completed_at=None,
                        context={
                            'max_retries': self.max_retries,
                            'timeout_seconds': self.timeout_seconds,
                            'llm_model': self.llm_model.value,
                            'use_native_caching': self.use_native_caching
                        },
                        state={'current_state': self.state.value, 'retry_count': self.retry_count}
                    )
                    session.add(new_agent)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to persist agent {self.id} state: {str(e)}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics"""
        return {
            'agent_id': self.id,
            'agent_type': self.agent_type,
            'state': self.state.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'total_executions': len(self.execution_history),
            'total_tokens_used': self.total_tokens_used,
            'total_cost_usd': self.total_cost_usd,
            'retry_count': self.retry_count,
            'success_rate': self._calculate_success_rate(),
            'average_execution_time_ms': self._calculate_average_execution_time()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate from execution history"""
        if not self.execution_history:
            return 0.0
        successful = sum(1 for exec in self.execution_history if exec['result']['success'])
        return successful / len(self.execution_history)
    
    def _calculate_average_execution_time(self) -> float:
        """Calculate average execution time from history"""
        if not self.execution_history:
            return 0.0
        total_time = sum(exec['result']['execution_time_ms'] for exec in self.execution_history)
        return total_time / len(self.execution_history)
    
    # Abstract methods for subclasses to implement
    
    @abstractmethod
    async def _agent_specific_initialization(self) -> bool:
        """Agent-specific initialization logic"""
        pass
    
    @abstractmethod
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for agent execution"""
        pass
    
    @abstractmethod
    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Agent-specific execution logic"""
        pass
    
    async def transition_to_waiting(self):
        """Transition agent to WAITING state for recursive coordination"""
        if self.state != AgentState.ACTIVE:
            raise RuntimeError(f"Cannot transition to WAITING from {self.state.value}")
        
        self.state = AgentState.WAITING
        await self._persist_agent_state()
        logger.info(f"Agent {self.id} ({self.agent_type}) entered WAITING state")
    
    async def transition_to_coordinating(self):
        """Transition agent to COORDINATING state for result aggregation"""
        if self.state != AgentState.WAITING:
            raise RuntimeError(f"Cannot transition to COORDINATING from {self.state.value}")
        
        self.state = AgentState.COORDINATING
        await self._persist_agent_state()
        logger.info(f"Agent {self.id} ({self.agent_type}) entered COORDINATING state")
    
    async def return_to_active(self):
        """Return agent to ACTIVE state for continued execution"""
        if self.state not in [AgentState.WAITING, AgentState.COORDINATING]:
            raise RuntimeError(f"Cannot return to ACTIVE from {self.state.value}")
        
        self.state = AgentState.ACTIVE
        await self._persist_agent_state()
        logger.info(f"Agent {self.id} ({self.agent_type}) returned to ACTIVE state")

    async def terminate(self):
        """Gracefully terminate agent"""
        self.state = AgentState.TERMINATED
        await self._persist_agent_state()
        logger.info(f"Agent {self.id} ({self.agent_type}) terminated")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id[:8]}..., type={self.agent_type}, state={self.state.value})>"