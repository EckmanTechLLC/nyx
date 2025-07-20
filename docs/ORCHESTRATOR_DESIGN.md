# NYX Orchestrator Layer Design

## Overview

The Orchestrator Layer sits above the Core Agent System and manages complex workflows through recursive task decomposition, agent lifecycle management, and resource coordination. It integrates directly with the existing agent system while providing workflow orchestration capabilities.

## Architecture Integration

### Existing Foundation
- **Core Agent System**: BaseAgent, TaskAgent, CouncilAgent, ValidatorAgent, MemoryAgent
- **Agent State Machine**: SPAWNED → ACTIVE → WAITING → COORDINATING → COMPLETED → TERMINATED
- **Database Models**: Orchestrator table already defined with relationships to ThoughtTree
- **LLM Integration**: Claude Native API with prompt caching

### Orchestrator Hierarchy
```
TopLevelOrchestrator
├── SubOrchestrator (recursive decomposition)
│   ├── TaskAgent spawning
│   ├── CouncilAgent coordination
│   └── ValidatorAgent validation
└── SubOrchestrator (parallel workstreams)
    ├── MemoryAgent context sharing
    └── Agent lifecycle management
```

## Core Components

### 1. BaseOrchestrator Class

**Purpose**: Foundation class for all orchestrators with common functionality

**Key Features**:
- **Agent Lifecycle Management**: Spawn, monitor, and terminate agents
- **Resource Management**: Track concurrent agents against limits
- **State Persistence**: Database integration with Orchestrator model
- **Context Management**: Global context sharing across agent hierarchies
- **Error Recovery**: Handle agent failures and retry logic

**Integration Points**:
- Uses `thought_tree_id` to link agents to orchestrated workflows
- Manages `parent_agent_id` relationships for recursive agent spawning
- Interfaces with existing database connection and session management

### 2. TopLevelOrchestrator Class

**Purpose**: Entry point for all workflows, handles external requests

**Responsibilities**:
- **Workflow Initiation**: Accept external goals and decompose into tasks
- **Goal Analysis**: Determine initial task breakdown strategy
- **Resource Planning**: Estimate agent requirements and execution timeline
- **Progress Monitoring**: Track overall workflow completion status
- **Result Aggregation**: Synthesize final outputs from sub-orchestrators

**Agent Integration Patterns**:
```python
# Pattern 1: Direct Task Execution
task_agent = TaskAgent(
    thought_tree_id=self.thought_tree_id,
    parent_agent_id=None  # Top-level orchestrator spawns directly
)

# Pattern 2: Recursive Decomposition
sub_orchestrator = SubOrchestrator(
    parent_orchestrator_id=self.id,
    thought_tree_id=self.thought_tree_id,
    global_context=self.extract_relevant_context()
)

# Pattern 3: Council Decision Making
council_agent = CouncilAgent(
    thought_tree_id=self.thought_tree_id,
    parent_agent_id=None,
    council_roles=["architect", "critic", "optimizer"]
)
```

### 3. SubOrchestrator Class

**Purpose**: Handle recursive task decomposition and local coordination

**Responsibilities**:
- **Task Decomposition**: Break complex tasks into manageable subtasks
- **Agent Spawning**: Create appropriate agent types based on task requirements
- **Coordination Management**: Handle agent state transitions during complex workflows
- **Local Context**: Maintain workflow-specific context while accessing global state
- **Result Synthesis**: Aggregate child agent outputs before reporting to parent

**Agent Coordination Patterns**:
```python
# Recursive Coordination Pattern
async def execute_complex_task(self, task_definition):
    # 1. Analyze task complexity
    complexity = await self.analyze_task(task_definition)
    
    if complexity.requires_decomposition:
        # 2. Spawn child agents in WAITING state
        parent_task_agent = TaskAgent(thought_tree_id=self.thought_tree_id)
        await parent_task_agent.initialize()
        await parent_task_agent.transition_to_waiting()
        
        # 3. Create subtasks and spawn child agents
        subtasks = await self.decompose_task(task_definition)
        child_agents = []
        
        for subtask in subtasks:
            if subtask.type == "execution":
                child = TaskAgent(
                    thought_tree_id=self.thought_tree_id,
                    parent_agent_id=parent_task_agent.id
                )
            elif subtask.type == "decision":
                child = CouncilAgent(
                    thought_tree_id=self.thought_tree_id,
                    parent_agent_id=parent_task_agent.id
                )
            
            await child.initialize()
            child_agents.append(child)
        
        # 4. Execute children and coordinate results
        results = await self.coordinate_child_execution(child_agents)
        
        # 5. Parent transitions to COORDINATING for result synthesis
        await parent_task_agent.transition_to_coordinating()
        final_result = await self.synthesize_results(results)
        
        # 6. Complete parent agent
        await parent_task_agent.return_to_active()
        await parent_task_agent.execute(final_result)
        
        return final_result
```

## Agent Integration Specifications

### Agent Spawning Protocol

**Standard Agent Creation**:
```python
async def spawn_agent(
    self,
    agent_type: str,
    task_context: Dict[str, Any],
    parent_agent_id: Optional[str] = None
) -> BaseAgent:
    """
    Spawn agent with orchestrator context integration
    
    Args:
        agent_type: "task", "council", "validator", "memory"
        task_context: Task-specific configuration
        parent_agent_id: For recursive agent hierarchies
    """
    
    # Create agent with orchestrator context
    agent_params = {
        'thought_tree_id': self.thought_tree_id,
        'parent_agent_id': parent_agent_id,
        'max_retries': task_context.get('max_retries', 3),
        'timeout_seconds': task_context.get('timeout', 300)
    }
    
    if agent_type == "task":
        agent = TaskAgent(**agent_params)
    elif agent_type == "council":
        agent = CouncilAgent(**agent_params)
    elif agent_type == "validator":
        agent = ValidatorAgent(**agent_params)
    elif agent_type == "memory":
        agent = MemoryAgent(**agent_params)
    
    await agent.initialize()
    
    # Update orchestrator tracking
    self.current_active_agents += 1
    await self._persist_orchestrator_state()
    
    return agent
```

### Resource Management Integration

**Concurrent Agent Limits**:
```python
async def check_resource_availability(self) -> bool:
    """Check if orchestrator can spawn new agents"""
    return self.current_active_agents < self.max_concurrent_agents

async def wait_for_agent_slot(self):
    """Wait for agent slot to become available"""
    while not await self.check_resource_availability():
        await asyncio.sleep(1)
        # Update current_active_agents from completed agents
        await self._update_agent_counts()
```

### Context Sharing Protocol

**Global Context Management**:
```python
class ContextManager:
    """Manage context sharing between orchestrators and agents"""
    
    async def share_context_to_agent(
        self, 
        agent: BaseAgent, 
        context_scope: str
    ):
        """Share relevant orchestrator context with agent"""
        relevant_context = self.extract_context_for_scope(context_scope)
        
        # Use MemoryAgent for context persistence
        memory_agent = MemoryAgent(thought_tree_id=self.thought_tree_id)
        await memory_agent.initialize()
        
        await memory_agent.store_context(
            content=relevant_context,
            scope="agent_context",
            target_agent_id=agent.id
        )
    
    async def aggregate_agent_results(
        self, 
        agent_results: List[AgentResult]
    ) -> Dict[str, Any]:
        """Aggregate results from multiple agents"""
        aggregated = {
            'success_count': sum(1 for r in agent_results if r.success),
            'total_tokens': sum(r.tokens_used for r in agent_results),
            'total_cost': sum(r.cost_usd for r in agent_results),
            'combined_output': self._synthesize_outputs(agent_results),
            'execution_summary': self._generate_execution_summary(agent_results)
        }
        
        # Update global context with results
        await self._update_global_context(aggregated)
        
        return aggregated
```

## Database Integration

### Orchestrator State Persistence

**State Management**:
```python
async def _persist_orchestrator_state(self):
    """Persist orchestrator state to database"""
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Orchestrator).filter(Orchestrator.id == self.id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.status = self.status
            existing.current_active_agents = self.current_active_agents
            existing.global_context = self.global_context
        else:
            new_orchestrator = Orchestrator(
                id=self.id,
                parent_orchestrator_id=self.parent_orchestrator_id,
                thought_tree_id=self.thought_tree_id,
                orchestrator_type=self.orchestrator_type,
                status=self.status,
                max_concurrent_agents=self.max_concurrent_agents,
                current_active_agents=self.current_active_agents,
                global_context=self.global_context
            )
            session.add(new_orchestrator)
        
        await session.commit()
```

### Relationship Management

**Agent-Orchestrator Linking**:
- Orchestrators create agents with `thought_tree_id` linkage
- Agent `spawned_by` field can reference orchestrator ID for tracking
- Parent-child agent relationships maintained independently of orchestrators
- Global context flows through `thought_tree_id` associations

## Orchestration Patterns

### Pattern 1: Linear Workflow
```
Orchestrator → TaskAgent1 → TaskAgent2 → ValidatorAgent → Complete
```

### Pattern 2: Parallel Execution
```
Orchestrator ┬→ TaskAgent1 ┐
              ├→ TaskAgent2 ├→ CouncilAgent → ValidatorAgent → Complete
              └→ TaskAgent3 ┘
```

### Pattern 3: Recursive Decomposition
```
TopOrchestrator → SubOrchestrator1 ┬→ TaskAgent1 → SubOrchestrator2 → TaskAgent3
                                   └→ TaskAgent2 ──────────────────→ TaskAgent4
```

### Pattern 4: Council-Driven Workflow
```
Orchestrator → CouncilAgent → [Decision] ┬→ TaskAgent (Option A)
                                         └→ SubOrchestrator (Option B) → [Recursive]
```

## Error Handling and Recovery

### Orchestrator-Level Error Recovery
```python
async def handle_agent_failure(
    self, 
    failed_agent: BaseAgent, 
    error: Exception
):
    """Handle agent failures within orchestrated workflows"""
    
    # 1. Log failure context
    await self._log_agent_failure(failed_agent, error)
    
    # 2. Assess impact on workflow
    impact = await self._assess_failure_impact(failed_agent)
    
    # 3. Recovery strategy
    if impact.is_critical:
        # Spawn council agent for failure analysis
        council = CouncilAgent(
            thought_tree_id=self.thought_tree_id,
            council_roles=["analyzer", "recovery_strategist", "risk_assessor"]
        )
        recovery_plan = await council.execute({
            'decision_type': 'failure_recovery',
            'failed_task': failed_agent.get_statistics(),
            'workflow_context': self.global_context
        })
        
        # Execute recovery plan
        await self._execute_recovery_plan(recovery_plan)
    else:
        # Simple retry with different parameters
        await self._retry_agent_task(failed_agent)
```

## Implementation Priority

1. **BaseOrchestrator** - Core functionality and agent integration
2. **TopLevelOrchestrator** - Entry point and workflow initiation
3. **SubOrchestrator** - Recursive decomposition capabilities
4. **Context Management** - Global state sharing
5. **Resource Management** - Concurrent agent limits and monitoring
6. **Error Recovery** - Failure handling and workflow resilience

## Testing Strategy

### Unit Tests
- Orchestrator state management
- Agent spawning and lifecycle tracking
- Resource limit enforcement
- Context sharing mechanisms

### Integration Tests
- End-to-end workflow execution
- Multi-level recursive decomposition
- Agent failure and recovery scenarios
- Performance under concurrent load

### Test Data Requirements
- Complex task scenarios requiring decomposition
- Resource constraint scenarios
- Agent failure simulation
- Multi-orchestrator coordination patterns

This design ensures the orchestrator layer integrates seamlessly with the existing agent system while providing the workflow orchestration capabilities needed for complex recursive task decomposition.