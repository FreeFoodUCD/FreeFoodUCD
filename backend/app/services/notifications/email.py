"""
Email notification service using Resend
"""
import logging
from typing import Dict, List
import resend
from datetime import timedelta, datetime

from app.core.config import settings
from app.db.models import Event, User

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via Resend"""
    
    def __init__(self):
        """Initialize Resend client"""
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>"
    
    async def send_event_notification(
        self,
        email: str,
        event_data: Dict
    ) -> Dict:
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
                
        Returns:
            Dict with success status and message details
        """
        try:
            subject = f"🍕 Free Food Alert: {event_data.get('society_name', 'UCD Society')}"
            html_content = self._format_event_html(event_data)
            
            params = {
                "from": self.from_email,
                "to": [email],
                "subject": subject,
                "html": html_content
            }
            
            result = resend.Emails.send(params)
            
            logger.info(f"Email sent successfully to {email}. ID: {result.get('id')}")
            
            return {
                "success": True,
                "message_id": result.get('id'),
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_event_html(self, event_data: Dict) -> str:
        """
        Format event data into HTML email
        
        Args:
            event_data: Event information
            
        Returns:
            HTML string
        """
        society = event_data.get("society_name", "Unknown Society")
        title = event_data.get("title", "Free Food Event")
        location = event_data.get("location", "Location TBA")
        time = event_data.get("start_time", "Time TBA")
        date = event_data.get("date", "Date TBA")
        source = event_data.get("source_type", "post")
        description = event_data.get("description", "")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Free Food Alert</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">🍕 Free Food Alert!</h1>
            </div>
            
            <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                <h2 style="margin-top: 0; color: #111827; font-size: 22px;">{title}</h2>
                
                <div style="margin: 20px 0;">
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>🏛 Society:</strong> {society}
                    </p>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>📍 Location:</strong> {location}
                    </p>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>🕒 Time:</strong> {time}
                    </p>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>📅 Date:</strong> {date}
                    </p>
                    <p style="margin: 10px 0; font-size: 14px; color: #6b7280;">
                        <strong>Source:</strong> Instagram {source.title()}
                    </p>
                </div>
                
                {f'<p style="margin-top: 20px; padding: 15px; background: white; border-radius: 8px; font-size: 14px; color: #4b5563;">{description}</p>' if description else ''}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="font-size: 18px; color: #059669; font-weight: 600;">Don't miss out! 🎉</p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 30px;">
                <p>You're receiving this because you signed up for FreeFood UCD alerts.</p>
                <p style="margin-top: 10px;">
                    <a href="https://freefooducd.ie/unsubscribe" style="color: #6b7280; text-decoration: underline;">Unsubscribe</a>
                </p>
            </div>
            
        </body>
        </html>
        """
        
        return html
    
    async def send_verification_code(
        self,
        email: str,
        code: str
    ) -> Dict:
        """
        Send verification code via email
        
        Args:
            email: Recipient's email address
            code: Verification code
            
        Returns:
            Dict with success status
        """
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
                <h2>Verify Your Email</h2>
                <p>Your verification code is:</p>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;">
                    {code}
                </div>
                <p>This code expires in 10 minutes.</p>
                <p>If you didn't request this code, please ignore this email.</p>
            </body>
            </html>
            """
            
            params = {
                "from": self.from_email,
                "to": [email],
                "subject": "Verify your FreeFood UCD account",
                "html": html_content
            }
            
            result = resend.Emails.send(params)
            
            logger.info(f"Verification code sent to {email}")
            
            return {
                "success": True,
                "message_id": result.get('id'),
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Error sending verification code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_welcome_message(self, email: str) -> Dict:
        """
        Send welcome email to new user
        
        Args:
            email: Recipient's email address
            
        Returns:
            Dict with success status
        """
        try:
            html_content = """
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 12px; text-align: center;">
                    <h1 style="margin: 0;">🍕 Welcome to FreeFood UCD!</h1>
                </div>
                
                <div style="padding: 30px 0;">
                    <p style="font-size: 16px;">You're all set! You'll now receive instant alerts when UCD societies post about free food.</p>
                    
                    <h3>What to expect:</h3>
                    <ul style="font-size: 15px; line-height: 1.8;">
                        <li>Real-time notifications for free food events</li>
                        <li>Details about location, time, and society</li>
                        <li>Never miss free pizza again!</li>
                    </ul>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <p style="font-size: 18px; color: #059669; font-weight: 600;">Happy eating! 🎉</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            params = {
                "from": self.from_email,
                "to": [email],
                "subject": "Welcome to FreeFood UCD! 🍕",
                "html": html_content
            }
            
            result = resend.Emails.send(params)
            
            logger.info(f"Welcome email sent to {email}")
            
            return {
                "success": True,
                "message_id": result.get('id'),
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_event_reminder(
        self,
        email: str,
        event_data: Dict
    ) -> Dict:
        """
        Send event reminder (1 hour before event starts)
        
        Args:
            email: Recipient's email address
            event_data: Event information dict
            
        Returns:
            Dict with success status
        """
        try:
            subject = f"⏰ Reminder: Free Food in 1 Hour - {event_data.get('society_name', 'UCD Society')}"
            html_content = self._format_reminder_html(event_data)
            
            params = {
                "from": self.from_email,
                "to": [email],
                "subject": subject,
                "html": html_content
            }
            
            result = resend.Emails.send(params)
            
            logger.info(f"Reminder email sent to {email}. ID: {result.get('id')}")
            
            return {
                "success": True,
                "message_id": result.get('id'),
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Error sending reminder email to {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_reminder_html(self, event_data: Dict) -> str:
        """Format event reminder into HTML email"""
        society = event_data.get("society_name", "Unknown Society")
        title = event_data.get("title", "Free Food Event")
        location = event_data.get("location", "Location TBA")
        time = event_data.get("start_time", "Time TBA")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Event Reminder</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">⏰ Starting in 1 Hour!</h1>
            </div>
            
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; margin-bottom: 20px; border-radius: 8px;">
                <p style="margin: 0; font-size: 18px; font-weight: 600; color: #92400e;">Don't forget! Free food event starting soon:</p>
            </div>
            
            <div style="background: #f9fafb; border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                <h2 style="margin-top: 0; color: #111827; font-size: 22px;">{title}</h2>
                
                <div style="margin: 20px 0;">
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>🏛 Society:</strong> {society}
                    </p>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>📍 Location:</strong> {location}
                    </p>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>🕒 Time:</strong> {time}
                    </p>
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
        
        return html


# Alias for backward compatibility
EmailNotifier = EmailService

# Made with Bob
