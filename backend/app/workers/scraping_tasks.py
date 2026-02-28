from celery import group
from app.workers.celery_app import celery_app
from app.core.config import settings
from app.db.base import task_db_session
from app.db.models import Society, Post, Story, Event, ScrapingLog
from app.services.nlp.extractor import EventExtractor
from app.services.scraper.apify_scraper import ApifyInstagramScraper
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import logging
import asyncio
import hashlib
import json
import redis as redis_lib

logger = logging.getLogger(__name__)


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

def get_scraper():
    """Create a fresh Apify scraper instance."""
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
    start_time = datetime.now(timezone.utc)

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
            society.last_story_check = datetime.now(timezone.utc)

            # Log scraping activity
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='story',
                status='success',
                items_found=stories_found,
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
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
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()
            raise


@celery_app.task(bind=True, max_retries=3)
def scrape_all_posts(self):
    """Scrape posts from all active societies."""
    try:
        return asyncio.run(_scrape_all_posts_async())
    except IntegrityError as e:
        # DB constraint violation — don't retry, it won't help and wastes Apify credits
        logger.error(f"IntegrityError in scrape_all_posts (not retrying): {e}")
        raise
    except Exception as e:
        logger.error(f"Error in scrape_all_posts: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_all_posts_async():
    """
    Async implementation of scrape_all_posts.

    Runs in three isolated phases to avoid holding a DB connection during the
    60-120 second Apify HTTP call, and to cache Apify results in Redis so that
    Celery retries (or same-hour re-triggers) never pay the $0.20 Apify cost twice.

    Phase 1 — Short DB session: load society metadata, close session.
    Phase 2 — Apify call + Redis cache: no DB session open.
    Phase 3 — Fresh DB session: re-load ORM objects, persist posts, commit.
    """
    start_time = datetime.now(timezone.utc)

    # ── Phase 1: load society metadata (session closed immediately after) ────
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
        # snapshot handle → id so we can re-fetch ORM objects in Phase 3
        society_id_by_handle = {s.instagram_handle.lower(): str(s.id) for s in societies}

    logger.info(f"Batch scraping {len(handles)} societies")

    # ── Distributed run lock (prevents overlapping scrape_all_posts runs) ────
    LOCK_KEY = "scrape_all_posts_lock"
    r = _get_redis()
    if not r.set(LOCK_KEY, "1", nx=True, ex=1800):
        logger.warning("scrape_all_posts already running — skipping duplicate invocation")
        return {"status": "skipped", "reason": "already_running"}

    try:
        # ── Phase 2: Apify call with Redis result cache ───────────────────────
        handle_hash = hashlib.md5(",".join(sorted(handles)).encode()).hexdigest()[:8]
        cache_key = f"apify_batch:{handle_hash}:{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}"

        cached = r.get(cache_key)
        if cached:
            logger.info("Using cached Apify results (saving ~$0.20)")
            raw = json.loads(cached)
            # Deserialise timestamp strings back to timezone-aware datetime objects
            batch_results: dict = {}
            for handle, posts in raw.items():
                batch_results[handle] = []
                for post in posts:
                    if post.get("timestamp"):
                        post["timestamp"] = datetime.fromisoformat(post["timestamp"])
                    batch_results[handle].append(post)
        else:
            apify_start = datetime.now(timezone.utc)
            scraper = get_scraper()
            batch_results = await scraper.scrape_posts_batch(
                handles, max_posts_per_user=settings.SCRAPE_MAX_POSTS_PER_SOCIETY
            )
            apify_ms = int((datetime.now(timezone.utc) - apify_start).total_seconds() * 1000)

            logger.info(
                f"Batch returned results for {len(batch_results)}/{len(handles)} societies "
                f"(Apify took {apify_ms}ms)"
            )

            # Zero-result guard: if ALL societies returned nothing, something is wrong
            if not batch_results and len(handles) > 10:
                logger.error(
                    f"ALERT: Apify returned 0 results for all {len(handles)} societies "
                    f"— possible quota exhaustion or Instagram block"
                )
                async with task_db_session() as session:
                    session.add(ScrapingLog(
                        society_id=None,
                        scrape_type="post",
                        status="failed",
                        items_found=0,
                        error_message="Zero results from Apify for all handles",
                        duration_ms=apify_ms,
                    ))
                    await session.commit()
                raise RuntimeError("Apify zero-result — aborting scrape")

            # Serialise to Redis (timestamp → ISO string) with 90-minute TTL
            serialisable: dict = {}
            for handle, posts in batch_results.items():
                serialisable[handle] = []
                for post in posts:
                    p = dict(post)
                    if isinstance(p.get("timestamp"), datetime):
                        p["timestamp"] = p["timestamp"].isoformat()
                    serialisable[handle].append(p)
            r.setex(cache_key, 5400, json.dumps(serialisable))

            # Batch-level timing log (Fix 8) — records how long Apify took
            async with task_db_session() as session:
                session.add(ScrapingLog(
                    society_id=None,
                    scrape_type="post",
                    status="success" if batch_results else "partial",
                    items_found=sum(len(v) for v in batch_results.values()),
                    duration_ms=apify_ms,
                ))
                await session.commit()

        # ── Phase 3: fresh DB session for all writes ─────────────────────────
        async with task_db_session() as session:
            # Re-fetch Society ORM objects by id (avoiding stale references)
            society_ids = list(society_id_by_handle.values())
            result = await session.execute(
                select(Society).where(Society.id.in_(society_ids))
            )
            society_by_handle = {s.instagram_handle.lower(): s for s in result.scalars().all()}

            total_new_posts = 0
            batch_event_ids = []

            for handle_lower, posts_data in batch_results.items():
                society = society_by_handle.get(handle_lower)
                if not society:
                    logger.warning(f"Got results for unknown handle @{handle_lower}, skipping")
                    continue

                posts_found = 0
                new_posts = 0

                for post_data in posts_data:
                    try:
                        post_id = post_data["url"].split("/p/")[-1].rstrip("/")

                        # Skip posts older than 7 days
                        post_age = datetime.now(timezone.utc) - post_data["timestamp"]
                        if post_age.days > 7:
                            logger.info(f"Skipping old post from @{handle_lower}: {post_age.days} days old")
                            continue

                        # Skip already-saved posts (unique constraint is on instagram_post_id)
                        existing = await session.execute(
                            select(Post).where(Post.instagram_post_id == post_id)
                        )
                        if existing.scalar_one_or_none():
                            continue

                        post = Post(
                            society_id=society.id,
                            instagram_post_id=post_id,
                            caption=post_data["caption"],
                            media_urls=post_data.get("image_urls") or (
                                [post_data["image_url"]] if post_data.get("image_url") else []
                            ),
                            source_url=post_data["url"],
                            detected_at=post_data["timestamp"],
                            processed=False,
                        )
                        session.add(post)
                        try:
                            await session.flush()
                        except IntegrityError:
                            await session.rollback()
                            logger.warning(f"Skipping duplicate post {post_id} (race condition)")
                            continue

                        new_posts += 1
                        posts_found += 1
                        total_new_posts += 1

                        try:
                            nlp_result = await _process_scraped_content_async("post", str(post.id))
                            if nlp_result.get("event_created") and nlp_result.get("event_id"):
                                batch_event_ids.append(nlp_result["event_id"])
                        except Exception as nlp_error:
                            logger.error(f"NLP processing failed for post {post.id}: {nlp_error}")

                        logger.info(f"New post from @{handle_lower}: {post_data['url']}")
                    except Exception as post_error:
                        logger.error(f"Skipping malformed post from @{handle_lower}: {post_error}")

                society.last_post_check = datetime.now(timezone.utc)
                session.add(ScrapingLog(
                    society_id=society.id,
                    scrape_type="post",
                    status="success",
                    items_found=posts_found,
                    duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                ))

            # Log societies that returned no results (private / no posts)
            for handle_lower, society in society_by_handle.items():
                if handle_lower not in batch_results:
                    society.last_post_check = datetime.now(timezone.utc)
                    session.add(ScrapingLog(
                        society_id=society.id,
                        scrape_type="post",
                        status="success",
                        items_found=0,
                        duration_ms=0,
                    ))

            await session.commit()

            # Send one combined email per user for all events found this scrape run
            if batch_event_ids:
                try:
                    from app.workers.notification_tasks import _notify_events_batch_async
                    await _notify_events_batch_async(batch_event_ids)
                except Exception as notify_error:
                    logger.error(f"Failed batch notification for {len(batch_event_ids)} event(s): {notify_error}")

            elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds())
            logger.info(
                f"Batch scrape complete: {total_new_posts} new posts "
                f"from {len(batch_results)} societies in {elapsed}s"
            )
            return {
                "societies_scraped": len(society_id_by_handle),
                "societies_with_results": len(batch_results),
                "total_new_posts": total_new_posts,
            }

    finally:
        r.delete(LOCK_KEY)


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
    start_time = datetime.now(timezone.utc)

    async with task_db_session() as session:
        society = await session.get(Society, society_id)
        if not society:
            return {"error": "Society not found"}

        try:
            logger.info(f"Scraping posts for @{society.instagram_handle}")

            scraper = get_scraper()

            # Scrape last 3 posts (societies post 2-3 times/week)
            posts_data = await scraper.scrape_posts(society.instagram_handle, max_posts=3)

            logger.info(f"Scraper returned {len(posts_data)} posts for @{society.instagram_handle}")
            if len(posts_data) == 0:
                logger.warning(f"No posts returned for @{society.instagram_handle}")
            
            posts_found = 0
            new_posts = 0
            society_event_ids = []

            for post_data in posts_data:
                try:
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
                        media_urls=post_data.get('image_urls') or (
                            [post_data['image_url']] if post_data.get('image_url') else []
                        ),
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
                        nlp_result = await _process_scraped_content_async('post', str(post.id))
                        if nlp_result.get('event_created') and nlp_result.get('event_id'):
                            society_event_ids.append(nlp_result['event_id'])
                    except Exception as nlp_error:
                        logger.error(f"NLP processing failed for post {post.id}: {nlp_error}")

                    logger.info(f"New post from @{society.instagram_handle}: {post_data['url']}")
                except Exception as post_error:
                    logger.error(f"Skipping malformed post from @{society.instagram_handle}: {post_error}")

            # Update last check time
            society.last_post_check = datetime.now(timezone.utc)

            # Log scraping activity
            log = ScrapingLog(
                society_id=society.id,
                scrape_type='post',
                status='success',
                items_found=posts_found,
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
            session.add(log)
            await session.commit()

            # Send one combined email per user for all events found this run
            if society_event_ids:
                try:
                    from app.workers.notification_tasks import _notify_events_batch_async
                    await _notify_events_batch_async(society_event_ids)
                except Exception as notify_error:
                    logger.error(f"Failed batch notification for {len(society_event_ids)} event(s): {notify_error}")

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
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
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
            
            # Fallback: society-level same-day dedup (catches reminder posts that
            # extract a slightly different time, bypassing the ±1 hour window)
            if not is_duplicate:
                today_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                same_day_query = select(Event).where(
                    Event.society_id == content.society_id,
                    Event.start_time >= today_start,
                    Event.start_time < today_end,
                    Event.is_active == True
                )
                same_day_result = await session.execute(same_day_query)
                same_day_events = same_day_result.scalars().all()
                if same_day_events:
                    is_duplicate = True
                    logger.info(
                        f"Same-day society dedup triggered: society {content.society_id} "
                        f"already has event on {today_start.date()} — skipping '{event_data['title']}'"
                    )

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
