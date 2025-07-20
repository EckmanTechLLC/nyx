"""
NYX Learning System - Pattern Recognition Module

Identifies successful and failed patterns across system executions.
Analyzes strategy performance, agent effectiveness, and failure modes.
"""

import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter

# System imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, ToolExecution, Orchestrator
from core.learning.metrics import ComplexityLevel, PerformanceMetrics
from config.settings import settings
from sqlalchemy import func, and_, desc, text, select
from sqlalchemy.orm import selectinload

import logging
logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be identified"""
    STRATEGY_SUCCESS = "strategy_success"
    STRATEGY_FAILURE = "strategy_failure"
    AGENT_PERFORMANCE = "agent_performance"
    FAILURE_SEQUENCE = "failure_sequence"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    TEMPORAL_PATTERN = "temporal_pattern"


@dataclass
class StrategyPattern:
    """Pattern representing strategy performance characteristics"""
    strategy_name: str
    complexity_level: ComplexityLevel
    workflow_type: Optional[str]
    success_rate: float
    avg_execution_time: float
    avg_cost: Decimal
    sample_size: int
    confidence: float
    last_updated: datetime
    
    # Performance characteristics
    speed_score: float
    quality_score: float
    reliability: float
    
    # Context patterns
    optimal_conditions: Dict[str, Any]
    failure_indicators: List[str]


@dataclass
class AgentPerformancePattern:
    """Pattern representing agent performance in specific contexts"""
    agent_type: str
    task_category: str
    complexity_level: ComplexityLevel
    success_rate: float
    avg_execution_time: float
    avg_retry_count: float
    typical_token_usage: int
    sample_size: int
    confidence: float
    
    # Performance insights
    strengths: List[str]
    weaknesses: List[str]
    optimal_scenarios: List[str]


@dataclass
class FailurePattern:
    """Pattern representing common failure modes"""
    pattern_id: str
    pattern_type: str
    frequency: int
    affected_components: List[str]
    common_context: Dict[str, Any]
    typical_error_messages: List[str]
    recovery_strategies: List[str]
    prevention_measures: List[str]
    first_observed: datetime
    last_observed: datetime


@dataclass
class OptimizationOpportunity:
    """Identified opportunity for system optimization"""
    opportunity_id: str
    category: str  # "timeout", "agent_selection", "strategy_choice", etc.
    description: str
    potential_improvement: float  # Expected improvement factor
    affected_workflows: List[str]
    implementation_effort: str  # "low", "medium", "high"
    confidence: float


class PatternAnalyzer:
    """Analyzes execution patterns to identify optimization opportunities"""
    
    def __init__(self):
        self.pattern_cache = {}
        self.cache_ttl = timedelta(hours=2)
        
    async def analyze_strategy_patterns(
        self,
        time_window: timedelta = timedelta(days=30),
        min_sample_size: int = 5
    ) -> Dict[str, List[StrategyPattern]]:
        """Analyze strategy performance patterns across different contexts"""
        
        logger.info(f"Analyzing strategy patterns over {time_window.days} days")
        
        cutoff_date = datetime.now() - time_window
        patterns_by_strategy = defaultdict(list)
        
        async with db_manager.get_async_session() as session:
            # Get orchestrator executions with strategy information
            orchestrators = await session.execute(
                select(Orchestrator)
                .join(ThoughtTree)
                .filter(
                    and_(
                        ThoughtTree.completed_at >= cutoff_date,
                        ThoughtTree.status.in_(["completed", "failed"]),
                        Orchestrator.orchestrator_type == "top_level"
                    )
                )
                .options(selectinload(Orchestrator.thought_tree))
            )
            orchestrators = orchestrators.scalars().all()
            
            # Group by strategy and context
            strategy_groups = defaultdict(list)
            
            for orchestrator in orchestrators:
                thought_tree = orchestrator.thought_tree
                if not thought_tree or not thought_tree.metadata_:
                    continue
                
                # Extract strategy from metadata
                strategy = thought_tree.metadata_.get("execution_strategy", "unknown")
                workflow_type = thought_tree.metadata_.get("workflow_type")
                complexity_level = self._get_complexity_from_metadata(thought_tree.metadata_)
                
                # Create grouping key
                group_key = (strategy, complexity_level, workflow_type)
                strategy_groups[group_key].append({
                    "orchestrator": orchestrator,
                    "thought_tree": thought_tree,
                    "strategy": strategy,
                    "complexity_level": complexity_level,
                    "workflow_type": workflow_type
                })
            
            # Analyze each strategy group
            for (strategy, complexity_level, workflow_type), executions in strategy_groups.items():
                if len(executions) < min_sample_size:
                    continue
                
                pattern = await self._analyze_strategy_group(executions, session)
                if pattern:
                    patterns_by_strategy[strategy].append(pattern)
        
        logger.info(f"Identified {sum(len(patterns) for patterns in patterns_by_strategy.values())} strategy patterns")
        return dict(patterns_by_strategy)
    
    async def _analyze_strategy_group(
        self,
        executions: List[Dict],
        session
    ) -> Optional[StrategyPattern]:
        """Analyze a group of executions using the same strategy"""
        
        if not executions:
            return None
        
        # Extract common characteristics
        first_execution = executions[0]
        strategy = first_execution["strategy"]
        complexity_level = first_execution["complexity_level"]
        workflow_type = first_execution["workflow_type"]
        
        # Calculate performance metrics
        success_count = 0
        execution_times = []
        costs = []
        speed_scores = []
        quality_scores = []
        
        for execution in executions:
            thought_tree = execution["thought_tree"]
            
            # Success rate
            if thought_tree.status == "completed":
                success_count += 1
            
            # Execution time
            if thought_tree.created_at and thought_tree.completed_at:
                exec_time = (thought_tree.completed_at - thought_tree.created_at).total_seconds()
                execution_times.append(exec_time)
            
            # Cost (from LLM interactions)
            llm_interactions = await session.execute(
                select(LLMInteraction)
                .filter(LLMInteraction.thought_tree_id == thought_tree.id)
            )
            tree_cost = sum(
                interaction.cost_usd or Decimal('0')
                for interaction in llm_interactions.scalars()
            )
            costs.append(tree_cost)
            
            # Existing scores
            if thought_tree.speed_score:
                speed_scores.append(float(thought_tree.speed_score))
            if thought_tree.quality_score:
                quality_scores.append(float(thought_tree.quality_score))
        
        # Calculate aggregated metrics
        success_rate = success_count / len(executions)
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        avg_cost = sum(costs) / len(costs) if costs else Decimal('0')
        avg_speed_score = sum(speed_scores) / len(speed_scores) if speed_scores else 0.5
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
        
        # Calculate reliability (consistency of success)
        reliability = self._calculate_reliability(executions)
        
        # Identify optimal conditions and failure indicators
        optimal_conditions, failure_indicators = await self._identify_context_patterns(
            executions, session
        )
        
        # Calculate confidence based on sample size and consistency
        confidence = min(1.0, len(executions) / 20.0) * (reliability * 0.5 + 0.5)
        
        return StrategyPattern(
            strategy_name=strategy,
            complexity_level=complexity_level,
            workflow_type=workflow_type,
            success_rate=success_rate,
            avg_execution_time=avg_execution_time,
            avg_cost=avg_cost,
            sample_size=len(executions),
            confidence=confidence,
            last_updated=datetime.now(),
            speed_score=avg_speed_score,
            quality_score=avg_quality_score,
            reliability=reliability,
            optimal_conditions=optimal_conditions,
            failure_indicators=failure_indicators
        )
    
    def _calculate_reliability(self, executions: List[Dict]) -> float:
        """Calculate reliability as consistency of outcomes"""
        
        outcomes = [exec["thought_tree"].status for exec in executions]
        most_common_outcome = Counter(outcomes).most_common(1)[0][1]
        return most_common_outcome / len(executions)
    
    async def _identify_context_patterns(
        self,
        executions: List[Dict],
        session
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Identify context patterns for optimal conditions and failure indicators"""
        
        successful_contexts = []
        failed_contexts = []
        
        for execution in executions:
            thought_tree = execution["thought_tree"]
            context = thought_tree.metadata_.get("execution_context", {})
            
            if thought_tree.status == "completed":
                successful_contexts.append(context)
            else:
                failed_contexts.append(context)
        
        # Analyze patterns in successful contexts
        optimal_conditions = self._extract_common_patterns(successful_contexts)
        
        # Analyze patterns in failed contexts
        failure_patterns = self._extract_common_patterns(failed_contexts)
        failure_indicators = list(failure_patterns.keys())
        
        return optimal_conditions, failure_indicators
    
    def _extract_common_patterns(self, contexts: List[Dict]) -> Dict[str, Any]:
        """Extract common patterns from context data"""
        
        if not contexts:
            return {}
        
        patterns = {}
        
        # Find common keys and their frequent values
        all_keys = set()
        for context in contexts:
            all_keys.update(context.keys())
        
        for key in all_keys:
            values = []
            for context in contexts:
                if key in context:
                    values.append(context[key])
            
            if values:
                # For numeric values, calculate average
                if all(isinstance(v, (int, float)) for v in values):
                    patterns[key] = sum(values) / len(values)
                # For categorical values, find most common
                else:
                    most_common = Counter(str(v) for v in values).most_common(1)
                    if most_common:
                        patterns[key] = most_common[0][0]
        
        return patterns
    
    def _get_complexity_from_metadata(self, metadata: Dict) -> ComplexityLevel:
        """Extract complexity level from metadata"""
        
        complexity_info = metadata.get("complexity", {})
        if isinstance(complexity_info, dict):
            high_count = sum(1 for level in complexity_info.values() if level == "high")
            if high_count >= 3:
                return ComplexityLevel.CRITICAL
            elif high_count >= 2:
                return ComplexityLevel.HIGH
            elif high_count >= 1:
                return ComplexityLevel.MEDIUM
            else:
                return ComplexityLevel.LOW
        else:
            return ComplexityLevel.MEDIUM
    
    async def analyze_agent_performance_patterns(
        self,
        time_window: timedelta = timedelta(days=30)
    ) -> Dict[str, List[AgentPerformancePattern]]:
        """Analyze agent performance patterns across different contexts"""
        
        logger.info("Analyzing agent performance patterns")
        
        cutoff_date = datetime.now() - time_window
        patterns_by_type = defaultdict(list)
        
        async with db_manager.get_async_session() as session:
            # Get agent executions
            agents = await session.execute(
                select(Agent)
                .join(ThoughtTree)
                .filter(
                    and_(
                        ThoughtTree.completed_at >= cutoff_date,
                        Agent.status.in_(["completed", "failed", "terminated"])
                    )
                )
                .options(selectinload(Agent.thought_tree))
            )
            agents = agents.scalars().all()
            
            # Group agents by type and context
            agent_groups = defaultdict(list)
            
            for agent in agents:
                if not agent.thought_tree:
                    continue
                
                # Determine task category from context
                task_category = self._determine_task_category(agent)
                complexity_level = self._get_complexity_from_metadata(
                    agent.thought_tree.metadata_ or {}
                )
                
                group_key = (agent.agent_type, task_category, complexity_level)
                agent_groups[group_key].append(agent)
            
            # Analyze each agent group
            for (agent_type, task_category, complexity_level), agent_list in agent_groups.items():
                if len(agent_list) >= 3:  # Minimum sample size for agent analysis
                    pattern = await self._analyze_agent_group(agent_list, session)
                    if pattern:
                        patterns_by_type[agent_type].append(pattern)
        
        logger.info(f"Identified {sum(len(patterns) for patterns in patterns_by_type.values())} agent patterns")
        return dict(patterns_by_type)
    
    def _determine_task_category(self, agent: Agent) -> str:
        """Determine task category for an agent based on context"""
        
        if not agent.context:
            return "general"
        
        # Look for task type indicators in context
        context = agent.context
        if isinstance(context, dict):
            task_type = context.get("task_type", "general")
            if task_type != "general":
                return task_type
            
            # Infer from agent class or other context
            agent_class = context.get("agent_class", agent.agent_class)
            if "document" in agent_class.lower():
                return "documentation"
            elif "code" in agent_class.lower():
                return "code_generation"
            elif "analysis" in agent_class.lower():
                return "analysis"
        
        return "general"
    
    async def _analyze_agent_group(
        self,
        agents: List[Agent],
        session
    ) -> Optional[AgentPerformancePattern]:
        """Analyze performance pattern for a group of similar agents"""
        
        if not agents:
            return None
        
        # Extract common characteristics
        first_agent = agents[0]
        agent_type = first_agent.agent_type
        task_category = self._determine_task_category(first_agent)
        complexity_level = self._get_complexity_from_metadata(
            first_agent.thought_tree.metadata_ or {}
        )
        
        # Calculate performance metrics
        success_count = sum(1 for agent in agents if agent.status == "completed")
        success_rate = success_count / len(agents)
        
        # Execution times
        execution_times = []
        for agent in agents:
            if agent.created_at and agent.completed_at:
                exec_time = (agent.completed_at - agent.created_at).total_seconds()
                execution_times.append(exec_time)
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        # Token usage from LLM interactions
        token_usages = []
        for agent in agents:
            llm_interactions = await session.execute(
                select(LLMInteraction)
                .filter(LLMInteraction.agent_id == agent.id)
            )
            agent_tokens = sum(
                (interaction.token_count_input or 0) + (interaction.token_count_output or 0)
                for interaction in llm_interactions.scalars()
            )
            if agent_tokens > 0:
                token_usages.append(agent_tokens)
        
        typical_token_usage = int(sum(token_usages) / len(token_usages)) if token_usages else 0
        
        # Retry analysis
        retry_counts = []
        for agent in agents:
            llm_interactions = await session.execute(
                select(LLMInteraction)
                .filter(LLMInteraction.agent_id == agent.id)
            )
            agent_retries = sum(
                interaction.retry_count or 0
                for interaction in llm_interactions.scalars()
            )
            retry_counts.append(agent_retries)
        
        avg_retry_count = sum(retry_counts) / len(retry_counts) if retry_counts else 0.0
        
        # Identify strengths and weaknesses
        strengths, weaknesses, optimal_scenarios = self._analyze_agent_characteristics(
            agents, success_rate, avg_execution_time, avg_retry_count
        )
        
        confidence = min(1.0, len(agents) / 10.0) * (success_rate * 0.5 + 0.5)
        
        return AgentPerformancePattern(
            agent_type=agent_type,
            task_category=task_category,
            complexity_level=complexity_level,
            success_rate=success_rate,
            avg_execution_time=avg_execution_time,
            avg_retry_count=avg_retry_count,
            typical_token_usage=typical_token_usage,
            sample_size=len(agents),
            confidence=confidence,
            strengths=strengths,
            weaknesses=weaknesses,
            optimal_scenarios=optimal_scenarios
        )
    
    def _analyze_agent_characteristics(
        self,
        agents: List[Agent],
        success_rate: float,
        avg_execution_time: float,
        avg_retry_count: float
    ) -> Tuple[List[str], List[str], List[str]]:
        """Analyze agent characteristics to identify strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        optimal_scenarios = []
        
        # Performance-based analysis
        if success_rate > 0.8:
            strengths.append("High reliability")
        elif success_rate < 0.6:
            weaknesses.append("Low success rate")
        
        if avg_execution_time < 30:  # seconds
            strengths.append("Fast execution")
        elif avg_execution_time > 120:
            weaknesses.append("Slow execution")
        
        if avg_retry_count < 0.5:
            strengths.append("Stable performance")
        elif avg_retry_count > 1.5:
            weaknesses.append("Frequent retries needed")
        
        # Context-based analysis
        agent_type = agents[0].agent_type if agents else "unknown"
        
        if agent_type == "task":
            if success_rate > 0.85:
                optimal_scenarios.append("Well-defined tasks")
            if avg_retry_count < 0.3:
                optimal_scenarios.append("Structured workflows")
        elif agent_type == "council":
            if success_rate > 0.8:
                optimal_scenarios.append("Complex decision-making")
                optimal_scenarios.append("Ambiguous requirements")
        elif agent_type == "validator":
            if success_rate > 0.9:
                optimal_scenarios.append("Quality assurance")
                optimal_scenarios.append("Error detection")
        
        return strengths, weaknesses, optimal_scenarios
    
    async def detect_failure_patterns(
        self,
        time_window: timedelta = timedelta(days=30),
        min_occurrences: int = 3
    ) -> List[FailurePattern]:
        """Detect common failure patterns in the system"""
        
        logger.info("Detecting failure patterns")
        
        cutoff_date = datetime.now() - time_window
        failure_patterns = []
        
        async with db_manager.get_async_session() as session:
            # Get failed thought trees
            failed_trees = await session.execute(
                select(ThoughtTree)
                .filter(
                    and_(
                        ThoughtTree.updated_at >= cutoff_date,
                        ThoughtTree.status == "failed"
                    )
                )
            )
            failed_trees = failed_trees.scalars().all()
            
            # Group failures by characteristics
            failure_groups = defaultdict(list)
            
            for tree in failed_trees:
                # Analyze failure context
                failure_key = self._classify_failure(tree)
                failure_groups[failure_key].append(tree)
            
            # Create patterns for frequent failure types
            for failure_key, trees in failure_groups.items():
                if len(trees) >= min_occurrences:
                    pattern = await self._create_failure_pattern(failure_key, trees, session)
                    if pattern:
                        failure_patterns.append(pattern)
        
        logger.info(f"Identified {len(failure_patterns)} failure patterns")
        return failure_patterns
    
    def _classify_failure(self, thought_tree: ThoughtTree) -> str:
        """Classify a failure based on its characteristics"""
        
        metadata = thought_tree.metadata_ or {}
        
        # Look for error information
        if "error" in metadata:
            error_info = metadata["error"]
            if isinstance(error_info, dict):
                error_type = error_info.get("type", "unknown")
                return f"error_{error_type}"
            else:
                return "error_general"
        
        # Classify based on complexity and context
        complexity_info = metadata.get("complexity", {})
        if isinstance(complexity_info, dict):
            high_complexity_areas = [
                key for key, value in complexity_info.items() 
                if value == "high"
            ]
            if high_complexity_areas:
                return f"complexity_{high_complexity_areas[0]}"
        
        # Default classification
        workflow_type = metadata.get("workflow_type", "unknown")
        return f"workflow_{workflow_type}"
    
    async def _create_failure_pattern(
        self,
        failure_key: str,
        trees: List[ThoughtTree],
        session
    ) -> Optional[FailurePattern]:
        """Create a failure pattern from a group of similar failures"""
        
        if not trees:
            return None
        
        # Analyze common characteristics
        common_context = {}
        error_messages = []
        affected_components = set()
        
        for tree in trees:
            metadata = tree.metadata_ or {}
            
            # Collect error messages
            if "error" in metadata:
                error_info = metadata["error"]
                if isinstance(error_info, dict) and "message" in error_info:
                    error_messages.append(error_info["message"])
            
            # Identify affected components
            if "failed_component" in metadata:
                affected_components.add(metadata["failed_component"])
            
            # Extract common context
            context = metadata.get("execution_context", {})
            for key, value in context.items():
                if key not in common_context:
                    common_context[key] = []
                common_context[key].append(value)
        
        # Process common context
        for key, values in common_context.items():
            if all(isinstance(v, (int, float)) for v in values):
                common_context[key] = sum(values) / len(values)
            else:
                most_common = Counter(str(v) for v in values).most_common(1)
                common_context[key] = most_common[0][0] if most_common else None
        
        # Generate recovery strategies based on failure type
        recovery_strategies = self._suggest_recovery_strategies(failure_key, common_context)
        prevention_measures = self._suggest_prevention_measures(failure_key, common_context)
        
        first_observed = min(tree.created_at for tree in trees if tree.created_at)
        last_observed = max(tree.updated_at for tree in trees if tree.updated_at)
        
        return FailurePattern(
            pattern_id=f"failure_{failure_key}_{len(trees)}",
            pattern_type=failure_key,
            frequency=len(trees),
            affected_components=list(affected_components),
            common_context=common_context,
            typical_error_messages=list(set(error_messages))[:5],  # Top 5 unique errors
            recovery_strategies=recovery_strategies,
            prevention_measures=prevention_measures,
            first_observed=first_observed,
            last_observed=last_observed
        )
    
    def _suggest_recovery_strategies(self, failure_key: str, context: Dict) -> List[str]:
        """Suggest recovery strategies based on failure pattern"""
        
        strategies = []
        
        if "timeout" in failure_key:
            strategies.extend([
                "Increase timeout limits",
                "Implement retry with exponential backoff",
                "Break down into smaller subtasks"
            ])
        elif "complexity" in failure_key:
            strategies.extend([
                "Use council-driven strategy for complex decisions",
                "Implement recursive decomposition",
                "Add validation agents"
            ])
        elif "error_llm" in failure_key:
            strategies.extend([
                "Retry with different model",
                "Simplify prompt structure",
                "Add prompt validation"
            ])
        else:
            strategies.extend([
                "Review execution context",
                "Add debugging logging",
                "Implement graceful degradation"
            ])
        
        return strategies
    
    def _suggest_prevention_measures(self, failure_key: str, context: Dict) -> List[str]:
        """Suggest prevention measures based on failure pattern"""
        
        measures = []
        
        if "timeout" in failure_key:
            measures.extend([
                "Implement predictive timeout calculation",
                "Add progress monitoring",
                "Use complexity-based resource allocation"
            ])
        elif "complexity" in failure_key:
            measures.extend([
                "Improve complexity analysis accuracy",
                "Add pre-execution validation",
                "Implement complexity-based strategy selection"
            ])
        elif "resource" in failure_key:
            measures.extend([
                "Implement resource usage prediction",
                "Add resource monitoring alerts",
                "Use adaptive resource limits"
            ])
        else:
            measures.extend([
                "Add comprehensive input validation",
                "Implement health checks",
                "Add monitoring and alerting"
            ])
        
        return measures
    
    async def identify_optimization_opportunities(
        self,
        threshold_improvement: float = 0.15
    ) -> List[OptimizationOpportunity]:
        """Identify specific optimization opportunities in the system"""
        
        logger.info("Identifying optimization opportunities")
        
        opportunities = []
        
        # Analyze strategy patterns for optimization
        strategy_patterns = await self.analyze_strategy_patterns()
        for strategy, patterns in strategy_patterns.items():
            for pattern in patterns:
                if pattern.success_rate < 0.8 or pattern.avg_execution_time > 300:
                    opportunity = OptimizationOpportunity(
                        opportunity_id=f"strategy_{strategy}_{pattern.complexity_level.value}",
                        category="strategy_optimization",
                        description=f"Optimize {strategy} strategy for {pattern.complexity_level.value} complexity",
                        potential_improvement=1.0 - pattern.success_rate,
                        affected_workflows=[pattern.workflow_type] if pattern.workflow_type else [],
                        implementation_effort="medium",
                        confidence=pattern.confidence
                    )
                    opportunities.append(opportunity)
        
        # Analyze agent patterns for optimization
        agent_patterns = await self.analyze_agent_performance_patterns()
        for agent_type, patterns in agent_patterns.items():
            for pattern in patterns:
                if pattern.avg_retry_count > 1.0:
                    opportunity = OptimizationOpportunity(
                        opportunity_id=f"agent_{agent_type}_{pattern.task_category}",
                        category="agent_optimization",
                        description=f"Reduce retry rate for {agent_type} agents in {pattern.task_category}",
                        potential_improvement=pattern.avg_retry_count - 0.5,
                        affected_workflows=[pattern.task_category],
                        implementation_effort="low",
                        confidence=pattern.confidence
                    )
                    opportunities.append(opportunity)
        
        logger.info(f"Identified {len(opportunities)} optimization opportunities")
        return opportunities


# Global pattern analyzer instance
pattern_analyzer = PatternAnalyzer()