"""
NYX Active Learning System

This module implements deterministic reinforcement learning for the NYX orchestration system.
It enables the AI to learn from experience and optimize performance over time through:

- Multi-dimensional scoring (speed, quality, success, usefulness)  
- Pattern recognition and failure analysis
- Adaptive decision making and parameter optimization
- Real-time workflow optimization

Components:
- scorer: Multi-dimensional performance scoring algorithms
- patterns: Pattern recognition and strategy optimization  
- adaptation: Dynamic parameter adjustment and decision making
- metrics: Performance metrics calculation and analysis
"""

from .scorer import PerformanceScorer, ScoringResult, ScoringContext
from .metrics import MetricsCalculator, BaselineManager, PerformanceMetrics

__all__ = [
    "PerformanceScorer",
    "ScoringResult", 
    "ScoringContext",
    "MetricsCalculator",
    "BaselineManager",
    "PerformanceMetrics"
]