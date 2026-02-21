from celery import group
from app.workers.celery_app import celery_app
from app.db.base import async_session_maker
from app.db.models import Society, Post, Story, Event, ScrapingLog
from app.services.nlp.extractor import EventExtractor
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def scrape_all_stories(self):
    """
    Scrape stories from all active societies.
    Creates individual tasks for each society.
    """
    try:
        # Run async function in sync context
        return asyncio.run(_scrape_all_stories_async())
    except Exception as e:
        logger.error(f"Error in scrape_all_stories: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_all_stories_async():
    """Async implementation of scrape_all_stories."""
    async with async_session_maker() as session:
        # Get all active societies that should be scraped
        query = select(Society).where(
            Society.is_active == True,
            Society.scrape_stories == True
        )
        result = await session.execute(query)
        societies = result.scalars().all()
        
        logger.info(f"Scraping stories for {len(societies)} societies")
        
        # Create parallel tasks for each society
        job = group(
            scrape_society_stories.s(str(society.id))
            for society in societies
        )
        
        result = job.apply_async()
        return {"societies_queued": len(societies)}


@celery_app.task(bind=True, max_retries=3)
def scrape_society_stories(self, society_id: str):
    """
    Scrape stories from a specific society.
    
    Args:
        society_id: UUID of the society to scrape
    """
    try:
        return asyncio.run(_scrape_society_stories_async(society_id))
    except Exception as e:
        logger.error(f"Error scraping stories for society {society_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_society_stories_async(society_id: str):
    """Async implementation of scrape_society_stories."""
    start_time = datetime.now()
    
    async with async_session_maker() as session:
        # Get society
        society = await session.get(Society, society_id)
        if not society:
            logger.error(f"Society {society_id} not found")
            return {"error": "Society not found"}
        
        try:
            # TODO: Initialize scraper and scrape stories
            # This is a placeholder - actual implementation would use the scraper service
            stories_found = 0
            
            # For now, just log the attempt
            logger.info(f"Would scrape stories for @{society.instagram_handle}")
            
            # Update last check time
            society.last_story_check = datetime.now()
            
            # Log scraping activity
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='story',
                status='success',
                items_found=stories_found,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            session.add(log)
            
            await session.commit()
            
            return {
                "society": society.instagram_handle,
                "stories_found": stories_found,
                "status": "success"
            }
            
        except Exception as e:
            # Log failure
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='story',
                status='failed',
                items_found=0,
                error_message=str(e),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()
            raise


@celery_app.task(bind=True, max_retries=3)
def scrape_all_posts(self):
    """Scrape posts from all active societies."""
    try:
        return asyncio.run(_scrape_all_posts_async())
    except Exception as e:
        logger.error(f"Error in scrape_all_posts: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_all_posts_async():
    """Async implementation of scrape_all_posts."""
    async with async_session_maker() as session:
        query = select(Society).where(
            Society.is_active == True,
            Society.scrape_posts == True
        )
        result = await session.execute(query)
        societies = result.scalars().all()
        
        logger.info(f"Scraping posts for {len(societies)} societies")
        
        job = group(
            scrape_society_posts.s(str(society.id))
            for society in societies
        )
        
        result = job.apply_async()
        return {"societies_queued": len(societies)}


@celery_app.task(bind=True, max_retries=3)
def scrape_society_posts(self, society_id: str):
    """Scrape posts from a specific society."""
    try:
        return asyncio.run(_scrape_society_posts_async(society_id))
    except Exception as e:
        logger.error(f"Error scraping posts for society {society_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_society_posts_async(society_id: str):
    """Async implementation of scrape_society_posts."""
    start_time = datetime.now()
    
    async with async_session_maker() as session:
        society = await session.get(Society, society_id)
        if not society:
            return {"error": "Society not found"}
        
        try:
            # TODO: Implement actual post scraping
            posts_found = 0
            
            logger.info(f"Would scrape posts for @{society.instagram_handle}")
            
            society.last_post_check = datetime.now()
            
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='post',
                status='success',
                items_found=posts_found,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()
            
            return {
                "society": society.instagram_handle,
                "posts_found": posts_found,
                "status": "success"
            }
            
        except Exception as e:
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='post',
                status='failed',
                items_found=0,
                error_message=str(e),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()
            raise


@celery_app.task
def process_scraped_content(content_type: str, content_id: str):
    """
    Process scraped content (post or story) to extract events.
    
    Args:
        content_type: 'post' or 'story'
        content_id: UUID of the content
    """
    return asyncio.run(_process_scraped_content_async(content_type, content_id))


async def _process_scraped_content_async(content_type: str, content_id: str):
    """Async implementation of process_scraped_content."""
    async with async_session_maker() as session:
        extractor = EventExtractor()
        
        # Get content
        if content_type == 'story':
            content = await session.get(Story, content_id)
            text = content.story_text if content else None
        else:
            content = await session.get(Post, content_id)
            text = content.caption if content else None
        
        if not content or not text:
            return {"error": "Content not found"}
        
        # Extract event
        event_data = extractor.extract_event(text, content_type)
        
        if event_data:
            # Create event
            event = Event(
                society_id=content.society_id,
                title=event_data['title'],
                description=event_data.get('description'),
                location=event_data.get('location'),
                location_building=event_data.get('location_building'),
                location_room=event_data.get('location_room'),
                start_time=event_data['start_time'],
                end_time=event_data.get('end_time'),
                source_type=content_type,
                source_id=content.id,
                confidence_score=event_data['confidence_score'],
                raw_text=event_data['raw_text'],
                extracted_data=event_data.get('extracted_data', {})
            )
            
            session.add(event)
            
            # Mark content as processed
            content.processed = True
            content.is_free_food = True
            
            await session.commit()
            await session.refresh(event)
            
            # Trigger notifications
            from app.workers.notification_tasks import notify_event
            notify_event.delay(str(event.id))
            
            return {
                "event_created": True,
                "event_id": str(event.id),
                "confidence": event_data['confidence_score']
            }
        else:
            # Mark as processed but not free food
            content.processed = True
            content.is_free_food = False
            await session.commit()
            
            return {"event_created": False}

# Made with Bob
