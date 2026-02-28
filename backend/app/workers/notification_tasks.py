from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app
from app.db.base import task_db_session
from app.db.models import Event, Post, Society, User, UserSocietyPreference, NotificationLog
from app.services.notifications.whatsapp import WhatsAppService
from app.services.notifications.brevo import BrevoEmailService
from app.core.config import settings
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
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
    async with task_db_session() as session:
        # Get event with society
        event = await session.get(Event, event_id)
        if not event:
            logger.error(f"Event {event_id} not found")
            return {"error": "Event not found"}

        # Get eligible users
        users = await _get_eligible_users(session, event)

        if not users:
            logger.info(f"No eligible users for event {event_id}")
            # Still mark notified so reminder task doesn't pick it up
            event.notified = True
            event.notification_sent_at = datetime.now(timezone.utc)
            await session.commit()
            return {"users_notified": 0}

        logger.info(f"Notifying {len(users)} users about event {event_id}")

        # Mark event as notified BEFORE sending (idempotency: safe to retry)
        event.notified = True
        event.notification_sent_at = datetime.now(timezone.utc)
        await session.commit()

        # Load society and source URL for event data
        society = await session.get(Society, event.society_id)

        source_url = None
        if event.source_type == 'post' and event.source_id:
            post = await session.get(Post, event.source_id)
            source_url = post.source_url if post else None

        now = datetime.now(timezone.utc)
        event_data = {
            "society_name": society.name if society else "Unknown Society",
            "title": event.title or "Free Food Event",
            "location": event.location or "Location TBA",
            "start_time": event.start_time.strftime("%I:%M %p") if event.start_time else "Time TBA",
            "date": event.start_time.strftime("%A, %B %d") if event.start_time else "Date TBA",
            "source_type": event.source_type or "post",
            "description": event.description or "",
            "members_only": (event.extracted_data or {}).get('members_only', False),
            "source_url": source_url,
            "reminder_will_fire": bool(event.start_time and event.start_time > now + timedelta(minutes=75)),
        }

        # Filter email users
        email_users = [u for u in users if u.notification_preferences.get('email', False)]

        if settings.NOTIFICATION_TEST_EMAILS:
            allowlist = {e.strip().lower() for e in settings.NOTIFICATION_TEST_EMAILS.split(",")}
            email_users = [u for u in email_users if u.email and u.email.lower() in allowlist]

        # Skip users already notified in a previous attempt (idempotency on retry)
        already_notified_result = await session.execute(
            select(NotificationLog.user_id).where(
                NotificationLog.event_id == event_id,
                NotificationLog.notification_type == 'email',
            )
        )
        already_notified_ids = {row[0] for row in already_notified_result}
        email_users = [u for u in email_users if u.id not in already_notified_ids]

        # Send emails concurrently (max 10 in flight)
        email_notifier = BrevoEmailService()
        semaphore = asyncio.Semaphore(10)

        async def _send_email(user):
            async with semaphore:
                result = await email_notifier.send_event_notification(user.email, event_data)
                return user, result

        send_outcomes = await asyncio.gather(
            *[_send_email(u) for u in email_users if u.email],
            return_exceptions=True,
        )

        email_results = []
        for outcome in send_outcomes:
            if isinstance(outcome, Exception):
                logger.error(f"Email send error: {outcome}")
                continue
            user, result = outcome
            email_results.append({
                'user_id': str(user.id),
                'status': 'sent' if result.get('success') else 'failed',
                'error': result.get('error'),
            })

        if email_results:
            await _log_notifications(session, event_id, email_results, 'email')

        return {
            "users_notified": len(users),
            "email_sent": len(email_results),
        }


async def _get_eligible_users(session, event):
    """Get users who should be notified about this event (single JOIN query)."""
    query = (
        select(User)
        .outerjoin(
            UserSocietyPreference,
            and_(
                UserSocietyPreference.user_id == User.id,
                UserSocietyPreference.society_id == event.society_id,
            ),
        )
        .where(
            User.is_active == True,
            or_(
                UserSocietyPreference.notify == True,
                UserSocietyPreference.user_id == None,
            ),
        )
    )
    result = await session.execute(query)
    return result.scalars().all()


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
    async with task_db_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"error": "User not found"}

        if method == 'whatsapp' and user.phone_number:
            notifier = WhatsAppService()
            result = await notifier.send_verification_code(user.phone_number, code)
            return result
        elif method == 'email' and user.email:
            notifier = BrevoEmailService()
            result = await notifier.send_verification_code(user.email, code)
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
    async with task_db_session() as session:
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
            notifier = BrevoEmailService()
            results['email'] = await notifier.send_welcome_message(user.email)

        return results


@celery_app.task
def send_upcoming_event_notifications():
    """
    Check for events starting within 75 minutes and send reminder notifications.
    Runs every 10 minutes to catch events.
    """
    return asyncio.run(_send_upcoming_event_notifications_async())


async def _send_upcoming_event_notifications_async():
    """Async implementation of send_upcoming_event_notifications."""
    async with task_db_session() as session:
        now = datetime.now(timezone.utc)
        window_start = now
        window_end = now + timedelta(minutes=75)

        # Find events that:
        # 1. Start within the next 75 minutes
        # 2. Haven't been reminded yet
        # 3. Are active
        # 4. Were NOT already notified via the discovery path in the last 30 minutes
        #    (prevents double-send when scrape and reminder overlap)
        query = select(Event).options(selectinload(Event.society)).where(
            Event.start_time >= window_start,
            Event.start_time <= window_end,
            Event.is_active == True,
            Event.reminder_sent == False,
            ~and_(
                Event.notified == True,
                Event.notification_sent_at >= now - timedelta(minutes=30),
            ),
        )
        result = await session.execute(query)
        upcoming_events = result.scalars().all()

        if not upcoming_events:
            logger.info("No upcoming events requiring reminders")
            return {"events_reminded": 0}

        logger.info(f"Sending reminders for {len(upcoming_events)} upcoming events")

        total_notified = 0
        for event in upcoming_events:
            # Get eligible users for this event
            users = await _get_eligible_users(session, event)

            if not users:
                event.reminder_sent = True
                event.reminder_sent_at = datetime.now(timezone.utc)
                continue

            # Format event data for notifications
            reminder_source_url = None
            if event.source_type == 'post' and event.source_id:
                reminder_post = await session.get(Post, event.source_id)
                reminder_source_url = reminder_post.source_url if reminder_post else None

            event_data = {
                'society_name': event.society.name if event.society else 'Unknown Society',
                'title': event.title,
                'location': event.location or 'Location TBA',
                'start_time': event.start_time.strftime('%I:%M %p') if event.start_time else 'Time TBA',
                'date': event.start_time.strftime('%A, %B %d') if event.start_time else 'Date TBA',
                'members_only': (event.extracted_data or {}).get('members_only', False),
                'source_url': reminder_source_url,
            }

            # Send WhatsApp reminders
            whatsapp_users = [u for u in users if u.notification_preferences.get('whatsapp', False)]

            whatsapp_results = []
            if whatsapp_users:
                try:
                    whatsapp_notifier = WhatsAppService()
                    semaphore = asyncio.Semaphore(10)

                    async def _send_whatsapp(user):
                        async with semaphore:
                            r = await whatsapp_notifier.send_event_reminder(user.phone_number, event_data)
                            return user, r

                    wa_outcomes = await asyncio.gather(
                        *[_send_whatsapp(u) for u in whatsapp_users if u.phone_number],
                        return_exceptions=True,
                    )
                    for outcome in wa_outcomes:
                        if isinstance(outcome, Exception):
                            logger.error(f"WhatsApp send error: {outcome}")
                            continue
                        user, r = outcome
                        whatsapp_results.append({
                            'user_id': str(user.id),
                            'status': 'success' if r.get('success') else 'failed',
                            'error': r.get('error'),
                        })
                except Exception as e:
                    logger.error(f"WhatsApp notifier failed: {e}")

            if whatsapp_results:
                await _log_notifications(session, str(event.id), whatsapp_results, 'whatsapp_reminder')

            # Send email reminders
            email_notifier = BrevoEmailService()
            email_users = [u for u in users if u.notification_preferences.get('email', False)]

            if settings.NOTIFICATION_TEST_EMAILS:
                allowlist = {e.strip().lower() for e in settings.NOTIFICATION_TEST_EMAILS.split(",")}
                email_users = [u for u in email_users if u.email and u.email.lower() in allowlist]

            semaphore = asyncio.Semaphore(10)

            async def _send_reminder_email(user):
                async with semaphore:
                    r = await email_notifier.send_event_reminder(user.email, event_data)
                    return user, r

            email_outcomes = await asyncio.gather(
                *[_send_reminder_email(u) for u in email_users if u.email],
                return_exceptions=True,
            )

            email_results = []
            for outcome in email_outcomes:
                if isinstance(outcome, Exception):
                    logger.error(f"Email reminder send error: {outcome}")
                    continue
                user, r = outcome
                email_results.append({
                    'user_id': str(user.id),
                    'status': 'success' if r.get('success') else 'failed',
                    'error': r.get('error'),
                })

            if email_results:
                await _log_notifications(session, str(event.id), email_results, 'email_reminder')

            # Mark event as reminded
            event.reminder_sent = True
            event.reminder_sent_at = datetime.now(timezone.utc)
            total_notified += len(users)

        await session.commit()

        logger.info(f"Sent reminders for {len(upcoming_events)} events to {total_notified} users")

        return {
            "events_reminded": len(upcoming_events),
            "users_notified": total_notified,
        }


@celery_app.task(bind=True, max_retries=3)
def notify_events_batch(self, event_ids: list):
    """
    Send one combined email per user for all events found in a single scrape run.
    Replaces per-event notify_event calls to prevent email spam when multiple events
    are discovered in the same scrape.
    """
    try:
        return asyncio.run(_notify_events_batch_async(event_ids))
    except Exception as e:
        logger.error(f"Error in batch event notification: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _notify_events_batch_async(event_ids: list):
    """
    Async implementation of notify_events_batch.

    Deduplicates eligible users across all events and sends each user one email
    covering all events they're eligible for. Uses single-event template for 1 event,
    multi-event template for 2+.
    """
    if not event_ids:
        return {"users_notified": 0}

    async with task_db_session() as session:
        now = datetime.now(timezone.utc)

        # Load all events
        events = []
        for eid in event_ids:
            event = await session.get(Event, eid)
            if event:
                events.append(event)

        if not events:
            logger.warning(f"No events found for batch IDs: {event_ids}")
            return {"users_notified": 0}

        # Mark all events notified BEFORE sending (idempotency: safe to retry)
        for event in events:
            event.notified = True
            event.notification_sent_at = now
        await session.commit()

        # Query already-notified (event_id, user_id) pairs for idempotency on retry
        already_logged_result = await session.execute(
            select(NotificationLog.event_id, NotificationLog.user_id).where(
                NotificationLog.event_id.in_([e.id for e in events]),
                NotificationLog.notification_type == 'email',
            )
        )
        already_logged = {(str(row[0]), str(row[1])) for row in already_logged_result}

        # Build user -> [eligible event_data] mapping across all events
        user_events_map: dict = {}  # uid -> {'user': User, 'events': [event_data]}

        for event in events:
            source_url = None
            if event.source_type == 'post' and event.source_id:
                post = await session.get(Post, event.source_id)
                source_url = post.source_url if post else None

            society = await session.get(Society, event.society_id)
            event_data = {
                "event_id": str(event.id),
                "society_name": society.name if society else "Unknown Society",
                "title": event.title or "Free Food Event",
                "location": event.location or "Location TBA",
                "start_time": event.start_time.strftime("%I:%M %p") if event.start_time else "Time TBA",
                "date": event.start_time.strftime("%A, %B %d") if event.start_time else "Date TBA",
                "source_type": event.source_type or "post",
                "description": event.description or "",
                "members_only": (event.extracted_data or {}).get('members_only', False),
                "source_url": source_url,
                "reminder_will_fire": bool(event.start_time and event.start_time > now + timedelta(minutes=75)),
            }

            users = await _get_eligible_users(session, event)
            email_users = [u for u in users if u.notification_preferences.get('email', False)]

            for user in email_users:
                uid = str(user.id)
                eid = str(event.id)
                if (eid, uid) in already_logged:
                    continue  # Already sent for this event in a previous attempt
                if uid not in user_events_map:
                    user_events_map[uid] = {'user': user, 'events': []}
                user_events_map[uid]['events'].append(event_data)

        # Apply test email allowlist
        if settings.NOTIFICATION_TEST_EMAILS:
            allowlist = {e.strip().lower() for e in settings.NOTIFICATION_TEST_EMAILS.split(",")}
            user_events_map = {
                uid: v for uid, v in user_events_map.items()
                if v['user'].email and v['user'].email.lower() in allowlist
            }

        if not user_events_map:
            logger.info(f"No users to notify in batch for {len(events)} event(s)")
            return {"users_notified": 0}

        logger.info(f"Sending batch notification to {len(user_events_map)} users for {len(events)} event(s)")

        email_notifier = BrevoEmailService()
        semaphore = asyncio.Semaphore(10)

        async def _send_batch(uid, entry):
            user = entry['user']
            user_events = entry['events']
            async with semaphore:
                if len(user_events) == 1:
                    result = await email_notifier.send_event_notification(user.email, user_events[0])
                else:
                    result = await email_notifier.send_batch_event_notification(user.email, user_events)
                return uid, user_events, result

        outcomes = await asyncio.gather(
            *[_send_batch(uid, entry) for uid, entry in user_events_map.items() if entry['user'].email],
            return_exceptions=True,
        )

        log_entries = []
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                logger.error(f"Batch email send error: {outcome}")
                continue
            uid, user_events, result = outcome
            for ed in user_events:
                log_entries.append({
                    'user_id': uid,
                    'event_id': ed['event_id'],
                    'status': 'sent' if result.get('success') else 'failed',
                    'error': result.get('error'),
                })

        for entry in log_entries:
            session.add(NotificationLog(
                event_id=entry['event_id'],
                user_id=entry['user_id'],
                notification_type='email',
                status=entry['status'],
                error_message=entry.get('error'),
            ))
        await session.commit()

        return {
            "users_notified": len(user_events_map),
            "events_in_batch": len(events),
        }


# Made with Bob
