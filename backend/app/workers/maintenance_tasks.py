from app.workers.celery_app import celery_app
from app.db.base import task_db_session
from app.db.models import Story, Event, Post, ScrapingLog
from sqlalchemy import select, delete
from datetime import datetime, timedelta, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_stories():
    """
    Delete stories that have expired (older than 24 hours).
    Instagram stories expire after 24 hours, so we clean up old data.
    """
    return asyncio.run(_cleanup_expired_stories_async())


async def _cleanup_expired_stories_async():
    """Async implementation of cleanup_expired_stories."""
    async with task_db_session() as session:
        # Delete stories older than 48 hours (give some buffer)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
        
        query = delete(Story).where(Story.detected_at < cutoff_time)
        result = await session.execute(query)
        deleted_count = result.rowcount
        
        await session.commit()
        
        logger.info(f"Cleaned up {deleted_count} expired stories")
        return {"deleted_stories": deleted_count}


@celery_app.task
def archive_old_events():
    """
    Archive events that are older than 7 days.
    Marks them as inactive rather than deleting for historical data.
    """
    return asyncio.run(_archive_old_events_async())


async def _archive_old_events_async():
    """Async implementation of archive_old_events."""
    async with task_db_session() as session:
        # Archive events older than 7 days
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        query = select(Event).where(
            Event.start_time < cutoff_time,
            Event.is_active == True
        )
        result = await session.execute(query)
        events = result.scalars().all()
        
        for event in events:
            event.is_active = False
        
        await session.commit()
        
        logger.info(f"Archived {len(events)} old events")
        return {"archived_events": len(events)}


@celery_app.task
def cleanup_old_logs():
    """
    Delete scraping logs older than 30 days to prevent database bloat.
    """
    return asyncio.run(_cleanup_old_logs_async())


async def _cleanup_old_logs_async():
    """Async implementation of cleanup_old_logs."""
    async with task_db_session() as session:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        query = delete(ScrapingLog).where(ScrapingLog.created_at < cutoff_time)
        result = await session.execute(query)
        deleted_count = result.rowcount
        
        await session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old scraping logs")
        return {"deleted_logs": deleted_count}


@celery_app.task
def health_check():
    """
    Perform health check on the system.
    Checks database connectivity and recent scraping activity.
    """
    return asyncio.run(_health_check_async())


async def _health_check_async():
    """Async implementation of health_check."""
    try:
        async with task_db_session() as session:
            # Check database connectivity
            await session.execute(select(1))
            
            # Check recent scraping activity (last 10 minutes)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            query = select(ScrapingLog).where(
                ScrapingLog.created_at >= recent_cutoff
            )
            result = await session.execute(query)
            recent_logs = result.scalars().all()
            
            # Calculate success rate
            if recent_logs:
                successful = sum(1 for log in recent_logs if log.status == 'success')
                success_rate = (successful / len(recent_logs)) * 100
            else:
                success_rate = 0
            
            health_status = {
                "status": "healthy",
                "database": "connected",
                "recent_scrapes": len(recent_logs),
                "success_rate": f"{success_rate:.1f}%",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Health check: {health_status}")
            return health_status
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@celery_app.task
def reprocess_nlp_failed_posts():
    """
    F6: Re-queue posts that failed NLP processing due to API errors.
    Only retries posts where nlp_failed=True AND processed=False
    (processed=True means it was a data error, not an API error — don't retry).
    Processes in batches of 50 to avoid overwhelming the Gemini API.
    """
    return asyncio.run(_reprocess_nlp_failed_posts_async())


async def _reprocess_nlp_failed_posts_async():
    """Async implementation of reprocess_nlp_failed_posts."""
    from app.workers.scraping_tasks import _process_scraped_content_async

    async with task_db_session() as session:
        # Find posts that failed NLP and haven't been processed yet
        result = await session.execute(
            select(Post)
            .where(Post.nlp_failed == True, Post.processed == False)
            .order_by(Post.detected_at.desc())
            .limit(50)
        )
        failed_posts = result.scalars().all()

        if not failed_posts:
            logger.info("reprocess_nlp_failed_posts: no failed posts to retry")
            return {"requeued": 0}

        requeued = 0
        for post in failed_posts:
            try:
                # Reset the failure flag before retrying
                post.nlp_failed = False
                post.nlp_error = None
                await session.flush()

                nlp_result = await _process_scraped_content_async("post", str(post.id))
                logger.info(
                    f"Reprocessed post {post.id}: "
                    f"event_created={nlp_result.get('event_created')}"
                )
                requeued += 1
            except Exception as exc:
                logger.error(f"Reprocess failed again for post {post.id}: {exc}")
                post.nlp_failed = True
                post.nlp_error = str(exc)[:500]
                post.processed = False

        await session.commit()
        logger.info(f"reprocess_nlp_failed_posts: requeued {requeued} posts")
        return {"requeued": requeued}

# Made with Bob
