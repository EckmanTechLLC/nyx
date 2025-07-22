#!/usr/bin/env python3
"""
Demonstration script for Autonomous NYX with Motivational Model

This script demonstrates NYX's autonomous, self-directing capabilities
by initializing the motivational model and letting it operate independently.
"""

import sys
import os
import asyncio
import logging
import signal
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import db_manager
from core.motivation import create_integrated_motivational_system
from core.motivation.initializer import create_motivational_test_environment

# Configure logging for demonstration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutonomousNYXDemo:
    """Demonstration of autonomous NYX operation"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.engine = None
        self.integration = None
        self.running = True
        self.start_time = datetime.utcnow()

    async def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"\nReceived signal {signum}, initiating graceful shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize_system(self):
        """Initialize the autonomous NYX system"""
        logger.info("🚀 Initializing Autonomous NYX System...")
        
        try:
            # Create the complete integrated system
            self.engine, self.integration = await create_integrated_motivational_system(
                start_engine=True,
                start_integration=True
            )
            
            logger.info("✓ Motivational model engine started")
            logger.info("✓ Orchestrator integration active")
            
            # Create test environment with boosted motivations
            await create_motivational_test_environment()
            logger.info("✓ Motivational test environment created")
            
            # Show initial system status
            await self.show_system_status()
            
            logger.info("\n🎯 NYX is now AUTONOMOUS and self-directing!")
            logger.info("   The system will now operate independently based on internal motivations.")
            logger.info("   Press Ctrl+C to stop the demonstration.\n")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize autonomous system: {e}")
            raise

    async def show_system_status(self):
        """Display current system status"""
        try:
            # Engine status
            engine_status = self.engine.get_status()
            logger.info(f"Engine Status: {'Running' if engine_status['running'] else 'Stopped'}")
            logger.info(f"Evaluation Interval: {engine_status['evaluation_interval']}s")
            
            # Integration status
            integration_status = await self.integration.get_integration_status()
            logger.info(f"Integration Status: {integration_status['status']}")
            logger.info(f"Active Workflows: {integration_status['active_motivated_workflows']}")
            
            # Motivational states
            async with self.db_manager.get_async_session() as session:
                from core.motivation.states import MotivationalStateManager
                
                state_manager = MotivationalStateManager()
                summary = await state_manager.get_motivation_summary(session)
                
                logger.info(f"Active Motivational States: {summary['total_active_states']}")
                
                # Show top 3 motivations by urgency
                top_motivations = sorted(
                    summary['states'], 
                    key=lambda x: x['arbitration_score'], 
                    reverse=True
                )[:3]
                
                logger.info("Top Motivations:")
                for i, motivation in enumerate(top_motivations, 1):
                    logger.info(f"  {i}. {motivation['motivation_type']}: "
                              f"urgency={motivation['urgency']:.2f}, "
                              f"satisfaction={motivation['satisfaction']:.2f}, "
                              f"score={motivation['arbitration_score']:.3f}")
            
        except Exception as e:
            logger.error(f"Error showing system status: {e}")

    async def monitor_autonomous_operation(self):
        """Monitor and report on autonomous operation"""
        last_status_time = datetime.utcnow()
        status_interval = 30  # Show status every 30 seconds
        
        activity_counts = {
            'total_tasks_generated': 0,
            'total_workflows_spawned': 0,
            'total_completions': 0
        }
        
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Show periodic status updates
                if (current_time - last_status_time).total_seconds() >= status_interval:
                    await self.show_periodic_status(activity_counts)
                    last_status_time = current_time
                
                # Check for new autonomous activity
                await self.check_autonomous_activity(activity_counts)
                
                # Small sleep to avoid busy waiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def show_periodic_status(self, activity_counts):
        """Show periodic status update"""
        runtime = datetime.utcnow() - self.start_time
        runtime_minutes = int(runtime.total_seconds() / 60)
        
        logger.info(f"\n📊 Autonomous Operation Status (Runtime: {runtime_minutes} minutes)")
        logger.info("-" * 50)
        
        # Integration status
        integration_status = await self.integration.get_integration_status()
        logger.info(f"Active Workflows: {integration_status['active_motivated_workflows']}")
        
        if integration_status['motivation_breakdown']:
            logger.info("Workflow Breakdown:")
            for motivation, count in integration_status['motivation_breakdown'].items():
                logger.info(f"  {motivation}: {count}")
        
        # Activity summary
        logger.info(f"Tasks Generated: {activity_counts['total_tasks_generated']}")
        logger.info(f"Workflows Spawned: {activity_counts['total_workflows_spawned']}")
        logger.info(f"Completions: {activity_counts['total_completions']}")
        
        # Recent motivational state changes
        await self.show_motivation_changes()
        
        logger.info("-" * 50)

    async def show_motivation_changes(self):
        """Show recent changes in motivational states"""
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, desc, func
                from database.models import MotivationalState
                
                # Get states that have been recently triggered
                recent_threshold = datetime.utcnow() - timedelta(minutes=5)
                recent_triggers = await session.execute(
                    select(MotivationalState.motivation_type, MotivationalState.urgency, 
                           MotivationalState.last_triggered_at)
                    .where(MotivationalState.last_triggered_at >= recent_threshold)
                    .order_by(desc(MotivationalState.last_triggered_at))
                )
                
                triggered_states = recent_triggers.fetchall()
                if triggered_states:
                    logger.info("Recently Triggered Motivations:")
                    for state in triggered_states:
                        logger.info(f"  {state.motivation_type}: urgency={state.urgency:.2f}")
                
        except Exception as e:
            logger.error(f"Error showing motivation changes: {e}")

    async def check_autonomous_activity(self, activity_counts):
        """Check for new autonomous activity and update counters"""
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, func
                from database.models import MotivationalTask, ThoughtTree
                
                # Count recent tasks
                since = self.start_time
                task_count = await session.execute(
                    select(func.count(MotivationalTask.id))
                    .where(MotivationalTask.spawned_at >= since)
                )
                current_tasks = task_count.scalar() or 0
                
                # Count autonomous thought trees  
                tree_count = await session.execute(
                    select(func.count(ThoughtTree.id))
                    .where(ThoughtTree.created_at >= since)
                    .where(ThoughtTree.goal.like('AUTONOMOUS:%'))
                )
                current_workflows = tree_count.scalar() or 0
                
                # Count completions
                completion_count = await session.execute(
                    select(func.count(MotivationalTask.id))
                    .where(MotivationalTask.completed_at >= since)
                )
                current_completions = completion_count.scalar() or 0
                
                # Update counters and log new activity
                if current_tasks > activity_counts['total_tasks_generated']:
                    new_tasks = current_tasks - activity_counts['total_tasks_generated']
                    logger.info(f"🎯 {new_tasks} new autonomous task(s) generated")
                    activity_counts['total_tasks_generated'] = current_tasks
                
                if current_workflows > activity_counts['total_workflows_spawned']:
                    new_workflows = current_workflows - activity_counts['total_workflows_spawned']
                    logger.info(f"⚙️  {new_workflows} new workflow(s) spawned autonomously")
                    activity_counts['total_workflows_spawned'] = current_workflows
                
                if current_completions > activity_counts['total_completions']:
                    new_completions = current_completions - activity_counts['total_completions']
                    logger.info(f"✅ {new_completions} autonomous task(s) completed")
                    activity_counts['total_completions'] = current_completions
                
        except Exception as e:
            logger.error(f"Error checking autonomous activity: {e}")

    async def shutdown(self):
        """Gracefully shutdown the autonomous system"""
        logger.info("\n🛑 Shutting down Autonomous NYX system...")
        
        try:
            # Show final statistics
            await self.show_final_statistics()
            
            # Stop integration
            if self.integration:
                await self.integration.stop_integration()
                logger.info("✓ Integration stopped")
            
            # Stop engine
            if self.engine:
                await self.engine.stop()
                logger.info("✓ Motivational engine stopped")
            
            logger.info("✓ Autonomous NYX system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def show_final_statistics(self):
        """Show final operation statistics"""
        try:
            runtime = datetime.utcnow() - self.start_time
            runtime_minutes = runtime.total_seconds() / 60
            
            logger.info(f"\n📈 Final Autonomous Operation Statistics")
            logger.info("=" * 50)
            logger.info(f"Total Runtime: {runtime_minutes:.1f} minutes")
            
            # Count total autonomous activity
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, func
                from database.models import MotivationalTask, ThoughtTree
                
                # Total tasks generated
                task_count = await session.execute(
                    select(func.count(MotivationalTask.id))
                    .where(MotivationalTask.spawned_at >= self.start_time)
                )
                total_tasks = task_count.scalar() or 0
                
                # Total autonomous workflows
                tree_count = await session.execute(
                    select(func.count(ThoughtTree.id))
                    .where(ThoughtTree.created_at >= self.start_time)
                    .where(ThoughtTree.goal.like('AUTONOMOUS:%'))
                )
                total_workflows = tree_count.scalar() or 0
                
                # Completed tasks
                completion_count = await session.execute(
                    select(func.count(MotivationalTask.id))
                    .where(MotivationalTask.completed_at >= self.start_time)
                )
                total_completions = completion_count.scalar() or 0
                
                logger.info(f"Tasks Generated: {total_tasks}")
                logger.info(f"Workflows Executed: {total_workflows}")
                logger.info(f"Tasks Completed: {total_completions}")
                
                if runtime_minutes > 0:
                    rate = total_tasks / runtime_minutes
                    logger.info(f"Autonomous Activity Rate: {rate:.2f} tasks/minute")
                
                if total_tasks > 0:
                    completion_rate = (total_completions / total_tasks) * 100
                    logger.info(f"Task Completion Rate: {completion_rate:.1f}%")
            
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error showing final statistics: {e}")

    async def run_demonstration(self):
        """Run the complete autonomous NYX demonstration"""
        try:
            await self.setup_signal_handlers()
            await self.initialize_system()
            await self.monitor_autonomous_operation()
            
        except KeyboardInterrupt:
            logger.info("\nKeyboard interrupt received")
        except Exception as e:
            logger.error(f"Demonstration failed: {e}")
        finally:
            await self.shutdown()


async def main():
    """Main demonstration runner"""
    print("🤖 Autonomous NYX Demonstration")
    print("=" * 40)
    print("This demonstration shows NYX operating as a truly autonomous agent.")
    print("NYX will generate its own tasks based on internal motivations and execute them independently.")
    print("The system will continue running until you stop it with Ctrl+C.")
    print()
    
    demo = AutonomousNYXDemo()
    await demo.run_demonstration()
    
    print("\n🎓 Demonstration complete!")
    print("NYX has demonstrated autonomous, self-directed operation.")
    print("The motivational model enables true AI agency - the ability to act")
    print("independently based on internal goals and motivations.")


if __name__ == "__main__":
    asyncio.run(main())