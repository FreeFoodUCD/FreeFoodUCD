#!/bin/bash
set -e

echo "🗄️  Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete. Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Made with Bob
