"""
Motivational Model for Autonomous NYX Behavior

This module contains components that enable NYX to autonomously initiate,
prioritize, and evaluate tasks based on internal motivations.
"""

from .engine import MotivationalModelEngine
from .arbitration import GoalArbitrationEngine
from .spawner import SelfInitiatedTaskSpawner
from .feedback import MotivationalFeedbackLoop
from .states import MotivationalStateManager
from .orchestrator_integration import MotivationalOrchestratorIntegration, create_integrated_motivational_system
from .initializer import MotivationalModelInitializer, quick_init_motivational_system

__all__ = [
    'MotivationalModelEngine',
    'GoalArbitrationEngine', 
    'SelfInitiatedTaskSpawner',
    'MotivationalFeedbackLoop',
    'MotivationalStateManager',
    'MotivationalOrchestratorIntegration',
    'create_integrated_motivational_system',
    'MotivationalModelInitializer',
    'quick_init_motivational_system'
]