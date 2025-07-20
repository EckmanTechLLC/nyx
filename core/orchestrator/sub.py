"""
SubOrchestrator for NYX System

Enables recursive task decomposition and hierarchical coordination.
Spawned by TopLevelOrchestrator to handle complex workflows that require
breaking down into smaller, manageable subtasks with proper parent-child
coordination and resource inheritance.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from core.orchestrator.base import BaseOrchestrator, OrchestratorResult, OrchestratorState
from core.agents.base import BaseAgent, AgentResult
from core.agents.task import TaskAgent
from core.agents.council import CouncilAgent
from core.agents.validator import ValidatorAgent
from core.agents.memory import MemoryAgent
from database.connection import db_manager
from database.models import ThoughtTree
from config.settings import settings

logger = logging.getLogger(__name__)

class DecompositionStrategy(Enum):
    """Task decomposition strategies"""
    SEQUENTIAL_BREAKDOWN = "sequential_breakdown"
    PARALLEL_BREAKDOWN = "parallel_breakdown"  
    DEPENDENCY_BASED = "dependency_based"
    HIERARCHICAL_LAYERS = "hierarchical_layers"

@dataclass
class SubtaskDefinition:
    """Definition of a subtask for decomposition"""
    subtask_id: str
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: str = "medium"
    required_agent_types: List[str] = field(default_factory=lambda: ["task"])
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)

@dataclass
class DecompositionPlan:
    """Plan for task decomposition"""
    subtasks: List[SubtaskDefinition] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL_BREAKDOWN
    estimated_depth: int = 1
    resource_allocation: Dict[str, Any] = field(default_factory=dict)

class SubOrchestrator(BaseOrchestrator):
    """
    Sub-orchestrator for recursive task decomposition and coordination
    
    Handles:
    - Dynamic task tree decomposition with depth limiting
    - Parent-child coordination and communication protocols
    - Resource inheritance and constraint propagation  
    - Local workflow context while accessing global state
    - Result synthesis before reporting to parent orchestrator
    """
    
    def __init__(
        self,
        parent_orchestrator_id: str,
        decomposition_task: Dict[str, Any],
        max_depth: int = 3,
        max_subtasks: int = 8,
        max_concurrent_agents: int = 10,
        inherit_context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            orchestrator_type="sub",
            thought_tree_id=decomposition_task.get("thought_tree_id"),
            parent_orchestrator_id=parent_orchestrator_id,
            max_concurrent_agents=max_concurrent_agents,
            global_context=inherit_context or {}
        )
        
        # SubOrchestrator-specific configuration
        self.decomposition_task = decomposition_task
        self.max_depth = max_depth
        self.max_subtasks = max_subtasks
        self.current_depth = decomposition_task.get("current_depth", 0)
        
        # Decomposition state
        self.decomposition_plan: Optional[DecompositionPlan] = None
        self.active_subtasks: Dict[str, Dict[str, Any]] = {}
        self.completed_subtasks: Dict[str, AgentResult] = {}
        self.failed_subtasks: Dict[str, str] = {}
        
        # Parent coordination
        self.parent_communication_channel = f"orchestrator_{parent_orchestrator_id}"
        self.result_aggregation_mode = "synthesis"  # or "collection"
        
        # Resource inheritance from parent
        inherit_context = inherit_context or {}
        self.inherited_constraints = inherit_context.get("resource_constraints", {})
        self.inherited_quality_settings = inherit_context.get("quality_settings", {})
        
    async def initialize(self) -> bool:
        """Initialize sub-orchestrator and validate decomposition task"""
        try:
            # Call parent initialization
            if not await super().initialize():
                return False
            
            logger.info(f"SubOrchestrator {self.id} initializing for task: {self.decomposition_task.get('title', 'Unknown')}")
            
            # Validate depth limits
            if self.current_depth >= self.max_depth:
                logger.error(f"SubOrchestrator {self.id}: Depth limit exceeded ({self.current_depth} >= {self.max_depth})")
                return False
            
            # Validate parent orchestrator exists
            if not self.parent_orchestrator_id:
                logger.error(f"SubOrchestrator {self.id}: No parent orchestrator specified")
                return False
                
            # Validate decomposition task structure
            if not self._validate_decomposition_task():
                logger.error(f"SubOrchestrator {self.id}: Invalid decomposition task structure")
                return False
            
            self.state = OrchestratorState.ACTIVE
            logger.info(f"SubOrchestrator {self.id} initialized successfully at depth {self.current_depth}")
            return True
            
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id} initialization failed: {str(e)}")
            self.state = OrchestratorState.FAILED
            return False
    
    def _validate_decomposition_task(self) -> bool:
        """Validate decomposition task has required structure"""
        required_fields = ['title', 'description', 'thought_tree_id']
        for field in required_fields:
            if field not in self.decomposition_task:
                logger.error(f"SubOrchestrator {self.id}: Missing required field '{field}' in decomposition task")
                return False
        return True
    
    async def execute_decomposition(self) -> OrchestratorResult:
        """
        Main execution method for recursive task decomposition
        
        Returns:
            OrchestratorResult with aggregated results from all subtasks
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"SubOrchestrator {self.id} starting decomposition execution")
            
            # Phase 1: Task Analysis and Decomposition Planning
            self.decomposition_plan = await self._analyze_and_plan_decomposition()
            if not self.decomposition_plan or not self.decomposition_plan.subtasks:
                return self._create_error_result("Failed to create decomposition plan")
            
            logger.info(f"SubOrchestrator {self.id}: Created plan with {len(self.decomposition_plan.subtasks)} subtasks")
            
            # Phase 2: Subtask Execution Based on Strategy
            execution_results = await self._execute_decomposition_plan()
            if not execution_results:
                return self._create_error_result("Decomposition plan execution failed")
            
            # Phase 3: Result Synthesis and Validation
            final_result = await self._synthesize_subtask_results(execution_results)
            
            # Phase 4: Report to Parent (if needed)
            await self._report_to_parent(final_result)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"SubOrchestrator {self.id} completed decomposition in {execution_time:.0f}ms")
            
            return OrchestratorResult(
                success=True,
                workflow_id=self.thought_tree_id or self.id,
                agents_spawned=len(self.spawned_agents) + len(self.completed_agents) + len(self.failed_agents),
                agents_completed=len(self.completed_agents),
                agents_failed=len(self.failed_agents),
                total_cost_usd=self.total_cost_usd,
                execution_time_ms=int(execution_time),
                final_output=final_result,
                metadata={
                    'decomposition_strategy': self.decomposition_plan.strategy.value,
                    'subtasks_completed': len(self.completed_subtasks),
                    'subtasks_failed': len(self.failed_subtasks),
                    'depth': self.current_depth,
                    'parent_orchestrator_id': self.parent_orchestrator_id
                }
            )
            
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id} execution failed: {str(e)}")
            return self._create_error_result(f"Execution error: {str(e)}")
    
    async def _analyze_and_plan_decomposition(self) -> Optional[DecompositionPlan]:
        """Analyze task and create decomposition plan"""
        try:
            # Spawn task agent for decomposition analysis
            analysis_agent = await self.spawn_agent(
                agent_type="task",
                task_context={
                    'task_type': 'decomposition_analysis',
                    'max_retries': 2,
                    'timeout': 180
                }
            )
            
            if not analysis_agent:
                logger.error(f"SubOrchestrator {self.id}: Failed to spawn analysis agent")
                return None
            
            # Create analysis input with string content
            task_title = self.decomposition_task.get('title', 'Unknown Task')
            task_desc = self.decomposition_task.get('description', 'No description provided')
            
            content_parts = [
                f"Analyze and decompose this task into subtasks:",
                f"\nTask Title: {task_title}",
                f"\nTask Description: {task_desc}",
                f"\nConstraints:",
                f"- Maximum {self.max_subtasks} subtasks",
                f"- Maximum depth remaining: {self.max_depth - self.current_depth}",
                f"- Current depth: {self.current_depth}"
            ]
            
            # Add resource constraints if any
            if self.inherited_constraints:
                content_parts.append(f"\nResource Limits:")
                for key, value in self.inherited_constraints.items():
                    content_parts.append(f"- {key}: {value}")
            
            # Add global context if available
            if self.global_context:
                content_parts.append(f"\nGlobal Context: {str(self.global_context)[:200]}...")
            
            content_parts.append(f"\nPlease provide a decomposition plan with specific subtasks, execution order, and strategy.")
            
            analysis_input = {
                'task_type': 'decomposition_analysis',
                'description': f"Analyze and decompose task: {task_title}",
                'content': "".join(content_parts)
            }
            
            # Execute analysis
            analysis_result = await self._execute_agent_with_tracking(analysis_agent, analysis_input)
            
            if not analysis_result or not analysis_result.success:
                logger.error(f"SubOrchestrator {self.id}: Task analysis failed")
                return self._create_fallback_decomposition_plan()
            
            # Parse analysis result into decomposition plan
            return await self._parse_analysis_to_plan(analysis_result)
            
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id}: Decomposition analysis error: {str(e)}")
            return self._create_fallback_decomposition_plan()
    
    def _create_fallback_decomposition_plan(self) -> DecompositionPlan:
        """Create a simple fallback decomposition plan"""
        fallback_subtask = SubtaskDefinition(
            subtask_id=str(uuid.uuid4()),
            title=f"Execute: {self.decomposition_task.get('title', 'Task')}",
            description=self.decomposition_task.get('description', 'No description available'),
            estimated_complexity="medium",
            required_agent_types=["task"]
        )
        
        return DecompositionPlan(
            subtasks=[fallback_subtask],
            execution_order=[fallback_subtask.subtask_id],
            strategy=DecompositionStrategy.SEQUENTIAL_BREAKDOWN,
            estimated_depth=1
        )
    
    async def _parse_analysis_to_plan(self, analysis_result: AgentResult) -> DecompositionPlan:
        """Parse agent analysis result into structured decomposition plan"""
        try:
            # This is a simplified implementation - in production you'd have
            # more sophisticated parsing logic based on the LLM response format
            
            content = analysis_result.content
            plan = DecompositionPlan()
            
            # Extract subtasks from analysis (simplified parsing)
            if isinstance(content, dict) and 'subtasks' in content:
                for i, subtask_data in enumerate(content['subtasks'][:self.max_subtasks]):
                    subtask = SubtaskDefinition(
                        subtask_id=str(uuid.uuid4()),
                        title=subtask_data.get('title', f'Subtask {i+1}'),
                        description=subtask_data.get('description', 'No description'),
                        dependencies=subtask_data.get('dependencies', []),
                        estimated_complexity=subtask_data.get('complexity', 'medium'),
                        required_agent_types=subtask_data.get('agent_types', ['task'])
                    )
                    plan.subtasks.append(subtask)
                    plan.execution_order.append(subtask.subtask_id)
            else:
                # Fallback to single subtask
                return self._create_fallback_decomposition_plan()
            
            # Determine strategy based on dependencies and parallelization potential
            plan.strategy = self._determine_execution_strategy(plan.subtasks)
            plan.estimated_depth = self.current_depth + 1
            
            return plan
            
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id}: Analysis parsing error: {str(e)}")
            return self._create_fallback_decomposition_plan()
    
    def _determine_execution_strategy(self, subtasks: List[SubtaskDefinition]) -> DecompositionStrategy:
        """Determine optimal execution strategy based on subtask characteristics"""
        # Check for dependencies
        has_dependencies = any(len(task.dependencies) > 0 for task in subtasks)
        
        if has_dependencies:
            return DecompositionStrategy.DEPENDENCY_BASED
        elif len(subtasks) <= 2:
            return DecompositionStrategy.SEQUENTIAL_BREAKDOWN
        else:
            return DecompositionStrategy.PARALLEL_BREAKDOWN
    
    async def _execute_decomposition_plan(self) -> Optional[Dict[str, AgentResult]]:
        """Execute the decomposition plan based on selected strategy"""
        try:
            if self.decomposition_plan.strategy == DecompositionStrategy.SEQUENTIAL_BREAKDOWN:
                return await self._execute_sequential_subtasks()
            elif self.decomposition_plan.strategy == DecompositionStrategy.PARALLEL_BREAKDOWN:
                return await self._execute_parallel_subtasks()
            elif self.decomposition_plan.strategy == DecompositionStrategy.DEPENDENCY_BASED:
                return await self._execute_dependency_based_subtasks()
            else:
                logger.warning(f"SubOrchestrator {self.id}: Unknown strategy, falling back to sequential")
                return await self._execute_sequential_subtasks()
                
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id}: Plan execution error: {str(e)}")
            return None
    
    async def _execute_sequential_subtasks(self) -> Dict[str, AgentResult]:
        """Execute subtasks in sequential order"""
        results = {}
        accumulated_context = {}
        
        for subtask in self.decomposition_plan.subtasks:
            logger.info(f"SubOrchestrator {self.id}: Executing subtask {subtask.title}")
            
            # Spawn appropriate agents for subtask
            agents = await self._spawn_agents_for_subtask(subtask)
            if not agents:
                logger.error(f"SubOrchestrator {self.id}: Failed to spawn agents for subtask {subtask.subtask_id}")
                continue
            
            # Execute subtask with accumulated context
            subtask_input = self._create_subtask_input(subtask, accumulated_context)
            
            # Execute primary agent (first in list)
            primary_agent = agents[0]
            result = await self._execute_agent_with_tracking(primary_agent, subtask_input)
            
            if result and result.success:
                results[subtask.subtask_id] = result
                self.completed_subtasks[subtask.subtask_id] = result
                
                # Add result to accumulated context for next subtask
                accumulated_context[f'subtask_{subtask.subtask_id}'] = {
                    'title': subtask.title,
                    'result': result.content,
                    'success': result.success
                }
            else:
                logger.warning(f"SubOrchestrator {self.id}: Subtask {subtask.subtask_id} failed")
                self.failed_subtasks[subtask.subtask_id] = result.error_message if result else "Unknown error"
        
        return results
    
    async def _execute_parallel_subtasks(self) -> Dict[str, AgentResult]:
        """Execute subtasks in parallel batches"""
        results = {}
        
        # Create all agents first
        agent_subtask_map = {}
        for subtask in self.decomposition_plan.subtasks:
            agents = await self._spawn_agents_for_subtask(subtask)
            if agents:
                agent_subtask_map[subtask.subtask_id] = (agents[0], subtask)  # Use primary agent
        
        # Execute all subtasks in parallel
        if agent_subtask_map:
            execution_coroutines = [
                self._execute_agent_with_tracking(
                    agent, 
                    self._create_subtask_input(subtask, {})
                )
                for agent, subtask in agent_subtask_map.values()
            ]
            
            parallel_results = await asyncio.gather(*execution_coroutines, return_exceptions=True)
            
            # Map results back to subtasks
            for i, (subtask_id, (agent, subtask)) in enumerate(agent_subtask_map.items()):
                result = parallel_results[i]
                if isinstance(result, Exception):
                    logger.error(f"SubOrchestrator {self.id}: Subtask {subtask_id} failed with exception: {str(result)}")
                    self.failed_subtasks[subtask_id] = str(result)
                elif result and result.success:
                    results[subtask_id] = result
                    self.completed_subtasks[subtask_id] = result
                else:
                    logger.warning(f"SubOrchestrator {self.id}: Subtask {subtask_id} failed")
                    self.failed_subtasks[subtask_id] = result.error_message if result else "Unknown error"
        
        return results
    
    async def _execute_dependency_based_subtasks(self) -> Dict[str, AgentResult]:
        """Execute subtasks respecting dependency order"""
        # For now, fall back to sequential execution
        # In future versions, implement topological sorting for dependencies
        logger.info(f"SubOrchestrator {self.id}: Using sequential execution for dependency-based strategy")
        return await self._execute_sequential_subtasks()
    
    async def _spawn_agents_for_subtask(self, subtask: SubtaskDefinition) -> List[BaseAgent]:
        """Spawn appropriate agents for a subtask"""
        agents = []
        
        for agent_type in subtask.required_agent_types:
            agent = await self.spawn_agent(
                agent_type=agent_type,
                task_context={
                    'subtask_id': subtask.subtask_id,
                    'max_retries': 2,
                    'timeout': 300
                }
            )
            if agent:
                agents.append(agent)
        
        return agents
    
    def _create_subtask_input(self, subtask: SubtaskDefinition, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create input for subtask execution"""
        # Create descriptive string content for TaskAgent
        content_parts = [
            f"Execute subtask: {subtask.title}",
            f"\nDescription: {subtask.description}",
            f"\nSuccess Criteria: {subtask.success_criteria}"
        ]
        
        # Add context if available
        if context:
            context_summary = []
            for key, value in context.items():
                if isinstance(value, dict) and 'result' in value:
                    context_summary.append(f"- {key}: {str(value['result'])[:100]}...")
                else:
                    context_summary.append(f"- {key}: {str(value)[:100]}...")
            
            if context_summary:
                content_parts.append(f"\nContext from previous subtasks:\n" + "\n".join(context_summary))
        
        # Add parent task info
        parent_title = self.decomposition_task.get('title', 'Unknown Task')
        content_parts.append(f"\nParent task: {parent_title} (depth: {self.current_depth})")
        
        return {
            'task_type': 'subtask_execution',
            'description': subtask.description,
            'content': "".join(content_parts)
        }
    
    async def _synthesize_subtask_results(self, subtask_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """Synthesize all subtask results into final output"""
        try:
            if not subtask_results:
                return {'content': 'No subtask results to synthesize', 'success': False}
            
            # Spawn memory agent for synthesis
            synthesis_agent = await self.spawn_agent(
                agent_type="memory",
                task_context={'max_retries': 2, 'timeout': 300}
            )
            
            if not synthesis_agent:
                return self._create_fallback_synthesis(subtask_results)
            
            # Prepare synthesis input
            synthesis_input = {
                'operation': 'summarize',
                'content': {
                    'main_task': self.decomposition_task,
                    'subtask_results': [
                        {
                            'subtask_id': subtask_id,
                            'content': result.content,
                            'success': result.success
                        }
                        for subtask_id, result in subtask_results.items()
                    ],
                    'decomposition_metadata': {
                        'strategy': self.decomposition_plan.strategy.value if self.decomposition_plan else 'unknown',
                        'depth': self.current_depth,
                        'total_subtasks': len(self.decomposition_plan.subtasks) if self.decomposition_plan else 0
                    }
                }
            }
            
            # Execute synthesis
            synthesis_result = await self._execute_agent_with_tracking(synthesis_agent, synthesis_input)
            
            if synthesis_result and synthesis_result.success:
                return {
                    'content': synthesis_result.content,
                    'success': True,
                    'synthesis_method': 'agent_driven',
                    'subtasks_synthesized': len(subtask_results)
                }
            else:
                return self._create_fallback_synthesis(subtask_results)
                
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id}: Synthesis error: {str(e)}")
            return self._create_fallback_synthesis(subtask_results)
    
    def _create_fallback_synthesis(self, subtask_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """Create fallback synthesis when agent-driven synthesis fails"""
        successful_results = [r for r in subtask_results.values() if r.success]
        content_pieces = [r.content for r in successful_results]
        
        return {
            'content': f"Completed {len(successful_results)}/{len(subtask_results)} subtasks successfully. Results: " + 
                      "; ".join(str(c) for c in content_pieces[:3]),  # Limit to first 3
            'success': len(successful_results) > 0,
            'synthesis_method': 'fallback_concatenation',
            'subtasks_synthesized': len(successful_results)
        }
    
    async def _report_to_parent(self, final_result: Dict[str, Any]):
        """Report completion to parent orchestrator"""
        try:
            # This is a placeholder for parent communication
            # In a full implementation, this would use a message queue or direct API calls
            logger.info(f"SubOrchestrator {self.id} reporting to parent {self.parent_orchestrator_id}")
            logger.info(f"Result summary: {final_result.get('success', False)} - {len(final_result.get('content', ''))} chars")
        except Exception as e:
            logger.error(f"SubOrchestrator {self.id}: Failed to report to parent: {str(e)}")
    
    async def _execute_agent_with_tracking(self, agent: BaseAgent, task_input: Dict[str, Any]) -> AgentResult:
        """Execute agent with proper tracking and cleanup"""
        try:
            result = await agent.execute(task_input)
            await self.track_agent_completion(agent, result)
            await agent.terminate()
            return result
        except Exception as e:
            error_result = AgentResult(
                success=False,
                content="",
                error_message=str(e)
            )
            await self.track_agent_completion(agent, error_result)
            await agent.terminate()
            return error_result
    
    def _create_error_result(self, error_message: str) -> OrchestratorResult:
        """Create error result for failed execution"""
        return OrchestratorResult(
            success=False,
            workflow_id=self.thought_tree_id or self.id,
            agents_spawned=len(self.spawned_agents) + len(self.completed_agents) + len(self.failed_agents),
            agents_completed=len(self.completed_agents),
            agents_failed=len(self.failed_agents),
            error_message=error_message,
            metadata={
                'depth': self.current_depth,
                'parent_orchestrator_id': self.parent_orchestrator_id
            }
        )