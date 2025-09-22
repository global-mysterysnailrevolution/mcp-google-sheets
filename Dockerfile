# Use Python 3.11 slim image for better performance and smaller size
FROM python:3.11-slim

# Force rebuild by adding a build argument
ARG BUILD_DATE
ARG BUILD_VERSION=1.0.3

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port (MCP servers typically run on stdio, but we'll expose 8000 for HTTP mode)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden)
CMD ["uv", "run", "python", "-m", "mcp_google_sheets.http_sse_server"]
