# NYX Docker Setup and Execution Guide

## Overview

Due to NYX's growing autonomous capabilities and upcoming motivational model, **ALL NYX testing and execution MUST occur within Docker containers** for safety and isolation.

## Prerequisites

1. **Docker Desktop** or **Docker Engine** installed
2. **Docker Compose** (usually included with Docker Desktop)
3. **Access to NYX project directory** (`/home/etl/projects/nyx`)

---

## Step 1: Create Docker Configuration Files

### Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV NYX_ENVIRONMENT=docker

# Create non-root user for security
RUN useradd -m -s /bin/bash nyxuser && chown -R nyxuser:nyxuser /app
USER nyxuser

# Default command (can be overridden)
CMD ["python", "-c", "print('NYX Container Ready - Run tests with: python tests/[test_file].py')"]
```

### Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  nyx:
    build: .
    container_name: nyx-container
    environment:
      - PYTHONPATH=/app
      - DATABASE_URL=${DATABASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - .:/app  # Mount project directory
    network_mode: "host"  # Access host database
    stdin_open: true
    tty: true
    working_dir: /app
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    
  # Optional: Run PostgreSQL in container if needed
  postgres:
    image: postgres:15
    container_name: nyx-postgres
    environment:
      - POSTGRES_DB=nyx
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=Aim33IsReal!
    ports:
      - "5433:5432"  # Different port to avoid conflicts
    volumes:
      - postgres_data:/var/lib/postgresql/data
    profiles:
      - database  # Only start with --profile database

volumes:
  postgres_data:
```

### Create `.env` file in project root:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:Aim33IsReal!@192.168.50.10:5432/nyx

# API Keys
ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here

# Configuration
LOG_LEVEL=INFO
```

**IMPORTANT**: Replace `your_actual_anthropic_api_key_here` with your real Anthropic API key.

### Create `.dockerignore` file:

```
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.git/
.pytest_cache/
node_modules/
*.log
.DS_Store
venv/
.venv/
```

---

## Step 2: Build and Prepare Docker Environment

### 1. Navigate to NYX project directory:
```bash
cd /home/etl/projects/nyx
```

### 2. Fix Docker permissions (if you get permission errors):
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Refresh group membership
newgrp docker

# Start Docker service if needed
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. Update your `.env` file with real credentials:
```bash
# Edit .env file with your actual Anthropic API key
nano .env
```

**Replace `your_actual_anthropic_api_key_here` with your real API key.**

### 4. Build the Docker image:
```bash
docker-compose build
```

### 5. Verify the build succeeded:
```bash
docker images | grep nyx
```

---

## Step 3: Running NYX Tests in Docker

### Method 1: Interactive Container (Recommended)

#### Start an interactive NYX container:
```bash
docker-compose run --rm nyx bash
```

This gives you a bash shell inside the container where you can:
- Run any test script: `python tests/tools/test_tool_integration.py`
- Execute individual components: `python -m core.learning.scorer`
- Debug issues: `python -c "from database.connection import db_manager; print('DB OK')"`

#### Exit the container when done:
```bash
exit
```

### Method 2: Single Command Execution

#### Run a specific test:
```bash
docker-compose run --rm nyx python tests/tools/test_tool_integration.py
```

#### Run database connection test:
```bash
docker-compose run --rm nyx python -c "
import asyncio
from database.connection import db_manager

async def test_db():
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text('SELECT 1'))
            print('✅ Database connection successful')
            return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

asyncio.run(test_db())
"
```

#### Run learning system test:
```bash
docker-compose run --rm nyx python tests/learning/test_learning_system.py
```

### Method 3: Docker Compose Profiles

#### Start with built-in PostgreSQL (if needed):
```bash
docker-compose --profile database up -d
```

#### Run tests against containerized database:
```bash
docker-compose --profile database run --rm nyx python tests/tools/test_tool_integration.py
```

---

## Step 4: Monitoring and Debugging

### View container logs:
```bash
docker-compose logs nyx
```

### Check running containers:
```bash
docker ps
```

### Access container filesystem (for debugging):
```bash
docker-compose run --rm nyx bash
ls -la /app
```

### Monitor resource usage:
```bash
docker stats nyx-container
```

### Clean up containers and images:
```bash
# Remove containers
docker-compose down

# Remove images (if needed)
docker rmi $(docker images | grep nyx | awk '{print $3}')
```

---

## Step 5: Safety Protocols

### Container Isolation Verification

#### Verify NYX cannot access host system:
```bash
docker-compose run --rm nyx bash -c "
echo 'Testing container isolation...'
ls /etc/passwd 2>/dev/null && echo '⚠️ WARNING: Can access host files' || echo '✅ Container properly isolated'
whoami
id
"
```

#### Test file system boundaries:
```bash
docker-compose run --rm nyx bash -c "
echo 'Testing file system access...'
ls /home/ 2>/dev/null && echo '⚠️ Can access /home' || echo '✅ /home properly isolated'
ls /root/ 2>/dev/null && echo '⚠️ Can access /root' || echo '✅ /root properly isolated'
"
```

### Network Isolation Testing

#### Test network restrictions:
```bash
docker-compose run --rm nyx bash -c "
echo 'Testing network access...'
curl -s --connect-timeout 5 https://www.google.com > /dev/null && echo '✅ Internet access available for API calls' || echo '❌ No internet access'
"
```

---

## Step 6: Production Considerations

### Resource Limits (Add to docker-compose.yml):

```yaml
services:
  nyx:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Security Enhancements:

```yaml
services:
  nyx:
    # ... existing configuration ...
    security_opt:
      - no-new-privileges:true
    read_only: false  # NYX needs write access for logs/temp files
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

---

## Troubleshooting

### Common Issues:

#### Database Connection Failed:
```bash
# Check if PostgreSQL is accessible from container
docker-compose run --rm nyx bash -c "nc -zv 192.168.50.10 5432"
```

#### Python Import Errors:
```bash
# Verify PYTHONPATH and project structure
docker-compose run --rm nyx bash -c "
echo \$PYTHONPATH
ls -la /app/core/
python -c 'import sys; print(sys.path)'
"
```

#### API Key Issues:
```bash
# Check environment variables
docker-compose run --rm nyx bash -c "
env | grep -E '(ANTHROPIC|DATABASE)' | sed 's/=.*/=***REDACTED***/'
"
```

#### Permission Errors:
```bash
# Check file ownership
docker-compose run --rm nyx bash -c "
whoami
ls -la /app/tests/
"
```

---

## Emergency Procedures

### Force Stop All NYX Containers:
```bash
docker stop $(docker ps -q --filter ancestor=nyx)
docker kill $(docker ps -q --filter ancestor=nyx) 2>/dev/null || true
```

### Complete NYX Environment Reset:
```bash
docker-compose down --volumes --remove-orphans
docker system prune -f
docker volume prune -f
```

### Backup Container State:
```bash
# Create container snapshot
docker commit nyx-container nyx-snapshot:$(date +%Y%m%d_%H%M%S)
```

---

## Summary - Quick Start Commands

After completing the setup above:

1. **Fix permissions** (if needed): `sudo usermod -aG docker $USER && newgrp docker`
2. **Edit .env file**: Replace `your_actual_anthropic_api_key_here` with your real API key
3. **Build Environment**: `docker-compose build`
4. **Run Tests**: `docker-compose run --rm nyx python tests/tools/test_tool_integration.py`
5. **Interactive Mode**: `docker-compose run --rm nyx bash`
6. **Monitor**: `docker-compose logs nyx`
7. **Clean Up**: `docker-compose down`

### Common Test Commands:
```bash
# Tool integration test (validates basic functionality)
docker-compose run --rm nyx python tests/tools/test_tool_integration.py

# Database connection test
docker-compose run --rm nyx python tests/scripts/test_database_connection.py

# Learning system test
docker-compose run --rm nyx python tests/scripts/test_learning_system.py

# Top-level orchestrator test
docker-compose run --rm nyx python tests/scripts/test_top_level_orchestrator.py
```

**Remember**: NYX MUST NEVER be executed outside of containers due to its autonomous capabilities and upcoming motivational model implementation.