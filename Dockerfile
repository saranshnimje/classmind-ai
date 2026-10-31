# syntax=docker/dockerfile:1

# ---- Frontend build -------------------------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Runtime --------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CLASSMIND_DATA_DIR=/app/data

WORKDIR /app

# OpenCV headless and NumPy may need these shared libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY pytest.ini ./
COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN mkdir -p /app/data
EXPOSE 8000

# Core image uses OpenCV HOG + energy VAD. Add requirements-vision.txt to the
# build if you need YOLO/Silero (large PyTorch download).
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
