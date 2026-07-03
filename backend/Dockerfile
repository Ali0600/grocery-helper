FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Migrations run at startup (app/migrations.py -> alembic upgrade head), so the
# alembic/ tree must be in the image. alembic.ini is dev-CLI-only (not needed here).
COPY alembic ./alembic

# Run as a non-root user (standard hardening). /app stays writable because the
# ephemeral SQLite file (grocery.db) is created in the workdir at runtime.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000
# Bind to $PORT when the host injects one (Render sets it, default 10000); fall back
# to 8000 for local runs / docker-compose. Shell form so the var is expanded.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
