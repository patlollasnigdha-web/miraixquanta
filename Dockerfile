FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files, configs, models and datasets
COPY src/ ./src/
COPY configs/ ./configs/
COPY models/ ./models/
COPY NIFTY-50-Stock-Market-Data-main/ ./NIFTY-50-Stock-Market-Data-main/
COPY nifty50-historical-data-main/ ./nifty50-historical-data-main/
COPY *.csv ./

# Ensure writable directories for SQLite database and logs
RUN mkdir -p /app/data /app/logs

# Production environment configuration
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    MIRAI_API_HOST=0.0.0.0 \
    MIRAI_API_PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Production entrypoint
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
