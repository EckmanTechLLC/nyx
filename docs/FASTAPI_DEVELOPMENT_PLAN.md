# NYX FastAPI Development Plan

## Overview

This document outlines the development plan for implementing a REST API layer for the NYX autonomous agent system using FastAPI. All references are verified against the actual codebase implementation.

**Status**: Not Yet Implemented (0% complete)  
**Priority**: Critical - Only remaining major component for production deployment  
**Estimated Timeline**: 2-3 weeks for full implementation

---

## Existing Foundation (Verified)

### ✅ Complete Pydantic Models Available
**File**: `/home/etl/projects/nyx/database/schemas.py`

**Available Request/Response Models**:
- `ThoughtTreeCreate`, `ThoughtTreeUpdate`, `ThoughtTree`
- `AgentCreate`, `AgentUpdate`, `Agent` 
- `OrchestratorCreate`, `OrchestratorUpdate`, `Orchestrator`
- `LLMInteractionCreate`, `LLMInteractionUpdate`, `LLMInteraction`
- `ToolExecutionCreate`, `ToolExecutionUpdate`, `ToolExecution`
- `MotivationalStateCreate`, `MotivationalStateUpdate`, `MotivationalState`
- `MotivationalTaskCreate`, `MotivationalTaskUpdate`, `MotivationalTask`

**Validated Enums**:
```python
# From database/schemas.py (lines 8-57)
class StatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentTypeEnum(str, Enum):
    TASK = "task"
    COUNCIL = "council"
    VALIDATOR = "validator"
    MEMORY = "memory"

class WorkflowInputType(Enum):  # From core/orchestrator/top_level.py (lines 27-34)
    USER_PROMPT = "user_prompt"
    STRUCTURED_TASK = "structured_task"
    GOAL_WORKFLOW = "goal_workflow"
    SCHEDULED_WORKFLOW = "scheduled_workflow"
    REACTIVE_WORKFLOW = "reactive_workflow"
    CONTINUATION_WORKFLOW = "continuation_workflow"
```

### ✅ Core System Interfaces (Verified)

#### TopLevelOrchestrator Interface
**File**: `/home/etl/projects/nyx/core/orchestrator/top_level.py`

**Key Method** (line 198):
```python
async def execute_workflow(self, workflow_input: WorkflowInput) -> OrchestratorResult
```

**Input Structure** (line 125):
```python
@dataclass
class WorkflowInput:
    input_type: WorkflowInputType
    content: Dict[str, Any]
    execution_context: Dict[str, Any] = field(default_factory=dict)
    domain_context: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)
    historical_context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    urgency: str = "normal"
```

#### MotivationalModelEngine Interface  
**File**: `/home/etl/projects/nyx/core/motivation/engine.py`

**Control Methods**:
- `async def start()` (line 58): Start autonomous operation daemon
- `async def stop()` (line 69): Stop the daemon gracefully
- `def get_status() -> Dict[str, Any]` (line 377): Get current engine status

**Status Response Structure** (lines 378-385):
```python
{
    'running': bool,
    'evaluation_interval': float,
    'max_concurrent_tasks': int,
    'min_arbitration_threshold': float,
    'safety_enabled': bool
}
```

**Engine Configuration** (lines 30-37):
```python
def __init__(
    self,
    evaluation_interval: float = 30.0,
    max_concurrent_motivated_tasks: int = 3,
    min_arbitration_threshold: float = 0.3,
    safety_enabled: bool = True,
    test_mode: bool = False
)
```

#### LLM Integration Interface
**File**: `/home/etl/projects/nyx/llm/claude_native.py`

**Main Method** (lines 77-89):
```python
async def call_claude(
    self,
    system_prompt: str = None,
    user_prompt: str = None,
    model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    thought_tree_id: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    use_native_caching: bool = True,
    **kwargs
) -> LLMResponse
```

#### Tool Execution Interface
**File**: `/home/etl/projects/nyx/core/tools/base.py`

**Execution Method** (lines 90-95):
```python
async def execute(
    self, 
    parameters: Dict[str, Any],
    agent_id: Optional[str] = None,
    thought_tree_id: Optional[str] = None
) -> ToolResult
```

**Tool Result Structure** (lines 31-51):
```python
@dataclass
class ToolResult:
    success: bool
    output: str
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    stdout: Optional[str] = None
    stderr: Optional[str] = None
```

#### Database Connection
**File**: `/home/etl/projects/nyx/database/connection.py`

**Session Management Pattern**:
```python
from database.connection import db_manager

async with db_manager.get_async_session() as session:
    # Database operations
    await session.commit()
```

---

## Implementation Plan

### Phase 1: Core FastAPI Application (Week 1)

#### 1.1 Application Structure
**Create**: `/home/etl/projects/nyx/app/main.py`
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import orchestrator, motivational, system, tools, llm
from .core.config import get_settings
from .core.exceptions import create_exception_handler

app = FastAPI(
    title="NYX Autonomous Agent API",
    description="REST API for NYX autonomous orchestration system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])
app.include_router(motivational.router, prefix="/api/v1/motivational", tags=["motivational"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])

# Exception handlers
app.add_exception_handler(Exception, create_exception_handler)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

#### 1.2 Configuration Management
**Create**: `/home/etl/projects/nyx/app/core/config.py`
```python
from functools import lru_cache
from config.settings import settings as base_settings

@lru_cache()
def get_settings():
    return base_settings
```

#### 1.3 Database Dependency
**Create**: `/home/etl/projects/nyx/app/core/database.py`
```python
from contextlib import asynccontextmanager
from database.connection import db_manager

@asynccontextmanager
async def get_db_session():
    async with db_manager.get_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Phase 2: Orchestrator API Endpoints (Week 1)

#### 2.1 Workflow Management
**Create**: `/home/etl/projects/nyx/app/api/v1/orchestrator.py`

Based on verified TopLevelOrchestrator interface:

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from uuid import UUID

from core.orchestrator.top_level import TopLevelOrchestrator, WorkflowInput, WorkflowInputType
from database.schemas import ThoughtTreeCreate
from ..core.database import get_db_session

router = APIRouter()

# Request/Response models using existing WorkflowInput structure
from pydantic import BaseModel
from enum import Enum

class WorkflowRequest(BaseModel):
    input_type: str  # Maps to WorkflowInputType enum values
    content: Dict[str, Any]
    execution_context: Dict[str, Any] = {}
    domain_context: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}
    priority: str = "medium"
    urgency: str = "normal"

@router.post("/workflows/execute")
async def execute_workflow(
    request: WorkflowRequest,
    db_session = Depends(get_db_session)
):
    """Execute a workflow using TopLevelOrchestrator"""
    async with db_session as session:
        orchestrator = TopLevelOrchestrator(session)
        
        # Create WorkflowInput from request
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType(request.input_type),
            content=request.content,
            execution_context=request.execution_context,
            domain_context=request.domain_context,
            user_context=request.user_context,
            priority=request.priority,
            urgency=request.urgency
        )
        
        try:
            result = await orchestrator.execute_workflow(workflow_input)
            return {
                "success": result.success,
                "content": result.content,
                "metadata": result.metadata,
                "execution_time_ms": result.execution_time_ms,
                "cost_usd": float(result.cost_usd) if result.cost_usd else 0.0
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: UUID):
    """Get status of a specific workflow"""
    # Implementation uses ThoughtTree queries
    async with get_db_session() as session:
        # Query workflow status from database
        pass
```

### Phase 3: Motivational System API (Week 1-2)

#### 3.1 Autonomous Control
**Create**: `/home/etl/projects/nyx/app/api/v1/motivational.py`

Based on verified MotivationalModelEngine interface:

```python
from fastapi import APIRouter, Depends, HTTPException
from core.motivation.engine import MotivationalModelEngine
from core.motivation.states import MotivationalStateManager
from core.motivation.orchestrator_integration import create_integrated_motivational_system

router = APIRouter()

# Global engine instance (in production, use dependency injection)
_engine_instance = None
_integration_instance = None

@router.post("/engine/start")
async def start_engine():
    """Start the autonomous motivational engine"""
    global _engine_instance, _integration_instance
    
    try:
        if not _engine_instance:
            _engine_instance, _integration_instance = await create_integrated_motivational_system(
                start_engine=True,
                start_integration=True
            )
        else:
            await _engine_instance.start()
            
        return {"message": "Motivational engine started", "status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start engine: {str(e)}")

@router.post("/engine/stop")
async def stop_engine():
    """Stop the autonomous motivational engine"""
    global _engine_instance
    
    if not _engine_instance:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    try:
        await _engine_instance.stop()
        return {"message": "Motivational engine stopped", "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop engine: {str(e)}")

@router.get("/engine/status")
async def get_engine_status():
    """Get current status of motivational engine"""
    global _engine_instance
    
    if not _engine_instance:
        return {"status": "not_initialized", "running": False}
    
    # Uses verified get_status() method from engine.py line 377
    status = _engine_instance.get_status()
    return status

@router.get("/states")
async def get_motivational_states():
    """Get all current motivational states"""
    async with get_db_session() as session:
        state_manager = MotivationalStateManager()
        summary = await state_manager.get_motivation_summary(session)
        return summary

@router.post("/states/{motivation_type}/boost")
async def boost_motivation(
    motivation_type: str,
    boost_amount: float,
    metadata: Dict[str, Any] = {}
):
    """Boost a specific motivation type"""
    async with get_db_session() as session:
        state_manager = MotivationalStateManager()
        await state_manager.boost_motivation(
            session, 
            motivation_type, 
            boost_amount, 
            metadata
        )
        return {"message": f"Boosted {motivation_type} by {boost_amount}"}
```

### Phase 4: System Status & Tools API (Week 2)

#### 4.1 System Status
**Create**: `/home/etl/projects/nyx/app/api/v1/system.py`

```python
from fastapi import APIRouter, Depends
from database.connection import db_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive system health check"""
    try:
        # Test database connection
        db_healthy = await db_manager.test_connection()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/stats")
async def get_system_stats():
    """Get comprehensive system statistics"""
    # Implementation would query various system components
    pass
```

#### 4.2 Tool Execution
**Create**: `/home/etl/projects/nyx/app/api/v1/tools.py`

Based on verified BaseTool interface:

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from core.tools.file_ops import FileOperationsTool

router = APIRouter()

@router.post("/execute")
async def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    agent_id: Optional[str] = None,
    thought_tree_id: Optional[str] = None
):
    """Execute a tool with given parameters"""
    
    # Tool factory (simplified)
    tools = {
        "file_operations": FileOperationsTool
    }
    
    if tool_name not in tools:
        raise HTTPException(status_code=400, detail=f"Tool {tool_name} not available")
    
    try:
        tool = tools[tool_name]()
        # Uses verified execute method from base.py line 90
        result = await tool.execute(
            parameters=parameters,
            agent_id=agent_id,
            thought_tree_id=thought_tree_id
        )
        
        return {
            "success": result.success,
            "output": result.output,
            "error_message": result.error_message,
            "execution_time_ms": result.execution_time_ms,
            "metadata": result.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available")
async def list_available_tools():
    """List all available tools"""
    return {
        "tools": [
            {
                "name": "file_operations",
                "description": "File system operations with safety validation",
                "operations": ["read_file", "list_directory", "analyze_codebase"]
            }
        ]
    }
```

### Phase 5: LLM API (Week 2)

#### 5.1 LLM Integration  
**Create**: `/home/etl/projects/nyx/app/api/v1/llm.py`

Based on verified ClaudeNativeAPI interface:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel

router = APIRouter()

class LLMRequest(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    model: str = "claude-3-5-haiku-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    use_native_caching: bool = True

@router.post("/generate")
async def generate_response(request: LLMRequest):
    """Generate LLM response using Claude API"""
    try:
        claude_api = ClaudeNativeAPI()
        
        # Uses verified call_claude method from claude_native.py line 77
        response = await claude_api.call_claude(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            model=LLMModel(request.model),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            use_native_caching=request.use_native_caching
        )
        
        return {
            "content": response.content,
            "success": response.success,
            "cached": response.cached,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_cost_usd": float(response.usage.total_cost_usd)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_llm_stats():
    """Get LLM usage statistics"""
    claude_api = ClaudeNativeAPI()
    stats = claude_api.get_statistics()
    return stats
```

### Phase 6: Authentication & Security (Week 2)

#### 6.1 Authentication Middleware
**Create**: `/home/etl/projects/nyx/app/core/auth.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional

security = HTTPBearer()

SECRET_KEY = "your-secret-key"  # Use environment variable
ALGORITHM = "HS256"

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

### Phase 7: WebSocket Support (Week 3)

#### 7.1 Real-Time Updates
**Create**: `/home/etl/projects/nyx/app/api/v1/websockets.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Connection closed
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws/system/status")
async def system_status_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Broadcast system status every 10 seconds
            status = await get_system_status()
            await manager.broadcast(status)
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## Development Milestones

### Week 1 Deliverables
- [ ] Core FastAPI application structure
- [ ] Orchestrator API endpoints (workflow execution)
- [ ] Motivational engine control endpoints
- [ ] Basic health checks and system status

### Week 2 Deliverables  
- [ ] Tool execution API endpoints
- [ ] LLM integration API endpoints
- [ ] Authentication and authorization system
- [ ] Comprehensive error handling

### Week 3 Deliverables
- [ ] WebSocket support for real-time updates
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Rate limiting and security hardening
- [ ] Production deployment configuration

---

## Testing Strategy

### Integration Tests
Using existing NYX patterns and database schemas:

```python
# tests/api/test_orchestrator.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_execute_workflow():
    response = client.post("/api/v1/orchestrator/workflows/execute", json={
        "input_type": "user_prompt",
        "content": {"prompt": "Test workflow execution"},
        "priority": "high"
    })
    assert response.status_code == 200
    assert "success" in response.json()
```

### Database Integration
All API endpoints will use the existing verified database patterns:
- Async session management with `db_manager.get_async_session()`
- Proper transaction handling and rollback
- Existing Pydantic schemas for validation

---

## Production Deployment

### Docker Configuration
**Create**: `/home/etl/projects/nyx/Dockerfile.api`

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Integration
**Update**: `/home/etl/projects/nyx/docker-compose.yml`

```yaml
services:
  nyx-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/nyx
    depends_on:
      - db
    volumes:
      - ./app:/app/app
```

---

## Success Criteria

1. **Core Functionality**: All major NYX systems accessible via REST API
2. **Performance**: API responses under 500ms for standard operations  
3. **Security**: JWT authentication and role-based access control
4. **Documentation**: Complete OpenAPI specification with examples
5. **Reliability**: 99.9% uptime with proper error handling
6. **Real-time**: WebSocket updates for system status and workflow progress

**Final Goal**: Production-ready REST API that exposes NYX's autonomous capabilities for external integration while maintaining all existing safety constraints and operational patterns.