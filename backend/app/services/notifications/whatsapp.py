"""
WhatsApp notification service using Twilio
"""
import logging
from typing import Dict, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp notifications via Twilio"""
    
    def __init__(self):
        """Initialize Twilio client"""
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number for WhatsApp
        
        Args:
            phone: Phone number (e.g., +353858760120 or 353858760120)
            
        Returns:
            Formatted WhatsApp number (e.g., whatsapp:+353858760120)
        """
        # Remove any existing whatsapp: prefix
        phone = phone.replace("whatsapp:", "")
        
        # Add + if not present
        if not phone.startswith("+"):
            phone = f"+{phone}"
        
        return f"whatsapp:{phone}"
    
    async def send_event_notification(
        self,
        phone_number: str,
        event_data: Dict
    ) -> Dict:
        """
        Send free food event notification via WhatsApp
        
        Args:
            phone_number: Recipient's phone number
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
            # Format phone number
            to_number = self._format_phone_number(phone_number)
            
            # Create message body
            message_body = self._format_event_message(event_data)
            
            # Send message
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=to_number
            )
            
            logger.info(
                f"WhatsApp notification sent successfully. "
                f"SID: {message.sid}, Status: {message.status}"
            )
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to_number
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending WhatsApp: {e.msg}")
            return {
                "success": False,
                "error": e.msg,
                "error_code": e.code
            }
        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_event_message(self, event_data: Dict) -> str:
        """
        Format event data into WhatsApp message
        
        Args:
            event_data: Event information
            
        Returns:
            Formatted message string
        """
        society = event_data.get("society_name", "Unknown Society")
        title = event_data.get("title", "Free Food Event")
        location = event_data.get("location", "Location TBA")
        time = event_data.get("start_time", "Time TBA")
        date = event_data.get("date", "Date TBA")
        source = event_data.get("source_type", "post")
        
        message = f"""🍕 FREE FOOD ALERT

Society: {society}
📍 Location: {location}
🕒 {time}
📅 {date}
🔗 Source: {source.capitalize()}

Don't miss out! 🎉"""
        
        return message
    
    async def send_verification_code(
        self,
        phone_number: str,
        code: str
    ) -> Dict:
        """
        Send verification code via WhatsApp
        
        Args:
            phone_number: Recipient's phone number
            code: Verification code
            
        Returns:
            Dict with success status
        """
        try:
            to_number = self._format_phone_number(phone_number)
            
            message_body = f"""🔐 FreeFood UCD Verification

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this message."""
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=to_number
            )
            
            logger.info(f"Verification code sent. SID: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
            
        except Exception as e:
            logger.error(f"Error sending verification code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_welcome_message(self, phone_number: str) -> Dict:
        """
        Send welcome message to new user
        
        Args:
            phone_number: Recipient's phone number
            
        Returns:
            Dict with success status
        """
        try:
            to_number = self._format_phone_number(phone_number)
            
            message_body = """🎉 Welcome to FreeFood UCD!

You'll now receive notifications about free food events from UCD societies.

You can manage your preferences anytime at freefooducd.ie

Happy eating! 🍕"""
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=to_number
            )
            
            logger.info(f"Welcome message sent. SID: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_event_reminder(
        self,
        phone_number: str,
        event_data: Dict
    ) -> Dict:
        """
        Send event reminder via WhatsApp (1 hour before event)
        
        Args:
            phone_number: Recipient's phone number
            event_data: Event information dict
            
        Returns:
            Dict with success status
        """
        try:
            to_number = self._format_phone_number(phone_number)
            
            society = event_data.get("society_name", "Unknown Society")
            title = event_data.get("title", "Free Food Event")
            location = event_data.get("location", "Location TBA")
            time = event_data.get("start_time", "Time TBA")
            
            message_body = f"""⏰ REMINDER: Starting in 1 Hour!

🍕 {title}

Society: {society}
📍 Location: {location}
🕒 Time: {time}

Don't miss out! Head over now! 🏃‍♂️💨"""
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=to_number
            )
            
            logger.info(f"Reminder sent. SID: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
            
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Made with Bob
