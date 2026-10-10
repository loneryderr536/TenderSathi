# Backend image for Railway: the FastAPI app, the agents, and the sample data the demo loader needs.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Download ChromaDB's embedding model now, so the first tender read after a deploy does not wait for it.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm up'])"

COPY backend backend
COPY data data
COPY scripts scripts

# The database and vector memory live here; mount a Railway volume at /storage so they survive redeploys.
ENV STORAGE_DIR=/storage

# Load the sample businesses, demo logins and sample request (safe to run on every start), then serve.
CMD ["sh", "-c", "python scripts/load_demo_data.py && cd backend && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
