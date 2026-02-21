"""
Test Resend email service
Run: python test_resend.py
"""
import resend
import os
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv('RESEND_API_KEY')

print("📧 Testing Resend Email Service")
print("=" * 50)

# Your test email
test_email = "freefooducd@outlook.com"  # Change to your email

params = {
    "from": "FreeFood UCD <freefooducd@resend.dev>",
    "to": [test_email],
    "subject": "🍕 Free Food Alert: Test Email",
    "html": """
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
            <h1 style="margin: 0; font-size: 28px;">🍕 Free Food Alert!</h1>
        </div>
        
        <div style="background: #f9fafb; border-radius: 12px; padding: 25px;">
            <h2 style="margin-top: 0; color: #111827;">Free Pizza Night</h2>
            <p><strong>🏛 Society:</strong> UCD Law Society</p>
            <p><strong>📍 Location:</strong> Newman Building A105</p>
            <p><strong>🕒 Time:</strong> 6:00 PM</p>
            <p><strong>📅 Date:</strong> Today</p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="font-size: 18px; color: #059669; font-weight: 600;">Don't miss out! 🎉</p>
        </div>
    </body>
    </html>
    """
}

try:
    email = resend.Emails.send(params)
    print(f"\n✅ Email sent successfully!")
    print(f"📨 Email ID: {email['id']}")
    print(f"\n💡 Check your inbox: {test_email}")
    print("(Should arrive in seconds, not minutes!)")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

# Made with Bob
