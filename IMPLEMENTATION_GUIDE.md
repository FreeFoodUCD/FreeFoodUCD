# FreeFood UCD - Implementation Guide

## 🚀 Getting Started

This guide provides step-by-step instructions for implementing FreeFood UCD from scratch.

---

## 📋 Prerequisites

### Required Software
- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose
- Git

### Required Accounts
- Instagram account (for monitoring)
- Twilio account (WhatsApp API)
- SendGrid account (Email)
- AWS account (S3 for screenshots) or MinIO for local

### Development Tools
- VS Code or PyCharm
- Postman or Insomnia (API testing)
- pgAdmin or DBeaver (database management)

---

## 🏗️ Phase 1: Project Setup (Day 1)

### 1.1 Create Project Structure

```bash
# Create main directory
mkdir freefood-ucd
cd freefood-ucd

# Initialize git
git init
echo "# FreeFood UCD" > README.md

# Create directory structure
mkdir -p backend/{app/{api/v1/endpoints,core,db,services/{scraper,nlp,notifications},workers},tests,alembic}
mkdir -p scraper-service/src/{instagram,queue,storage}
mkdir -p frontend/src/{app,components/{ui},lib,types}
mkdir -p docs
```

### 1.2 Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create requirements.txt
cat > requirements.txt << EOF
# FastAPI
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# Cache & Queue
redis==5.0.1
celery==5.3.6
kombu==5.3.5

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP Client
aiohttp==3.9.1
httpx==0.26.0

# Notifications
twilio==8.11.1
sendgrid==6.11.0

# Scraping (for scraper service)
playwright==1.41.0
beautifulsoup4==4.12.3

# Utilities
python-dotenv==1.0.0
pytz==2024.1

# Monitoring
prometheus-client==0.19.0
sentry-sdk==1.39.2

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
EOF

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 1.3 Environment Configuration

```bash
# Create .env file
cat > .env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://freefood:password@localhost:5432/freefood
DATABASE_URL_SYNC=postgresql://freefood:password@localhost:5432/freefood

# Redis
REDIS_URL=redis://localhost:6379/0

# Instagram Credentials
INSTAGRAM_USERNAME=your_monitoring_account
INSTAGRAM_PASSWORD=your_secure_password

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886

# SendGrid (Email)
SENDGRID_API_KEY=your_api_key
SENDGRID_FROM_EMAIL=alerts@freefooducd.ie

# AWS S3 (or MinIO for local)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=freefood-screenshots
AWS_REGION=eu-west-1

# Application
SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
ENVIRONMENT=development
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
EOF

# Add .env to .gitignore
echo ".env" >> .gitignore
echo "venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
```

### 1.4 Database Setup

```bash
# Start PostgreSQL (using Docker)
docker run -d \
  --name freefood-postgres \
  -e POSTGRES_DB=freefood \
  -e POSTGRES_USER=freefood \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16-alpine

# Start Redis
docker run -d \
  --name freefood-redis \
  -p 6379:6379 \
  redis:7-alpine
```

---

## 🗄️ Phase 2: Database Layer (Days 2-3)

### 2.1 SQLAlchemy Models

Create [`backend/app/db/base.py`](backend/app/db/base.py:1):

```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
```

Create [`backend/app/db/models.py`](backend/app/db/models.py:1):

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class Society(Base):
    __tablename__ = "societies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    instagram_handle = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    scrape_posts = Column(Boolean, default=True)
    scrape_stories = Column(Boolean, default=True)
    last_post_check = Column(DateTime(timezone=True))
    last_story_check = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    posts = relationship("Post", back_populates="society")
    stories = relationship("Story", back_populates="society")
    events = relationship("Event", back_populates="society")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id"))
    instagram_post_id = Column(String(255), unique=True, index=True)
    caption = Column(Text)
    source_url = Column(Text)
    media_urls = Column(JSONB)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    is_free_food = Column(Boolean, default=False, index=True)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    society = relationship("Society", back_populates="posts")

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id"))
    story_text = Column(Text)
    story_timestamp = Column(DateTime(timezone=True))
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_free_food = Column(Boolean, default=False)
    content_hash = Column(String(64), unique=True, index=True)
    screenshot_url = Column(Text)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    society = relationship("Society", back_populates="stories")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id"))
    title = Column(String(500))
    description = Column(Text)
    location = Column(String(255))
    location_building = Column(String(100))
    location_room = Column(String(50))
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True))
    source_type = Column(String(20), CheckConstraint("source_type IN ('post', 'story')"))
    source_id = Column(UUID(as_uuid=True))
    confidence_score = Column(Float)
    raw_text = Column(Text)
    extracted_data = Column(JSONB)
    notified = Column(Boolean, default=False, index=True)
    notification_sent_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    society = relationship("Society", back_populates="events")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)
    phone_number = Column(String(20), unique=True, index=True)
    whatsapp_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    notification_preferences = Column(JSONB, default={"whatsapp": True, "email": True})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserSocietyPreference(Base):
    __tablename__ = "user_society_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"), primary_key=True)
    notify = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    notification_type = Column(String(20))
    status = Column(String(20))
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id"))
    scrape_type = Column(String(20))
    status = Column(String(20))
    items_found = Column(Integer)
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

### 2.2 Alembic Setup

```bash
cd backend

# Initialize Alembic
alembic init alembic

# Edit alembic.ini - update sqlalchemy.url
# sqlalchemy.url = postgresql://freefood:password@localhost:5432/freefood
```

Edit [`backend/alembic/env.py`](backend/alembic/env.py:1):

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.base import Base
from app.db.models import *  # Import all models
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create initial migration:

```bash
# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### 2.3 Seed Data

Create [`backend/app/db/seed.py`](backend/app/db/seed.py:1):

```python
from sqlalchemy.orm import Session
from app.db.models import Society

def seed_societies(db: Session):
    societies = [
        {"name": "UCD Law Society", "instagram_handle": "ucdlawsoc"},
        {"name": "UCD Commerce Society", "instagram_handle": "ucdcommsoc"},
        {"name": "UCD Drama Society", "instagram_handle": "ucddramasoc"},
        {"name": "UCD Computer Science Society", "instagram_handle": "ucdcompsoc"},
        {"name": "UCD Students' Union", "instagram_handle": "ucdsu"},
        # Add more societies
    ]
    
    for society_data in societies:
        society = Society(**society_data)
        db.add(society)
    
    db.commit()
    print(f"Seeded {len(societies)} societies")

if __name__ == "__main__":
    from app.db.base import SessionLocal
    db = SessionLocal()
    seed_societies(db)
    db.close()
```

---

## 🔧 Phase 3: Core Backend (Days 4-5)

### 3.1 Configuration

Create [`backend/app/core/config.py`](backend/app/core/config.py:1):

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    
    # Redis
    REDIS_URL: str
    
    # Instagram
    INSTAGRAM_USERNAME: str
    INSTAGRAM_PASSWORD: str
    
    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    
    # SendGrid
    SENDGRID_API_KEY: str
    SENDGRID_FROM_EMAIL: str
    
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET: str
    AWS_REGION: str = "eu-west-1"
    
    # Application
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 3.2 FastAPI Application

Create [`backend/app/main.py`](backend/app/main.py:1):

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title="FreeFood UCD API",
    description="API for FreeFood UCD platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3.3 API Endpoints

Create [`backend/app/api/v1/endpoints/events.py`](backend/app/api/v1/endpoints/events.py:1):

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID

from app.db.base import get_db
from app.db.models import Event, Society
from pydantic import BaseModel

router = APIRouter()

class EventResponse(BaseModel):
    id: UUID
    title: str
    location: str
    start_time: datetime
    society_name: str
    source_type: str
    
    class Config:
        from_attributes = True

@router.get("/events", response_model=List[EventResponse])
async def get_events(
    date_filter: Optional[date] = Query(None, alias="date"),
    society_id: Optional[UUID] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(Event).join(Society).where(Event.is_active == True)
    
    if date_filter:
        query = query.where(Event.start_time >= date_filter)
    
    if society_id:
        query = query.where(Event.society_id == society_id)
    
    query = query.order_by(Event.start_time.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return events
```

Create [`backend/app/api/v1/api.py`](backend/app/api/v1/api.py:1):

```python
from fastapi import APIRouter
from app.api.v1.endpoints import events

api_router = APIRouter()
api_router.include_router(events.router, tags=["events"])
```

---

## 🕷️ Phase 4: Instagram Scraper Service (Days 6-8)

### 4.1 Scraper Service Setup

```bash
cd scraper-service

# Create requirements.txt
cat > requirements.txt << EOF
playwright==1.41.0
aiohttp==3.9.1
redis==5.0.1
python-dotenv==1.0.0
pillow==10.2.0
boto3==1.34.34
EOF

pip install -r requirements.txt
playwright install chromium
```

### 4.2 Browser Manager

Create [`scraper-service/src/instagram/browser.py`](scraper-service/src/instagram/browser.py:1):

```python
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import random
import asyncio
from typing import Optional

class InstagramBrowser:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    
    async def initialize(self):
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={'width': 1920, 'height': 1080},
            locale='en-GB',
            timezone_id='Europe/Dublin'
        )
        
        # Anti-detection
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await self.context.new_page()
    
    async def random_delay(self, min_ms=1000, max_ms=3000):
        await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))
    
    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
```

### 4.3 Story Scraper

Create [`scraper-service/src/instagram/story_scraper.py`](scraper-service/src/instagram/story_scraper.py:1):

```python
import hashlib
from typing import List, Dict, Optional
from playwright.async_api import Page
from datetime import datetime

class StoryScraper:
    def __init__(self, browser):
        self.browser = browser
    
    async def scrape_stories(self, username: str) -> List[Dict]:
        stories = []
        page = self.browser.page
        
        try:
            # Navigate to profile
            await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.browser.random_delay()
            
            # Check for story ring
            story_ring = await page.query_selector('canvas[aria-label*="story"]')
            if not story_ring:
                return stories
            
            # Click story
            await story_ring.click()
            await page.wait_for_selector('[role="dialog"]', timeout=5000)
            
            # Extract all stories
            while True:
                story_data = await self._extract_story_content(page)
                if story_data:
                    stories.append(story_data)
                
                # Check for next story
                next_button = await page.query_selector('button[aria-label="Next"]')
                if not next_button:
                    break
                
                await next_button.click()
                await self.browser.random_delay(500, 1000)
            
        except Exception as e:
            print(f"Error scraping stories for {username}: {e}")
        
        return stories
    
    async def _extract_story_content(self, page: Page) -> Optional[Dict]:
        try:
            # Extract text overlays
            text_elements = await page.query_selector_all('[dir="auto"]')
            texts = []
            for el in text_elements:
                text = await el.inner_text()
                if text:
                    texts.append(text)
            
            # Extract location
            location_el = await page.query_selector('[aria-label*="location"]')
            location = await location_el.inner_text() if location_el else None
            
            # Screenshot
            screenshot = await page.screenshot()
            
            # Create content hash
            content = " ".join(texts)
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return {
                "text": content,
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "content_hash": content_hash,
                "screenshot": screenshot
            }
        except Exception as e:
            print(f"Error extracting story content: {e}")
            return None
```

---

## 📝 Next Steps Summary

The implementation guide continues with:

- **Phase 5**: NLP Extraction Layer
- **Phase 6**: Notification System
- **Phase 7**: Celery Workers & Scheduling
- **Phase 8**: Frontend Implementation
- **Phase 9**: Docker & Deployment
- **Phase 10**: Testing & Monitoring

Each phase builds on the previous one, creating a complete, production-ready system.

---

## 🎯 Quick Start Commands

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Celery Worker
celery -A app.workers.celery_app worker --loglevel=info

# Celery Beat
celery -A app.workers.celery_app beat --loglevel=info

# Frontend
cd frontend
npm run dev

# Docker (all services)
docker-compose up
```

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Playwright Python](https://playwright.dev/python/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)

---

This guide provides a solid foundation. Each component can be expanded based on specific requirements and learnings during development.