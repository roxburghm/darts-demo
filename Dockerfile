# --- Stage 1: Build frontend ---
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Production image ---
FROM python:3.12-slim

# System deps for darts/pyod compiled extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# HuggingFace cache dir (persisted via volume at /app/data)
ENV HF_HUB_CACHE=/app/data/hf_cache

# Install Python dependencies (copy app code first so pyproject.toml can find packages)
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir ".[torch]" && rm -rf /root/.cache

# Copy built frontend into /app/static (served by FastAPI in production)
COPY --from=frontend-build /build/dist ./static

# Create data directories
RUN mkdir -p data/uploads data/parsed data/results

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Single worker — darts models are CPU-bound and memory-heavy
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
