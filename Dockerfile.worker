# Dockerfile — Phase 5 Railway Python worker
#
# Why an explicit Dockerfile and not Nixpacks/railpack auto-detection?
#
# The stale root package.json (now deleted in this commit) tricked
# Railway's railpack builder into running `bun install` against a
# fictional Next.js manifest. The actual workload is a Python HTTP
# server (scripts.perception_worker) that ships the Phase 2.5B
# perception pipeline + Phase 4 OBS-03 daily spend report + Phase 5
# manager endpoints (voice / apply / undo / morning-briefing /
# email-intent).
#
# This Dockerfile is the simplest, most predictable build path:
#   - python:3.12-slim base (matches the .venv used in CI + tests)
#   - tesseract-ocr installed at the OS layer (Phase 5 image_ocr.py)
#   - pip install -r requirements.txt (the same one developers use)
#   - Start command runs the worker on Railway's $PORT (default 8000)
#
# Build size sanity: tesseract adds ~80 MB. The full image is ~600 MB,
# acceptable on Railway's Hobby tier.

FROM python:3.12-slim

# --- OS deps -----------------------------------------------------------------
# tesseract-ocr — Phase 5 MNG-03 image OCR fallback path
# libgl1 / libglib2.0-0 — Pillow / OpenCV image-decode runtime needs
# build-essential — psycopg2-binary occasionally needs a compiler on slim
# curl — Railway healthcheck convenience
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        libgl1 \
        libglib2.0-0 \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps -------------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Layer 1: deps — invalidated only when requirements.txt changes
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Layer 2: code — copied last so iterative re-deploys don't reinstall deps
COPY . /app

# Railway injects $PORT at runtime; perception_worker defaults to 8000
EXPOSE 8000

# Health check matches railway.json healthcheckPath = /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" || exit 1

CMD ["python", "-X", "utf8", "-m", "scripts.perception_worker"]
