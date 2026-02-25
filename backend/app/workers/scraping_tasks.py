from celery import group
from app.workers.celery_app import celery_app
from app.db.base import task_db_session
from app.db.models import Society, Post, Story, Event, ScrapingLog
from app.services.nlp.extractor import EventExtractor
from app.services.scraper.apify_scraper import ApifyInstagramScraper
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging
import asyncio
import hashlib

logger = logging.getLogger(__name__)

def get_scraper():
    """Create a fresh Apify scraper instance (no caching to avoid stale state)."""
    from app.core.config import settings
    return ApifyInstagramScraper(api_token=settings.APIFY_API_TOKEN)


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
    async with task_db_session() as session:
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
    
    async with task_db_session() as session:
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
    """
    Async implementation of scrape_all_posts.

    Issues ONE Apify actor run for all active societies instead of N separate
    runs, reducing overhead from O(N) actor startups to O(1).
    """
    start_time = datetime.now()

    async with task_db_session() as session:
        query = select(Society).where(
            Society.is_active == True,
            Society.scrape_posts == True
        )
        result = await session.execute(query)
        societies = result.scalars().all()

        if not societies:
            logger.info("No active societies to scrape")
            return {"societies_scraped": 0, "total_new_posts": 0}

        handles = [s.instagram_handle for s in societies]
        society_by_handle = {s.instagram_handle.lower(): s for s in societies}

        logger.info(f"Batch scraping {len(handles)} societies in one Apify run")

        scraper = get_scraper()
        batch_results = await scraper.scrape_posts_batch(handles, max_posts_per_user=3)

        logger.info(f"Batch returned results for {len(batch_results)}/{len(handles)} societies")

        total_new_posts = 0

        for handle_lower, posts_data in batch_results.items():
            society = society_by_handle.get(handle_lower)
            if not society:
                logger.warning(f"Got results for unknown handle @{handle_lower}, skipping")
                continue

            posts_found = 0
            new_posts = 0

            for post_data in posts_data:
                post_id = post_data["url"].split("/p/")[-1].rstrip("/")

                # Skip posts older than 7 days
                post_age = datetime.now(timezone.utc) - post_data["timestamp"]
                if post_age.days > 7:
                    logger.info(f"Skipping old post from @{handle_lower}: {post_age.days} days old")
                    continue

                # Skip already-saved posts
                existing = await session.execute(
                    select(Post).where(
                        Post.society_id == society.id,
                        Post.instagram_post_id == post_id
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                post = Post(
                    society_id=society.id,
                    instagram_post_id=post_id,
                    caption=post_data["caption"],
                    media_urls=[post_data["image_url"]] if post_data.get("image_url") else [],
                    source_url=post_data["url"],
                    detected_at=post_data["timestamp"],
                    processed=False,
                )
                session.add(post)
                await session.flush()

                new_posts += 1
                posts_found += 1
                total_new_posts += 1

                try:
                    await _process_scraped_content_async("post", str(post.id))
                except Exception as nlp_error:
                    logger.error(f"NLP processing failed for post {post.id}: {nlp_error}")

                logger.info(f"New post from @{handle_lower}: {post_data['url']}")

            society.last_post_check = datetime.now()
            session.add(ScrapingLog(
                society_id=society.id,
                scrape_type="post",
                status="success",
                items_found=posts_found,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            ))

        # Log societies that returned no results (private / no posts)
        for handle_lower, society in society_by_handle.items():
            if handle_lower not in batch_results:
                society.last_post_check = datetime.now()
                session.add(ScrapingLog(
                    society_id=society.id,
                    scrape_type="post",
                    status="success",
                    items_found=0,
                    duration_ms=0,
                ))

        await session.commit()

        logger.info(
            f"Batch scrape complete: {total_new_posts} new posts "
            f"from {len(batch_results)} societies "
            f"in {(datetime.now() - start_time).seconds}s"
        )
        return {
            "societies_scraped": len(societies),
            "societies_with_results": len(batch_results),
            "total_new_posts": total_new_posts,
        }


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
    print(f"[DEBUG] _scrape_society_posts_async called with society_id: {society_id}")
    logger.info(f"[DEBUG] _scrape_society_posts_async called with society_id: {society_id}")
    start_time = datetime.now()
    
    async with task_db_session() as session:
        society = await session.get(Society, society_id)
        if not society:
            print(f"[DEBUG] Society not found: {society_id}")
            return {"error": "Society not found"}
        
        print(f"[DEBUG] Found society: {society.name} (@{society.instagram_handle})")
        
        try:
            print(f"[DEBUG] About to scrape posts for @{society.instagram_handle}")
            logger.info(f"Scraping posts for @{society.instagram_handle}")
            
            # Get Apify scraper instance
            print(f"[DEBUG] Getting scraper instance...")
            scraper = get_scraper()
            print(f"[DEBUG] Scraper instance created: {type(scraper)}")
            
            # Scrape last 3 posts (societies post 2-3 times/week)
            # Apify handles authentication automatically
            print(f"[DEBUG] Calling scraper.scrape_posts for @{society.instagram_handle}")
            posts_data = await scraper.scrape_posts(society.instagram_handle, max_posts=3)
            print(f"[DEBUG] scraper.scrape_posts returned {len(posts_data)} posts")
            
            logger.info(f"Apify returned {len(posts_data)} posts for @{society.instagram_handle}")
            if len(posts_data) == 0:
                logger.warning(f"No posts returned by Apify for @{society.instagram_handle}")
            
            posts_found = 0
            new_posts = 0
            
            for post_data in posts_data:
                # Extract post ID from URL (e.g., https://instagram.com/p/ABC123/)
                post_id = post_data['url'].split('/p/')[-1].rstrip('/')
                
                # Filter out old posts (>7 days old)
                post_timestamp = post_data['timestamp']
                post_age = datetime.now(timezone.utc) - post_timestamp
                if post_age.days > 7:
                    logger.info(f"Skipping old post from @{society.instagram_handle}: {post_age.days} days old")
                    continue
                
                # Check if post already exists
                existing_query = select(Post).where(
                    Post.society_id == society.id,
                    Post.instagram_post_id == post_id
                )
                result = await session.execute(existing_query)
                existing_post = result.scalar_one_or_none()
                
                if existing_post:
                    logger.debug(f"Post already exists: {post_data['url']}")
                    continue
                
                # Create new post
                post = Post(
                    society_id=society.id,
                    instagram_post_id=post_id,
                    caption=post_data['caption'],
                    media_urls=[post_data.get('image_url')] if post_data.get('image_url') else [],
                    source_url=post_data['url'],
                    detected_at=post_data['timestamp'],
                    processed=False
                )
                
                session.add(post)
                await session.flush()  # Get post ID
                
                new_posts += 1
                posts_found += 1
                
                # Process NLP synchronously (no Celery on Railway)
                try:
                    await _process_scraped_content_async('post', str(post.id))
                except Exception as nlp_error:
                    logger.error(f"NLP processing failed for post {post.id}: {nlp_error}")
                
                logger.info(f"New post from @{society.instagram_handle}: {post_data['url']}")
            
            # Update last check time
            society.last_post_check = datetime.now()
            
            # Log scraping activity
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='post',
                status='success',
                items_found=posts_found,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()
            
            logger.info(f"Scraped {posts_found} posts from @{society.instagram_handle} ({new_posts} new)")
            
            return {
                "society": society.instagram_handle,
                "posts_found": posts_found,
                "new_posts": new_posts,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error scraping posts for @{society.instagram_handle}: {e}")
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
    async with task_db_session() as session:
        extractor = EventExtractor()
        
        # Get content
        if content_type == 'story':
            content = await session.get(Story, content_id)
            text = content.story_text if content else None
        else:
            content = await session.get(Post, content_id)
            text = content.caption if content else ""
            
            # Extract text from images using OCR
            if content and content.media_urls:
                from app.services.ocr.image_text_extractor import ImageTextExtractor
                ocr = ImageTextExtractor()
                
                logger.info(f"Extracting text from {len(content.media_urls)} images")
                ocr_text = ocr.extract_text_from_urls(content.media_urls)
                
                if ocr_text:
                    # Combine caption and OCR text
                    text = f"{text}\n\n[Image Text]\n{ocr_text}"
                    logger.info(f"Combined text length: {len(text)} chars")
        
        if not content or not text:
            logger.warning(f"No text found for {content_type} {content_id}")
            return {"error": "Content not found or empty"}
        
        # Extract event with post timestamp for better date validation
        post_timestamp = content.detected_at if hasattr(content, 'detected_at') else None
        logger.info(f"Processing {content_type} {content_id} with {len(text)} chars")
        event_data = extractor.extract_event(text, content_type, post_timestamp)
        
        if event_data:
            # Check for duplicate events (same time + location within 1 hour window)
            start_time = event_data['start_time']
            location = event_data.get('location', '').lower().strip()
            
            # Query for similar events within ±1 hour
            time_window_start = start_time - timedelta(hours=1)
            time_window_end = start_time + timedelta(hours=1)
            
            duplicate_query = select(Event).where(
                Event.start_time >= time_window_start,
                Event.start_time <= time_window_end,
                Event.is_active == True
            )
            result = await session.execute(duplicate_query)
            existing_events = result.scalars().all()
            
            # Check if any existing event has similar location
            is_duplicate = False
            for existing in existing_events:
                existing_location = (existing.location or '').lower().strip()
                # Consider duplicate if locations match or one is empty
                if location and existing_location:
                    # Simple string matching (could be improved with fuzzy matching)
                    if location in existing_location or existing_location in location:
                        is_duplicate = True
                        logger.info(f"Duplicate event detected: {existing.title} at {existing.start_time}")
                        break
                elif not location and not existing_location:
                    # Both have no location, check if titles are similar
                    existing_title = existing.title.lower()
                    new_title = event_data['title'].lower()
                    if existing_title in new_title or new_title in existing_title:
                        is_duplicate = True
                        logger.info(f"Duplicate event detected (by title): {existing.title}")
                        break
            
            if is_duplicate:
                # Mark content as processed but don't create duplicate event
                content.processed = True
                content.is_free_food = True
                await session.commit()
                logger.info(f"Skipped duplicate event: {event_data['title']} at {start_time}")
                return {
                    "event_created": False,
                    "reason": "duplicate",
                    "title": event_data['title']
                }
            
            # Create event (no duplicate found)
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

            # Send discovery notifications
            try:
                from app.workers.notification_tasks import _notify_event_async
                await _notify_event_async(str(event.id))
            except Exception as notify_error:
                logger.error(f"Failed to send notifications for event {event.id}: {notify_error}")

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
