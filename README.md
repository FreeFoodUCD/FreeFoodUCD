# FreeFood UCD 🍕

Automatically detect when UCD societies post about free food on Instagram and notify students via WhatsApp or email.

## Features

- 🔍 **Instagram Scraping** - Monitors UCD society accounts via Apify
- 🧠 **Smart Filtering** - 6-layer NLP validation (rejects other colleges, off-campus, paid events)
- 📸 **OCR Support** - Extracts text from post images
- 📱 **WhatsApp Notifications** - Primary notification channel via Twilio
- 📧 **Email Notifications** - Secondary channel via Resend
- 🎯 **Real-time Detection** - Scrapes every 30 minutes
- 🗄️ **PostgreSQL Database** - Stores events, posts, and user preferences

## Tech Stack

**Backend:**
- FastAPI (Python)
- PostgreSQL + SQLAlchemy
- Celery + Redis (task queue)
- Apify (Instagram scraping)
- Pytesseract (OCR)

**Frontend:**
- Next.js 14
- TypeScript
- Tailwind CSS

## Quick Start

### 1. Prerequisites

```bash
# Install system dependencies
brew install postgresql redis tesseract  # macOS
# or
sudo apt install postgresql redis tesseract-ocr  # Linux

# Install Python 3.11+
python --version
```

### 2. Clone & Setup

```bash
git clone <repo-url>
cd FreeFoodUCD

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### 3. Configure Environment

```bash
# Copy example env file
cp backend/.env.example backend/.env

# Edit backend/.env with your credentials:
# - DATABASE_URL
# - REDIS_URL
# - APIFY_API_TOKEN (get from https://apify.com)
# - TWILIO_* (WhatsApp credentials)
# - RESEND_API_KEY (email service)
```

### 4. Initialize Database

```bash
cd backend
source venv/bin/activate

# Run migrations
alembic upgrade head

# Seed with UCD societies
python seed_data.py
```

### 5. Start Services

```bash
# Terminal 1: PostgreSQL
brew services start postgresql  # or sudo service postgresql start

# Terminal 2: Redis
brew services start redis  # or sudo service redis-server start

# Terminal 3: Backend API
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 4: Celery Worker
cd backend && source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 5: Celery Beat (Scheduler)
cd backend && source venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 6: Frontend
cd frontend
npm run dev
```

### 6. Access

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Testing

```bash
cd backend && source venv/bin/activate

# Test Apify scraper
python test_apify.py

# Test end-to-end flow
python test_end_to_end.py
```

## Project Structure

```
FreeFoodUCD/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── core/             # Config
│   │   ├── db/               # Database models
│   │   ├── services/
│   │   │   ├── nlp/          # Event extraction
│   │   │   ├── ocr/          # Image text extraction
│   │   │   ├── scraper/      # Apify Instagram scraper
│   │   │   └── notifications/ # WhatsApp & Email
│   │   └── workers/          # Celery tasks
│   ├── alembic/              # Database migrations
│   ├── requirements.txt
│   ├── seed_data.py
│   ├── test_apify.py
│   └── test_end_to_end.py
├── frontend/
│   ├── app/                  # Next.js pages
│   ├── components/           # React components
│   └── lib/                  # Utilities
├── ARCHITECTURE.md           # System design
├── APIFY_SETUP_GUIDE.md     # Apify configuration
└── README.md                 # This file
```

## How It Works

1. **Scraping** - Celery Beat triggers scraping every 30 minutes
2. **Apify** - Scrapes last 3 posts from each UCD society
3. **OCR** - Extracts text from post images (event details often in images)
4. **NLP Filtering** - 6-layer validation:
   - ✅ Contains free food keywords (pizza, snacks, refreshments, etc.)
   - ❌ Rejects other colleges (DCU, Trinity, Maynooth)
   - ❌ Rejects off-campus venues (pubs, bars, Temple Bar)
   - ❌ Rejects paid events (tickets, €, ball, gala)
   - ✅ Requires UCD location (campus buildings)
   - ✅ Extracts time, date, location
5. **Database** - Stores events with duplicate detection
6. **Notifications** - Sends WhatsApp/Email to subscribed users

## Apify Setup

1. Create account at https://apify.com (free tier: $5/month credit)
2. Get API token from Settings → Integrations
3. Add to `backend/.env`:
   ```
   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxx
   ```

**Costs:**
- Free tier: ~20,000 posts/month (perfect for testing)
- Production: ~$58/month (35,000 posts for 8 societies)

See `APIFY_SETUP_GUIDE.md` for details.

## Monitored Societies

- UCD Law Society
- UCD Computer Science Society
- UCD Engineering Society
- UCD Business Society
- UCD Medical Society
- UCD Drama Society
- UCD Music Society
- UCD Sports Societies

Add more in `backend/seed_data.py`

## API Endpoints

- `GET /api/v1/events` - List events (with filters)
- `GET /api/v1/events/{id}` - Get event details
- `GET /api/v1/societies` - List societies
- `POST /api/v1/users/signup` - Subscribe to notifications
- `GET /api/v1/users/{id}/preferences` - Get notification preferences

## Configuration

### Scraping Frequency

Edit `backend/app/workers/celery_app.py`:

```python
beat_schedule = {
    'scrape-posts': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}
```

### Posts Per Society

Edit `backend/app/workers/scraping_tasks.py`:

```python
posts_data = await scraper.scrape_posts(
    society.instagram_handle,
    max_posts=3  # Adjust as needed
)
```

## Troubleshooting

### OCR Not Working
```bash
# Install tesseract
brew install tesseract  # macOS
sudo apt install tesseract-ocr  # Linux
```

### Celery Not Starting
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check Celery config
celery -A app.workers.celery_app inspect active
```

### No Events Detected
- Check if societies have posted about free food recently
- View NLP logs: `grep "NLP" celery.log`
- Test with known free food post

### Apify Errors
- Check API token in `.env`
- Verify credits at https://console.apify.com
- View run logs in Apify Console

## Production Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Use production database (not localhost)
3. Set up SSL certificates
4. Configure domain and CORS
5. Use process manager (PM2, systemd)
6. Set up monitoring (Sentry)
7. Configure backups

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file

## Support

- **Issues:** GitHub Issues
- **Email:** support@freefooducd.ie
- **Apify Support:** https://docs.apify.com

---

Made with ❤️ for UCD students