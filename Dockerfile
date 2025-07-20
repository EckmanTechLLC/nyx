FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    curl \
    netcat-openbsd \
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
CMD ["python", "-c", "print('🐳 NYX Container Ready\\n📋 Run tests with: python tests/[test_file].py\\n🔧 Interactive mode: docker-compose run --rm nyx bash')"]