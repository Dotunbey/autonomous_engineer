# Use official Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (e.g., for Docker-in-Docker sandboxing if needed)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

# Expose API and Metrics ports
EXPOSE 8000 9090

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "autonomous_engineer.api.server:app", "--host", "0.0.0.0", "--port", "8000"] 