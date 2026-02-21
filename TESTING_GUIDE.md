# Testing Guide - Frontend to Backend Connection

## 🚀 Quick Start

### 1. Start the Backend API

```bash
cd backend

# Make sure PostgreSQL and Redis are running
# Check docker-compose.yml or start them manually

# Run database migrations
alembic upgrade head

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**

### 2. Start the Frontend

```bash
cd frontend

# Frontend is already running on port 3000
# If not, run:
npm run dev
```

Frontend will be available at: **http://localhost:3000**

---

## 🧪 Test the Connection

### Test 1: Signup Flow (WhatsApp)

1. Go to http://localhost:3000
2. Click "sign me up"
3. Choose "WhatsApp"
4. Enter phone number: `85 123 4567`
5. Click "continue"
6. **Expected**: User created in database, success screen shown

**Check Backend:**
```bash
# In another terminal
curl http://localhost:8000/api/v1/users
```

### Test 2: Signup Flow (Email)

1. Go to http://localhost:3000/signup
2. Choose "Email"
3. Enter email: `test@ucd.ie`
4. Click "continue"
5. **Expected**: User created, success screen shown

### Test 3: Event Feed

1. Go to http://localhost:3000
2. **Expected**: 
   - If backend has events: Shows real events
   - If backend is empty: Shows mock events (fallback)

---

## 🔍 Debugging

### Check if Backend is Running

```bash
curl http://localhost:8000/docs
```

Should return the FastAPI Swagger UI.

### Check API Endpoints

```bash
# Get all events
curl http://localhost:8000/api/v1/events

# Get all societies
curl http://localhost:8000/api/v1/societies

# Create a test user
curl -X POST http://localhost:8000/api/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@ucd.ie"}'
```

### Check Frontend API Calls

Open browser DevTools (F12) → Network tab → Filter by "Fetch/XHR"

You should see:
- `GET /api/v1/events` when loading homepage
- `POST /api/v1/users/signup` when signing up

### Common Issues

**Issue**: "Failed to fetch" error
**Solution**: Make sure backend is running on port 8000

**Issue**: CORS error
**Solution**: Backend already has CORS configured for localhost:3000

**Issue**: Database connection error
**Solution**: Make sure PostgreSQL is running and DATABASE_URL is correct in backend/.env

---

## 📊 Add Test Data

### Add Test Societies

```bash
cd backend
python -c "
from app.db.base import SessionLocal
from app.db.models import Society

db = SessionLocal()

societies = [
    Society(name='UCD Law Society', instagram_handle='ucdlawsoc', is_active=True),
    Society(name='UCD Computer Science Society', instagram_handle='ucdcompsci', is_active=True),
    Society(name='UCD Business Society', instagram_handle='ucdbusiness', is_active=True),
]

for society in societies:
    db.add(society)

db.commit()
print('Test societies added!')
"
```

### Add Test Events

```bash
python -c "
from app.db.base import SessionLocal
from app.db.models import Event, Society
from datetime import datetime, timedelta

db = SessionLocal()

# Get first society
society = db.query(Society).first()

if society:
    event = Event(
        title='Pizza Night & Movie Screening',
        location='Newman Building A105',
        start_time=datetime.now() + timedelta(hours=2),
        end_time=datetime.now() + timedelta(hours=4),
        society_id=society.id,
        source_type='story',
        is_free_food=True,
        notified=False
    )
    db.add(event)
    db.commit()
    print('Test event added!')
else:
    print('No societies found. Add societies first.')
"
```

---

## ✅ Success Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Can access http://localhost:8000/docs
- [ ] Can access http://localhost:3000
- [ ] Signup creates user in database
- [ ] Events show on homepage (real or mock)
- [ ] No CORS errors in browser console
- [ ] API calls visible in Network tab

---

## 🎯 Next Steps

Once everything is working:

1. **Add real Instagram data** - Run the scraping service
2. **Test notifications** - Verify WhatsApp/Email alerts work
3. **Add more test users** - Test with different phone numbers/emails
4. **Test verification flow** - Implement verification code checking

---

Made with Bob