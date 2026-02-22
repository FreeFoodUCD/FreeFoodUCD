# FreeFood UCD - System Architecture

## 🎯 Overview

FreeFood UCD is a notification system that monitors UCD society Instagram accounts for free food events and alerts students via email.

**Core Flow:** Instagram → Scraper → Event Detection → Email Notification

---

## 🏗️ System Architecture

```
┌─────────────┐
│   Users     │
│  (Browser)  │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────┐
│         Frontend (Next.js/Vercel)       │
│  - Landing page (shows next 24h events) │
│  - Signup flow with email verification  │
│  - Admin dashboard                      │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│       Backend API (FastAPI/Railway)     │
│  - REST endpoints                       │
│  - User management                      │
│  - Event CRUD                           │
│  - Admin operations                     │
└──────┬──────────────────────────────────┘
       │
       ├─────────────────┬─────────────────┬──────────────────┐
       ↓                 ↓                 ↓                  ↓
┌─────────────┐   ┌─────────────┐   ┌──────────────┐   ┌──────────┐
│ PostgreSQL  │   │   Redis     │   │ Celery Beat  │   │  Brevo   │
│  Database   │   │   Cache     │   │  Scheduler   │   │  Email   │
└─────────────┘   └─────────────┘   └──────┬───────┘   └──────────┘
                                            │
                                            ↓
                                    ┌───────────────┐
                                    │ Celery Worker │
                                    │  - Scraping   │
                                    │  - Reminders  │
                                    └───────┬───────┘
                                            │
                                            ↓
                                    ┌───────────────┐
                                    │ Apify Service │
                                    │   Instagram   │
                                    │    Scraper    │
                                    └───────────────┘
```

---

## 📦 Core Components

### 1. **Frontend (Next.js + TypeScript)**
**Location:** `frontend/`  
**Deployed:** Vercel  
**Purpose:** User interface

**Pages:**
- `/` - Landing page (shows events in next 24 hours)
- `/signup` - Email signup with verification
- `/admin` - Admin dashboard (9 tabs)
- `/societies` - Society list
- `/about` - About page

**Key Features:**
- React Query for data fetching
- Tailwind CSS for styling
- Real-time event countdown timers
- Responsive design

---

### 2. **Backend API (FastAPI + Python)**
**Location:** `backend/`  
**Deployed:** Railway  
**Purpose:** Business logic and data management

**Structure:**
```
backend/
├── app/
│   ├── api/v1/endpoints/     # REST endpoints
│   │   ├── events.py         # Event CRUD
│   │   ├── users.py          # User management
│   │   ├── societies.py      # Society management
│   │   └── admin.py          # Admin operations
│   ├── core/
│   │   └── config.py         # Settings
│   ├── db/
│   │   ├── models.py         # SQLAlchemy models
│   │   └── base.py           # Database session
│   ├── services/
│   │   ├── notifications/
│   │   │   └── brevo.py      # Email service (Brevo)
│   │   ├── scraper/
│   │   │   └── apify_scraper.py  # Instagram scraper
│   │   ├── nlp/
│   │   │   └── extractor.py  # Event extraction
│   │   └── ocr/
│   │       └── image_text_extractor.py  # OCR
│   └── workers/
│       ├── celery_app.py     # Celery config
│       ├── scraping_tasks.py # Scraping jobs
│       └── notification_tasks.py  # Email jobs
```

**Key Endpoints:**
```
GET  /api/v1/events?date=24h          # Get events (next 24h)
POST /api/v1/users/signup             # User signup
POST /api/v1/users/verify             # Verify email code
GET  /api/v1/admin/upcoming-events    # Admin: upcoming events
POST /api/v1/admin/scrape             # Admin: manual scrape
```

---

### 3. **Database (PostgreSQL)**
**Deployed:** Railway  
**Purpose:** Persistent data storage

**Core Tables:**
```sql
societies           # UCD societies to monitor
├── id, name, instagram_handle
├── is_active, scrape_posts, scrape_stories
└── last_scraped_at

posts               # Raw Instagram posts
├── id, society_id, instagram_post_id
├── caption, media_urls
└── is_free_food, processed

events              # Processed free food events
├── id, society_id, title, description
├── location, start_time, end_time
├── source_type (post/story)
├── notified, reminder_sent
└── confidence_score

users               # Registered users
├── id, email, email_verified
├── is_active, notification_preferences
└── verification_code, code_expires_at

notification_logs   # Audit trail
├── id, event_id, user_id
├── notification_type, status
└── sent_at, error_message

scraping_logs       # Monitoring
├── id, society_id, status
├── items_found, duration_ms
└── error_message
```

---

### 4. **Background Jobs (Celery + Redis)**
**Purpose:** Scheduled tasks and async processing

**Celery Beat Schedule:**
```python
# Daily scraping at 9 AM UTC
'daily-scrape': {
    'task': 'scrape_all_societies',
    'schedule': crontab(hour=9, minute=0)
}

# Check for reminders every 30 minutes
'check-reminders': {
    'task': 'send_upcoming_event_notifications',
    'schedule': crontab(minute='*/30')
}

# Cleanup old data daily at 2 AM
'cleanup': {
    'task': 'cleanup_old_data',
    'schedule': crontab(hour=2, minute=0)
}
```

**Tasks:**
1. **Scraping** - Fetch Instagram posts via Apify
2. **Event Detection** - Extract event details using NLP
3. **Notifications** - Send emails via Brevo
4. **Reminders** - Send 1-hour before event starts
5. **Cleanup** - Remove old posts/logs

---

### 5. **External Services**

#### **Apify (Instagram Scraping)**
- **Purpose:** Scrape Instagram posts and stories
- **API:** Apify Instagram Scraper actor
- **Config:** `APIFY_API_TOKEN`
- **Rate:** Once daily per society

#### **Brevo (Email Service)**
- **Purpose:** Send transactional emails
- **API:** Brevo SMTP API
- **Config:** `BREVO_API_KEY`, `BREVO_FROM_EMAIL`
- **Emails:**
  - Verification codes
  - Welcome messages
  - Event notifications
  - Event reminders (1 hour before)

---

## 🔄 Data Flow

### **1. Scraping Flow**
```
Celery Beat (9 AM UTC)
    ↓
Trigger scraping task
    ↓
For each active society:
    ↓
    Call Apify API
    ↓
    Get Instagram posts
    ↓
    Save to posts table
    ↓
    Check for free food keywords
    ↓
    If match: Extract event details (NLP)
    ↓
    Validate and score confidence
    ↓
    Save to events table
    ↓
    Send notifications to users
```

### **2. Notification Flow**
```
New event created
    ↓
Get all active users
    ↓
Filter by email_verified = true
    ↓
For each user:
    ↓
    Format email with event details
    ↓
    Send via Brevo API
    ↓
    Log result to notification_logs
    ↓
Mark event as notified
```

### **3. Reminder Flow**
```
Every 30 minutes:
    ↓
Query events starting in ~1 hour
    ↓
Filter: reminder_sent = false
    ↓
For each event:
    ↓
    Get eligible users
    ↓
    Send reminder emails
    ↓
    Mark reminder_sent = true
```

### **4. User Signup Flow**
```
User enters email
    ↓
Generate 6-digit code
    ↓
Send verification email (Brevo)
    ↓
User enters code
    ↓
Verify code (10 min expiry)
    ↓
Mark email_verified = true
    ↓
Send welcome email
```

---

## 🔐 Security

### **Authentication**
- Admin endpoints: API key in header (`X-Admin-Key`)
- User data: Email verification required
- Rate limiting: 100 requests/minute per IP

### **Data Privacy**
- No passwords stored (email-only signup)
- Verification codes expire in 10 minutes
- Users can unsubscribe anytime
- GDPR compliant

### **API Security**
```python
# Input validation with Pydantic
class EventQuery(BaseModel):
    date_filter: Optional[str]
    society_id: Optional[UUID]
    limit: int = Field(default=20, le=100)

# CORS configuration
allow_origins=[
    "https://freefooducd.vercel.app",
    "http://localhost:3000"
]
```

---

## 📊 Monitoring & Logging

### **Health Checks**
```python
GET /api/v1/health
{
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "celery_worker": "running",
    "celery_beat": "running"
}
```

### **Admin Dashboard**
- **Dashboard:** System overview, recent activity
- **Events:** View/manage upcoming events
- **Societies:** Monitor scraping performance
- **Notifications:** Delivery stats, retry failed
- **Health:** System status, error logs
- **Logs:** Scraping history
- **Posts:** Raw Instagram data
- **Users:** User management
- **Scrape:** Manual scraping trigger

### **Logging**
```python
# Structured logging
logger.info(f"Scraped {count} posts from {society.name}")
logger.error(f"Failed to scrape {society.name}: {error}")

# Stored in:
- scraping_logs table
- notification_logs table
- Application logs (Railway)
```

---

## 🚀 Deployment

### **Production Stack**
```
Frontend:  Vercel (Next.js)
Backend:   Railway (FastAPI + Celery)
Database:  Railway (PostgreSQL)
Cache:     Railway (Redis)
Email:     Brevo
Scraping:  Apify
```

### **Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Apify
APIFY_API_TOKEN=xxx

# Brevo (Email)
BREVO_API_KEY=xxx
BREVO_FROM_EMAIL=alerts@freefooducd.ie
BREVO_FROM_NAME=FreeFood UCD

# Application
SECRET_KEY=xxx
ADMIN_API_KEY=xxx
ENVIRONMENT=production
```

### **Deployment Process**
1. Push to GitHub main branch
2. Railway auto-deploys backend
3. Vercel auto-deploys frontend
4. Database migrations run automatically
5. Celery workers restart

---

## 🎯 Design Principles

### **1. Simplicity**
- Single email service (Brevo)
- Single scraping service (Apify)
- Clear separation of concerns
- Minimal dependencies

### **2. Reliability**
- Retry logic for failed tasks
- Error logging and monitoring
- Graceful degradation
- Health checks

### **3. Maintainability**
- Type hints throughout
- Clear naming conventions
- Comprehensive logging
- Documentation

### **4. Scalability**
- Async operations (FastAPI)
- Background job queue (Celery)
- Database indexing
- Caching layer (Redis)

---

## 📈 Future Enhancements

### **Phase 1 (Current)**
- ✅ Email notifications
- ✅ Daily scraping
- ✅ Event reminders
- ✅ Admin dashboard

### **Phase 2 (Planned)**
- WhatsApp notifications (Twilio)
- Real-time scraping (webhooks)
- Mobile app (React Native)
- Event categories/tags

### **Phase 3 (Future)**
- Multi-university support
- AI-powered event extraction
- User event submissions
- Social features (comments, ratings)

---

## 🧪 Testing

### **Unit Tests**
```python
# NLP extraction
test_extract_time()
test_extract_location()

# Event validation
test_event_confidence_score()
test_duplicate_detection()
```

### **Integration Tests**
```python
# API endpoints
test_get_events()
test_user_signup()
test_admin_scrape()

# Background jobs
test_scraping_task()
test_notification_task()
```

### **E2E Tests**
```python
# Full user flow
test_signup_to_notification()
test_event_display()
```

---

## 📝 API Documentation

**Interactive Docs:** `https://api.freefooducd.ie/docs`

**Key Endpoints:**
```python
# Public
GET  /api/v1/events?date=24h
POST /api/v1/users/signup
POST /api/v1/users/verify

# Admin (requires X-Admin-Key header)
GET  /api/v1/admin/upcoming-events
POST /api/v1/admin/scrape
GET  /api/v1/admin/notification-logs
GET  /api/v1/admin/system-health
```

---

This architecture provides a simple, reliable, and maintainable system for notifying UCD students about free food events.