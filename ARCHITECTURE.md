# FreeFood UCD - System Architecture

## 🏗️ High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Next.js Frontend]
        A1[Mobile Browser]
        A2[Desktop Browser]
    end
    
    subgraph "API Gateway"
        B[FastAPI Backend]
        B1[REST Endpoints]
        B2[WebSocket Server]
    end
    
    subgraph "Scraping Microservice"
        C[Instagram Scraper Service]
        C1[Post Monitor]
        C2[Story Monitor]
        C3[Session Manager]
    end
    
    subgraph "Processing Pipeline"
        D[Event Processor]
        D1[NLP Extractor]
        D2[Deduplication Engine]
        D3[Event Validator]
    end
    
    subgraph "Notification Service"
        E[Notification Manager]
        E1[WhatsApp Handler]
        E2[Email Handler]
        E3[Queue Manager]
    end
    
    subgraph "Data Layer"
        F[(PostgreSQL)]
        G[(Redis Cache)]
        H[S3/Object Storage]
    end
    
    subgraph "Background Workers"
        I[Celery Workers]
        I1[Scraping Jobs]
        I2[Notification Jobs]
        I3[Cleanup Jobs]
    end
    
    subgraph "Message Queue"
        J[RabbitMQ/Redis]
    end
    
    A --> B
    B --> F
    B --> G
    C --> J
    J --> D
    D --> F
    D --> E
    E --> I2
    I1 --> C
    I --> G
    C --> H
    D --> H
```

---

## 🎯 Core Design Principles

### 1. **Microservice Isolation**
- Story scraper runs independently
- Can fail/restart without affecting main system
- Separate health monitoring and alerting
- Independent scaling

### 2. **Event-Driven Architecture**
- Loose coupling between services
- Asynchronous processing
- Easy to add new consumers
- Fault-tolerant by design

### 3. **Fail-Safe Defaults**
- Graceful degradation
- Circuit breakers for external services
- Retry mechanisms with exponential backoff
- Dead letter queues for failed messages

### 4. **Data Integrity**
- Idempotent operations
- Content-based deduplication
- Audit trails for all actions
- Soft deletes for compliance

---

## 📦 Service Breakdown

### **1. FastAPI Backend** (Port 8000)

**Responsibilities:**
- REST API endpoints
- User authentication
- Event CRUD operations
- Society management
- User preferences
- WebSocket connections for real-time updates

**Key Endpoints:**
```
GET    /api/v1/events              # List events with filters
GET    /api/v1/events/{id}         # Get event details
GET    /api/v1/societies           # List societies
POST   /api/v1/users/signup        # User registration
PUT    /api/v1/users/preferences   # Update preferences
GET    /api/v1/health              # Health check
```

**Tech Stack:**
- FastAPI 0.109+
- SQLAlchemy 2.0 (async)
- Pydantic v2
- Python 3.11+

---

### **2. Instagram Scraper Service** (Port 8001)

**Responsibilities:**
- Instagram authentication
- Post scraping
- Story scraping
- Rate limiting
- Session management
- Screenshot capture

**Architecture:**
```
scraper-service/
├── src/
│   ├── instagram/
│   │   ├── browser.py          # Playwright browser management
│   │   ├── login.py            # Authentication handler
│   │   ├── post_scraper.py     # Feed post scraping
│   │   └── story_scraper.py    # Story scraping
│   ├── queue/
│   │   ├── consumer.py         # Consume scraping jobs
│   │   └── publisher.py        # Publish results
│   ├── storage/
│   │   └── s3_client.py        # Screenshot storage
│   └── main.py                 # Service entry point
```

**Communication:**
- Consumes: `scraping.jobs` queue
- Publishes: `scraping.results` queue
- Stores: Screenshots in S3/MinIO

**Anti-Detection Measures:**
```python
# Rotating user agents
# Random delays (1-3s between actions)
# Human-like scrolling patterns
# Session persistence
# Proxy rotation (optional)
# Browser fingerprint randomization
```

---

### **3. Event Processor Service**

**Responsibilities:**
- Consume raw scraping results
- NLP extraction (time, date, location)
- Event validation
- Deduplication
- Confidence scoring
- Trigger notifications

**Processing Pipeline:**
```
Raw Content → Keyword Filter → NLP Extraction → Validation → Deduplication → Save Event → Notify
```

**NLP Components:**
```python
# Time extraction
- Regex patterns for times (6pm, 18:00, etc.)
- Relative time parsing (in 2 hours, etc.)

# Date extraction
- Today/tomorrow detection
- Weekday parsing
- Date format parsing (dd/mm, mm/dd)

# Location extraction
- UCD building database matching
- Room number extraction
- NER for unknown locations
```

---

### **4. Notification Service**

**Responsibilities:**
- Queue management
- WhatsApp message sending (Twilio)
- Email sending (SendGrid/Resend)
- Delivery tracking
- Retry logic
- User preference filtering

**Message Flow:**
```
Event Created → Filter Users → Queue Messages → Send (WhatsApp/Email) → Log Result
```

**Rate Limiting:**
- WhatsApp: 1 msg/sec per user
- Email: 100 msg/sec (SendGrid limit)
- Batch processing for efficiency

---

## 🗄️ Database Schema

### **Core Tables**

#### `societies`
```sql
id              UUID PRIMARY KEY
name            VARCHAR(255)
instagram_handle VARCHAR(100) UNIQUE
is_active       BOOLEAN DEFAULT true
scrape_posts    BOOLEAN DEFAULT true
scrape_stories  BOOLEAN DEFAULT true
last_post_check TIMESTAMP
last_story_check TIMESTAMP
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### `posts` (Raw Data)
```sql
id                UUID PRIMARY KEY
society_id        UUID REFERENCES societies
instagram_post_id VARCHAR(255) UNIQUE
caption           TEXT
source_url        TEXT
media_urls        JSONB
detected_at       TIMESTAMP
is_free_food      BOOLEAN
processed         BOOLEAN
created_at        TIMESTAMP
```

#### `stories` (Raw Data - Partitioned)
```sql
id              UUID PRIMARY KEY
society_id      UUID REFERENCES societies
story_text      TEXT
story_timestamp TIMESTAMP
detected_at     TIMESTAMP
expires_at      TIMESTAMP
is_free_food    BOOLEAN
content_hash    VARCHAR(64) UNIQUE
screenshot_url  TEXT
processed       BOOLEAN
created_at      TIMESTAMP
```

**Partitioning Strategy:**
```sql
-- Daily partitions, auto-drop after 7 days
CREATE TABLE stories_2024_01_15 PARTITION OF stories
    FOR VALUES FROM ('2024-01-15') TO ('2024-01-16');
```

#### `events` (Processed Data)
```sql
id                UUID PRIMARY KEY
society_id        UUID REFERENCES societies
title             VARCHAR(500)
description       TEXT
location          VARCHAR(255)
location_building VARCHAR(100)
location_room     VARCHAR(50)
start_time        TIMESTAMP
end_time          TIMESTAMP
source_type       VARCHAR(20) -- 'post' or 'story'
source_id         UUID
confidence_score  FLOAT
raw_text          TEXT
extracted_data    JSONB
notified          BOOLEAN
notification_sent_at TIMESTAMP
is_active         BOOLEAN
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

#### `users`
```sql
id                      UUID PRIMARY KEY
email                   VARCHAR(255) UNIQUE
phone_number            VARCHAR(20) UNIQUE
whatsapp_verified       BOOLEAN
email_verified          BOOLEAN
notification_preferences JSONB
is_active               BOOLEAN
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

#### `user_society_preferences`
```sql
user_id     UUID REFERENCES users
society_id  UUID REFERENCES societies
notify      BOOLEAN
created_at  TIMESTAMP
PRIMARY KEY (user_id, society_id)
```

#### `notification_logs` (Audit Trail)
```sql
id                UUID PRIMARY KEY
event_id          UUID REFERENCES events
user_id           UUID REFERENCES users
notification_type VARCHAR(20)
status            VARCHAR(20)
sent_at           TIMESTAMP
error_message     TEXT
```

#### `scraping_logs` (Monitoring)
```sql
id            UUID PRIMARY KEY
society_id    UUID REFERENCES societies
scrape_type   VARCHAR(20)
status        VARCHAR(20)
items_found   INTEGER
error_message TEXT
duration_ms   INTEGER
created_at    TIMESTAMP
```

---

## 🔄 Data Flow

### **1. Scraping Flow**

```
Celery Beat (Scheduler)
    ↓
Scraping Task Triggered
    ↓
Publish to scraping.jobs queue
    ↓
Scraper Service Consumes Job
    ↓
Login to Instagram (if needed)
    ↓
Navigate to Society Profile
    ↓
Scrape Posts/Stories
    ↓
Extract Text & Metadata
    ↓
Take Screenshots (stories)
    ↓
Publish to scraping.results queue
    ↓
Event Processor Consumes Result
    ↓
Save Raw Data (posts/stories table)
    ↓
Check for Free Food Keywords
    ↓
If Match: Extract Event Details
    ↓
Validate & Score Confidence
    ↓
Check for Duplicates (content hash)
    ↓
Save Event (events table)
    ↓
Trigger Notification
```

### **2. Notification Flow**

```
Event Created
    ↓
Query Users (preferences + society filters)
    ↓
For Each User:
    ↓
    Check notification preferences
    ↓
    Create notification job
    ↓
    Add to notification queue
    ↓
Notification Worker Consumes Job
    ↓
Send WhatsApp (Twilio) or Email (SendGrid)
    ↓
Log Result (notification_logs)
    ↓
Update Event (notified = true)
```

### **3. User Signup Flow**

```
User Submits Phone/Email
    ↓
Validate Input
    ↓
Check if User Exists
    ↓
Send Verification Code (WhatsApp/Email)
    ↓
User Enters Code
    ↓
Verify Code
    ↓
Create User Record
    ↓
Show Society Preferences
    ↓
Save Preferences
    ↓
Send Welcome Message
```

---

## 🔐 Security & Privacy

### **Authentication**
- JWT tokens for API access
- Refresh token rotation
- Rate limiting per IP/user
- CORS configuration

### **Instagram Account Security**
- Dedicated monitoring account
- 2FA enabled
- Session persistence
- Automatic re-login on failure
- Activity logging

### **Data Privacy**
- User data encrypted at rest
- GDPR compliance
- Easy account deletion
- Opt-out mechanisms
- No data selling

### **API Security**
```python
# Rate limiting
@limiter.limit("100/minute")
async def get_events():
    pass

# Input validation
class EventQuery(BaseModel):
    date: Optional[date]
    society_id: Optional[UUID]
    limit: int = Field(default=20, le=100)
```

---

## 📊 Caching Strategy

### **Redis Cache Layers**

#### **1. Session Cache**
```python
# Instagram session cookies
Key: f"ig:session:{account_id}"
TTL: 24 hours
```

#### **2. Rate Limiting**
```python
# Track scraping rate
Key: f"rate:scrape:{society_id}"
TTL: 60 seconds
```

#### **3. Deduplication**
```python
# Story content hashes
Key: f"story:hash:{content_hash}"
TTL: 48 hours
```

#### **4. API Response Cache**
```python
# Event list cache
Key: f"events:list:{filters_hash}"
TTL: 60 seconds
```

#### **5. User Preferences**
```python
# Frequently accessed preferences
Key: f"user:prefs:{user_id}"
TTL: 5 minutes
```

---

## 🔄 Background Jobs

### **Celery Beat Schedule**

```python
celery_app.conf.beat_schedule = {
    # Story scraping (high frequency)
    'scrape-stories': {
        'task': 'scrape_all_stories',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Post scraping (lower frequency)
    'scrape-posts': {
        'task': 'scrape_all_posts',
        'schedule': 900.0,  # Every 15 minutes
    },
    
    # Cleanup expired stories
    'cleanup-stories': {
        'task': 'cleanup_expired_stories',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    
    # Archive old events
    'archive-events': {
        'task': 'archive_old_events',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    
    # Health check
    'health-check': {
        'task': 'check_scraper_health',
        'schedule': 60.0,  # Every minute
    },
}
```

---

## 🚨 Error Handling & Monitoring

### **Circuit Breaker Pattern**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def scrape_instagram(society_id: str):
    # If 5 failures occur, circuit opens for 60 seconds
    pass
```

### **Retry Strategy**

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
async def scrape_society(self, society_id: str):
    try:
        await scraper.scrape(society_id)
    except Exception as e:
        # Exponential backoff: 60s, 120s, 240s
        self.retry(
            exc=e,
            countdown=60 * (2 ** self.request.retries)
        )
```

### **Health Checks**

```python
# /health endpoint
{
    "status": "healthy",
    "services": {
        "database": "up",
        "redis": "up",
        "scraper": "up",
        "celery": "up"
    },
    "last_scrape": "2024-01-15T14:30:00Z",
    "events_today": 12
}
```

### **Monitoring Stack**

```yaml
# Prometheus metrics
- scraping_success_rate
- scraping_duration_seconds
- events_detected_total
- notifications_sent_total
- api_request_duration_seconds

# Grafana dashboards
- System overview
- Scraping performance
- Event detection accuracy
- Notification delivery
- Error rates

# Sentry error tracking
- Exception monitoring
- Performance monitoring
- Release tracking
```

---

## 🔧 Configuration Management

### **Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/freefood
REDIS_URL=redis://localhost:6379/0

# Instagram
INSTAGRAM_USERNAME=freefood_monitor
INSTAGRAM_PASSWORD=secure_password

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886

# SendGrid (Email)
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=alerts@freefooducd.ie

# AWS S3 (Screenshots)
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_S3_BUCKET=freefood-screenshots

# Application
SECRET_KEY=xxxxx
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 🐳 Docker Architecture

### **Services**

```yaml
services:
  # Database
  postgres:
    image: postgres:16-alpine
    
  # Cache
  redis:
    image: redis:7-alpine
    
  # Message Queue
  rabbitmq:
    image: rabbitmq:3-management-alpine
    
  # API Backend
  backend:
    build: ./backend
    depends_on: [postgres, redis]
    
  # Scraper Service (isolated)
  scraper:
    build: ./scraper-service
    depends_on: [rabbitmq, redis]
    restart: on-failure
    
  # Celery Workers
  celery-worker:
    build: ./backend
    command: celery -A app.workers worker
    
  # Celery Beat (scheduler)
  celery-beat:
    build: ./backend
    command: celery -A app.workers beat
    
  # Frontend
  frontend:
    build: ./frontend
    depends_on: [backend]
    
  # Monitoring
  prometheus:
    image: prom/prometheus
    
  grafana:
    image: grafana/grafana
```

---

## 📈 Scalability Plan

### **Phase 1: UCD Only (MVP)**
- Single scraper instance
- 20-30 societies
- ~1000 users
- Single server deployment

### **Phase 2: Irish Universities**
- Multiple scraper instances (per university)
- 100+ societies
- ~10,000 users
- Load balancer + multiple backend instances

### **Phase 3: UK Expansion**
- Distributed scraper fleet
- 500+ societies
- ~100,000 users
- Kubernetes deployment
- Multi-region setup

### **Scaling Strategies**

```python
# Horizontal scaling
- Add more Celery workers
- Add more scraper instances
- Database read replicas
- Redis cluster

# Vertical scaling
- Increase worker memory
- Faster database instance
- SSD storage

# Optimization
- Database indexing
- Query optimization
- Caching layer
- CDN for frontend
```

---

## 🧪 Testing Strategy

### **Unit Tests**
```python
# NLP extraction
test_extract_time()
test_extract_date()
test_extract_location()

# Deduplication
test_content_hash()
test_duplicate_detection()

# Validation
test_event_validation()
test_confidence_scoring()
```

### **Integration Tests**
```python
# API endpoints
test_get_events()
test_create_user()
test_update_preferences()

# Database operations
test_save_event()
test_query_events()
```

### **E2E Tests**
```python
# Full flow
test_scrape_to_notification()
test_user_signup_flow()
test_event_display()
```

### **Load Tests**
```python
# Locust scenarios
- 1000 concurrent users
- 100 events/minute
- API response time < 200ms
```

---

## 🚀 Deployment Strategy

### **Development**
```bash
docker-compose up
# All services run locally
```

### **Staging**
```bash
# Deploy to staging server
# Test with real Instagram account
# Verify notifications
```

### **Production**
```bash
# Blue-green deployment
# Zero-downtime updates
# Automated rollback on failure
```

### **CI/CD Pipeline**
```yaml
# GitHub Actions
1. Run tests
2. Build Docker images
3. Push to registry
4. Deploy to staging
5. Run E2E tests
6. Deploy to production (manual approval)
```

---

## 📝 API Documentation

### **OpenAPI/Swagger**
- Auto-generated from FastAPI
- Available at `/docs`
- Interactive API testing

### **Example Endpoints**

```python
# Get events
GET /api/v1/events?date=today&society_id=xxx
Response: {
    "events": [...],
    "total": 12,
    "page": 1
}

# Create user
POST /api/v1/users/signup
Body: {
    "phone_number": "+353871234567",
    "email": "user@ucd.ie"
}
Response: {
    "user_id": "xxx",
    "verification_sent": true
}
```

---

This architecture provides a robust, scalable, and maintainable foundation for FreeFood UCD with clear separation of concerns and fault tolerance built in.