"""
Base Tool Class for NYX System

Provides core tool functionality with database persistence, safety validation,
and comprehensive execution tracking following NYX agent patterns.
"""
import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

from database.connection import db_manager
from database.models import ToolExecution
from config.settings import settings

logger = logging.getLogger(__name__)

class ToolState(Enum):
    """Tool execution states"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ToolResult:
    """Result of tool execution following AgentResult pattern"""
    success: bool
    output: str
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'success': self.success,
            'output': self.output,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'metadata': self.metadata,
            'stdout': self.stdout,
            'stderr': self.stderr
        }

class BaseTool(ABC):
    """
    Base class for all NYX tools
    
    Provides:
    - Database persistence and execution tracking
    - Safety validation and error handling
    - Resource management and timeouts
    - Integration with existing agent patterns
    """
    
    def __init__(
        self,
        tool_name: str,
        agent_id: Optional[str] = None,
        thought_tree_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: int = 3
    ):
        # Core identifiers
        self.id = str(uuid.uuid4())
        self.tool_name = tool_name
        self.agent_id = agent_id
        self.thought_tree_id = thought_tree_id
        
        # Execution configuration
        self.timeout_seconds = timeout_seconds or settings.tool_timeout_seconds
        self.max_retries = max_retries
        
        # State management
        self.state = ToolState.IDLE
        self.created_at = datetime.now()
        self.retry_count = 0
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        
    async def execute(
        self, 
        parameters: Dict[str, Any],
        agent_id: Optional[str] = None,
        thought_tree_id: Optional[str] = None
    ) -> ToolResult:
        """
        Execute tool with comprehensive error handling and logging
        """
        execution_start = datetime.now()
        
        # Use provided IDs or fall back to instance defaults
        agent_id = agent_id or self.agent_id
        thought_tree_id = thought_tree_id or self.thought_tree_id
        
        try:
            # Validate parameters
            if not await self._validate_parameters(parameters):
                return ToolResult(
                    success=False,
                    output="",
                    error_message="Parameter validation failed",
                    execution_time_ms=0
                )
            
            # Check safety constraints
            if not await self._validate_safety(parameters):
                return ToolResult(
                    success=False,
                    output="",
                    error_message="Safety validation failed",
                    execution_time_ms=0
                )
            
            # Update state
            self.state = ToolState.RUNNING
            
            # Execute with retry logic and logging
            result = await self._execute_with_retries_and_logging(
                parameters, agent_id, thought_tree_id
            )
            
            # Update state based on result
            if result.success:
                self.state = ToolState.COMPLETED
            else:
                self.state = ToolState.FAILED
            
            # Calculate execution time
            execution_end = datetime.now()
            result.execution_time_ms = int((execution_end - execution_start).total_seconds() * 1000)
            
            # Update tracking
            self.execution_history.append({
                'timestamp': execution_start,
                'parameters': parameters,
                'result': result.to_dict()
            })
            
            logger.info(f"Tool {self.tool_name} execution completed: success={result.success}, time={result.execution_time_ms}ms")
            
            return result
            
        except Exception as e:
            execution_end = datetime.now()
            execution_time = int((execution_end - execution_start).total_seconds() * 1000)
            
            self.state = ToolState.FAILED
            
            error_result = ToolResult(
                success=False,
                output="",
                error_message=f"Tool execution error: {str(e)}",
                execution_time_ms=execution_time
            )
            
            # Log error to database
            await self._log_tool_execution(
                parameters, error_result, agent_id, thought_tree_id, execution_start
            )
            
            logger.error(f"Tool {self.tool_name} execution error: {str(e)}")
            return error_result
    
    async def _execute_with_retries_and_logging(
        self,
        parameters: Dict[str, Any],
        agent_id: Optional[str],
        thought_tree_id: Optional[str]
    ) -> ToolResult:
        """Execute tool with retry logic and database logging"""
        last_error = None
        execution_start = datetime.now()
        
        for attempt in range(self.max_retries + 1):
            try:
                self.retry_count = attempt
                result = await asyncio.wait_for(
                    self._tool_specific_execution(parameters),
                    timeout=self.timeout_seconds
                )
                
                # Log successful execution to database
                await self._log_tool_execution(
                    parameters, result, agent_id, thought_tree_id, execution_start
                )
                
                if result.success:
                    return result
                    
                # If not successful, prepare for retry
                last_error = result.error_message
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
                    
            except asyncio.TimeoutError:
                self.state = ToolState.TIMEOUT
                last_error = f"Tool execution timeout after {self.timeout_seconds} seconds"
                logger.warning(f"Tool {self.tool_name} timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Tool {self.tool_name} error on attempt {attempt + 1}: {str(e)}")
                
            if attempt < self.max_retries:
                await asyncio.sleep(min(2 ** attempt, 10))
        
        # All retries exhausted
        failed_result = ToolResult(
            success=False,
            output="",
            error_message=f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}",
            execution_time_ms=0
        )
        
        # Log failed execution
        await self._log_tool_execution(
            parameters, failed_result, agent_id, thought_tree_id, execution_start
        )
        
        return failed_result
    
    async def _log_tool_execution(
        self,
        parameters: Dict[str, Any],
        result: ToolResult,
        agent_id: Optional[str],
        thought_tree_id: Optional[str],
        started_at: datetime
    ):
        """Log tool execution to database following existing patterns"""
        try:
            from database.models import ThoughtTree, Agent, ToolExecution
            import uuid as uuid_module
            from sqlalchemy import select
            
            # Handle all database operations in a single session to ensure consistency
            async with db_manager.get_async_session() as session:
                # Convert string UUIDs to UUID objects for database operations
                thought_tree_uuid = None
                agent_uuid = None
                
                # Handle ThoughtTree - check existence and create if needed
                if thought_tree_id:
                    thought_tree_uuid = uuid_module.UUID(thought_tree_id) if isinstance(thought_tree_id, str) else thought_tree_id
                    # Check if exists
                    thought_tree_result = await session.execute(
                        select(ThoughtTree).filter(ThoughtTree.id == thought_tree_uuid)
                    )
                    existing_thought_tree = thought_tree_result.scalar_one_or_none()
                    
                    if not existing_thought_tree:
                        # Create new ThoughtTree
                        default_tree = ThoughtTree(
                            id=thought_tree_uuid,
                            goal=f"Tool {self.tool_name} operations",
                            status="in_progress",
                            depth=1
                        )
                        session.add(default_tree)
                        await session.flush()  # Ensure it's available for agent creation
                else:
                    # Create new ThoughtTree if none provided
                    thought_tree_uuid = uuid_module.uuid4()
                    thought_tree_id = str(thought_tree_uuid)
                    default_tree = ThoughtTree(
                        id=thought_tree_uuid,
                        goal=f"Tool {self.tool_name} operations",
                        status="in_progress",
                        depth=1
                    )
                    session.add(default_tree)
                    await session.flush()
                
                # Handle Agent - check existence and create if needed
                if agent_id:
                    agent_uuid = uuid_module.UUID(agent_id) if isinstance(agent_id, str) else agent_id
                    # Check if exists
                    agent_result = await session.execute(
                        select(Agent).filter(Agent.id == agent_uuid)
                    )
                    existing_agent = agent_result.scalar_one_or_none()
                    
                    if not existing_agent:
                        # Create new Agent
                        temp_agent = Agent(
                            id=agent_uuid,
                            thought_tree_id=thought_tree_uuid,
                            agent_type="task",
                            agent_class="ToolAgent",
                            status="active",
                            spawned_by=None,
                            context={
                                'tool_name': self.tool_name,
                                'tool_class': self.__class__.__name__,
                                'created_for_tool_execution': True
                            },
                            state={'current_state': 'active'}
                        )
                        session.add(temp_agent)
                        await session.flush()
                else:
                    # Create new Agent if none provided
                    agent_uuid = uuid_module.uuid4()
                    agent_id = str(agent_uuid)
                    temp_agent = Agent(
                        id=agent_uuid,
                        thought_tree_id=thought_tree_uuid,
                        agent_type="task",
                        agent_class="ToolAgent", 
                        status="active",
                        spawned_by=None,
                        context={
                            'tool_name': self.tool_name,
                            'tool_class': self.__class__.__name__,
                            'created_for_tool_execution': True
                        },
                        state={'current_state': 'active'}
                    )
                    session.add(temp_agent)
                    await session.flush()
                
                # Create the ToolExecution record with valid references
                tool_execution = ToolExecution(
                    id=uuid_module.uuid4(),
                    agent_id=agent_uuid,
                    thought_tree_id=thought_tree_uuid,
                    tool_name=self.tool_name,
                    tool_class=self.__class__.__name__,
                    input_parameters=parameters,
                    output_result=result.to_dict(),
                    stdout=result.stdout,
                    stderr=result.stderr,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    duration_ms=result.execution_time_ms
                )
                
                session.add(tool_execution)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log tool execution for {self.tool_name}: {str(e)}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tool statistics following agent pattern"""
        return {
            'tool_id': self.id,
            'tool_name': self.tool_name,
            'tool_class': self.__class__.__name__,
            'state': self.state.value,
            'created_at': self.created_at,
            'total_executions': len(self.execution_history),
            'retry_count': self.retry_count,
            'success_rate': self._calculate_success_rate(),
            'average_execution_time_ms': self._calculate_average_execution_time(),
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries
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
    async def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters for tool execution"""
        pass
    
    @abstractmethod
    async def _validate_safety(self, parameters: Dict[str, Any]) -> bool:
        """Validate safety constraints for tool execution"""
        pass
    
    @abstractmethod
    async def _tool_specific_execution(self, parameters: Dict[str, Any]) -> ToolResult:
        """Tool-specific execution logic"""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id[:8]}..., name={self.tool_name}, state={self.state.value})>"