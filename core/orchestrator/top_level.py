"""
TopLevelOrchestrator for NYX System

Entry point for all workflows with comprehensive input handling, 
complexity analysis, strategy selection, and dynamic adaptation.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union
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

class WorkflowInputType(Enum):
    """Types of workflow input"""
    USER_PROMPT = "user_prompt"
    STRUCTURED_TASK = "structured_task"
    GOAL_WORKFLOW = "goal_workflow"
    SCHEDULED_WORKFLOW = "scheduled_workflow"
    REACTIVE_WORKFLOW = "reactive_workflow"
    CONTINUATION_WORKFLOW = "continuation_workflow"

class WorkflowStrategy(Enum):
    """Execution strategies for workflows"""
    DIRECT_EXECUTION = "direct_execution"
    SEQUENTIAL_DECOMPOSITION = "sequential_decomposition"
    PARALLEL_EXECUTION = "parallel_execution"
    RECURSIVE_DECOMPOSITION = "recursive_decomposition"
    COUNCIL_DRIVEN = "council_driven"
    ITERATIVE_REFINEMENT = "iterative_refinement"

class ComplexityLevel(Enum):
    """Complexity assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class WorkflowComplexity:
    """Analysis of workflow complexity across multiple dimensions"""
    cognitive_complexity: ComplexityLevel = ComplexityLevel.LOW
    technical_complexity: ComplexityLevel = ComplexityLevel.LOW
    coordination_complexity: ComplexityLevel = ComplexityLevel.LOW
    data_complexity: ComplexityLevel = ComplexityLevel.LOW
    time_sensitivity: ComplexityLevel = ComplexityLevel.LOW
    quality_requirements: ComplexityLevel = ComplexityLevel.LOW
    scope_breadth: ComplexityLevel = ComplexityLevel.LOW
    risk_level: ComplexityLevel = ComplexityLevel.LOW
    
    def overall_complexity(self) -> ComplexityLevel:
        """Calculate overall complexity score"""
        critical_count = sum(1 for level in [
            self.cognitive_complexity, self.technical_complexity,
            self.coordination_complexity, self.data_complexity,
            self.scope_breadth, self.risk_level
        ] if level == ComplexityLevel.CRITICAL)
        
        high_count = sum(1 for level in [
            self.cognitive_complexity, self.technical_complexity,
            self.coordination_complexity, self.data_complexity,
            self.scope_breadth, self.risk_level
        ] if level == ComplexityLevel.HIGH)
        
        medium_count = sum(1 for level in [
            self.cognitive_complexity, self.technical_complexity,
            self.coordination_complexity, self.data_complexity,
            self.scope_breadth, self.risk_level
        ] if level == ComplexityLevel.MEDIUM)
        
        if critical_count >= 1 or high_count >= 4:
            return ComplexityLevel.CRITICAL
        elif high_count >= 2:
            return ComplexityLevel.HIGH
        elif high_count >= 1 or medium_count >= 4:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
    
    def requires_decomposition(self) -> bool:
        """Determine if workflow needs recursive decomposition"""
        return (
            self.overall_complexity() in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL] or
            self.scope_breadth in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL] or
            self.coordination_complexity in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL]
        )

@dataclass
class ResourceEstimate:
    """Resource requirement estimates for workflow execution"""
    estimated_agents: Dict[str, int] = field(default_factory=dict)
    estimated_cost: Dict[str, float] = field(default_factory=dict)
    estimated_time: Dict[str, str] = field(default_factory=dict)
    resource_warnings: List[str] = field(default_factory=list)
    confidence_level: float = 0.7

@dataclass
class WorkflowMonitoringState:
    """Real-time workflow monitoring metrics"""
    progress_percentage: float = 0.0
    agents_active: int = 0
    agents_completed: int = 0
    agents_failed: int = 0
    cost_consumed: float = 0.0
    time_elapsed_minutes: float = 0.0
    quality_indicators: Dict[str, float] = field(default_factory=dict)
    bottlenecks: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class WorkflowInput:
    """Complete workflow input specification"""
    input_type: WorkflowInputType
    content: Dict[str, Any]
    execution_context: Dict[str, Any] = field(default_factory=dict)
    domain_context: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)
    historical_context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    urgency: str = "normal"

class TopLevelOrchestrator(BaseOrchestrator):
    """
    Top-level orchestrator for comprehensive workflow management
    
    Handles all types of workflow input, performs complexity analysis,
    selects optimal execution strategies, and provides dynamic adaptation
    with real-time monitoring and strategy adjustment.
    """
    
    def __init__(
        self,
        max_concurrent_agents: int = 20,
        max_execution_time_minutes: int = 120,
        max_cost_usd: float = 100.0,
        max_recursion_depth: int = 8
    ):
        super().__init__(
            orchestrator_type="top_level",
            max_concurrent_agents=max_concurrent_agents,
            global_context={
                "max_execution_time_minutes": max_execution_time_minutes,
                "max_cost_usd": max_cost_usd,
                "max_recursion_depth": max_recursion_depth
            }
        )
        
        # Store constructor parameters as instance attributes
        self.max_execution_time_minutes = max_execution_time_minutes
        self.max_cost_usd = max_cost_usd
        self.max_recursion_depth = max_recursion_depth
        
        # Workflow state
        self.current_workflow_input: Optional[WorkflowInput] = None
        self.selected_strategy: Optional[WorkflowStrategy] = None
        self.complexity_analysis: Optional[WorkflowComplexity] = None
        self.resource_estimate: Optional[ResourceEstimate] = None
        self.monitoring_state = WorkflowMonitoringState()
        
        # Strategy adaptation
        self.strategy_adaptation_enabled = True
        self.adaptation_triggers = []
        
        # Historical learning
        self.workflow_patterns = {}
        self.performance_metrics = {}
    
    async def _orchestrator_specific_initialization(self) -> bool:
        """Initialize top-level orchestrator with historical data loading"""
        try:
            # Load historical patterns and performance metrics
            await self._load_historical_context()
            
            # Initialize monitoring systems
            self.monitoring_state = WorkflowMonitoringState()
            
            logger.info(f"TopLevelOrchestrator {self.id} initialized with historical context")
            return True
            
        except Exception as e:
            logger.error(f"TopLevelOrchestrator initialization failed: {str(e)}")
            return False
    
    async def execute_workflow(self, workflow_input: WorkflowInput) -> OrchestratorResult:
        """
        Execute complete workflow with comprehensive orchestration
        
        Args:
            workflow_input: Complete workflow specification with all context
            
        Returns:
            Comprehensive orchestration result with metrics and output
        """
        try:
            start_time = datetime.now()
            self.current_workflow_input = workflow_input
            
            logger.info(f"TopLevelOrchestrator {self.id} starting workflow: {workflow_input.input_type.value}")
            
            # Phase 1: Analysis and Planning
            await self._update_monitoring_state("analysis", 10)
            self.complexity_analysis = await self._analyze_complexity(workflow_input)
            
            await self._update_monitoring_state("planning", 20)
            self.resource_estimate = await self._estimate_resources(workflow_input, self.complexity_analysis)
            
            await self._update_monitoring_state("strategy_selection", 30)
            self.selected_strategy = await self._select_strategy(workflow_input, self.complexity_analysis)
            
            # Phase 2: Execution with Monitoring
            await self._update_monitoring_state("executing", 40)
            execution_result = await self._execute_with_strategy(workflow_input, self.selected_strategy)
            
            # Phase 3: Result Processing
            await self._update_monitoring_state("finalizing", 90)
            final_result = await self._process_final_results(execution_result)
            
            # Phase 4: Learning and Persistence
            await self._update_monitoring_state("learning", 95)
            await self._record_workflow_outcomes(workflow_input, final_result)
            
            await self._update_monitoring_state("completed", 100)
            
            execution_time = (datetime.now() - start_time).total_seconds() / 60
            logger.info(f"TopLevelOrchestrator {self.id} completed workflow in {execution_time:.1f} minutes")
            
            return final_result
            
        except Exception as e:
            logger.error(f"TopLevelOrchestrator {self.id} workflow execution failed: {str(e)}")
            await self._handle_workflow_failure(e)
            
            return OrchestratorResult(
                success=False,
                workflow_id=self.thought_tree_id or "",
                agents_spawned=self.monitoring_state.agents_active,
                agents_completed=self.monitoring_state.agents_completed,
                agents_failed=self.monitoring_state.agents_failed + 1,
                error_message=f"Workflow execution failed: {str(e)}",
                total_cost_usd=self.monitoring_state.cost_consumed
            )
    
    async def _analyze_complexity(self, workflow_input: WorkflowInput) -> WorkflowComplexity:
        """Analyze workflow complexity across multiple dimensions"""
        try:
            complexity = WorkflowComplexity()
            content = workflow_input.content
            
            # Analyze cognitive complexity
            if workflow_input.input_type == WorkflowInputType.GOAL_WORKFLOW:
                complexity.cognitive_complexity = ComplexityLevel.HIGH
            elif workflow_input.input_type == WorkflowInputType.USER_PROMPT:
                # For USER_PROMPT, content is a string, not a dict
                prompt_text = content if isinstance(content, str) else content.get("content", "")
                if len(prompt_text.split()) <= 5 and any(
                    prompt_text.lower().startswith(prefix) 
                    for prefix in ["what is", "who is", "what does", "how to", "define", "explain"]
                ):
                    complexity.cognitive_complexity = ComplexityLevel.LOW
                else:
                    # Analyze prompt complexity using LLM for more complex prompts
                    prompt_analysis = await self._analyze_prompt_complexity(prompt_text)
                    complexity.cognitive_complexity = prompt_analysis.get("cognitive_level", ComplexityLevel.MEDIUM)
            
            # Analyze technical complexity
            # For USER_PROMPT, content is string, so check execution_context instead
            if isinstance(content, dict):
                tech_indicators = content.get("technical_requirements", [])
            else:
                tech_indicators = workflow_input.execution_context.get("technical_requirements", [])
            
            if len(tech_indicators) > 5 or any("complex" in str(req).lower() for req in tech_indicators):
                complexity.technical_complexity = ComplexityLevel.HIGH
            elif len(tech_indicators) > 2:
                complexity.technical_complexity = ComplexityLevel.MEDIUM
            
            # Analyze scope and coordination
            if isinstance(content, dict):
                deliverables = content.get("deliverables", [])
            else:
                deliverables = workflow_input.execution_context.get("deliverables", [])
            
            if len(deliverables) > 5:
                complexity.scope_breadth = ComplexityLevel.HIGH
                complexity.coordination_complexity = ComplexityLevel.HIGH
            elif len(deliverables) > 2:
                complexity.scope_breadth = ComplexityLevel.MEDIUM
                complexity.coordination_complexity = ComplexityLevel.MEDIUM
            
            # Analyze quality requirements
            quality_reqs = workflow_input.execution_context.get("quality_settings", {})
            validation_level = quality_reqs.get("validation_level", "standard")
            if validation_level in ["strict", "critical"]:
                complexity.quality_requirements = ComplexityLevel.HIGH
            elif validation_level == "standard":
                complexity.quality_requirements = ComplexityLevel.MEDIUM
            
            # Analyze time sensitivity and risk
            if workflow_input.urgency == "critical":
                complexity.time_sensitivity = ComplexityLevel.HIGH
                complexity.risk_level = ComplexityLevel.HIGH
            elif workflow_input.urgency == "high":
                complexity.time_sensitivity = ComplexityLevel.MEDIUM
                complexity.risk_level = ComplexityLevel.MEDIUM
            
            logger.info(f"Complexity analysis: {complexity.overall_complexity().value}")
            return complexity
            
        except Exception as e:
            logger.error(f"Complexity analysis failed: {str(e)}")
            # Default to medium complexity if analysis fails
            return WorkflowComplexity(
                cognitive_complexity=ComplexityLevel.MEDIUM,
                technical_complexity=ComplexityLevel.MEDIUM,
                coordination_complexity=ComplexityLevel.MEDIUM
            )
    
    async def _analyze_prompt_complexity(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt complexity using LLM assistance"""
        try:
            # Use a task agent to analyze prompt complexity
            analysis_agent = TaskAgent(
                thought_tree_id=self.thought_tree_id,
                parent_agent_id=None
            )
            await analysis_agent.initialize()
            
            analysis_input = {
                'task_type': 'data_analysis',
                'description': 'Analyze prompt complexity and requirements',
                'content': f"Analyze the complexity of this request: {prompt}",
                'analysis_focus': 'cognitive_complexity,technical_requirements,scope_assessment',
                'max_tokens': 200
            }
            
            result = await analysis_agent.execute(analysis_input)
            await analysis_agent.terminate()
            
            if result.success:
                # Parse complexity indicators from result
                complexity_indicators = {
                    "cognitive_level": ComplexityLevel.MEDIUM,
                    "technical_requirements": [],
                    "estimated_scope": "medium"
                }
                
                # Simple heuristics based on content analysis
                content_lower = result.content.lower()
                if any(word in content_lower for word in ["complex", "comprehensive", "detailed", "multiple", "various"]):
                    complexity_indicators["cognitive_level"] = ComplexityLevel.HIGH
                elif any(word in content_lower for word in ["simple", "basic", "quick", "straightforward"]):
                    complexity_indicators["cognitive_level"] = ComplexityLevel.LOW
                
                return complexity_indicators
            else:
                return {"cognitive_level": ComplexityLevel.MEDIUM}
                
        except Exception as e:
            logger.error(f"Prompt complexity analysis failed: {str(e)}")
            return {"cognitive_level": ComplexityLevel.MEDIUM}
    
    async def _estimate_resources(self, workflow_input: WorkflowInput, complexity: WorkflowComplexity) -> ResourceEstimate:
        """Estimate resource requirements based on workflow input and complexity"""
        try:
            estimate = ResourceEstimate()
            
            # Base estimates by complexity level
            complexity_multipliers = {
                ComplexityLevel.LOW: 1.0,
                ComplexityLevel.MEDIUM: 2.0,
                ComplexityLevel.HIGH: 4.0
            }
            
            base_multiplier = complexity_multipliers[complexity.overall_complexity()]
            
            # Estimate agent requirements
            estimate.estimated_agents = {
                "task_agents": max(1, int(2 * base_multiplier)),
                "council_agents": 1 if complexity.quality_requirements == ComplexityLevel.HIGH else 0,
                "validator_agents": max(1, int(1 * base_multiplier)),
                "memory_agents": 1
            }
            
            # Estimate costs (based on token usage patterns)
            base_cost = 15.0  # Base cost for simple workflows
            
            estimate.estimated_cost = {
                "llm_calls": base_cost * base_multiplier,
                "agent_coordination": 5.0 * base_multiplier,
                "validation": 3.0 * base_multiplier if complexity.quality_requirements == ComplexityLevel.HIGH else 1.0,
                "total": (base_cost + 5.0 + 3.0) * base_multiplier
            }
            
            # Estimate time requirements
            base_time_minutes = 15
            estimated_minutes = int(base_time_minutes * base_multiplier)
            
            estimate.estimated_time = {
                "sequential_execution": f"{estimated_minutes} minutes",
                "parallel_execution": f"{max(10, estimated_minutes // 2)} minutes",
                "recommended": "parallel_execution" if base_multiplier > 2 else "sequential_execution"
            }
            
            # Add warnings based on analysis
            if estimate.estimated_cost["total"] > self.global_context.get("max_cost_usd", 100.0) * 0.8:
                estimate.resource_warnings.append("Estimated cost approaches budget limits")
            
            if estimated_minutes > self.global_context.get("max_execution_time_minutes", 120) * 0.8:
                estimate.resource_warnings.append("Estimated execution time approaches time limits")
            
            if complexity.requires_decomposition():
                estimate.resource_warnings.append("Complex workflow may require recursive decomposition")
            
            # Set confidence level based on available historical data
            estimate.confidence_level = 0.8 if len(self.workflow_patterns) > 5 else 0.6
            
            logger.info(f"Resource estimate: {estimate.estimated_agents} agents, ${estimate.estimated_cost['total']:.2f}")
            return estimate
            
        except Exception as e:
            logger.error(f"Resource estimation failed: {str(e)}")
            # Return conservative estimates if estimation fails
            return ResourceEstimate(
                estimated_agents={"task_agents": 2, "validator_agents": 1, "memory_agents": 1},
                estimated_cost={"total": 25.0},
                estimated_time={"recommended": "sequential_execution"},
                confidence_level=0.5
            )
    
    async def _select_strategy(self, workflow_input: WorkflowInput, complexity: WorkflowComplexity) -> WorkflowStrategy:
        """Select optimal execution strategy based on analysis and learned patterns"""
        try:
            # LEARNING INTEGRATION: Get strategy recommendation from adaptive engine
            try:
                from core.learning.adaptation import adaptive_engine
                
                # Prepare context for learning system
                workflow_dict = {
                    "type": workflow_input.input_type.value,
                    "content": workflow_input.content,
                    "execution_context": workflow_input.execution_context
                }
                
                complexity_dict = {
                    "cognitive_complexity": complexity.cognitive_complexity.value,
                    "technical_complexity": complexity.technical_complexity.value,
                    "coordination_complexity": complexity.coordination_complexity.value,
                    "data_complexity": complexity.data_complexity.value,
                    "scope_breadth": complexity.scope_breadth.value,
                    "risk_level": complexity.risk_level.value,
                    "quality_requirements": complexity.quality_requirements.value,
                    "time_sensitivity": complexity.time_sensitivity.value
                }
                
                # Get learning-based recommendation
                recommendation = await adaptive_engine.recommend_strategy(
                    workflow_dict, complexity_dict, workflow_input.execution_context
                )
                
                # Convert recommendation to WorkflowStrategy enum
                strategy_mapping = {
                    "direct_execution": WorkflowStrategy.DIRECT_EXECUTION,
                    "sequential_decomposition": WorkflowStrategy.SEQUENTIAL_DECOMPOSITION,
                    "parallel_execution": WorkflowStrategy.PARALLEL_EXECUTION,
                    "recursive_decomposition": WorkflowStrategy.RECURSIVE_DECOMPOSITION,
                    "council_driven": WorkflowStrategy.COUNCIL_DRIVEN,
                    "iterative_refinement": WorkflowStrategy.ITERATIVE_REFINEMENT
                }
                
                recommended_strategy = strategy_mapping.get(recommendation.recommended_strategy)
                
                if recommended_strategy and recommendation.confidence > 0.6:
                    logger.info(f"Learning system recommends {recommendation.recommended_strategy} (confidence: {recommendation.confidence:.3f})")
                    logger.info(f"Reasoning: {'; '.join(recommendation.reasoning)}")
                    
                    # Store learning recommendation in context for later scoring
                    if not hasattr(self, 'learning_context'):
                        self.learning_context = {}
                    self.learning_context['strategy_recommendation'] = recommendation
                    
                    return recommended_strategy
                else:
                    logger.info(f"Learning recommendation confidence too low ({recommendation.confidence:.3f}), using heuristic selection")
                    
            except ImportError:
                logger.warning("Learning system not available, using heuristic strategy selection")
            except Exception as e:
                logger.error(f"Error in learning-based strategy selection: {e}")
                logger.info("Falling back to heuristic strategy selection")
            
            # FALLBACK: Original heuristic strategy selection
            # FIRST: Content type considerations - these are ABSOLUTE requirements
            if workflow_input.input_type == WorkflowInputType.GOAL_WORKFLOW:
                return WorkflowStrategy.RECURSIVE_DECOMPOSITION
            
            execution_context = workflow_input.execution_context
            preferences = execution_context.get("execution_preferences", {})
            
            # Critical path: High-risk or critical validation requirements
            if complexity.risk_level == ComplexityLevel.HIGH or complexity.quality_requirements == ComplexityLevel.HIGH:
                quality_settings = execution_context.get("quality_settings", {})
                if quality_settings.get("require_council_consensus", False):
                    return WorkflowStrategy.COUNCIL_DRIVEN
            
            # Complex decomposition path
            if complexity.requires_decomposition():
                time_constraints = self.global_context.get("max_execution_time_minutes", 120)
                if time_constraints < 60:  # Tight time constraints
                    return WorkflowStrategy.PARALLEL_EXECUTION
                else:
                    return WorkflowStrategy.RECURSIVE_DECOMPOSITION
            
            # Optimization preference path (only for non-goal workflows)
            optimization_focus = preferences.get("optimization_focus", "balanced")
            if optimization_focus == "speed":
                return WorkflowStrategy.PARALLEL_EXECUTION
            elif optimization_focus == "quality":
                return WorkflowStrategy.ITERATIVE_REFINEMENT
            
            # Default strategy based on overall complexity
            if complexity.overall_complexity() == ComplexityLevel.LOW:
                return WorkflowStrategy.DIRECT_EXECUTION
            elif complexity.overall_complexity() == ComplexityLevel.HIGH:
                return WorkflowStrategy.PARALLEL_EXECUTION
            
            # Content type considerations for medium complexity
            if workflow_input.input_type in [WorkflowInputType.STRUCTURED_TASK, WorkflowInputType.SCHEDULED_WORKFLOW]:
                return WorkflowStrategy.SEQUENTIAL_DECOMPOSITION
            else:
                # Medium complexity, simple content type
                return WorkflowStrategy.SEQUENTIAL_DECOMPOSITION
                
        except Exception as e:
            logger.error(f"Strategy selection failed: {str(e)}")
            return WorkflowStrategy.DIRECT_EXECUTION  # Safe fallback
    
    async def _execute_with_strategy(self, workflow_input: WorkflowInput, strategy: WorkflowStrategy) -> Dict[str, Any]:
        """Execute workflow using selected strategy"""
        try:
            logger.info(f"Executing workflow with strategy: {strategy.value}")
            
            if strategy == WorkflowStrategy.DIRECT_EXECUTION:
                return await self._execute_direct(workflow_input)
            elif strategy == WorkflowStrategy.SEQUENTIAL_DECOMPOSITION:
                return await self._execute_sequential(workflow_input)
            elif strategy == WorkflowStrategy.PARALLEL_EXECUTION:
                return await self._execute_parallel(workflow_input)
            elif strategy == WorkflowStrategy.RECURSIVE_DECOMPOSITION:
                return await self._execute_recursive(workflow_input)
            elif strategy == WorkflowStrategy.COUNCIL_DRIVEN:
                return await self._execute_council_driven(workflow_input)
            elif strategy == WorkflowStrategy.ITERATIVE_REFINEMENT:
                return await self._execute_iterative(workflow_input)
            else:
                logger.warning(f"Unknown strategy {strategy}, falling back to direct execution")
                return await self._execute_direct(workflow_input)
                
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            raise
    
    async def _execute_direct(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with single task agent"""
        task_agent = await self.spawn_agent(
            agent_type="task",
            task_context={
                'max_retries': 3,
                'timeout': 300
            }
        )
        
        if not task_agent:
            raise RuntimeError("Failed to spawn task agent for direct execution")
        
        # Convert workflow input to task input
        task_input = await self._convert_to_task_input(workflow_input)
        
        # Execute and track
        result = await task_agent.execute(task_input)
        await self.track_agent_completion(task_agent, result)
        await task_agent.terminate()
        
        return {
            "strategy": "direct_execution",
            "primary_result": result,
            "agent_results": [result],
            "synthesis_required": False
        }
    
    async def _execute_sequential(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with sequential task breakdown"""
        # Decompose into sequential subtasks
        subtasks = await self._decompose_to_subtasks(workflow_input, max_tasks=5)
        
        agent_results = []
        accumulated_context = ""
        
        for i, subtask in enumerate(subtasks):
            task_agent = await self.spawn_agent(
                agent_type="task",
                task_context={'max_retries': 2, 'timeout': 180}
            )
            
            if not task_agent:
                logger.warning(f"Failed to spawn agent for subtask {i+1}")
                continue
            
            # Add accumulated context to subtask
            enhanced_subtask = subtask.copy()
            if accumulated_context:
                enhanced_subtask['context'] = accumulated_context
            
            result = await task_agent.execute(enhanced_subtask)
            await self.track_agent_completion(task_agent, result)
            await task_agent.terminate()
            
            agent_results.append(result)
            
            # Accumulate successful results for context
            if result.success:
                accumulated_context += f"Previous step result: {result.content[:200]}...\n"
            
            # Check for adaptation triggers during execution
            if self.strategy_adaptation_enabled:
                await self._check_adaptation_triggers()
        
        # Synthesize results
        synthesis_result = await self._synthesize_sequential_results(agent_results)
        
        return {
            "strategy": "sequential_decomposition",
            "subtask_results": agent_results,
            "synthesis_result": synthesis_result,
            "synthesis_required": True
        }
    
    async def _execute_parallel(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with parallel task execution"""
        # Decompose into parallel subtasks
        subtasks = await self._decompose_to_subtasks(workflow_input, max_tasks=6)
        
        # Limit parallel execution to available agent slots
        max_parallel = min(len(subtasks), self.max_concurrent_agents - self.current_active_agents)
        
        # Execute tasks in parallel batches
        agent_results = []
        for batch_start in range(0, len(subtasks), max_parallel):
            batch_end = min(batch_start + max_parallel, len(subtasks))
            batch_tasks = subtasks[batch_start:batch_end]
            
            # Spawn agents for batch
            batch_agents = []
            for subtask in batch_tasks:
                agent = await self.spawn_agent(
                    agent_type="task",
                    task_context={'max_retries': 2, 'timeout': 240}
                )
                if agent:
                    batch_agents.append((agent, subtask))
            
            # Execute batch in parallel
            batch_coroutines = [
                self._execute_agent_with_tracking(agent, subtask)
                for agent, subtask in batch_agents
            ]
            
            batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
            
            # Process batch results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch task {batch_start + i} failed: {str(result)}")
                    agent_results.append(AgentResult(
                        success=False,
                        content="",
                        error_message=str(result)
                    ))
                else:
                    agent_results.append(result)
        
        # Synthesize parallel results
        synthesis_result = await self._synthesize_parallel_results(agent_results)
        
        return {
            "strategy": "parallel_execution",
            "parallel_results": agent_results,
            "synthesis_result": synthesis_result,
            "synthesis_required": True
        }
    
    async def _execute_recursive(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with recursive sub-orchestrator decomposition"""
        try:
            from core.orchestrator.sub import SubOrchestrator
            
            # Create decomposition task from workflow input
            decomposition_task = {
                'title': self._extract_workflow_title(workflow_input),
                'description': self._extract_workflow_description(workflow_input),
                'thought_tree_id': self.thought_tree_id,
                'current_depth': 1,  # TopLevel is depth 0, SubOrchestrator starts at 1
                'original_input': workflow_input.content
            }
            
            # Create inherited context for sub-orchestrator
            inherited_context = {
                'resource_constraints': {
                    'max_concurrent_agents': min(self.max_concurrent_agents - self.current_active_agents, 8),
                    'max_cost_remaining': max(0, self.max_cost_usd - self.total_cost_usd),
                    'max_time_remaining': self.global_context.get("max_execution_time_minutes", 120)
                },
                'quality_settings': workflow_input.execution_context.get('quality_settings', {}),
                'parent_context': self.global_context
            }
            
            # Spawn sub-orchestrator
            sub_orchestrator = SubOrchestrator(
                parent_orchestrator_id=self.id,
                decomposition_task=decomposition_task,
                max_depth=min(3, self.max_recursion_depth - 1),  # Limit recursion depth
                max_subtasks=6,  # Reasonable subtask limit
                max_concurrent_agents=inherited_context['resource_constraints']['max_concurrent_agents'],
                inherit_context=inherited_context
            )
            
            # Initialize and execute sub-orchestrator
            if not await sub_orchestrator.initialize():
                logger.warning("SubOrchestrator initialization failed, falling back to parallel execution")
                return await self._execute_parallel(workflow_input)
            
            logger.info(f"TopLevelOrchestrator {self.id}: Spawning SubOrchestrator {sub_orchestrator.id} for recursive decomposition")
            
            # Execute recursive decomposition
            sub_result = await sub_orchestrator.execute_decomposition()
            
            # Update our cost tracking (not agent tracking - different orchestrator context)
            self.total_cost_usd += sub_result.total_cost_usd
            
            # Create synthesis-compatible result format
            # SubOrchestrator already synthesizes internally, so we wrap its final result
            synthesis_result = AgentResult(
                success=sub_result.success,
                content=str(sub_result.final_output) if sub_result.final_output else "",
                tokens_used=sub_result.total_tokens,
                cost_usd=sub_result.total_cost_usd,
                execution_time_ms=sub_result.execution_time_ms
            )
            
            # Return results in expected format
            return {
                "strategy": "recursive_decomposition",
                "sub_orchestrator_id": sub_orchestrator.id,
                "decomposition_result": sub_result,  # Keep for debugging/metadata
                "synthesis_result": synthesis_result,  # Expected by _process_final_results
                "synthesis_required": False  # SubOrchestrator handles synthesis internally
            }
            
        except ImportError as e:
            logger.error(f"SubOrchestrator import failed: {str(e)}")
            logger.info("Falling back to parallel execution")
            return await self._execute_parallel(workflow_input)
        except Exception as e:
            logger.error(f"Recursive decomposition failed: {str(e)}")
            logger.info("Falling back to parallel execution")
            return await self._execute_parallel(workflow_input)
    
    def _extract_workflow_title(self, workflow_input: WorkflowInput) -> str:
        """Extract a title from workflow input"""
        content = workflow_input.content
        
        if workflow_input.input_type == WorkflowInputType.GOAL_WORKFLOW:
            return content.get('goal', {}).get('objective', 'Goal Workflow')
        elif workflow_input.input_type == WorkflowInputType.STRUCTURED_TASK:
            return content.get('task_definition', {}).get('primary_objective', 'Structured Task')
        elif workflow_input.input_type == WorkflowInputType.USER_PROMPT:
            prompt_text = content.get('content', 'User Request')
            # Truncate long prompts for title
            return prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text
        else:
            return f"{workflow_input.input_type.value} Workflow"
    
    def _extract_workflow_description(self, workflow_input: WorkflowInput) -> str:
        """Extract a detailed description from workflow input"""
        content = workflow_input.content
        
        if workflow_input.input_type == WorkflowInputType.GOAL_WORKFLOW:
            goal = content.get('goal', {})
            description = f"Goal: {goal.get('objective', 'No objective specified')}"
            if 'success_criteria' in goal:
                description += f"\nSuccess criteria: {'; '.join(goal['success_criteria'])}"
            return description
        elif workflow_input.input_type == WorkflowInputType.STRUCTURED_TASK:
            task_def = content.get('task_definition', {})
            description = f"Primary objective: {task_def.get('primary_objective', 'No objective')}"
            if 'deliverables' in task_def:
                description += f"\nDeliverables: {'; '.join(task_def['deliverables'])}"
            if 'constraints' in task_def:
                description += f"\nConstraints: {'; '.join(task_def['constraints'])}"
            return description
        else:
            return str(content)
    
    async def _execute_council_driven(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with council decision-making"""
        # Phase 1: Council analysis and decision
        council_agent = await self.spawn_agent(
            agent_type="council",
            task_context={'max_retries': 2, 'timeout': 300}
        )
        
        if not council_agent:
            raise RuntimeError("Failed to spawn council agent")
        
        # Create council decision input
        council_input = {
            'decision_context': f"Workflow strategy decision for {workflow_input.input_type.value} workflow",
            'decision_question': "What is the optimal execution strategy for this workflow?",
            'decision_type': 'workflow_strategy',
            'context': workflow_input.content,
            'options': ['direct_approach', 'decomposed_approach', 'hybrid_approach'],
            'decision_criteria': [
                'technical_feasibility',
                'resource_efficiency',
                'quality_assurance',
                'time_constraints'
            ]
        }
        
        council_result = await council_agent.execute(council_input)
        await self.track_agent_completion(council_agent, council_result)
        await council_agent.terminate()
        
        # Phase 2: Execute based on council decision
        if council_result.success:
            # Parse council recommendation and execute accordingly
            # For now, use parallel execution as the recommended approach
            execution_result = await self._execute_parallel(workflow_input)
            
            return {
                "strategy": "council_driven",
                "council_decision": council_result,
                "execution_result": execution_result,
                "synthesis_required": True
            }
        else:
            # Fallback if council fails
            logger.warning("Council decision failed, falling back to parallel execution")
            return await self._execute_parallel(workflow_input)
    
    async def _execute_iterative(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Execute workflow with iterative refinement"""
        iteration_results = []
        current_content = workflow_input.content
        max_iterations = 3
        
        for iteration in range(max_iterations):
            logger.info(f"Iterative refinement - iteration {iteration + 1}/{max_iterations}")
            
            # Execute current iteration
            task_agent = await self.spawn_agent(
                agent_type="task",
                task_context={'max_retries': 2, 'timeout': 240}
            )
            
            if not task_agent:
                logger.warning(f"Failed to spawn agent for iteration {iteration + 1}")
                break
            
            task_input = await self._convert_to_task_input(
                WorkflowInput(
                    input_type=workflow_input.input_type,
                    content=current_content,
                    execution_context=workflow_input.execution_context
                )
            )
            
            result = await task_agent.execute(task_input)
            await self.track_agent_completion(task_agent, result)
            await task_agent.terminate()
            
            iteration_results.append(result)
            
            if not result.success:
                logger.warning(f"Iteration {iteration + 1} failed: {result.error_message}")
                break
            
            # Evaluate if further refinement is needed
            if iteration < max_iterations - 1:  # Don't validate on last iteration
                needs_refinement = await self._evaluate_refinement_need(result)
                if not needs_refinement:
                    logger.info(f"Quality threshold met after {iteration + 1} iterations")
                    break
                
                # Prepare next iteration with feedback
                current_content = await self._prepare_refinement_input(current_content, result)
        
        return {
            "strategy": "iterative_refinement",
            "iteration_results": iteration_results,
            "final_result": iteration_results[-1] if iteration_results else None,
            "iterations_completed": len(iteration_results),
            "synthesis_required": False
        }
    
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
    
    async def _convert_to_task_input(self, workflow_input: WorkflowInput) -> Dict[str, Any]:
        """Convert workflow input to task agent input format"""
        if workflow_input.input_type == WorkflowInputType.USER_PROMPT:
            return {
                'task_type': 'document_generation',
                'description': 'User request fulfillment',
                'content': workflow_input.content.get('content', ''),
                'max_tokens': 1000
            }
        elif workflow_input.input_type == WorkflowInputType.STRUCTURED_TASK:
            task_def = workflow_input.content.get('task_definition', {})
            return {
                'task_type': 'structured_execution',
                'description': task_def.get('primary_objective', 'Structured task execution'),
                'content': str(task_def),
                'constraints': task_def.get('constraints', []),
                'max_tokens': 1200
            }
        elif workflow_input.input_type == WorkflowInputType.GOAL_WORKFLOW:
            goal = workflow_input.content.get('goal', {})
            return {
                'task_type': 'goal_achievement',
                'description': goal.get('objective', 'Goal achievement'),
                'content': f"Objective: {goal.get('objective', '')}\nSuccess Criteria: {goal.get('success_criteria', [])}",
                'max_tokens': 1500
            }
        else:
            # Generic conversion for other types
            return {
                'task_type': 'document_generation',
                'description': f"Workflow execution: {workflow_input.input_type.value}",
                'content': str(workflow_input.content),
                'max_tokens': 1000
            }
    
    async def _decompose_to_subtasks(self, workflow_input: WorkflowInput, max_tasks: int = 5) -> List[Dict[str, Any]]:
        """Decompose workflow into manageable subtasks"""
        try:
            # Use a task agent to help with decomposition
            decomposition_agent = await self.spawn_agent(
                agent_type="task",
                task_context={'max_retries': 2, 'timeout': 180}
            )
            
            if not decomposition_agent:
                # Fallback to simple decomposition
                return [await self._convert_to_task_input(workflow_input)]
            
            decomposition_input = {
                'task_type': 'task_decomposition',
                'description': 'Break down complex workflow into subtasks',
                'content': f"Decompose this workflow into {max_tasks} or fewer subtasks: {workflow_input.content}",
                'output_format': 'numbered_list',
                'max_tokens': 800
            }
            
            result = await decomposition_agent.execute(decomposition_input)
            await self.track_agent_completion(decomposition_agent, result)
            await decomposition_agent.terminate()
            
            if result.success:
                # Parse subtasks from result
                subtasks = await self._parse_subtasks_from_content(result.content, workflow_input)
                return subtasks[:max_tasks]  # Limit to max_tasks
            else:
                # Fallback to single task
                return [await self._convert_to_task_input(workflow_input)]
                
        except Exception as e:
            logger.error(f"Task decomposition failed: {str(e)}")
            return [await self._convert_to_task_input(workflow_input)]
    
    async def _parse_subtasks_from_content(self, content: str, original_input: WorkflowInput) -> List[Dict[str, Any]]:
        """Parse subtasks from decomposition content"""
        subtasks = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Extract task description
                task_desc = line.split('.', 1)[-1].strip() if '.' in line else line
                if len(task_desc) > 10:  # Reasonable minimum length
                    subtasks.append({
                        'task_type': 'document_generation',
                        'description': task_desc,
                        'content': task_desc,
                        'max_tokens': 600
                    })
        
        # Ensure we have at least one task
        if not subtasks:
            subtasks = [await self._convert_to_task_input(original_input)]
        
        return subtasks
    
    async def _synthesize_sequential_results(self, agent_results: List[AgentResult]) -> AgentResult:
        """Synthesize results from sequential execution"""
        try:
            # Use memory agent for synthesis
            synthesis_agent = await self.spawn_agent(
                agent_type="memory",
                task_context={'max_retries': 2, 'timeout': 300}
            )
            
            if not synthesis_agent:
                return self._create_fallback_synthesis(agent_results)
            
            # Prepare synthesis input
            successful_results = [r for r in agent_results if r.success]
            content_pieces = [r.content for r in successful_results]
            
            synthesis_input = {
                'operation': 'summarize',
                'operation_type': 'context_synthesis',
                'content_pieces': content_pieces,
                'synthesis_focus': 'sequential_workflow_completion',
                'target_scope': 'workflow'
            }
            
            synthesis_result = await synthesis_agent.execute(synthesis_input)
            await self.track_agent_completion(synthesis_agent, synthesis_result)
            await synthesis_agent.terminate()
            
            return synthesis_result if synthesis_result.success else self._create_fallback_synthesis(agent_results)
            
        except Exception as e:
            logger.error(f"Sequential synthesis failed: {str(e)}")
            return self._create_fallback_synthesis(agent_results)
    
    async def _synthesize_parallel_results(self, agent_results: List[AgentResult]) -> AgentResult:
        """Synthesize results from parallel execution"""
        try:
            synthesis_agent = await self.spawn_agent(
                agent_type="memory",
                task_context={'max_retries': 2, 'timeout': 300}
            )
            
            if not synthesis_agent:
                return self._create_fallback_synthesis(agent_results)
            
            successful_results = [r for r in agent_results if r.success]
            content_pieces = [r.content for r in successful_results]
            
            synthesis_input = {
                'operation': 'summarize',
                'operation_type': 'context_synthesis',
                'content_pieces': content_pieces,
                'synthesis_focus': 'parallel_workflow_aggregation',
                'target_scope': 'workflow'
            }
            
            synthesis_result = await synthesis_agent.execute(synthesis_input)
            await self.track_agent_completion(synthesis_agent, synthesis_result)
            await synthesis_agent.terminate()
            
            return synthesis_result if synthesis_result.success else self._create_fallback_synthesis(agent_results)
            
        except Exception as e:
            logger.error(f"Parallel synthesis failed: {str(e)}")
            return self._create_fallback_synthesis(agent_results)
    
    def _create_fallback_synthesis(self, agent_results: List[AgentResult]) -> AgentResult:
        """Create fallback synthesis when dedicated synthesis fails"""
        successful_results = [r for r in agent_results if r.success]
        failed_results = [r for r in agent_results if not r.success]
        
        if successful_results:
            combined_content = "\n\n".join([
                f"Result {i+1}: {result.content}" 
                for i, result in enumerate(successful_results)
            ])
            
            synthesis_content = f"Workflow Completion Summary:\n\n{combined_content}"
            
            if failed_results:
                synthesis_content += f"\n\nNote: {len(failed_results)} subtasks failed during execution."
            
            return AgentResult(
                success=True,
                content=synthesis_content,
                metadata={
                    'successful_subtasks': len(successful_results),
                    'failed_subtasks': len(failed_results),
                    'synthesis_method': 'fallback_concatenation'
                }
            )
        else:
            return AgentResult(
                success=False,
                content="",
                error_message="All subtasks failed - no content to synthesize"
            )
    
    async def _evaluate_refinement_need(self, result: AgentResult) -> bool:
        """Evaluate if result needs further refinement"""
        try:
            # Use validator for quality assessment
            validator = await self.spawn_agent(
                agent_type="validator",
                task_context={'max_retries': 1, 'timeout': 120}
            )
            
            if not validator:
                return False  # No refinement if we can't validate
            
            validation_input = {
                'content_to_validate': result.content,
                'validation_type': 'quality_assessment',
                'content': result.content,
                'quality_threshold': 'medium',
                'assessment_focus': ['completeness', 'accuracy', 'clarity']
            }
            
            validation_result = await validator.execute(validation_input)
            await self.track_agent_completion(validator, validation_result)
            await validator.terminate()
            
            if validation_result.success:
                # Parse validation result for refinement need
                content_lower = validation_result.content.lower()
                needs_improvement = any(phrase in content_lower for phrase in [
                    'needs improvement', 'requires refinement', 'could be better',
                    'incomplete', 'unclear', 'insufficient'
                ])
                return needs_improvement
            else:
                return False
                
        except Exception as e:
            logger.error(f"Refinement evaluation failed: {str(e)}")
            return False
    
    async def _prepare_refinement_input(self, original_content: Dict[str, Any], previous_result: AgentResult) -> Dict[str, Any]:
        """Prepare input for next refinement iteration"""
        refinement_content = original_content.copy()
        
        # Add feedback context
        if 'refinement_feedback' not in refinement_content:
            refinement_content['refinement_feedback'] = []
        
        refinement_content['refinement_feedback'].append({
            'iteration': len(refinement_content['refinement_feedback']) + 1,
            'previous_output': previous_result.content[:500] + "...",
            'improvement_focus': 'Address quality concerns and enhance completeness'
        })
        
        return refinement_content
    
    async def _process_final_results(self, execution_result: Dict[str, Any]) -> OrchestratorResult:
        """Process execution results into final orchestrator result"""
        try:
            # Use the actual selected strategy, not the execution method's hardcoded strategy
            strategy = self.selected_strategy.value if self.selected_strategy else "unknown"
            
            # Determine final output based on strategy
            if strategy in ["direct_execution", "iterative_refinement"]:
                primary_result = execution_result.get("primary_result") or execution_result.get("final_result")
                final_output = {
                    'strategy_used': strategy,
                    'content': primary_result.content if primary_result else "",
                    'success': primary_result.success if primary_result else False
                }
            else:
                # Strategies with synthesis
                synthesis_result = execution_result.get("synthesis_result")
                
                # Handle nested execution results (e.g., council_driven -> parallel execution)
                if not synthesis_result and "execution_result" in execution_result:
                    nested_result = execution_result["execution_result"]
                    synthesis_result = nested_result.get("synthesis_result") if nested_result else None
                
                final_output = {
                    'strategy_used': strategy,
                    'content': synthesis_result.content if synthesis_result else "",
                    'success': synthesis_result.success if synthesis_result else False,
                    'subtask_count': len(execution_result.get("subtask_results", []) or 
                                        execution_result.get("parallel_results", []) or
                                        execution_result.get("iteration_results", []) or
                                        (execution_result.get("execution_result", {}).get("parallel_results", [])))
                }
            
            # Calculate comprehensive metrics
            total_cost = self.total_cost_usd
            execution_time_ms = int((datetime.now() - self.created_at).total_seconds() * 1000)
            
            # Determine error message if workflow failed
            error_message = None
            if not final_output.get('success', False):
                if len(self.failed_agents) > 0:
                    error_message = f"{len(self.failed_agents)} of {len(self.spawned_agents) + len(self.completed_agents) + len(self.failed_agents)} agents failed during execution"
                elif not final_output.get('content'):
                    error_message = "Workflow completed but produced no output"
                else:
                    error_message = "Workflow execution failed"
            
            # LEARNING INTEGRATION: Score this workflow execution
            orchestrator_result = OrchestratorResult(
                success=final_output.get('success', False),
                workflow_id=self.thought_tree_id or "",
                agents_spawned=len(self.spawned_agents) + len(self.completed_agents) + len(self.failed_agents),
                agents_completed=len(self.completed_agents),
                agents_failed=len(self.failed_agents),
                total_cost_usd=total_cost,
                total_tokens=self.total_tokens,
                execution_time_ms=execution_time_ms,
                final_output=final_output,
                error_message=error_message,
                metadata={
                    'strategy_used': strategy,
                    'complexity_analysis': self.complexity_analysis.__dict__ if self.complexity_analysis else {},
                    'resource_estimate': self.resource_estimate.__dict__ if self.resource_estimate else {},
                    'monitoring_final_state': self.monitoring_state.__dict__,
                    'learning_context': getattr(self, 'learning_context', {})
                }
            )
            
            # Schedule scoring in background to avoid blocking the response
            if self.thought_tree_id:
                asyncio.create_task(self._score_workflow_execution(orchestrator_result))
            
            return orchestrator_result
            
        except Exception as e:
            logger.error(f"Final result processing failed: {str(e)}")
            return OrchestratorResult(
                success=False,
                workflow_id=self.thought_tree_id or "",
                agents_spawned=0,
                agents_completed=0,
                agents_failed=1,
                error_message=f"Result processing failed: {str(e)}"
            )
    
    async def _update_monitoring_state(self, phase: str, progress: float):
        """Update monitoring state with current progress"""
        self.monitoring_state.progress_percentage = progress
        self.monitoring_state.last_updated = datetime.now()
        self.monitoring_state.agents_active = self.current_active_agents
        self.monitoring_state.agents_completed = len(self.completed_agents)
        self.monitoring_state.agents_failed = len(self.failed_agents)
        self.monitoring_state.cost_consumed = self.total_cost_usd
        
        elapsed = (datetime.now() - self.created_at).total_seconds() / 60
        self.monitoring_state.time_elapsed_minutes = elapsed
        
        logger.info(f"Workflow phase: {phase} ({progress:.1f}% complete)")
    
    async def _check_adaptation_triggers(self):
        """Check if workflow strategy needs adaptation using learning system"""
        if not self.strategy_adaptation_enabled:
            return
        
        # LEARNING INTEGRATION: Use adaptive engine for intelligent adaptation
        try:
            from core.learning.adaptation import adaptive_engine
            
            # Prepare current performance metrics
            current_performance = {
                "execution_time": self.monitoring_state.time_elapsed_minutes * 60,  # Convert to seconds
                "cost_consumed": float(self.monitoring_state.cost_consumed),
                "success_rate": self._calculate_current_success_rate(),
                "failure_rate": self._calculate_current_failure_rate(),
                "agent_count": self.monitoring_state.agents_completed + self.monitoring_state.agents_failed
            }
            
            # Get expected performance from learning context
            expected_performance = {}
            if hasattr(self, 'learning_context') and 'strategy_recommendation' in self.learning_context:
                expected_performance = self.learning_context['strategy_recommendation'].expected_performance
            else:
                # Use default expectations
                expected_performance = {
                    "execution_time": 300.0,  # 5 minutes default
                    "cost_estimate": 25.0,
                    "success_rate": 0.8,
                    "quality_score": 0.7
                }
            
            # Check if adaptation is needed
            adaptation_rec = await adaptive_engine.should_adapt_workflow(
                current_performance=current_performance,
                expected_performance=expected_performance,
                execution_context={
                    "current_strategy": self.selected_strategy.value if self.selected_strategy else "unknown",
                    "complexity_level": self.complexity_analysis.overall_complexity().value if self.complexity_analysis else "medium",
                    "workflow_type": self.workflow_input.input_type.value if hasattr(self, 'workflow_input') else "unknown"
                }
            )
            
            if adaptation_rec:
                logger.info(f"Learning system recommends adaptation: {adaptation_rec.description}")
                logger.info(f"Urgency: {adaptation_rec.urgency}, Actions: {adaptation_rec.recommended_actions}")
                
                # Store adaptation recommendation
                self.adaptation_triggers.extend(adaptation_rec.triggers)
                
                # Execute intelligent adaptations
                await self._execute_learning_adaptations(adaptation_rec)
                return
                
        except ImportError:
            logger.warning("Learning system not available for adaptation")
        except Exception as e:
            logger.error(f"Error in learning-based adaptation: {e}")
        
        # FALLBACK: Original trigger-based adaptation
        triggers = []
        
        # Cost overrun check
        max_cost = self.global_context.get("max_cost_usd", 100.0)
        if self.monitoring_state.cost_consumed > max_cost * 0.8:
            triggers.append("cost_overrun_risk")
        
        # Time overrun check
        max_time = self.global_context.get("max_execution_time_minutes", 120)
        if self.monitoring_state.time_elapsed_minutes > max_time * 0.8:
            triggers.append("time_overrun_risk")
        
        # Failure rate check
        total_agents = self.monitoring_state.agents_completed + self.monitoring_state.agents_failed
        if total_agents > 0:
            failure_rate = self.monitoring_state.agents_failed / total_agents
            if failure_rate > 0.3:
                triggers.append("high_failure_rate")
        
        if triggers:
            self.adaptation_triggers.extend(triggers)
            await self._adapt_strategy(triggers)
    
    def _calculate_current_success_rate(self) -> float:
        """Calculate current success rate of agents"""
        total = self.monitoring_state.agents_completed + self.monitoring_state.agents_failed
        if total == 0:
            return 1.0
        return self.monitoring_state.agents_completed / total
    
    def _calculate_current_failure_rate(self) -> float:
        """Calculate current failure rate of agents"""
        total = self.monitoring_state.agents_completed + self.monitoring_state.agents_failed
        if total == 0:
            return 0.0
        return self.monitoring_state.agents_failed / total
    
    async def _execute_learning_adaptations(self, adaptation_rec):
        """Execute adaptations recommended by the learning system"""
        try:
            from core.learning.adaptation import AdaptationType
            
            if adaptation_rec.adaptation_type == AdaptationType.TIMEOUT_ADJUSTMENT:
                # Increase timeouts as recommended
                if "Increase timeout limits by 50%" in adaptation_rec.recommended_actions:
                    # Adjust agent timeouts
                    for agent in self.spawned_agents:
                        if hasattr(agent, 'timeout_seconds'):
                            agent.timeout_seconds = int(agent.timeout_seconds * 1.5)
                    logger.info("Increased agent timeout limits by 50%")
            
            elif adaptation_rec.adaptation_type == AdaptationType.STRATEGY_CHANGE:
                if "Switch to council-driven strategy" in adaptation_rec.recommended_actions:
                    # This would require more complex strategy switching mid-workflow
                    # For now, just adjust parameters to be more conservative
                    self.max_concurrent_agents = max(2, self.max_concurrent_agents // 2)
                    logger.info("Reduced concurrency for more careful execution")
                    
            elif adaptation_rec.adaptation_type == AdaptationType.RESOURCE_ADJUSTMENT:
                if "Reduce concurrent agent count" in adaptation_rec.recommended_actions:
                    self.max_concurrent_agents = max(2, self.max_concurrent_agents // 2)
                    logger.info(f"Reduced max concurrent agents to {self.max_concurrent_agents}")
                    
            elif adaptation_rec.adaptation_type == AdaptationType.PARAMETER_OPTIMIZATION:
                # Apply parameter optimizations as recommended
                logger.info("Applying parameter optimizations from learning system")
                
            # Log adaptation for future learning
            if not hasattr(self, 'learning_context'):
                self.learning_context = {}
            self.learning_context['adaptations_applied'] = adaptation_rec.recommended_actions
            
        except Exception as e:
            logger.error(f"Error executing learning-based adaptations: {e}")
            # Fall back to original adaptation logic
            await self._adapt_strategy(adaptation_rec.triggers)
    
    async def _adapt_strategy(self, triggers: List[str]):
        """Adapt workflow strategy based on triggers"""
        try:
            logger.info(f"Adapting strategy due to triggers: {triggers}")
            
            for trigger in triggers:
                if trigger == "cost_overrun_risk":
                    # Reduce parallelization to save costs
                    self.max_concurrent_agents = max(2, self.max_concurrent_agents // 2)
                    logger.info(f"Reduced max concurrent agents to {self.max_concurrent_agents}")
                
                elif trigger == "time_overrun_risk":
                    # Increase parallelization to speed up
                    original_max = self.global_context.get("max_concurrent_agents", 20)
                    self.max_concurrent_agents = min(original_max, self.max_concurrent_agents + 2)
                    logger.info(f"Increased max concurrent agents to {self.max_concurrent_agents}")
                
                elif trigger == "high_failure_rate":
                    # Switch to more conservative strategy
                    logger.info("High failure rate detected - implementing conservative approach")
                    # Could spawn council agent for failure analysis here
        
        except Exception as e:
            logger.error(f"Strategy adaptation failed: {str(e)}")
    
    async def _load_historical_context(self):
        """Load historical workflow patterns and performance metrics"""
        try:
            # This would typically load from database
            # For now, initialize with empty patterns
            self.workflow_patterns = {}
            self.performance_metrics = {
                'avg_workflow_duration_minutes': 25.0,
                'avg_success_rate': 0.87,
                'avg_cost_per_workflow': 35.0
            }
            
            logger.info("Historical context loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load historical context: {str(e)}")
    
    async def _record_workflow_outcomes(self, workflow_input: WorkflowInput, result: OrchestratorResult):
        """Record workflow outcomes for future learning"""
        try:
            outcome_record = {
                'input_type': workflow_input.input_type.value,
                'strategy_used': self.selected_strategy.value if self.selected_strategy else "unknown",
                'success': result.success,
                'cost': result.total_cost_usd,
                'execution_time_minutes': result.execution_time_ms / 60000,
                'agents_used': result.agents_spawned,
                'complexity_overall': self.complexity_analysis.overall_complexity().value if self.complexity_analysis else "unknown",
                'timestamp': datetime.now()
            }
            
            # Store for future pattern recognition
            pattern_key = f"{workflow_input.input_type.value}_{self.selected_strategy.value if self.selected_strategy else 'unknown'}"
            if pattern_key not in self.workflow_patterns:
                self.workflow_patterns[pattern_key] = []
            
            self.workflow_patterns[pattern_key].append(outcome_record)
            
            logger.info(f"Recorded workflow outcome: {pattern_key}")
            
        except Exception as e:
            logger.error(f"Failed to record workflow outcomes: {str(e)}")
    
    async def _handle_workflow_failure(self, error: Exception):
        """Handle workflow-level failures"""
        try:
            logger.error(f"Handling workflow failure: {str(error)}")
            
            # Update monitoring state
            self.monitoring_state.risk_factors.append(f"Workflow failure: {str(error)}")
            
            # Attempt cleanup of any remaining agents
            for agent in self.spawned_agents[:]:
                try:
                    await agent.terminate()
                    await self.track_agent_completion(agent, AgentResult(
                        success=False,
                        content="",
                        error_message="Terminated due to workflow failure"
                    ))
                except:
                    pass  # Best effort cleanup
            
        except Exception as cleanup_error:
            logger.error(f"Workflow failure cleanup failed: {str(cleanup_error)}")
    
    async def _score_workflow_execution(self, orchestrator_result: OrchestratorResult):
        """Score completed workflow execution using learning system"""
        try:
            from core.learning.scorer import performance_scorer, ScoringContext, update_thought_tree_scores
            from core.learning.metrics import ComplexityLevel
            
            if not self.thought_tree_id:
                logger.warning("No thought_tree_id available for scoring")
                return
            
            # Determine complexity level
            if self.complexity_analysis:
                complexity_level = self.complexity_analysis.overall_complexity()
            else:
                complexity_level = ComplexityLevel.MEDIUM
            
            # Create scoring context
            context = ScoringContext(
                thought_tree_id=self.thought_tree_id,
                workflow_type=getattr(self.workflow_input, 'input_type', {}).value if hasattr(self, 'workflow_input') else None,
                complexity_level=complexity_level,
                goal_alignment=0.9 if orchestrator_result.success else 0.3,  # Basic goal alignment based on success
                business_impact=0.7,  # Default business impact
                validation_results=None,  # Could be enhanced with actual validation results
                custom_weights=None
            )
            
            # Calculate execution time
            start_time = self.created_at
            end_time = datetime.now()
            
            # Score the workflow
            scoring_result = await performance_scorer.score_workflow_execution(
                self.thought_tree_id, start_time, end_time, context
            )
            
            # Update database with scores
            await update_thought_tree_scores(self.thought_tree_id, scoring_result)
            
            logger.info(f"Workflow scored - Composite: {scoring_result.composite_score:.3f}, "
                       f"Speed: {scoring_result.speed_score:.3f}, "
                       f"Quality: {scoring_result.quality_score:.3f}, "
                       f"Success: {scoring_result.success_score:.3f}")
            
        except ImportError:
            logger.debug("Learning system not available for scoring")
        except Exception as e:
            logger.error(f"Error scoring workflow execution: {e}")
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status for monitoring"""
        return {
            'orchestrator_id': self.id,
            'workflow_state': self.state.value,
            'current_strategy': self.selected_strategy.value if self.selected_strategy else None,
            'monitoring_state': self.monitoring_state.__dict__,
            'complexity_analysis': self.complexity_analysis.__dict__ if self.complexity_analysis else None,
            'resource_estimate': self.resource_estimate.__dict__ if self.resource_estimate else None,
            'adaptation_triggers': self.adaptation_triggers,
            'last_updated': datetime.now().isoformat()
        }