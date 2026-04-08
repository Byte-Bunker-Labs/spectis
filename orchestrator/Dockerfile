# Stage 1: Build dashboard
FROM node:22-alpine AS dashboard-build
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

# Stage 2: Python API
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY orchestrator/pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy app code
COPY orchestrator/app/ ./app/
COPY orchestrator/alembic.ini ./
COPY orchestrator/alembic/ ./alembic/

# Copy built dashboard into static dir
COPY --from=dashboard-build /dashboard/dist/ ./app/static/

# Create logs dir
RUN mkdir -p /app/logs

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
