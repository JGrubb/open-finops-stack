FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY finops ./finops
COPY pytest.ini ./

# Create data directory
RUN mkdir -p /data

# Set environment variables
ENV PYTHONPATH=/app
ENV OPEN_FINOPS_DATA_DIR=/data

# Default command runs the CLI
ENTRYPOINT ["python", "-m", "src.cli.main"]
CMD ["--help"]

# Labels for better Docker Hub integration
LABEL org.opencontainers.image.title="Open FinOps Stack"
LABEL org.opencontainers.image.description="FOCUS-first open source FinOps platform for cloud cost management"
LABEL org.opencontainers.image.source="https://github.com/JGrubb/open-finops-stack"
LABEL org.opencontainers.image.documentation="https://github.com/JGrubb/open-finops-stack/blob/master/README.md"