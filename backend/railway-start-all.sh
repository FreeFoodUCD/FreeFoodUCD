#!/bin/bash
set -e

echo "🗄️  Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete. Starting all services..."

# Start uvicorn in background
uvicorn app.main:app --host 0.0.0.0 --port $PORT &

# Start celery worker in background with solo pool (fixes asyncio event loop issues)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo --queues=celery,scraping,notifications,maintenance &

# Start celery beat in foreground (this keeps the script running)
exec celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule

# Made with Bob
