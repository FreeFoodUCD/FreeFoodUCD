"""Test single-event discovery and reminder emails."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.services.notifications.brevo import BrevoEmailService

EVENT = {
    "society_name": "UCD Baking Society",
    "title": "Weekly Bake Sale - cakes & pastries",
    "location": "Newman Concourse",
    "start_time": "12:00",
    "date": "Saturday, 1 March",
    "source_url": "https://www.instagram.com/p/test1/",
    "members_only": False,
    "reminder_will_fire": True,
}

async def main():
    svc = BrevoEmailService()
    print(f"Sender: {svc.from_email}")

    r1 = await svc.send_event_notification("gotoaditya4@gmail.com", EVENT)
    print(f"Discovery email: {r1}")

    r2 = await svc.send_event_reminder("gotoaditya4@gmail.com", EVENT)
    print(f"Reminder email:  {r2}")

asyncio.run(main())
