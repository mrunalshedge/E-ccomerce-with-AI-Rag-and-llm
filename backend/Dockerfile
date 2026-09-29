# ShopSense API. Works on Hugging Face Spaces (Docker), Render, Fly.io, Railway, Cloud Run…
# Needs ~800 MB RAM with the local embedding model (Render's 512 MB free tier is too small).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    EMBEDDING_CACHE_DIR=/app/.models \
    PORT=7860

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the multilingual embedding model into the image: no ~250 MB download on every cold start.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/app/.models')"

COPY . .

# Run as an unprivileged user (uid 1000 is also what Hugging Face Spaces expects).
RUN useradd --uid 1000 --create-home app && chown -R app /app
USER app

EXPOSE 7860
# Apply migrations, then serve. Settings (DB, JWT, Gemini key, CORS, TRUSTED_PROXY_HOPS) come from
# the platform's environment variables / secrets, never from a baked-in .env.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
