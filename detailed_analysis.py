#!/usr/bin/env python3
"""
Detailed analysis script to gather additional insights from the pressure test
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

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

async def get_detailed_motivational_insights():
    """Get detailed insights about motivational states and their triggers"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    async with db_manager.get_async_session() as session:
        # Get all motivational states with recent activity
        states_query = select(MotivationalState).where(
            or_(
                MotivationalState.last_triggered_at >= time_window,
                MotivationalState.is_active == True
            )
        ).order_by(desc(MotivationalState.urgency))
        
        result = await session.execute(states_query)
        states = result.scalars().all()
        
        print("🔍 DETAILED MOTIVATIONAL STATE ANALYSIS")
        print("-" * 60)
        
        for state in states:
            print(f"Motivation: {state.motivation_type}")
            print(f"  Urgency: {state.urgency:.3f} | Satisfaction: {state.satisfaction:.3f}")
            print(f"  Success Rate: {state.success_rate:.3f} ({state.success_count}/{state.total_attempts})")
            print(f"  Last Triggered: {state.last_triggered_at}")
            print(f"  Trigger Condition: {state.trigger_condition}")
            print(f"  Active: {'Yes' if state.is_active else 'No'}")
            print()

async def get_detailed_task_analysis():
    """Get detailed analysis of recent tasks"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    async with db_manager.get_async_session() as session:
        # Get tasks with full details
        tasks_query = select(MotivationalTask).where(
            MotivationalTask.spawned_at >= time_window
        ).options(
            selectinload(MotivationalTask.motivational_state),
            selectinload(MotivationalTask.thought_tree)
        ).order_by(desc(MotivationalTask.spawned_at))
        
        result = await session.execute(tasks_query)
        tasks = result.scalars().all()
        
        print("📋 DETAILED TASK ANALYSIS")
        print("-" * 60)
        
        for i, task in enumerate(tasks[:10]):  # Show first 10 tasks
            print(f"Task {i+1}: ID {task.id}")
            print(f"  Status: {task.status} | Priority: {task.task_priority:.3f}")
            print(f"  Spawned: {task.spawned_at}")
            print(f"  Motivation: {task.motivational_state.motivation_type if task.motivational_state else 'Unknown'}")
            if task.thought_tree:
                print(f"  Associated Goal: {task.thought_tree.goal[:100]}...")
            print(f"  Generated Prompt: {task.generated_prompt[:150]}...")
            if task.success is not None:
                print(f"  Success: {'Yes' if task.success else 'No'}")
            print()

async def get_system_performance_metrics():
    """Get system performance metrics"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    async with db_manager.get_async_session() as session:
        # LLM interaction metrics
        llm_query = select(LLMInteraction).where(
            LLMInteraction.request_timestamp >= time_window
        )
        
        result = await session.execute(llm_query)
        llm_interactions = result.scalars().all()
        
        # Tool execution metrics
        tool_query = select(ToolExecution).where(
            ToolExecution.started_at >= time_window
        )
        
        result = await session.execute(tool_query)
        tool_executions = result.scalars().all()
        
        print("⚡ SYSTEM PERFORMANCE METRICS")
        print("-" * 60)
        
        if llm_interactions:
            total_tokens_in = sum(i.token_count_input or 0 for i in llm_interactions)
            total_tokens_out = sum(i.token_count_output or 0 for i in llm_interactions)
            total_cost = sum(float(i.cost_usd or 0) for i in llm_interactions)
            avg_latency = sum(i.latency_ms or 0 for i in llm_interactions) / len(llm_interactions)
            success_rate = sum(1 for i in llm_interactions if i.success) / len(llm_interactions)
            
            print(f"LLM Interactions: {len(llm_interactions)}")
            print(f"  Success Rate: {success_rate:.2%}")
            print(f"  Total Input Tokens: {total_tokens_in:,}")
            print(f"  Total Output Tokens: {total_tokens_out:,}")
            print(f"  Total Cost: ${total_cost:.4f}")
            print(f"  Average Latency: {avg_latency:.0f}ms")
        else:
            print("No LLM interactions in the last 30 minutes")
        
        print()
        
        if tool_executions:
            avg_duration = sum(t.duration_ms or 0 for t in tool_executions) / len(tool_executions)
            success_rate = sum(1 for t in tool_executions if t.success) / len(tool_executions)
            
            print(f"Tool Executions: {len(tool_executions)}")
            print(f"  Success Rate: {success_rate:.2%}")
            print(f"  Average Duration: {avg_duration:.0f}ms")
            
            # Tool usage breakdown
            tool_usage = {}
            for tool in tool_executions:
                tool_usage[tool.tool_name] = tool_usage.get(tool.tool_name, 0) + 1
            
            print("  Tool Usage:")
            for tool_name, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
                print(f"    {tool_name}: {count}")
        else:
            print("No tool executions in the last 30 minutes")

async def get_thought_tree_hierarchy():
    """Analyze thought tree hierarchy and relationships"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    async with db_manager.get_async_session() as session:
        # Get recent thought trees with their relationships
        trees_query = select(ThoughtTree).where(
            ThoughtTree.created_at >= time_window
        ).order_by(ThoughtTree.depth, desc(ThoughtTree.created_at))
        
        result = await session.execute(trees_query)
        trees = result.scalars().all()
        
        print("🌳 THOUGHT TREE HIERARCHY")
        print("-" * 60)
        
        # Group by depth
        by_depth = {}
        for tree in trees:
            depth = tree.depth
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(tree)
        
        for depth in sorted(by_depth.keys()):
            trees_at_depth = by_depth[depth]
            print(f"Depth {depth}: {len(trees_at_depth)} trees")
            
            for i, tree in enumerate(trees_at_depth[:5]):  # Show first 5 at each depth
                indent = "  " + "  " * depth
                status_emoji = {"completed": "✅", "failed": "❌", "in_progress": "⏳", "pending": "⏸️"}.get(tree.status, "❓")
                print(f"{indent}{status_emoji} {tree.goal[:80]}{'...' if len(tree.goal) > 80 else ''}")
                if tree.parent_id:
                    print(f"{indent}   └─ Parent: {tree.parent_id}")
            
            if len(trees_at_depth) > 5:
                print(f"  ... and {len(trees_at_depth) - 5} more")
            print()

async def get_communication_analysis():
    """Analyze agent communication patterns"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    async with db_manager.get_async_session() as session:
        # Get recent communications
        comm_query = select(AgentCommunication).where(
            AgentCommunication.sent_at >= time_window
        ).order_by(desc(AgentCommunication.sent_at))
        
        result = await session.execute(comm_query)
        communications = result.scalars().all()
        
        print("💬 AGENT COMMUNICATION ANALYSIS")
        print("-" * 60)
        
        if communications:
            # Message type breakdown
            msg_types = {}
            for comm in communications:
                msg_types[comm.message_type] = msg_types.get(comm.message_type, 0) + 1
            
            print(f"Total Communications: {len(communications)}")
            print("Message Types:")
            for msg_type, count in msg_types.items():
                print(f"  {msg_type}: {count}")
            
            # Delivery success rate
            delivered = sum(1 for c in communications if c.delivered)
            processed = sum(1 for c in communications if c.processed)
            
            print(f"Delivery Rate: {delivered/len(communications):.2%}")
            print(f"Processing Rate: {processed/len(communications):.2%}")
        else:
            print("No agent communications in the last 30 minutes")

async def main():
    """Run detailed analysis"""
    print("="*80)
    print("DETAILED NYX PRESSURE TEST ANALYSIS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()
    
    try:
        await get_detailed_motivational_insights()
        print()
        await get_detailed_task_analysis()
        print()
        await get_system_performance_metrics()
        print()
        await get_thought_tree_hierarchy()
        print()
        await get_communication_analysis()
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())