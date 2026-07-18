# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# CRITICAL: exec form (array) — Python becomes PID 1 and receives SIGTERM directly.
# Shell form ("python daemon.py") spawns /bin/sh as PID 1, which does NOT forward
# SIGTERM to Python, causing a 10-second forced kill on docker compose stop.
CMD ["python", "daemon.py"]
