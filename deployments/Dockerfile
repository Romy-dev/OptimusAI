FROM python:3.12-slim

WORKDIR /code

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir ".[dev]" || \
    pip install --no-cache-dir \
      "fastapi[standard]>=0.115" \
      "sqlalchemy[asyncio]>=2.0" \
      "alembic>=1.14" \
      "asyncpg>=0.30" \
      "pydantic>=2.10" \
      "pydantic-settings>=2.6" \
      "redis>=5.2" \
      "arq>=0.26" \
      "httpx>=0.28" \
      "python-jose[cryptography]>=3.3" \
      "passlib[bcrypt]>=1.7" \
      "bcrypt<5" \
      "python-multipart>=0.0.18" \
      "boto3>=1.35" \
      "pillow>=11.0" \
      "pgvector>=0.3" \
      "structlog>=24.4" \
      "jinja2>=3.1" \
      "cryptography>=44.0" \
      "pymupdf>=1.25" \
      "python-docx>=1.1" \
      "edge-tts>=7.0" \
      "faster-whisper>=1.0"

# App code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
