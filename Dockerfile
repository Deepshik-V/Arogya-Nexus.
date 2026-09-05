# Production Dockerfile for Arogya Nexus Backend & Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and data
COPY backend/ ./backend/
COPY docs/ ./docs/
COPY n8n/ ./n8n/
COPY public/ ./public/
COPY .env.example .
COPY README.md .

# Copy built frontend assets
COPY --from=frontend-builder /app/dist ./dist

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
