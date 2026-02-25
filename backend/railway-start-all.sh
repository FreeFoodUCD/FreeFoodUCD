#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Migrations complete. Starting all services..."

# Start uvicorn in background
uvicorn app.main:app --host 0.0.0.0 --port $PORT &
UVICORN_PID=$!

# Start celery worker in background
celery -A app.workers.celery_app worker --loglevel=info --pool=solo --queues=celery,scraping,notifications,maintenance &
WORKER_PID=$!

# Start celery beat in background
celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule &
BEAT_PID=$!

echo "All services started (uvicorn=$UVICORN_PID, worker=$WORKER_PID, beat=$BEAT_PID)"

# Exit if ANY process dies — Railway will restart the whole service
wait -n $UVICORN_PID $WORKER_PID $BEAT_PID
echo "A process exited unexpectedly. Shutting down for restart..."
kill $UVICORN_PID $WORKER_PID $BEAT_PID 2>/dev/null
exit 1

# Made with Bob
