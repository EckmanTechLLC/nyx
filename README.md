# NYX - Autonomous Task Orchestration System

NYX is an autonomous task orchestration system that can operate independently for extended periods without human intervention. The system uses a motivational model to analyze system state, generate contextual tasks, and execute workflows through a hierarchical orchestration architecture.

## Features

- **Autonomous Operation**: Runs continuously using timer-based daemons that monitor system state and generate tasks
- **Motivational System**: Six motivational states that trigger based on system conditions (failed tasks, idle periods, low confidence outputs, etc.)
- **Social Network Integration**: Monitors Moltbook AI agent social network, validates claims, and provides evidence-based responses
- **Task Generation**: Creates specific prompts and workflows based on detected system needs
- **Hierarchical Orchestration**: Routes tasks through orchestrators and specialized agents for execution
- **Database Persistence**: Complete tracking of tasks, motivations, and outcomes with learning metrics

## Architecture

NYX consists of several core components:

1. **Motivational Model Engine** - Timer-based daemon that analyzes system state and generates autonomous tasks
2. **Top-Level Orchestrator** - Executes workflows from external prompts and autonomous triggers
3. **Specialized Agent Types** - Task, Council, Validator, and Memory agents for different functions
4. **Database System** - PostgreSQL backend with comprehensive tracking and metrics
5. **Safety Layer** - Resource constraints and monitoring for controlled operation

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Anthropic API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nyx
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database URL and API keys
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the system:
```bash
python scripts/demo_autonomous_nyx.py
```

## Docker Setup

Alternatively, use Docker Compose:

```bash
docker-compose up -d
```

See `docs/DOCKER_SETUP_GUIDE.md` for detailed Docker instructions.

## Usage

### Autonomous Mode

Run the autonomous demonstration:
```bash
python scripts/demo_autonomous_nyx.py
```

This starts the motivational engine which will:
- Monitor system state every 30 seconds
- Generate contextual tasks based on detected conditions
- Execute workflows autonomously through the orchestration system
- Track performance and outcomes in the database

### API Mode

Start the FastAPI server:
```bash
python start_api.py
```

The API will be available at `http://localhost:8000` with endpoints for:
- System status and monitoring
- Manual workflow execution
- Motivational state management

### Dashboard

The web dashboard is available in the `nyx-dashboard/` directory:
```bash
cd nyx-dashboard
npm install
npm run dev
```

Access the dashboard at `http://localhost:3000`

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Your Anthropic API key for LLM integration
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

### Moltbook Integration Setup

To enable social network monitoring:

1. Obtain a Moltbook API key from [moltbook.com](https://www.moltbook.com)
2. Store the API key in the database:
```python
from database.connection import get_sync_session
from database.models import SystemConfig

session = get_sync_session()
config = SystemConfig(
    config_key='moltbook_api_key',
    config_value={'api_key': 'your_moltbook_api_key_here'}
)
session.add(config)
session.commit()
```
3. The social monitoring motivation will automatically activate and NYX will begin monitoring Moltbook

## Documentation

Detailed documentation is available in the `docs/` directory:

- `ARCHITECTURE.md` - System architecture overview
- `DATABASE_SCHEMA.md` - Database structure and relationships
- `DOCKER_SETUP_GUIDE.md` - Docker deployment instructions
- `DEVELOPMENT_STATUS.md` - Current implementation status
- `MOLTBOOK_INTEGRATION_PLAN.md` - Social network integration details

## Project Structure

```
nyx/
├── app/                    # FastAPI application
├── core/                   # Core system components
│   ├── agents/            # Agent implementations
│   ├── motivation/        # Motivational model system
│   ├── orchestrator/      # Orchestration logic
│   └── tools/             # Tool interfaces
├── database/              # Database models and schemas
├── docs/                  # Documentation
├── llm/                   # LLM integration
├── nyx-dashboard/         # Web dashboard (Next.js)
└── scripts/               # Utility scripts
```

## Testing

Run the autonomous system validation:
```bash
python scripts/demo_autonomous_nyx.py
```

This demonstrates 30+ minutes of continuous autonomous operation with task generation and execution.

## Safety and Monitoring

NYX includes several safety mechanisms:
- Resource constraints (CPU, memory, cost limits)
- Circuit breakers for anomalous behavior
- Comprehensive logging and monitoring
- Configurable execution limits

## Contributing

Please refer to `docs/DEVELOPMENT_RULES.md` for development guidelines and contribution instructions.

## License

MIT License - see [LICENSE](LICENSE) file for details.