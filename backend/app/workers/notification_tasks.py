from app.workers.celery_app import celery_app
from app.db.base import async_session_maker
from app.db.models import Event, User, UserSocietyPreference, NotificationLog
from app.services.notifications.whatsapp import WhatsAppService
from app.services.notifications.email import EmailNotifier
from sqlalchemy import select, and_
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def notify_event(self, event_id: str):
    """
    Send notifications for a new event to all eligible users.
    
    Args:
        event_id: UUID of the event to notify about
    """
    try:
        return asyncio.run(_notify_event_async(event_id))
    except Exception as e:
        logger.error(f"Error notifying event {event_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _notify_event_async(event_id: str):
    """Async implementation of notify_event."""
    async with async_session_maker() as session:
        # Get event with society
        event = await session.get(Event, event_id)
        if not event:
            logger.error(f"Event {event_id} not found")
            return {"error": "Event not found"}
        
        # Get eligible users
        users = await _get_eligible_users(session, event)
        
        if not users:
            logger.info(f"No eligible users for event {event_id}")
            return {"users_notified": 0}
        
        logger.info(f"Notifying {len(users)} users about event {event_id}")
        
        # Send WhatsApp notifications
        whatsapp_notifier = WhatsAppService()
        whatsapp_users = [u for u in users if u.notification_preferences.get('whatsapp', False)]
        
        if whatsapp_users:
            whatsapp_results = await whatsapp_notifier.send_event_notification(event, whatsapp_users)
            await _log_notifications(session, event_id, whatsapp_results, 'whatsapp')
        
        # Send email notifications
        email_notifier = EmailNotifier()
        email_users = [u for u in users if u.notification_preferences.get('email', False)]
        
        if email_users:
            email_results = await email_notifier.send_event_notification(event, email_users)
            await _log_notifications(session, event_id, email_results, 'email')
        
        # Mark event as notified
        event.notified = True
        event.notification_sent_at = datetime.now()
        await session.commit()
        
        return {
            "users_notified": len(users),
            "whatsapp_sent": len(whatsapp_users),
            "email_sent": len(email_users)
        }


async def _get_eligible_users(session, event):
    """Get users who should be notified about this event."""
    # Get all active users
    query = select(User).where(User.is_active == True)
    result = await session.execute(query)
    all_users = result.scalars().all()
    
    eligible_users = []
    
    for user in all_users:
        # Check if user has society preferences
        pref_query = select(UserSocietyPreference).where(
            and_(
                UserSocietyPreference.user_id == user.id,
                UserSocietyPreference.society_id == event.society_id
            )
        )
        pref_result = await session.execute(pref_query)
        preference = pref_result.scalar_one_or_none()
        
        # If no preference exists, notify by default
        # If preference exists, check if notify is True
        if preference is None or preference.notify:
            eligible_users.append(user)
    
    return eligible_users


async def _log_notifications(session, event_id: str, results: list, notification_type: str):
    """Log notification results to database."""
    for result in results:
        log = NotificationLog(
            event_id=event_id,
            user_id=result['user_id'],
            notification_type=notification_type,
            status=result['status'],
            error_message=result.get('error')
        )
        session.add(log)
    
    await session.commit()


@celery_app.task
def send_verification_code(user_id: str, code: str, method: str):
    """
    Send verification code to user.
    
    Args:
        user_id: UUID of the user
        code: Verification code
        method: 'whatsapp' or 'email'
    """
    return asyncio.run(_send_verification_code_async(user_id, code, method))


async def _send_verification_code_async(user_id: str, code: str, method: str):
    """Async implementation of send_verification_code."""
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        if method == 'whatsapp' and user.phone_number:
            notifier = WhatsAppService()
            result = await notifier.send_verification_code(user.phone_number, code)
            return result
        elif method == 'email' and user.email:
            notifier = EmailNotifier()
            result = await notifier.send_verification_email(user.email, code)
            return result
        else:
            return {"error": "Invalid method or missing contact info"}


@celery_app.task
def send_welcome_message(user_id: str):
    """
    Send welcome message to new user.
    
    Args:
        user_id: UUID of the user
    """
    return asyncio.run(_send_welcome_message_async(user_id))


async def _send_welcome_message_async(user_id: str):
    """Async implementation of send_welcome_message."""
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        results = {}
        
        # Send WhatsApp welcome if verified
        if user.phone_number and user.whatsapp_verified:
            notifier = WhatsAppService()
            results['whatsapp'] = await notifier.send_welcome_message(user.phone_number)
        
        # Send email welcome if verified
        if user.email and user.email_verified:
            notifier = EmailNotifier()
            results['email'] = await notifier.send_welcome_email(user.email)
        
        return results


# Import datetime
from datetime import datetime

# Made with Bob
