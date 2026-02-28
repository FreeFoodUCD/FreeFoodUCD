"""One-off script: send a test batch discovery email to personal address."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.services.notifications.brevo import BrevoEmailService

TEST_EVENTS = [
    {
        "society_name": "UCD Baking Society",
        "title": "Weekly Bake Sale — cakes & pastries",
        "location": "Newman Concourse",
        "start_time": "12:00",
        "date": "Saturday, 1 March",
        "source_url": "https://www.instagram.com/p/test1/",
        "members_only": False,
    },
    {
        "society_name": "UCD Debating Union",
        "title": "Pizza after the debate night",
        "location": "Dramsoc Green Room",
        "start_time": "19:30",
        "date": "Saturday, 1 March",
        "source_url": "https://www.instagram.com/p/test2/",
        "members_only": True,
    },
    {
        "society_name": "UCD Engineering Society",
        "title": "Free lunch at the careers fair",
        "location": "Engineering Building Atrium",
        "start_time": "13:00",
        "date": "Saturday, 1 March",
        "source_url": None,
        "members_only": False,
    },
]


async def main():
    svc = BrevoEmailService()
    print(f"Sending from: {svc.from_email}")
    result = await svc.send_batch_event_notification("gotoaditya4@gmail.com", TEST_EVENTS)
    print(result)


asyncio.run(main())
