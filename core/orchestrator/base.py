"""
Base Orchestrator Class for NYX System

Provides core orchestration functionality with agent lifecycle management,
resource tracking, and workflow coordination.
"""
import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from core.agents.base import BaseAgent, AgentState, AgentResult
from core.agents.task import TaskAgent
from core.agents.council import CouncilAgent
from core.agents.validator import ValidatorAgent
from core.agents.memory import MemoryAgent
from database.connection import db_manager
from database.models import Orchestrator, ThoughtTree
from config.settings import settings

logger = logging.getLogger(__name__)

class OrchestratorState(Enum):
    """Orchestrator execution states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

@dataclass
class OrchestratorResult:
    """Result of orchestrator execution"""
    success: bool
    workflow_id: str
    agents_spawned: int
    agents_completed: int
    agents_failed: int
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseOrchestrator(ABC):
    """
    Base class for all NYX orchestrators
    
    Provides:
    - Agent lifecycle management and spawning
    - Resource tracking and limits enforcement
    - Database persistence and state management
    - Context sharing across agent hierarchies
    - Error handling and recovery coordination
    """
    
    def __init__(
        self,
        orchestrator_type: str,
        thought_tree_id: Optional[str] = None,
        parent_orchestrator_id: Optional[str] = None,
        max_concurrent_agents: int = 10,
        global_context: Optional[Dict[str, Any]] = None
    ):
        # Core identifiers
        self.id = str(uuid.uuid4())
        self.orchestrator_type = orchestrator_type
        self.thought_tree_id = thought_tree_id
        self.parent_orchestrator_id = parent_orchestrator_id
        
        # Resource management
        self.max_concurrent_agents = max_concurrent_agents
        self.current_active_agents = 0
        
        # State management
        self.state = OrchestratorState.INITIALIZING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Context and agent tracking
        self.global_context = global_context or {}
        self.spawned_agents: List[BaseAgent] = []
        self.completed_agents: List[BaseAgent] = []
        self.failed_agents: List[BaseAgent] = []
        
        # Execution metrics
        self.total_cost_usd = 0.0
        self.total_tokens = 0
        self.execution_start_time = None
        
    async def initialize(self) -> bool:
        """
        Initialize orchestrator and create thought tree if needed
        Returns True if successful, False otherwise
        """
        try:
            self.execution_start_time = datetime.now()
            
            # Create thought tree if not provided
            if not self.thought_tree_id:
                await self._create_thought_tree()
            
            # Persist orchestrator to database
            await self._persist_orchestrator_state()
            
            # Run orchestrator-specific initialization
            initialization_success = await self._orchestrator_specific_initialization()
            
            if initialization_success:
                self.state = OrchestratorState.ACTIVE
                await self._persist_orchestrator_state()
                logger.info(f"Orchestrator {self.id} ({self.orchestrator_type}) initialized successfully")
                return True
            else:
                self.state = OrchestratorState.FAILED
                await self._persist_orchestrator_state()
                logger.error(f"Orchestrator {self.id} initialization failed")
                return False
                
        except Exception as e:
            self.state = OrchestratorState.FAILED
            await self._persist_orchestrator_state()
            logger.error(f"Orchestrator {self.id} initialization error: {str(e)}")
            return False
    
    async def spawn_agent(
        self,
        agent_type: str,
        task_context: Dict[str, Any],
        parent_agent_id: Optional[str] = None
    ) -> Optional[BaseAgent]:
        """
        Spawn agent with orchestrator context integration
        
        Args:
            agent_type: "task", "council", "validator", "memory"
            task_context: Task-specific configuration
            parent_agent_id: For recursive agent hierarchies
        
        Returns:
            Spawned agent or None if failed
        """
        try:
            # Check resource availability
            if not await self._check_resource_availability():
                logger.warning(f"Orchestrator {self.id} at agent limit ({self.current_active_agents}/{self.max_concurrent_agents})")
                return None
            
            # Create agent with orchestrator context
            agent_params = {
                'thought_tree_id': self.thought_tree_id,
                'parent_agent_id': parent_agent_id,
                'max_retries': task_context.get('max_retries', 3),
                'timeout_seconds': task_context.get('timeout', 300)
            }
            
            # Spawn appropriate agent type
            agent = None
            if agent_type == "task":
                agent = TaskAgent(**agent_params)
            elif agent_type == "council":
                agent = CouncilAgent(**agent_params)
            elif agent_type == "validator":
                agent = ValidatorAgent(**agent_params)
            elif agent_type == "memory":
                agent = MemoryAgent(**agent_params)
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return None
            
            # Initialize agent
            if await agent.initialize():
                self.spawned_agents.append(agent)
                self.current_active_agents += 1
                await self._persist_orchestrator_state()
                logger.info(f"Orchestrator {self.id} spawned {agent_type} agent {agent.id[:8]}...")
                return agent
            else:
                logger.error(f"Failed to initialize {agent_type} agent")
                return None
                
        except Exception as e:
            logger.error(f"Orchestrator {self.id} failed to spawn {agent_type} agent: {str(e)}")
            return None
    
    async def track_agent_completion(self, agent: BaseAgent, result: AgentResult):
        """
        Track completed agent and update orchestrator metrics
        
        Args:
            agent: Completed agent
            result: Agent execution result
        """
        try:
            # Update tracking lists
            if agent in self.spawned_agents:
                self.spawned_agents.remove(agent)
            
            if result.success:
                self.completed_agents.append(agent)
            else:
                self.failed_agents.append(agent)
            
            # Update metrics
            self.current_active_agents = max(0, self.current_active_agents - 1)
            self.total_tokens += result.tokens_used
            self.total_cost_usd += result.cost_usd
            
            # Persist updated state
            await self._persist_orchestrator_state()
            
            logger.info(f"Orchestrator {self.id} tracked completion of agent {agent.id[:8]}... (success={result.success})")
            
        except Exception as e:
            logger.error(f"Orchestrator {self.id} failed to track agent completion: {str(e)}")
    
    async def coordinate_agents(self, agents: List[BaseAgent]) -> List[AgentResult]:
        """
        Coordinate execution of multiple agents with proper lifecycle tracking
        
        Args:
            agents: List of agents to coordinate
            
        Returns:
            List of agent results
        """
        try:
            results = []
            
            # Execute agents and track completion
            for agent in agents:
                # For this base implementation, we'll execute sequentially
                # Subclasses can override for parallel execution
                result = await self._execute_and_track_agent(agent)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Orchestrator {self.id} agent coordination failed: {str(e)}")
            # Return partial results if available
            return results if 'results' in locals() else []
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        execution_time_ms = 0
        if self.execution_start_time:
            execution_time_ms = int((datetime.now() - self.execution_start_time).total_seconds() * 1000)
        
        return {
            'orchestrator_id': self.id,
            'orchestrator_type': self.orchestrator_type,
            'state': self.state.value,
            'thought_tree_id': self.thought_tree_id,
            'current_active_agents': self.current_active_agents,
            'max_concurrent_agents': self.max_concurrent_agents,
            'agents_spawned': len(self.spawned_agents),
            'agents_completed': len(self.completed_agents),
            'agents_failed': len(self.failed_agents),
            'total_tokens': self.total_tokens,
            'total_cost_usd': self.total_cost_usd,
            'execution_time_ms': execution_time_ms,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    async def terminate(self) -> OrchestratorResult:
        """
        Gracefully terminate orchestrator and return final results
        """
        try:
            # Terminate any remaining active agents
            for agent in self.spawned_agents[:]:  # Copy list to avoid modification during iteration
                try:
                    await agent.terminate()
                    await self.track_agent_completion(agent, AgentResult(
                        success=False,
                        content="",
                        error_message="Terminated by orchestrator shutdown"
                    ))
                except Exception as e:
                    logger.warning(f"Failed to terminate agent {agent.id}: {str(e)}")
            
            # Update final state
            self.state = OrchestratorState.TERMINATED
            await self._persist_orchestrator_state()
            
            # Calculate execution time
            execution_time_ms = 0
            if self.execution_start_time:
                execution_time_ms = int((datetime.now() - self.execution_start_time).total_seconds() * 1000)
            
            # Create final result
            result = OrchestratorResult(
                success=len(self.failed_agents) == 0,
                workflow_id=self.thought_tree_id,
                agents_spawned=len(self.spawned_agents) + len(self.completed_agents) + len(self.failed_agents),
                agents_completed=len(self.completed_agents),
                agents_failed=len(self.failed_agents),
                total_cost_usd=self.total_cost_usd,
                total_tokens=self.total_tokens,
                execution_time_ms=execution_time_ms,
                final_output=await self._generate_final_output()
            )
            
            logger.info(f"Orchestrator {self.id} ({self.orchestrator_type}) terminated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator {self.id} termination error: {str(e)}")
            return OrchestratorResult(
                success=False,
                workflow_id=self.thought_tree_id or "",
                agents_spawned=0,
                agents_completed=0,
                agents_failed=0,
                error_message=f"Termination error: {str(e)}"
            )
    
    # Private helper methods
    
    async def _check_resource_availability(self) -> bool:
        """Check if orchestrator can spawn new agents"""
        return self.current_active_agents < self.max_concurrent_agents
    
    async def _create_thought_tree(self):
        """Create a thought tree for the orchestrator"""
        try:
            self.thought_tree_id = str(uuid.uuid4())
            
            async with db_manager.get_async_session() as session:
                thought_tree = ThoughtTree(
                    id=self.thought_tree_id,
                    goal=f"Orchestrator {self.orchestrator_type} workflow",
                    status="in_progress",
                    depth=1 if not self.parent_orchestrator_id else 2,
                    metadata_={'orchestrator_id': self.id, 'orchestrator_type': self.orchestrator_type}
                )
                session.add(thought_tree)
                await session.commit()
                
            logger.info(f"Created thought tree {self.thought_tree_id} for orchestrator {self.id}")
            
        except Exception as e:
            logger.error(f"Failed to create thought tree: {str(e)}")
            raise
    
    async def _persist_orchestrator_state(self):
        """Persist orchestrator state to database"""
        try:
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Orchestrator).filter(Orchestrator.id == self.id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing orchestrator
                    existing.status = self.state.value
                    existing.current_active_agents = self.current_active_agents
                    existing.global_context = self.global_context
                    existing.completed_at = datetime.now() if self.state.value in ['completed', 'failed', 'terminated'] else None
                else:
                    # Create new orchestrator
                    new_orchestrator = Orchestrator(
                        id=self.id,
                        parent_orchestrator_id=self.parent_orchestrator_id,
                        thought_tree_id=self.thought_tree_id,
                        orchestrator_type=self.orchestrator_type,
                        status=self.state.value,
                        max_concurrent_agents=self.max_concurrent_agents,
                        current_active_agents=self.current_active_agents,
                        global_context=self.global_context
                    )
                    session.add(new_orchestrator)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to persist orchestrator {self.id} state: {str(e)}")
    
    async def _execute_and_track_agent(self, agent: BaseAgent) -> AgentResult:
        """Execute agent and track its completion"""
        try:
            # This is a placeholder - subclasses should implement specific execution logic
            result = AgentResult(
                success=True,
                content="Base orchestrator execution - override in subclass",
                execution_time_ms=100
            )
            
            # Track completion
            await self.track_agent_completion(agent, result)
            
            return result
            
        except Exception as e:
            error_result = AgentResult(
                success=False,
                content="",
                error_message=f"Agent execution failed: {str(e)}"
            )
            await self.track_agent_completion(agent, error_result)
            return error_result
    
    async def _generate_final_output(self) -> Dict[str, Any]:
        """Generate final workflow output - override in subclasses"""
        return {
            'orchestrator_type': self.orchestrator_type,
            'completion_summary': f"Orchestrator completed with {len(self.completed_agents)} successful agents, {len(self.failed_agents)} failed agents",
            'total_cost_usd': self.total_cost_usd,
            'total_tokens': self.total_tokens
        }
    
    # Abstract methods for subclasses
    
    async def _orchestrator_specific_initialization(self) -> bool:
        """Orchestrator-specific initialization logic - override in subclasses"""
        # Default implementation for testing - subclasses should override
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id[:8]}..., type={self.orchestrator_type}, state={self.state.value})>"