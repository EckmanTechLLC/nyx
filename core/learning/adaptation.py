"""
NYX Learning System - Adaptive Decision Engine

Makes real-time decisions based on learned patterns.
Provides dynamic strategy selection, parameter optimization, and workflow adaptation.
"""

import asyncio
import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

# System imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, Orchestrator
from core.learning.patterns import (
    pattern_analyzer, StrategyPattern, AgentPerformancePattern, 
    OptimizationOpportunity, PatternType
)
from core.learning.metrics import ComplexityLevel, PerformanceMetrics, baseline_manager
from config.settings import settings

import logging
logger = logging.getLogger(__name__)


class AdaptationType(Enum):
    """Types of adaptations that can be made"""
    STRATEGY_CHANGE = "strategy_change"
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    RESOURCE_ADJUSTMENT = "resource_adjustment"
    AGENT_SELECTION = "agent_selection"
    TIMEOUT_ADJUSTMENT = "timeout_adjustment"


@dataclass
class StrategyRecommendation:
    """Recommendation for workflow strategy selection"""
    recommended_strategy: str
    confidence: float
    reasoning: List[str]
    expected_performance: Dict[str, float]  # success_rate, execution_time, etc.
    alternative_strategies: List[Tuple[str, float]]  # (strategy, confidence)
    learned_from_patterns: List[str]  # Pattern IDs that influenced decision
    
    # Context
    complexity_level: ComplexityLevel
    workflow_type: Optional[str]
    historical_success_rate: Optional[float]


@dataclass
class OptimizedParameters:
    """Optimized parameters based on historical performance"""
    parameter_name: str
    original_value: Any
    optimized_value: Any
    expected_improvement: float
    confidence: float
    reasoning: str
    applicable_contexts: List[str]


@dataclass
class AdaptationRecommendation:
    """Recommendation for real-time workflow adaptation"""
    adaptation_type: AdaptationType
    urgency: str  # "low", "medium", "high", "critical"
    description: str
    recommended_actions: List[str]
    expected_impact: float
    confidence: float
    triggers: List[str]  # What triggered this recommendation
    
    # Implementation details
    immediate: bool
    rollback_plan: Optional[str]


class AdaptiveDecisionEngine:
    """Makes intelligent decisions based on learned patterns and real-time performance"""
    
    def __init__(self):
        self.strategy_cache = {}
        self.parameter_cache = {}
        self.cache_ttl = timedelta(minutes=30)
        
        # Decision weights
        self.decision_weights = {
            "historical_success": 0.4,
            "recent_performance": 0.3,
            "complexity_match": 0.2,
            "resource_efficiency": 0.1
        }
    
    async def recommend_strategy(
        self,
        workflow_input: Dict[str, Any],
        complexity_analysis: Dict[str, Any],
        historical_context: Optional[Dict] = None
    ) -> StrategyRecommendation:
        """Recommend optimal strategy based on learned patterns"""
        
        start_time = time.time()
        
        try:
            # Extract key characteristics
            workflow_type = workflow_input.get("type", "unknown")
            complexity_level = self._determine_complexity_level(complexity_analysis)
            
            # Get relevant strategy patterns
            strategy_patterns = await pattern_analyzer.analyze_strategy_patterns()
            
            # Find matching patterns
            relevant_patterns = self._find_relevant_patterns(
                strategy_patterns, complexity_level, workflow_type
            )
            
            # Score strategies based on patterns
            strategy_scores = await self._score_strategies(
                relevant_patterns, workflow_input, complexity_analysis
            )
            
            # Select best strategy
            best_strategy, confidence, reasoning = self._select_best_strategy(
                strategy_scores, relevant_patterns
            )
            
            # Generate alternatives
            alternatives = self._generate_alternatives(strategy_scores)
            
            # Predict performance
            expected_performance = await self._predict_performance(
                best_strategy, complexity_level, workflow_type, relevant_patterns
            )
            
            # Get historical success rate
            historical_success_rate = self._get_historical_success_rate(
                best_strategy, relevant_patterns
            )
            
            # Track pattern usage
            learned_from_patterns = [p.strategy_name for p in relevant_patterns if p.strategy_name == best_strategy]
            
            recommendation = StrategyRecommendation(
                recommended_strategy=best_strategy,
                confidence=confidence,
                reasoning=reasoning,
                expected_performance=expected_performance,
                alternative_strategies=alternatives,
                learned_from_patterns=learned_from_patterns,
                complexity_level=complexity_level,
                workflow_type=workflow_type,
                historical_success_rate=historical_success_rate
            )
            
            # Cache recommendation
            cache_key = f"{workflow_type}_{complexity_level.value}"
            self.strategy_cache[cache_key] = (recommendation, datetime.now())
            
            calc_time = time.time() - start_time
            logger.info(f"Strategy recommendation: {best_strategy} (confidence: {confidence:.3f}) in {calc_time:.3f}s")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error in strategy recommendation: {e}")
            # Return safe default
            return self._get_default_strategy_recommendation(complexity_level, workflow_type)
    
    def _determine_complexity_level(self, complexity_analysis: Dict) -> ComplexityLevel:
        """Determine complexity level from analysis"""
        
        if not complexity_analysis:
            return ComplexityLevel.MEDIUM
        
        # Count high complexity dimensions
        high_count = sum(
            1 for value in complexity_analysis.values()
            if str(value).lower() == "high"
        )
        
        if high_count >= 3:
            return ComplexityLevel.CRITICAL
        elif high_count >= 2:
            return ComplexityLevel.HIGH
        elif high_count >= 1:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
    
    def _find_relevant_patterns(
        self,
        strategy_patterns: Dict[str, List[StrategyPattern]],
        complexity_level: ComplexityLevel,
        workflow_type: str
    ) -> List[StrategyPattern]:
        """Find strategy patterns relevant to current context"""
        
        relevant_patterns = []
        
        for strategy_name, patterns in strategy_patterns.items():
            for pattern in patterns:
                relevance_score = 0.0
                
                # Exact complexity match
                if pattern.complexity_level == complexity_level:
                    relevance_score += 1.0
                elif abs(list(ComplexityLevel).index(pattern.complexity_level) - 
                        list(ComplexityLevel).index(complexity_level)) == 1:
                    relevance_score += 0.5
                
                # Workflow type match
                if pattern.workflow_type == workflow_type:
                    relevance_score += 1.0
                elif pattern.workflow_type is None:
                    relevance_score += 0.3  # Generic patterns have some value
                
                # Confidence and sample size
                relevance_score *= pattern.confidence
                
                if relevance_score > 0.3:  # Minimum relevance threshold
                    relevant_patterns.append(pattern)
        
        # Sort by relevance
        relevant_patterns.sort(key=lambda p: p.success_rate * p.confidence, reverse=True)
        
        return relevant_patterns[:10]  # Top 10 most relevant patterns
    
    async def _score_strategies(
        self,
        relevant_patterns: List[StrategyPattern],
        workflow_input: Dict,
        complexity_analysis: Dict
    ) -> Dict[str, float]:
        """Score each strategy based on relevant patterns and context"""
        
        strategy_scores = {}
        
        # Get all unique strategies from patterns
        strategies = set(pattern.strategy_name for pattern in relevant_patterns)
        
        # Add default strategies if not present
        default_strategies = [
            "direct_execution", "sequential_decomposition", "parallel_execution",
            "recursive_decomposition", "council_driven", "iterative_refinement"
        ]
        strategies.update(default_strategies)
        
        for strategy in strategies:
            score = 0.0
            
            # Find patterns for this strategy
            strategy_patterns = [p for p in relevant_patterns if p.strategy_name == strategy]
            
            if strategy_patterns:
                # Calculate weighted score from patterns
                total_weight = sum(p.confidence * p.sample_size for p in strategy_patterns)
                if total_weight > 0:
                    weighted_success = sum(
                        p.success_rate * p.confidence * p.sample_size
                        for p in strategy_patterns
                    )
                    score = weighted_success / total_weight
                else:
                    score = 0.5
            else:
                # No patterns available, use heuristic scoring
                score = self._heuristic_strategy_score(strategy, complexity_analysis, workflow_input)
            
            strategy_scores[strategy] = score
        
        return strategy_scores
    
    def _heuristic_strategy_score(
        self,
        strategy: str,
        complexity_analysis: Dict,
        workflow_input: Dict
    ) -> float:
        """Provide heuristic score when no patterns are available"""
        
        complexity_level = self._determine_complexity_level(complexity_analysis)
        workflow_type = workflow_input.get("type", "unknown")
        
        # Heuristic rules based on system design
        heuristics = {
            "direct_execution": 0.7 if complexity_level == ComplexityLevel.LOW else 0.3,
            "sequential_decomposition": 0.6,
            "parallel_execution": 0.8 if complexity_level in [ComplexityLevel.MEDIUM, ComplexityLevel.HIGH] else 0.4,
            "recursive_decomposition": 0.9 if complexity_level == ComplexityLevel.HIGH else 0.5,
            "council_driven": 0.8 if complexity_level == ComplexityLevel.CRITICAL else 0.4,
            "iterative_refinement": 0.6
        }
        
        # Adjust for workflow type
        if workflow_type == "goal_workflow":
            heuristics["recursive_decomposition"] *= 1.2
            heuristics["council_driven"] *= 1.1
        
        return min(1.0, heuristics.get(strategy, 0.5))
    
    def _select_best_strategy(
        self,
        strategy_scores: Dict[str, float],
        relevant_patterns: List[StrategyPattern]
    ) -> Tuple[str, float, List[str]]:
        """Select the best strategy and provide reasoning"""
        
        if not strategy_scores:
            return "parallel_execution", 0.5, ["No patterns available, using default"]
        
        # Find best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        strategy_name, score = best_strategy
        
        # Calculate confidence
        confidence = min(1.0, score * 1.2)  # Boost confidence slightly
        
        # Generate reasoning
        reasoning = []
        
        # Find supporting patterns
        supporting_patterns = [p for p in relevant_patterns if p.strategy_name == strategy_name]
        if supporting_patterns:
            avg_success = sum(p.success_rate for p in supporting_patterns) / len(supporting_patterns)
            total_samples = sum(p.sample_size for p in supporting_patterns)
            reasoning.append(f"Historical success rate: {avg_success:.1%} across {total_samples} executions")
            reasoning.append(f"Based on {len(supporting_patterns)} matching patterns")
        else:
            reasoning.append("Based on heuristic analysis (no historical patterns)")
        
        # Add score-based reasoning
        if score > 0.8:
            reasoning.append("High confidence based on strong historical performance")
        elif score > 0.6:
            reasoning.append("Moderate confidence with acceptable historical performance")
        else:
            reasoning.append("Low confidence - consider alternative strategies")
        
        return strategy_name, confidence, reasoning
    
    def _generate_alternatives(
        self,
        strategy_scores: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """Generate alternative strategy recommendations"""
        
        # Sort strategies by score
        sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 alternatives (excluding the best one)
        alternatives = sorted_strategies[1:4]
        
        return alternatives
    
    async def _predict_performance(
        self,
        strategy: str,
        complexity_level: ComplexityLevel,
        workflow_type: str,
        relevant_patterns: List[StrategyPattern]
    ) -> Dict[str, float]:
        """Predict expected performance for the recommended strategy"""
        
        # Find patterns for this strategy
        strategy_patterns = [p for p in relevant_patterns if p.strategy_name == strategy]
        
        if strategy_patterns:
            # Calculate weighted averages
            total_weight = sum(p.confidence * p.sample_size for p in strategy_patterns)
            if total_weight > 0:
                success_rate = sum(
                    p.success_rate * p.confidence * p.sample_size
                    for p in strategy_patterns
                ) / total_weight
                
                execution_time = sum(
                    p.avg_execution_time * p.confidence * p.sample_size
                    for p in strategy_patterns
                ) / total_weight
                
                cost_estimate = float(sum(
                    float(p.avg_cost) * p.confidence * p.sample_size
                    for p in strategy_patterns
                ) / total_weight)
                
                quality_score = sum(
                    p.quality_score * p.confidence * p.sample_size
                    for p in strategy_patterns
                ) / total_weight
            else:
                success_rate = execution_time = cost_estimate = quality_score = 0.5
        else:
            # Use baseline predictions
            baseline = await baseline_manager.get_baseline_metrics(complexity_level, workflow_type)
            if baseline:
                success_rate = baseline.avg_success_rate
                execution_time = baseline.avg_execution_time
                cost_estimate = float(baseline.avg_cost_usd)
                quality_score = 0.7  # Reasonable default
            else:
                success_rate = execution_time = cost_estimate = quality_score = 0.5
        
        return {
            "success_rate": success_rate,
            "execution_time": execution_time,
            "cost_estimate": cost_estimate,
            "quality_score": quality_score
        }
    
    def _get_historical_success_rate(
        self,
        strategy: str,
        relevant_patterns: List[StrategyPattern]
    ) -> Optional[float]:
        """Get historical success rate for the strategy"""
        
        strategy_patterns = [p for p in relevant_patterns if p.strategy_name == strategy]
        if strategy_patterns:
            total_weight = sum(p.sample_size for p in strategy_patterns)
            if total_weight > 0:
                return sum(p.success_rate * p.sample_size for p in strategy_patterns) / total_weight
        
        return None
    
    def _get_default_strategy_recommendation(
        self,
        complexity_level: ComplexityLevel,
        workflow_type: str
    ) -> StrategyRecommendation:
        """Get safe default recommendation when pattern analysis fails"""
        
        # Safe default based on complexity
        if complexity_level == ComplexityLevel.CRITICAL:
            strategy = "council_driven"
        elif complexity_level == ComplexityLevel.HIGH:
            strategy = "recursive_decomposition"
        else:
            strategy = "parallel_execution"
        
        return StrategyRecommendation(
            recommended_strategy=strategy,
            confidence=0.5,
            reasoning=[f"Default strategy for {complexity_level.value} complexity", "Pattern analysis unavailable"],
            expected_performance={"success_rate": 0.7, "execution_time": 120.0, "cost_estimate": 15.0, "quality_score": 0.7},
            alternative_strategies=[("sequential_decomposition", 0.4), ("direct_execution", 0.3)],
            learned_from_patterns=[],
            complexity_level=complexity_level,
            workflow_type=workflow_type,
            historical_success_rate=None
        )
    
    async def optimize_parameters(
        self,
        current_parameters: Dict[str, Any],
        performance_history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[OptimizedParameters]:
        """Optimize parameters based on performance history"""
        
        logger.info("Optimizing parameters based on performance history")
        
        optimized_params = []
        
        # Analyze each parameter
        for param_name, current_value in current_parameters.items():
            optimization = await self._optimize_single_parameter(
                param_name, current_value, performance_history, context
            )
            if optimization:
                optimized_params.append(optimization)
        
        logger.info(f"Generated {len(optimized_params)} parameter optimizations")
        return optimized_params
    
    async def _optimize_single_parameter(
        self,
        param_name: str,
        current_value: Any,
        performance_history: List[Dict],
        context: Dict
    ) -> Optional[OptimizedParameters]:
        """Optimize a single parameter based on performance patterns"""
        
        if not performance_history:
            return None
        
        # Parameter-specific optimization logic
        if param_name in ["timeout_seconds", "max_execution_time_minutes"]:
            return await self._optimize_timeout_parameter(
                param_name, current_value, performance_history, context
            )
        elif param_name in ["max_concurrent_agents", "agent_limit"]:
            return await self._optimize_concurrency_parameter(
                param_name, current_value, performance_history, context
            )
        elif param_name in ["max_retries", "retry_limit"]:
            return await self._optimize_retry_parameter(
                param_name, current_value, performance_history, context
            )
        
        return None
    
    async def _optimize_timeout_parameter(
        self,
        param_name: str,
        current_value: Any,
        performance_history: List[Dict],
        context: Dict
    ) -> Optional[OptimizedParameters]:
        """Optimize timeout parameters based on execution times"""
        
        # Extract execution times from history
        execution_times = []
        timeouts = []
        
        for record in performance_history:
            if "execution_time" in record and "timeout_used" in record:
                execution_times.append(record["execution_time"])
                timeouts.append(record["timeout_used"])
        
        if len(execution_times) < 3:
            return None
        
        # Calculate optimal timeout
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        timeout_failures = sum(1 for i, timeout in enumerate(timeouts) if execution_times[i] >= timeout * 0.9)
        
        # If we have timeout failures, increase timeout
        if timeout_failures > len(execution_times) * 0.1:  # >10% timeout failure rate
            optimal_value = int(max_time * 1.5)  # 50% buffer
            expected_improvement = timeout_failures / len(execution_times)
            reasoning = f"Increasing timeout to reduce {timeout_failures} timeout failures"
        # If timeouts are much higher than needed, decrease
        elif current_value > avg_time * 3:
            optimal_value = int(avg_time * 2)  # 100% buffer
            expected_improvement = 0.1  # Modest improvement
            reasoning = f"Decreasing excessive timeout (avg execution: {avg_time:.1f}s)"
        else:
            return None  # No optimization needed
        
        applicable_contexts = [
            f"complexity_{context.get('complexity_level', 'medium')}",
            f"workflow_{context.get('workflow_type', 'general')}"
        ]
        
        return OptimizedParameters(
            parameter_name=param_name,
            original_value=current_value,
            optimized_value=optimal_value,
            expected_improvement=expected_improvement,
            confidence=min(1.0, len(execution_times) / 10.0),
            reasoning=reasoning,
            applicable_contexts=applicable_contexts
        )
    
    async def _optimize_concurrency_parameter(
        self,
        param_name: str,
        current_value: Any,
        performance_history: List[Dict],
        context: Dict
    ) -> Optional[OptimizedParameters]:
        """Optimize concurrency parameters based on resource utilization"""
        
        # Extract resource utilization from history
        agent_counts = []
        success_rates = []
        execution_times = []
        
        for record in performance_history:
            if all(key in record for key in ["agent_count", "success_rate", "execution_time"]):
                agent_counts.append(record["agent_count"])
                success_rates.append(record["success_rate"])
                execution_times.append(record["execution_time"])
        
        if len(agent_counts) < 3:
            return None
        
        # Analyze relationship between concurrency and performance
        avg_agents = sum(agent_counts) / len(agent_counts)
        avg_success = sum(success_rates) / len(success_rates)
        
        # If success rate is low and we're hitting the limit, increase
        if avg_success < 0.8 and avg_agents >= current_value * 0.8:
            optimal_value = int(current_value * 1.5)
            expected_improvement = (0.8 - avg_success) * 0.5
            reasoning = f"Increasing concurrency limit due to low success rate ({avg_success:.1%})"
        # If we never use full capacity, decrease
        elif avg_agents < current_value * 0.5:
            optimal_value = max(1, int(avg_agents * 1.5))
            expected_improvement = 0.05  # Modest resource savings
            reasoning = f"Decreasing unused concurrency capacity (avg usage: {avg_agents:.1f})"
        else:
            return None  # No optimization needed
        
        return OptimizedParameters(
            parameter_name=param_name,
            original_value=current_value,
            optimized_value=optimal_value,
            expected_improvement=expected_improvement,
            confidence=min(1.0, len(agent_counts) / 10.0),
            reasoning=reasoning,
            applicable_contexts=[f"avg_agents_{int(avg_agents)}"]
        )
    
    async def _optimize_retry_parameter(
        self,
        param_name: str,
        current_value: Any,
        performance_history: List[Dict],
        context: Dict
    ) -> Optional[OptimizedParameters]:
        """Optimize retry parameters based on failure patterns"""
        
        retry_counts = []
        success_rates = []
        
        for record in performance_history:
            if "retry_count" in record and "success_rate" in record:
                retry_counts.append(record["retry_count"])
                success_rates.append(record["success_rate"])
        
        if len(retry_counts) < 3:
            return None
        
        avg_retries = sum(retry_counts) / len(retry_counts)
        avg_success = sum(success_rates) / len(success_rates)
        
        # If we're frequently hitting retry limits and success is low
        if avg_retries >= current_value * 0.8 and avg_success < 0.7:
            optimal_value = min(10, current_value + 2)  # Increase but cap at 10
            expected_improvement = (0.8 - avg_success) * 0.3
            reasoning = f"Increasing retries due to frequent limit hits and low success"
        # If retries are rarely used, we can be more conservative
        elif avg_retries < current_value * 0.3:
            optimal_value = max(1, int(avg_retries * 2))
            expected_improvement = 0.02  # Minimal improvement
            reasoning = f"Decreasing rarely-used retry limit (avg: {avg_retries:.1f})"
        else:
            return None
        
        return OptimizedParameters(
            parameter_name=param_name,
            original_value=current_value,
            optimized_value=optimal_value,
            expected_improvement=expected_improvement,
            confidence=min(1.0, len(retry_counts) / 10.0),
            reasoning=reasoning,
            applicable_contexts=[f"avg_retries_{avg_retries:.1f}"]
        )
    
    async def should_adapt_workflow(
        self,
        current_performance: Dict[str, Any],
        expected_performance: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Optional[AdaptationRecommendation]:
        """Determine if a running workflow should be adapted"""
        
        # Calculate performance deviation
        deviations = {}
        for metric, expected_value in expected_performance.items():
            if metric in current_performance:
                current_value = current_performance[metric]
                if isinstance(expected_value, (int, float)) and expected_value > 0:
                    deviation = (current_value - expected_value) / expected_value
                    deviations[metric] = deviation
        
        # Check for critical deviations
        triggers = []
        urgency = "low"
        adaptation_type = AdaptationType.PARAMETER_OPTIMIZATION
        
        # Execution time significantly over estimate
        if "execution_time" in deviations and deviations["execution_time"] > 0.5:
            triggers.append(f"Execution time {deviations['execution_time']:.1%} over estimate")
            urgency = "high"
            adaptation_type = AdaptationType.TIMEOUT_ADJUSTMENT
        
        # Success rate significantly below expected
        if "success_rate" in deviations and deviations["success_rate"] < -0.2:
            triggers.append(f"Success rate {abs(deviations['success_rate']):.1%} below estimate")
            urgency = "high"
            adaptation_type = AdaptationType.STRATEGY_CHANGE
        
        # Cost significantly over budget
        if "cost_estimate" in deviations and deviations["cost_estimate"] > 0.3:
            triggers.append(f"Cost {deviations['cost_estimate']:.1%} over estimate")
            if urgency == "low":
                urgency = "medium"
        
        # High failure rate
        current_failure_rate = current_performance.get("failure_rate", 0)
        if current_failure_rate > 0.3:
            triggers.append(f"High failure rate: {current_failure_rate:.1%}")
            urgency = "critical"
            adaptation_type = AdaptationType.STRATEGY_CHANGE
        
        if not triggers:
            return None  # No adaptation needed
        
        # Generate adaptation recommendations
        recommended_actions = await self._generate_adaptation_actions(
            adaptation_type, deviations, execution_context
        )
        
        expected_impact = sum(abs(dev) for dev in deviations.values()) / len(deviations)
        confidence = min(1.0, len(triggers) * 0.3)
        
        return AdaptationRecommendation(
            adaptation_type=adaptation_type,
            urgency=urgency,
            description=f"Performance deviation detected: {', '.join(triggers)}",
            recommended_actions=recommended_actions,
            expected_impact=expected_impact,
            confidence=confidence,
            triggers=triggers,
            immediate=urgency in ["high", "critical"],
            rollback_plan="Restore original parameters if adaptation fails" if adaptation_type == AdaptationType.PARAMETER_OPTIMIZATION else None
        )
    
    async def _generate_adaptation_actions(
        self,
        adaptation_type: AdaptationType,
        deviations: Dict[str, float],
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate specific actions for adaptation"""
        
        actions = []
        
        if adaptation_type == AdaptationType.TIMEOUT_ADJUSTMENT:
            if "execution_time" in deviations and deviations["execution_time"] > 0:
                actions.append("Increase timeout limits by 50%")
                actions.append("Add progress monitoring")
                actions.append("Consider breaking into smaller subtasks")
        
        elif adaptation_type == AdaptationType.STRATEGY_CHANGE:
            current_strategy = context.get("current_strategy", "unknown")
            if "success_rate" in deviations and deviations["success_rate"] < -0.2:
                if current_strategy != "council_driven":
                    actions.append("Switch to council-driven strategy")
                else:
                    actions.append("Add additional validation agents")
                actions.append("Implement more thorough error checking")
        
        elif adaptation_type == AdaptationType.PARAMETER_OPTIMIZATION:
            if "cost_estimate" in deviations and deviations["cost_estimate"] > 0:
                actions.append("Reduce concurrent agent count")
                actions.append("Implement more aggressive caching")
            actions.append("Optimize resource allocation")
        
        elif adaptation_type == AdaptationType.RESOURCE_ADJUSTMENT:
            actions.append("Adjust memory limits")
            actions.append("Modify concurrency settings")
        
        if not actions:
            actions.append("Monitor performance closely")
            actions.append("Prepare for manual intervention")
        
        return actions


# Global adaptive decision engine instance
adaptive_engine = AdaptiveDecisionEngine()