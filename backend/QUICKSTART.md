# Quick Start Guide - Test WhatsApp Integration

## Step 1: Create Virtual Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

## Step 2: Install Dependencies (Minimal - Just for WhatsApp Test)

```bash
# Install only what's needed for WhatsApp testing
uv pip install -r requirements-minimal.txt
```

This installs only:
- FastAPI (core framework)
- Twilio (for WhatsApp)
- Pydantic (for settings)
- python-dotenv (for .env file)

**Note:** We're using `requirements-minimal.txt` to avoid PostgreSQL build issues. For full setup later, use `requirements.txt`.

## Step 3: Test WhatsApp (No Database Needed!)

The test script doesn't need the database running. Just run:

```bash
python test_whatsapp.py
```

You should see:
```
🧪 Testing WhatsApp Notification Service
==================================================

📱 Sending test message to: +353858760120
📋 Event: Free Pizza Night
📍 Location: Newman Building A105
🕒 Time: 18:00

✅ Message sent successfully!
📨 Message SID: MMxxxxxxxxxxxxxxxxxx
📊 Status: queued

💡 Check your WhatsApp for the message!
```

## Step 4: Check Your Phone

Open WhatsApp and you should receive:

```
🍕 FREE FOOD ALERT

Society: UCD Law Society
📍 Location: Newman Building A105
🕒 18:00
📅 Today
🔗 Source: Story

Don't miss out! 🎉
```

## Troubleshooting

### Error: "No module named 'twilio'"
```bash
pip install twilio
```

### Error: "No module named 'app'"
Make sure you're in the `backend` directory and venv is activated.

### Message not received?
1. Check if you've joined the Twilio sandbox (send "join [keyword]" to the Twilio number)
2. Verify your phone number is correct in `.env`
3. Check Twilio console for delivery status

## Next Steps

Once WhatsApp works, you can:

1. **Start the database:**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start the API:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Start background workers:**
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info
   celery -A app.workers.celery_app beat --loglevel=info
   ```

## Full Setup

For complete setup instructions, see:
- `SETUP_GUIDE.md` - Local development setup
- `SERVICES_SETUP_GUIDE.md` - External services (Instagram, Twilio, SendGrid)
- `IMPLEMENTATION_GUIDE.md` - Development guide