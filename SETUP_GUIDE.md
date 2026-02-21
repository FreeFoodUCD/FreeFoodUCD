# FreeFood UCD - Setup Guide

This guide will help you set up and run the FreeFood UCD platform locally.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker & Docker Compose** - [Download](https://www.docker.com/products/docker-desktop)
- **Git** - [Download](https://git-scm.com/downloads)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/freefood-ucd.git
cd freefood-ucd
```

### 2. Start Infrastructure Services

Start PostgreSQL, Redis, and MinIO using Docker Compose:

```bash
cd backend
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

You should see:
- `freefood-postgres` on port 5432
- `freefood-redis` on port 6379
- `freefood-minio` on ports 9000 and 9001

### 3. Set Up Backend

#### Create Virtual Environment

```bash
# From backend directory
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

#### Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# At minimum, update:
# - INSTAGRAM_USERNAME
# - INSTAGRAM_PASSWORD
# - TWILIO credentials (for WhatsApp)
# - SENDGRID_API_KEY (for email)
```

#### Initialize Database

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

#### Seed Database (Optional)

```bash
# Create a seed script
python -c "
from app.db.base import async_session_maker
from app.db.models import Society
import asyncio

async def seed():
    async with async_session_maker() as session:
        societies = [
            Society(name='UCD Law Society', instagram_handle='ucdlawsoc'),
            Society(name='UCD Commerce Society', instagram_handle='ucdcommsoc'),
            Society(name='UCD Drama Society', instagram_handle='ucddramasoc'),
            Society(name='UCD Computer Science Society', instagram_handle='ucdcompsoc'),
            Society(name='UCD Students\' Union', instagram_handle='ucdsu'),
        ]
        session.add_all(societies)
        await session.commit()
        print('Seeded 5 societies')

asyncio.run(seed())
"
```

#### Run Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### 4. Set Up Frontend

```bash
# Open new terminal
cd frontend

# Initialize Next.js project
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir

# Install additional dependencies
npm install zustand @tanstack/react-query date-fns
npm install -D @types/node

# Run development server
npm run dev
```

The frontend will be available at http://localhost:3000

---

## 🔧 Development Workflow

### Running All Services

#### Terminal 1: Infrastructure
```bash
cd backend
docker-compose up
```

#### Terminal 2: Backend API
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

#### Terminal 3: Frontend
```bash
cd frontend
npm run dev
```

### Stopping Services

```bash
# Stop Docker services
cd backend
docker-compose down

# Stop backend (Ctrl+C in terminal)
# Stop frontend (Ctrl+C in terminal)
```

---

## 🧪 Testing the API

### Using the Interactive Docs

1. Open http://localhost:8000/docs
2. Try the endpoints:
   - `GET /api/v1/societies` - List all societies
   - `GET /api/v1/events` - List events
   - `POST /api/v1/users/signup` - Create a user

### Using cURL

```bash
# Get societies
curl http://localhost:8000/api/v1/societies

# Get events for today
curl "http://localhost:8000/api/v1/events?date=today"

# Create a user
curl -X POST http://localhost:8000/api/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+353871234567", "email": "test@ucd.ie"}'
```

---

## 📊 Database Management

### Access PostgreSQL

```bash
# Using Docker
docker exec -it freefood-postgres psql -U freefood -d freefood

# Common commands:
\dt          # List tables
\d events    # Describe events table
SELECT * FROM societies;
```

### Access Redis

```bash
# Using Docker
docker exec -it freefood-redis redis-cli

# Common commands:
KEYS *       # List all keys
GET key      # Get value
FLUSHALL     # Clear all data (careful!)
```

### Access MinIO Console

Open http://localhost:9001 in your browser:
- Username: `minioadmin`
- Password: `minioadmin`

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # or :5432, :6379, etc.

# Kill process
kill -9 <PID>
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Alembic Migration Issues

```bash
# Reset migrations (WARNING: deletes data)
alembic downgrade base
alembic upgrade head

# Or drop and recreate database
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

---

## 📝 Next Steps

Now that your development environment is set up:

1. **Review the Architecture** - Read [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Understand the Design** - Read [FRONTEND_DESIGN_SPEC.md](FRONTEND_DESIGN_SPEC.md)
3. **Follow Implementation Guide** - Read [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
4. **Start Building** - Begin with the scraper service or frontend components

---

## 🔐 Security Notes

### For Development

- The `.env.example` file contains placeholder values
- Never commit your actual `.env` file
- Use strong passwords for production
- Keep API keys secure

### Instagram Account

- Create a dedicated monitoring account
- Enable 2FA
- Don't use your personal account
- Age the account naturally (2-3 weeks before heavy use)

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)

---

## 💬 Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review the logs: `docker-compose logs`
3. Open an issue on GitHub
4. Check existing issues for solutions

---

**Happy Coding! 🍕**