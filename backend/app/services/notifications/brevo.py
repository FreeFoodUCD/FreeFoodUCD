"""
Email notification service using Brevo (Sendinblue)
This is the ONLY email service - Resend is deprecated.
"""
import httpx
from app.core.config import settings
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Service for sending email notifications via Brevo (Sendinblue)"""
    
    def __init__(self):
        """Initialize Brevo email service"""
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        self.headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }
        self.from_email = settings.BREVO_FROM_EMAIL
        self.from_name = settings.BREVO_FROM_NAME
    
    async def send_verification_code(self, email: str, code: str) -> Dict:
        """
        Send verification code via email
        
        Args:
            email: Recipient's email address
            code: Verification code
            
        Returns:
            Dict with success status
        """
        try:
            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": "Your FreeFood UCD Verification Code",
                "tags": ["transactional", "verification"],
                "htmlContent": f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                        .container {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            border-radius: 16px;
                            padding: 40px;
                            text-align: center;
                        }}
                        .code-box {{
                            background: white;
                            border-radius: 12px;
                            padding: 30px;
                            margin: 30px 0;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        }}
                        .code {{
                            font-size: 48px;
                            font-weight: bold;
                            letter-spacing: 8px;
                            color: #667eea;
                            font-family: 'Courier New', monospace;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div style="font-size: 48px; margin-bottom: 20px;">🍕</div>
                        <div style="color: white; font-size: 28px; font-weight: bold; margin-bottom: 10px;">
                            Welcome to FreeFood UCD!
                        </div>
                        <div style="color: rgba(255,255,255,0.9); font-size: 16px; margin-bottom: 20px;">
                            Your verification code is ready
                        </div>
                        
                        <div class="code-box">
                            <div style="color: #666; font-size: 14px; margin-bottom: 10px;">
                                Enter this code to complete your signup:
                            </div>
                            <div class="code">{code}</div>
                            <div style="color: #999; font-size: 12px; margin-top: 10px;">
                                Code expires in 10 minutes
                            </div>
                        </div>
                        
                        <div style="color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 30px;">
                            Never miss free food on campus again! 🎉<br>
                            You'll get notified about free food events from UCD societies.
                        </div>
                    </div>
                </body>
                </html>
                """,
                "textContent": f"""
FreeFood UCD - Verification Code

Your verification code: {code}

Enter this code to complete your signup.
Code expires in 10 minutes.

Never miss free food on campus again!
You'll get notified about free food events from UCD societies.
                """
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=data, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Verification code sent to {email}")
            return {"success": True, "status": "sent"}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error sending verification code: {str(e)} — body: {e.response.text}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error sending verification code: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_welcome_message(self, email: str) -> Dict:
        """
        Send welcome email after successful verification
        
        Args:
            email: Recipient's email address
            
        Returns:
            Dict with success status
        """
        try:
            # Extract first name from email (before @ and before any dots/numbers)
            email_prefix = email.split("@")[0]
            # Remove numbers and split by dots/underscores to get first part
            name_parts = email_prefix.replace(".", " ").replace("_", " ").split()
            # Get first part and capitalize, or just use "there" if it's not a name
            first_name = name_parts[0].capitalize() if name_parts and name_parts[0].isalpha() else None
            
            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": first_name or email.split("@")[0]}],
                "subject": "you're on the list",
                "tags": ["transactional", "welcome"],
                "htmlContent": f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1A1A1A;">
                    <div style="background: linear-gradient(135deg, #F78620 0%, #6FC266 100%); border-radius: 16px; padding: 32px 40px; text-align: center; color: white; margin-bottom: 30px;">
                        <div style="font-size: 24px; font-weight: bold;">Welcome to FreeFood UCD</div>
                    </div>
                    <div style="padding: 0 20px;">
                        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">Hi{f" {first_name}" if first_name else ""},</p>

                        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                            You got us early — we're still fine tuning our bots. We'll notify you when we launch. :)
                        </p>

                        <p style="font-size: 14px; color: #6b7280; margin-top: 40px;">-FreeFoodUCD</p>
                    </div>
                </body>
                </html>
                """,
                "textContent": f"""
Hi{f" {first_name}" if first_name else ""},

You got us early — we're still fine tuning our bots. We'll notify you when we launch. :)

-FreeFoodUCD
                """
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=data, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Welcome email sent to {email}")
            return {"success": True, "status": "sent"}
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_event_notification(self, email: str, event_data: Dict) -> Dict:
        """
        Send free food event notification via email
        
        Args:
            email: Recipient's email address
            event_data: Event information dict with keys:
                - society_name: str
                - title: str
                - location: str
                - start_time: str
                - date: str
                - source_type: str (post/story)
                - description: str (optional)
                
        Returns:
            Dict with success status
        """
        try:
            society = event_data.get("society_name", "Unknown Society")
            title = event_data.get("title", "Free Food Event")
            location = event_data.get("location", "Location TBA")
            time = event_data.get("start_time", "Time TBA")
            date = event_data.get("date", "Date TBA")

            maps_url = f"https://www.google.com/maps/search/?api=1&query={location.replace(' ', '+')}+UCD"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1A1A1A;">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 24px 30px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
                    <p style="margin: 0; font-size: 20px; font-weight: 600;">free food spotted</p>
                </div>

                <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                    <h2 style="margin-top: 0; color: #111827; font-size: 20px;">{title}</h2>

                    <div style="margin: 20px 0;">
                        <p style="margin: 10px 0; font-size: 15px;">🏛 <strong>Society:</strong> {society}</p>
                        <p style="margin: 10px 0; font-size: 15px;">📍 <strong>Location:</strong> {location} &nbsp;<a href="{maps_url}" style="color: #059669; font-size: 13px; text-decoration: none;">Open in Google Maps ↗</a></p>
                        <p style="margin: 10px 0; font-size: 15px;">🕒 <strong>Time:</strong> {time}</p>
                        <p style="margin: 10px 0; font-size: 15px;">📅 <strong>Date:</strong> {date}</p>
                    </div>
                </div>

                <div style="text-align: center; padding: 16px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 24px;">
                    FreeFoodUCD &middot; <a href="https://freefooducd.com/unsubscribe?email={email}" style="color: #9ca3af;">unsubscribe</a>
                </div>
            </body>
            </html>
            """

            plain_text = f"""
{title}

Society: {society}
Location: {location}
Maps: {maps_url}
Time: {time}
Date: {date}

---
FreeFoodUCD · unsubscribe: https://freefooducd.com/unsubscribe?email={email}
            """

            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": f"free food at {location}, {date}",
                "headers": {
                    "List-Unsubscribe": f"<https://freefooducd.com/unsubscribe?email={email}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
                },
                "tags": ["transactional", "event-notification"],
                "htmlContent": html_content,
                "textContent": plain_text
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=data, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Event notification sent to {email}")
            return {"success": True, "status": "sent"}
            
        except Exception as e:
            logger.error(f"Error sending event notification to {email}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_event_reminder(self, email: str, event_data: Dict) -> Dict:
        """
        Send event reminder (1 hour before event starts)
        
        Args:
            email: Recipient's email address
            event_data: Event information dict
            
        Returns:
            Dict with success status
        """
        try:
            society = event_data.get("society_name", "Unknown Society")
            title = event_data.get("title", "Free Food Event")
            location = event_data.get("location", "Location TBA")
            time = event_data.get("start_time", "Time TBA")

            maps_url = f"https://www.google.com/maps/search/?api=1&query={location.replace(' ', '+')}+UCD"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1A1A1A;">
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 10px 18px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 13px; font-weight: 500;">⏰ Starting in 1 hour</p>
                </div>

                <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                    <h2 style="margin-top: 0; color: #111827; font-size: 20px;">{title}</h2>

                    <div style="margin: 20px 0;">
                        <p style="margin: 10px 0; font-size: 15px;">🏛 <strong>Society:</strong> {society}</p>
                        <p style="margin: 10px 0; font-size: 15px;">📍 <strong>Location:</strong> {location} &nbsp;<a href="{maps_url}" style="color: #059669; font-size: 13px; text-decoration: none;">Open in Google Maps ↗</a></p>
                        <p style="margin: 10px 0; font-size: 15px;">🕒 <strong>Time:</strong> {time}</p>
                    </div>
                </div>

                <div style="text-align: center; padding: 16px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 24px;">
                    FreeFoodUCD &middot; <a href="https://freefooducd.com/unsubscribe?email={email}" style="color: #9ca3af;">unsubscribe</a>
                </div>
            </body>
            </html>
            """

            plain_text = f"""
{title}

Society: {society}
Location: {location}
Maps: {maps_url}
Time: {time}

---
FreeFoodUCD · unsubscribe: https://freefooducd.com/unsubscribe?email={email}
            """

            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": f"heads up: free food at {location}, {time}",
                "headers": {
                    "List-Unsubscribe": f"<https://freefooducd.com/unsubscribe?email={email}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
                },
                "tags": ["transactional", "event-reminder"],
                "htmlContent": html_content,
                "textContent": plain_text
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=data, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Reminder email sent to {email}")
            return {"success": True, "status": "sent"}
            
        except Exception as e:
            logger.error(f"Error sending reminder email to {email}: {str(e)}")
            return {"success": False, "error": str(e)}


# Backward compatibility functions (deprecated - use BrevoEmailService class instead)
async def send_verification_email(email: str, code: str) -> bool:
    """Deprecated: Use BrevoEmailService().send_verification_code() instead"""
    service = BrevoEmailService()
    result = await service.send_verification_code(email, code)
    return result.get("success", False)


async def send_welcome_email(email: str) -> bool:
    """Deprecated: Use BrevoEmailService().send_welcome_message() instead"""
    service = BrevoEmailService()
    result = await service.send_welcome_message(email)
    return result.get("success", False)


# Alias for backward compatibility
EmailNotifier = BrevoEmailService

# Made with Bob
