"""
Ultra-simple WhatsApp test - no dependencies on app code
Run: python test_whatsapp_simple.py
"""
from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio credentials
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
FROM_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')

# Your phone number
TO_NUMBER = "+353858760120"

print("🧪 Testing WhatsApp Notification")
print("=" * 50)
print(f"📱 From: whatsapp:{FROM_NUMBER}")
print(f"📱 To: whatsapp:{TO_NUMBER}")
print()

# Create Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Message body
message_body = """🍕 FREE FOOD ALERT

Society: UCD Law Society
📍 Location: Newman Building A105
🕒 18:00
📅 Today
🔗 Source: Story

Don't miss out! 🎉"""

try:
    # Send message
    message = client.messages.create(
        from_=f'whatsapp:{FROM_NUMBER}',
        body=message_body,
        to=f'whatsapp:{TO_NUMBER}'
    )
    
    print("✅ Message sent successfully!")
    print(f"📨 Message SID: {message.sid}")
    print(f"📊 Status: {message.status}")
    print()
    print("💡 Check your WhatsApp for the message!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")

# Made with Bob
