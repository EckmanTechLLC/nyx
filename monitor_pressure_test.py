#!/usr/bin/env python3
"""
Real-time monitoring script for NYX autonomous agent system pressure test
Connects to the database and provides live analytics of autonomous behavior
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
from typing import Dict, List, Any
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.connection import db_manager
from database.models import (
    ThoughtTree, Agent, Orchestrator, LLMInteraction, 
    ToolExecution, MotivationalState, MotivationalTask,
    AgentCommunication
)
from sqlalchemy import select, func, desc, text, and_, or_
from sqlalchemy.orm import selectinload

class NYXPressureTestMonitor:
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.test_window_minutes = 30
        
    async def get_time_window(self):
        """Get datetime for 30 minutes ago"""
        return datetime.now(timezone.utc) - timedelta(minutes=self.test_window_minutes)
    
    async def check_database_connection(self):
        """Verify database connectivity"""
        try:
            health = await db_manager.health_check()
            if health:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    async def get_recent_autonomous_activity(self):
        """Get recent autonomous activity from ThoughtTree table"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Get autonomous workflows (goals starting with "AUTONOMOUS:")
            autonomous_query = select(ThoughtTree).where(
                and_(
                    ThoughtTree.goal.like('AUTONOMOUS:%'),
                    ThoughtTree.created_at >= time_window
                )
            ).order_by(desc(ThoughtTree.created_at))
            
            result = await session.execute(autonomous_query)
            autonomous_workflows = result.scalars().all()
            
            # Get all recent thought trees for comparison
            all_recent_query = select(ThoughtTree).where(
                ThoughtTree.created_at >= time_window
            ).order_by(desc(ThoughtTree.created_at))
            
            result = await session.execute(all_recent_query)
            all_recent = result.scalars().all()
            
            return {
                'autonomous_workflows': autonomous_workflows,
                'all_recent_workflows': all_recent,
                'total_autonomous': len(autonomous_workflows),
                'total_recent': len(all_recent)
            }
    
    async def get_motivational_tasks(self):
        """Analyze MotivationalTask table for recent tasks"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Get recent motivational tasks
            tasks_query = select(MotivationalTask).where(
                MotivationalTask.spawned_at >= time_window
            ).options(
                selectinload(MotivationalTask.motivational_state)
            ).order_by(desc(MotivationalTask.spawned_at))
            
            result = await session.execute(tasks_query)
            tasks = result.scalars().all()
            
            # Group by status
            status_counts = {}
            for task in tasks:
                status = task.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Group by motivation type
            motivation_types = {}
            for task in tasks:
                if task.motivational_state:
                    motivation_type = task.motivational_state.motivation_type
                    motivation_types[motivation_type] = motivation_types.get(motivation_type, 0) + 1
            
            return {
                'tasks': tasks,
                'total_tasks': len(tasks),
                'status_breakdown': status_counts,
                'motivation_types': motivation_types
            }
    
    async def get_motivational_states(self):
        """Analyze current motivation levels"""
        async with db_manager.get_async_session() as session:
            # Get all active motivational states
            states_query = select(MotivationalState).where(
                MotivationalState.is_active == True
            ).order_by(desc(MotivationalState.urgency))
            
            result = await session.execute(states_query)
            states = result.scalars().all()
            
            # Categorize by urgency levels
            high_urgency = [s for s in states if s.urgency >= 0.7]
            medium_urgency = [s for s in states if 0.3 <= s.urgency < 0.7]
            low_urgency = [s for s in states if s.urgency < 0.3]
            
            return {
                'all_states': states,
                'total_states': len(states),
                'high_urgency': high_urgency,
                'medium_urgency': medium_urgency,
                'low_urgency': low_urgency,
                'avg_urgency': sum(s.urgency for s in states) / len(states) if states else 0,
                'avg_satisfaction': sum(s.satisfaction for s in states) / len(states) if states else 0
            }
    
    async def get_agent_orchestrator_activity(self):
        """Check recent Agent and Orchestrator activity"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Recent agents
            agents_query = select(Agent).where(
                Agent.created_at >= time_window
            ).order_by(desc(Agent.created_at))
            
            result = await session.execute(agents_query)
            recent_agents = result.scalars().all()
            
            # Recent orchestrators
            orchestrators_query = select(Orchestrator).where(
                Orchestrator.created_at >= time_window
            ).order_by(desc(Orchestrator.created_at))
            
            result = await session.execute(orchestrators_query)
            recent_orchestrators = result.scalars().all()
            
            # Agent status breakdown
            agent_statuses = {}
            for agent in recent_agents:
                status = agent.status
                agent_statuses[status] = agent_statuses.get(status, 0) + 1
            
            # Orchestrator status breakdown
            orchestrator_statuses = {}
            for orch in recent_orchestrators:
                status = orch.status
                orchestrator_statuses[status] = orchestrator_statuses.get(status, 0) + 1
            
            return {
                'agents': recent_agents,
                'orchestrators': recent_orchestrators,
                'total_agents': len(recent_agents),
                'total_orchestrators': len(recent_orchestrators),
                'agent_statuses': agent_statuses,
                'orchestrator_statuses': orchestrator_statuses
            }
    
    async def check_for_errors(self):
        """Look for errors and failures in recent activity"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Failed thought trees
            failed_trees_query = select(ThoughtTree).where(
                and_(
                    ThoughtTree.status == 'failed',
                    ThoughtTree.created_at >= time_window
                )
            )
            
            result = await session.execute(failed_trees_query)
            failed_trees = result.scalars().all()
            
            # Failed agents
            failed_agents_query = select(Agent).where(
                and_(
                    Agent.status == 'failed',
                    Agent.created_at >= time_window
                )
            )
            
            result = await session.execute(failed_agents_query)
            failed_agents = result.scalars().all()
            
            # Failed LLM interactions
            failed_llm_query = select(LLMInteraction).where(
                and_(
                    LLMInteraction.success == False,
                    LLMInteraction.request_timestamp >= time_window
                )
            )
            
            result = await session.execute(failed_llm_query)
            failed_llm = result.scalars().all()
            
            # Failed tool executions
            failed_tools_query = select(ToolExecution).where(
                and_(
                    ToolExecution.success == False,
                    ToolExecution.started_at >= time_window
                )
            )
            
            result = await session.execute(failed_tools_query)
            failed_tools = result.scalars().all()
            
            # Failed motivational tasks
            failed_tasks_query = select(MotivationalTask).where(
                and_(
                    MotivationalTask.status == 'failed',
                    MotivationalTask.spawned_at >= time_window
                )
            )
            
            result = await session.execute(failed_tasks_query)
            failed_tasks = result.scalars().all()
            
            return {
                'failed_trees': failed_trees,
                'failed_agents': failed_agents,
                'failed_llm_interactions': failed_llm,
                'failed_tool_executions': failed_tools,
                'failed_motivational_tasks': failed_tasks,
                'total_failures': len(failed_trees) + len(failed_agents) + len(failed_llm) + len(failed_tools) + len(failed_tasks)
            }
    
    async def calculate_task_generation_rate(self):
        """Calculate tasks per minute generation rate"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Count motivational tasks in time window
            tasks_count_query = select(func.count(MotivationalTask.id)).where(
                MotivationalTask.spawned_at >= time_window
            )
            
            result = await session.execute(tasks_count_query)
            task_count = result.scalar()
            
            # Calculate rate
            elapsed_minutes = (datetime.now(timezone.utc) - time_window).total_seconds() / 60
            rate = task_count / elapsed_minutes if elapsed_minutes > 0 else 0
            
            return {
                'total_tasks': task_count,
                'elapsed_minutes': elapsed_minutes,
                'tasks_per_minute': rate
            }
    
    async def analyze_task_types(self):
        """Analyze types of autonomous tasks being generated"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Get recent tasks with their motivational states
            tasks_query = select(MotivationalTask).where(
                MotivationalTask.spawned_at >= time_window
            ).options(
                selectinload(MotivationalTask.motivational_state)
            )
            
            result = await session.execute(tasks_query)
            tasks = result.scalars().all()
            
            # Analyze task prompt patterns
            task_patterns = {}
            motivation_priorities = {}
            
            for task in tasks:
                # Extract patterns from generated prompts
                prompt = task.generated_prompt[:100] if task.generated_prompt else "No prompt"
                
                # Simple categorization (in real system, could use NLP)
                if "optimize" in prompt.lower():
                    task_patterns["optimization"] = task_patterns.get("optimization", 0) + 1
                elif "monitor" in prompt.lower():
                    task_patterns["monitoring"] = task_patterns.get("monitoring", 0) + 1
                elif "analyze" in prompt.lower():
                    task_patterns["analysis"] = task_patterns.get("analysis", 0) + 1
                elif "improve" in prompt.lower():
                    task_patterns["improvement"] = task_patterns.get("improvement", 0) + 1
                else:
                    task_patterns["other"] = task_patterns.get("other", 0) + 1
                
                # Track priorities
                priority = task.task_priority
                if priority >= 0.8:
                    motivation_priorities["high"] = motivation_priorities.get("high", 0) + 1
                elif priority >= 0.5:
                    motivation_priorities["medium"] = motivation_priorities.get("medium", 0) + 1
                else:
                    motivation_priorities["low"] = motivation_priorities.get("low", 0) + 1
            
            return {
                'task_patterns': task_patterns,
                'priority_distribution': motivation_priorities,
                'sample_prompts': [task.generated_prompt[:200] for task in tasks[:5]]
            }
    
    async def look_for_patterns(self):
        """Look for patterns in autonomous behavior"""
        time_window = await self.get_time_window()
        
        async with db_manager.get_async_session() as session:
            # Time-based analysis - tasks per 5-minute intervals
            intervals = []
            current_time = time_window
            end_time = datetime.now(timezone.utc)
            
            while current_time < end_time:
                interval_end = current_time + timedelta(minutes=5)
                
                tasks_in_interval_query = select(func.count(MotivationalTask.id)).where(
                    and_(
                        MotivationalTask.spawned_at >= current_time,
                        MotivationalTask.spawned_at < interval_end
                    )
                )
                
                result = await session.execute(tasks_in_interval_query)
                task_count = result.scalar()
                
                intervals.append({
                    'start': current_time.strftime('%H:%M'),
                    'end': interval_end.strftime('%H:%M'),
                    'task_count': task_count
                })
                
                current_time = interval_end
            
            # Success rate analysis
            completed_tasks_query = select(func.count(MotivationalTask.id)).where(
                and_(
                    MotivationalTask.spawned_at >= time_window,
                    MotivationalTask.status == 'completed',
                    MotivationalTask.success == True
                )
            )
            
            result = await session.execute(completed_tasks_query)
            successful_tasks = result.scalar()
            
            total_tasks_query = select(func.count(MotivationalTask.id)).where(
                MotivationalTask.spawned_at >= time_window
            )
            
            result = await session.execute(total_tasks_query)
            total_tasks = result.scalar()
            
            success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0
            
            return {
                'time_intervals': intervals,
                'success_rate': success_rate,
                'successful_tasks': successful_tasks,
                'total_tasks': total_tasks
            }
    
    def print_status_report(self, data: Dict[str, Any]):
        """Print comprehensive status report"""
        print("=" * 80)
        print(f"NYX AUTONOMOUS AGENT SYSTEM - PRESSURE TEST MONITOR")
        print(f"Test Duration: {self.test_window_minutes} minutes")
        print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Database connection status
        print(f"\n🔗 DATABASE CONNECTION")
        print(f"Status: {'✅ Connected' if data.get('db_connected') else '❌ Disconnected'}")
        
        # Recent autonomous activity
        activity = data.get('autonomous_activity', {})
        print(f"\n🤖 AUTONOMOUS ACTIVITY (Last {self.test_window_minutes} minutes)")
        print(f"Autonomous Workflows: {activity.get('total_autonomous', 0)}")
        print(f"Total Recent Workflows: {activity.get('total_recent', 0)}")
        if activity.get('total_recent', 0) > 0:
            autonomous_ratio = activity.get('total_autonomous', 0) / activity.get('total_recent', 1)
            print(f"Autonomous Ratio: {autonomous_ratio:.2%}")
        
        # Motivational tasks
        tasks = data.get('motivational_tasks', {})
        print(f"\n📋 MOTIVATIONAL TASKS")
        print(f"Total Generated: {tasks.get('total_tasks', 0)}")
        print(f"Status Breakdown: {tasks.get('status_breakdown', {})}")
        print(f"Motivation Types: {tasks.get('motivation_types', {})}")
        
        # Task generation rate
        rate = data.get('task_rate', {})
        print(f"\n⚡ TASK GENERATION RATE")
        print(f"Rate: {rate.get('tasks_per_minute', 0):.2f} tasks/minute")
        print(f"Total Tasks: {rate.get('total_tasks', 0)}")
        
        # Motivational states
        states = data.get('motivational_states', {})
        print(f"\n💭 MOTIVATIONAL STATES")
        print(f"Total Active States: {states.get('total_states', 0)}")
        print(f"High Urgency (>=0.7): {len(states.get('high_urgency', []))}")
        print(f"Medium Urgency (0.3-0.7): {len(states.get('medium_urgency', []))}")
        print(f"Low Urgency (<0.3): {len(states.get('low_urgency', []))}")
        print(f"Average Urgency: {states.get('avg_urgency', 0):.3f}")
        print(f"Average Satisfaction: {states.get('avg_satisfaction', 0):.3f}")
        
        # Agent/Orchestrator activity
        agent_activity = data.get('agent_activity', {})
        print(f"\n👥 AGENT & ORCHESTRATOR ACTIVITY")
        print(f"Recent Agents: {agent_activity.get('total_agents', 0)}")
        print(f"Agent Statuses: {agent_activity.get('agent_statuses', {})}")
        print(f"Recent Orchestrators: {agent_activity.get('total_orchestrators', 0)}")
        print(f"Orchestrator Statuses: {agent_activity.get('orchestrator_statuses', {})}")
        
        # Errors and failures
        errors = data.get('errors', {})
        print(f"\n❌ ERRORS & FAILURES")
        print(f"Total Failures: {errors.get('total_failures', 0)}")
        print(f"Failed Trees: {len(errors.get('failed_trees', []))}")
        print(f"Failed Agents: {len(errors.get('failed_agents', []))}")
        print(f"Failed LLM Interactions: {len(errors.get('failed_llm_interactions', []))}")
        print(f"Failed Tool Executions: {len(errors.get('failed_tool_executions', []))}")
        print(f"Failed Motivational Tasks: {len(errors.get('failed_motivational_tasks', []))}")
        
        # Task types analysis
        task_types = data.get('task_types', {})
        print(f"\n📊 TASK TYPE ANALYSIS")
        print(f"Task Patterns: {task_types.get('task_patterns', {})}")
        print(f"Priority Distribution: {task_types.get('priority_distribution', {})}")
        
        # Behavioral patterns
        patterns = data.get('patterns', {})
        print(f"\n🔍 BEHAVIORAL PATTERNS")
        print(f"Success Rate: {patterns.get('success_rate', 0):.2%}")
        print(f"Successful Tasks: {patterns.get('successful_tasks', 0)}")
        
        # Time-based activity
        intervals = patterns.get('time_intervals', [])
        if intervals:
            print(f"\n⏰ ACTIVITY OVER TIME (5-minute intervals)")
            for interval in intervals[-6:]:  # Show last 6 intervals (30 minutes)
                print(f"  {interval['start']}-{interval['end']}: {interval['task_count']} tasks")
        
        # Sample prompts
        sample_prompts = task_types.get('sample_prompts', [])
        if sample_prompts:
            print(f"\n📝 SAMPLE RECENT PROMPTS")
            for i, prompt in enumerate(sample_prompts[:3]):
                print(f"  {i+1}. {prompt[:150]}{'...' if len(prompt) > 150 else ''}")
        
        print("\n" + "=" * 80)
    
    async def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        try:
            # Check database connection
            db_connected = await self.check_database_connection()
            if not db_connected:
                return {'db_connected': False}
            
            # Gather all monitoring data
            data = {
                'db_connected': True,
                'autonomous_activity': await self.get_recent_autonomous_activity(),
                'motivational_tasks': await self.get_motivational_tasks(),
                'motivational_states': await self.get_motivational_states(),
                'agent_activity': await self.get_agent_orchestrator_activity(),
                'errors': await self.check_for_errors(),
                'task_rate': await self.calculate_task_generation_rate(),
                'task_types': await self.analyze_task_types(),
                'patterns': await self.look_for_patterns()
            }
            
            return data
            
        except Exception as e:
            print(f"❌ Error during monitoring cycle: {e}")
            return {'error': str(e)}
    
    async def continuous_monitoring(self, refresh_interval=30):
        """Run continuous monitoring with specified refresh interval"""
        print(f"Starting continuous monitoring (refresh every {refresh_interval}s)...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                data = await self.run_monitoring_cycle()
                
                # Clear screen and print report
                os.system('clear' if os.name == 'posix' else 'cls')
                self.print_status_report(data)
                
                # Wait for next cycle
                await asyncio.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
        finally:
            await db_manager.close()

async def main():
    """Main function"""
    monitor = NYXPressureTestMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Run once
        data = await monitor.run_monitoring_cycle()
        monitor.print_status_report(data)
        await db_manager.close()
    else:
        # Continuous monitoring
        await monitor.continuous_monitoring(refresh_interval=30)

if __name__ == "__main__":
    asyncio.run(main())