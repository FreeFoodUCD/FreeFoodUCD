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
                """
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=data, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Verification code sent to {email}")
            return {"success": True, "status": "sent"}
            
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
            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": "🎉 You're All Set - FreeFood UCD",
                "htmlContent": """
                <!DOCTYPE html>
                <html>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 40px; text-align: center; color: white;">
                        <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
                        <div style="font-size: 32px; font-weight: bold; margin-bottom: 20px;">Welcome to FreeFood UCD!</div>
                        <div style="font-size: 18px; margin-bottom: 30px;">
                            You're all set! We'll notify you whenever there's free food on campus.
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin: 20px 0; text-align: left;">
                            <div style="margin: 15px 0; font-size: 16px;">🍕 Get instant notifications about free food events</div>
                            <div style="margin: 15px 0; font-size: 16px;">🎓 From all major UCD societies</div>
                            <div style="margin: 15px 0; font-size: 16px;">⚡ Real-time updates from Instagram</div>
                            <div style="margin: 15px 0; font-size: 16px;">📧 Delivered straight to your inbox</div>
                        </div>
                        
                        <div style="margin-top: 30px; font-size: 14px; opacity: 0.9;">
                            Never miss free food on campus again! 🚀
                        </div>
                    </div>
                </body>
                </html>
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
            source = event_data.get("source_type", "post")
            description = event_data.get("description", "")
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 28px;">🍕 Free Food Alert!</h1>
                </div>
                
                <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                    <h2 style="margin-top: 0; color: #111827; font-size: 22px;">{title}</h2>
                    
                    <div style="margin: 20px 0;">
                        <p style="margin: 10px 0; font-size: 16px;"><strong>🏛 Society:</strong> {society}</p>
                        <p style="margin: 10px 0; font-size: 16px;"><strong>📍 Location:</strong> {location}</p>
                        <p style="margin: 10px 0; font-size: 16px;"><strong>🕒 Time:</strong> {time}</p>
                        <p style="margin: 10px 0; font-size: 16px;"><strong>📅 Date:</strong> {date}</p>
                        <p style="margin: 10px 0; font-size: 14px; color: #6b7280;"><strong>Source:</strong> Instagram {source.title()}</p>
                    </div>
                    
                    {f'<p style="margin-top: 20px; padding: 15px; background: white; border-radius: 8px; font-size: 14px; color: #4b5563;">{description}</p>' if description else ''}
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 18px; color: #059669; font-weight: 600;">Don't miss out! 🎉</p>
                </div>
                
                <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 30px;">
                    <p>You're receiving this because you signed up for FreeFood UCD alerts.</p>
                </div>
            </body>
            </html>
            """
            
            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": f"🍕 Free Food Alert: {society}",
                "htmlContent": html_content
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
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 28px;">⏰ Starting in 1 Hour!</h1>
                </div>
                
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; margin-bottom: 20px; border-radius: 8px;">
                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #92400e;">Don't forget! Free food event starting soon:</p>
                </div>
                
                <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                    <h2 style="margin-top: 0; color: #111827; font-size: 22px;">{title}</h2>
                    
                    <div style="margin: 20px 0;">
                        <p style="margin: 10px 0; font-size: 16px;"><strong>🏛 Society:</strong> {society}</p>
                        <p style="margin: 10px 0; font-size: 16px;"><strong>📍 Location:</strong> {location}</p>
                        <p style="margin: 10px 0; font-size: 16px;"><strong>🕒 Time:</strong> {time}</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 18px; color: #d97706; font-weight: 600;">Head over now! 🏃‍♂️💨</p>
                </div>
                
                <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 30px;">
                    <p>FreeFood UCD - Never miss free food again!</p>
                </div>
            </body>
            </html>
            """
            
            data = {
                "sender": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [{"email": email, "name": email.split("@")[0]}],
                "subject": f"⏰ Reminder: Free Food in 1 Hour - {society}",
                "htmlContent": html_content
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
