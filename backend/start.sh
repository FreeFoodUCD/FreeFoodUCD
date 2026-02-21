#!/bin/bash

# FreeFoodUCD Backend Startup Script
# This script starts all required services for the backend

set -e  # Exit on error

echo "🚀 Starting FreeFoodUCD Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your credentials"
    exit 1
fi

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL..."
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL is not running. Starting it..."
    if command -v brew &> /dev/null; then
        brew services start postgresql@15
        sleep 2
    else
        echo "❌ Please start PostgreSQL manually"
        exit 1
    fi
fi

# Check if Redis is running
echo "🔍 Checking Redis..."
if ! redis-cli ping &> /dev/null; then
    echo "⚠️  Redis is not running. Starting it..."
    if command -v brew &> /dev/null; then
        brew services start redis
        sleep 2
    else
        echo "❌ Please start Redis manually"
        exit 1
    fi
fi

# Run database migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

echo ""
echo "✅ All services ready!"
echo ""
echo "Starting backend services..."
echo "  - FastAPI: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI server
echo "🌐 Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Wait a bit for FastAPI to start
sleep 3

# Start Celery worker
echo "👷 Starting Celery worker..."
celery -A app.workers.celery_app worker --loglevel=info &

# Wait a bit for worker to start
sleep 2

# Start Celery beat (scheduler)
echo "⏰ Starting Celery beat scheduler..."
celery -A app.workers.celery_app beat --loglevel=info &

# Wait for all background processes
wait

# Made with Bob
