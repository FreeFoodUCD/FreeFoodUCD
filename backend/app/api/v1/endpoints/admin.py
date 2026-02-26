from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from typing import List, Optional
from pydantic import BaseModel
from app.db.base import get_db
from app.db.models import User, Society, Event, Post, ScrapingLog, NotificationLog, PostFeedback
from app.core.config import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_admin_key(x_admin_key: str = Header(...)):
    """Verify admin API key from header."""
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """List all users."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    return {
        "total": len(users),
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "whatsapp_verified": user.whatsapp_verified,
                "email_verified": user.email_verified,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Delete a specific user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": f"User {user_id} deleted successfully"}


@router.delete("/users")
async def delete_all_users(
    confirm: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Delete all users. Requires confirmation."""
    if confirm != "DELETE_ALL_USERS":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirm='DELETE_ALL_USERS' query parameter"
        )
    
    result = await db.execute(delete(User))
    await db.commit()
    
    return {
        "message": "All users deleted",
        "deleted_count": result.rowcount
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get system statistics."""
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()
    
    societies_result = await db.execute(select(Society))
    societies = societies_result.scalars().all()
    
    events_result = await db.execute(select(Event))
    events = events_result.scalars().all()
    
    return {
        "users": {
            "total": len(users),
            "whatsapp_verified": sum(1 for u in users if u.whatsapp_verified),
            "email_verified": sum(1 for u in users if u.email_verified),
            "active": sum(1 for u in users if u.is_active),
        },
        "societies": {
            "total": len(societies),
            "active": sum(1 for s in societies if s.is_active),
        },
        "events": {
            "total": len(events),
        }
    }


@router.post("/societies/{society_id}/toggle")
async def toggle_society(
    society_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Toggle society active status."""
    result = await db.execute(select(Society).where(Society.id == society_id))
    society = result.scalar_one_or_none()
    
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    society.is_active = not society.is_active
    await db.commit()
    
    return {
        "message": f"Society {society.name} is now {'active' if society.is_active else 'inactive'}",
        "is_active": society.is_active
    }


class SocietyCreate(BaseModel):
    """Schema for creating a new society."""
    name: str
    instagram_handle: str
    scrape_posts: bool = True
    scrape_stories: bool = False


@router.post("/societies")
async def create_society(
    society_data: SocietyCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Create a new society."""
    # Check if society with this handle already exists
    result = await db.execute(
        select(Society).where(Society.instagram_handle == society_data.instagram_handle)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Society with Instagram handle @{society_data.instagram_handle} already exists"
        )
    
    # Create new society
    new_society = Society(
        name=society_data.name,
        instagram_handle=society_data.instagram_handle,
        is_active=True,
        scrape_posts=society_data.scrape_posts,
        scrape_stories=society_data.scrape_stories
    )
    
    db.add(new_society)
    await db.commit()
    await db.refresh(new_society)
    
    return {
        "message": f"Society {society_data.name} created successfully",
        "society": {
            "id": str(new_society.id),
            "name": new_society.name,
            "instagram_handle": new_society.instagram_handle,
            "is_active": new_society.is_active,
            "scrape_posts": new_society.scrape_posts,
            "scrape_stories": new_society.scrape_stories
        }
    }


class PostFeedbackCreate(BaseModel):
    """Schema for submitting post feedback."""
    is_correct: bool
    correct_classification: Optional[bool] = None
    classification_notes: Optional[str] = None
    correct_date: Optional[datetime] = None
    correct_time: Optional[str] = None
    correct_location: Optional[str] = None
    extraction_notes: Optional[str] = None
    notes: Optional[str] = None


@router.get("/posts/recent")
async def get_recent_posts(
    limit: int = 100,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Get recent posts with their processing status and extracted events.
    Shows posts from the last N days for review.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get posts with society info
    query = (
        select(Post, Society, Event)
        .join(Society, Post.society_id == Society.id)
        .outerjoin(Event, Event.source_id == Post.id)
        .where(Post.detected_at >= cutoff_date)
        .order_by(desc(Post.detected_at))
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()

    from app.services.nlp.extractor import EventExtractor
    extractor = EventExtractor()

    seen_post_ids = set()
    posts_data = []
    for post, society, event in rows:
        # Skip duplicate post rows caused by multiple events per post
        post_id_str = str(post.id)
        if post_id_str in seen_post_ids:
            continue
        seen_post_ids.add(post_id_str)

        # Get feedback if exists
        feedback_query = select(PostFeedback).where(PostFeedback.post_id == post.id)
        feedback_result = await db.execute(feedback_query)
        feedback = feedback_result.scalar_one_or_none()

        # Compute rejection reason for rejected posts
        rejection_reason = None
        if not post.is_free_food and post.caption:
            reason = extractor.get_rejection_reason(post.caption)
            if reason != "Accepted":
                rejection_reason = reason

        post_data = {
            "id": post_id_str,
            "society_name": society.name,
            "society_handle": society.instagram_handle,
            "caption": post.caption,
            "source_url": post.source_url,
            "detected_at": post.detected_at.isoformat(),
            "is_free_food": post.is_free_food,
            "processed": post.processed,
            "event_created": event is not None,
            "feedback_submitted": feedback is not None,
            "rejection_reason": rejection_reason,
        }

        # Add event data if exists
        if event:
            post_data["event"] = {
                "id": str(event.id),
                "title": event.title,
                "start_time": event.start_time.isoformat() if event.start_time else None,
                "location": event.location,
                "confidence_score": event.confidence_score,
                "notified": event.notified,
                "users_notified": 0  # TODO: Count from notification_logs
            }

        # Add feedback if exists
        if feedback:
            post_data["feedback"] = {
                "is_correct": feedback.is_correct,
                "notes": feedback.notes,
                "created_at": feedback.created_at.isoformat()
            }

        posts_data.append(post_data)

    return {
        "total": len(posts_data),
        "posts": posts_data
    }


@router.post("/posts/{post_id}/feedback")
async def submit_post_feedback(
    post_id: str,
    feedback_data: PostFeedbackCreate,
    x_admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Submit feedback on a post's NLP classification and extraction.
    - is_correct=True on a rejected post → creates an Event and marks post as free food.
    - is_correct=False on an accepted post → deactivates its events.
    """
    from app.services.nlp.extractor import EventExtractor

    # Check if post exists
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Upsert feedback record
    existing_query = select(PostFeedback).where(PostFeedback.post_id == post_id)
    result = await db.execute(existing_query)
    existing_feedback = result.scalar_one_or_none()

    if existing_feedback:
        existing_feedback.is_correct = feedback_data.is_correct
        existing_feedback.correct_classification = feedback_data.correct_classification
        existing_feedback.classification_notes = feedback_data.classification_notes
        existing_feedback.correct_date = feedback_data.correct_date
        existing_feedback.correct_time = feedback_data.correct_time
        existing_feedback.correct_location = feedback_data.correct_location
        existing_feedback.extraction_notes = feedback_data.extraction_notes
        existing_feedback.notes = feedback_data.notes
        existing_feedback.admin_email = x_admin_key[:50]
        feedback_id = str(existing_feedback.id)
        message = "Feedback updated successfully"
    else:
        new_feedback = PostFeedback(
            post_id=post_id,
            admin_email=x_admin_key[:50],
            is_correct=feedback_data.is_correct,
            correct_classification=feedback_data.correct_classification,
            classification_notes=feedback_data.classification_notes,
            correct_date=feedback_data.correct_date,
            correct_time=feedback_data.correct_time,
            correct_location=feedback_data.correct_location,
            extraction_notes=feedback_data.extraction_notes,
            notes=feedback_data.notes
        )
        db.add(new_feedback)
        await db.flush()
        feedback_id = str(new_feedback.id)
        message = "Feedback submitted successfully"

    # --- Apply event effects ---

    if feedback_data.is_correct and not post.is_free_food:
        # Admin says this rejected post actually had free food — create event
        post.is_free_food = True
        post.processed = True

        existing_event_result = await db.execute(
            select(Event).where(Event.source_id == post.id, Event.source_type == 'post')
        )
        existing_event = existing_event_result.scalar_one_or_none()

        if existing_event:
            existing_event.is_active = True
            message += " and event reactivated"
        else:
            extractor = EventExtractor()
            event_data = extractor.extract_event(post.caption or "")

            # Build start_time: prefer admin-supplied correct_date/correct_time over NLP
            start_time = None
            if feedback_data.correct_date:
                start_time = feedback_data.correct_date
                if feedback_data.correct_time:
                    parsed_time = extractor.time_parser.parse_time(
                        feedback_data.correct_time.lower()
                    )
                    if parsed_time and start_time:
                        start_time = start_time.replace(
                            hour=parsed_time['hour'],
                            minute=parsed_time['minute'],
                            second=0, microsecond=0
                        )
            elif event_data:
                start_time = event_data.get('start_time')

            new_event = Event(
                society_id=post.society_id,
                title=event_data.get('title', 'Free Food Event') if event_data else 'Free Food Event',
                description=(post.caption or "")[:500],
                location=feedback_data.correct_location or (
                    event_data.get('location') if event_data else None
                ),
                start_time=start_time,
                source_type='post',
                source_id=post.id,
                confidence_score=event_data.get('confidence_score', 0.5) if event_data else 0.5,
                raw_text=post.caption,
                is_active=True
            )
            db.add(new_event)
            message += " and event created"

    elif not feedback_data.is_correct and post.is_free_food:
        # Admin says this accepted post was wrong — deactivate its events
        post.is_free_food = False
        events_result = await db.execute(
            select(Event).where(Event.source_id == post.id, Event.source_type == 'post')
        )
        for evt in events_result.scalars().all():
            evt.is_active = False
        message += " and events deactivated"

    await db.commit()

    return {
        "message": message,
        "feedback_id": feedback_id
    }


@router.get("/posts/analytics")
async def get_post_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Get analytics on NLP accuracy based on feedback.
    Shows overall accuracy and common failure patterns.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get all posts with feedback
    query = (
        select(Post, PostFeedback)
        .join(PostFeedback, Post.id == PostFeedback.post_id)
        .where(Post.detected_at >= cutoff_date)
    )
    result = await db.execute(query)
    feedback_rows = result.all()
    
    # Get all posts (for total count)
    total_query = select(Post).where(Post.detected_at >= cutoff_date)
    total_result = await db.execute(total_query)
    total_posts = len(total_result.scalars().all())
    
    # Calculate metrics
    total_reviewed = len(feedback_rows)
    correct_count = sum(1 for _, feedback in feedback_rows if feedback.is_correct)
    
    accuracy = (correct_count / total_reviewed * 100) if total_reviewed > 0 else 0
    
    # Count common issues
    classification_errors = sum(
        1 for _, feedback in feedback_rows
        if not feedback.is_correct and feedback.correct_classification is not None
    )
    
    extraction_errors = sum(
        1 for _, feedback in feedback_rows
        if not feedback.is_correct and (
            feedback.correct_date or feedback.correct_time or feedback.correct_location
        )
    )
    
    return {
        "period_days": days,
        "total_posts": total_posts,
        "total_reviewed": total_reviewed,
        "review_rate": (total_reviewed / total_posts * 100) if total_posts > 0 else 0,
        "accuracy": round(accuracy, 1),
        "correct_count": correct_count,
        "incorrect_count": total_reviewed - correct_count,
        "classification_errors": classification_errors,
        "extraction_errors": extraction_errors
    }


@router.delete("/events")
async def delete_all_events(
    confirm: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Delete all events. Requires confirmation."""
    if confirm != "DELETE_ALL_EVENTS":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirm='DELETE_ALL_EVENTS' query parameter"
        )
    
    result = await db.execute(delete(Event))
    await db.commit()
    
    return {
        "message": "All events deleted",
        "deleted_count": result.rowcount
    }

@router.post("/seed-societies")
async def seed_societies(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Seed UCD societies into the database."""
    societies_data = [
        # --- Original 22 ---
        {"name": "UCD Mechsoc", "instagram_handle": "ucdmechsoc"},
        {"name": "UCD Indian Society", "instagram_handle": "ucdindsoc"},
        {"name": "UCD Arabic Culture & Language Society", "instagram_handle": "ucd.aclsoc"},
        {"name": "UCD Politics & International Relations Society", "instagram_handle": "ucdpolsoc"},
        {"name": "UCD Engineering Society", "instagram_handle": "ucdengsoc"},
        {"name": "UCD Japanese Society", "instagram_handle": "ucdjsoc"},
        {"name": "UCD Malaysian Society", "instagram_handle": "ucdmsoc"},
        {"name": "UCD Islamic Society", "instagram_handle": "ucdisoc"},
        {"name": "UCD French Society", "instagram_handle": "ucdfrenchsoc"},
        {"name": "UCD Mathematical Society", "instagram_handle": "ucdmathsoc"},
        {"name": "UCD Medical Society", "instagram_handle": "ucdmedsoc"},
        {"name": "UCD Veterinary Nursing Society", "instagram_handle": "ucdvnsoc"},
        {"name": "UCD Law Society", "instagram_handle": "ucdlawsoc"},
        {"name": "UCD Social Sciences Students", "instagram_handle": "ucdsocscistudents"},
        {"name": "UCD Film & Video Society", "instagram_handle": "ucdfilmsoc"},
        {"name": "UCD GameSoc", "instagram_handle": "ucdgamesociety"},
        {"name": "UCD Science Society", "instagram_handle": "ucdscisoc"},
        {"name": "UCD Chem Eng Soc", "instagram_handle": "ucdchemengsoc"},
        {"name": "UCD ElecSoc", "instagram_handle": "ucd.elecsoc"},
        {"name": "UCD Africa Society", "instagram_handle": "ucdafricasociety"},
        {"name": "UCD Food Society", "instagram_handle": "ucdfoodsoc"},
        {"name": "UCD Dance Society", "instagram_handle": "ucddancesoc"},
        # --- Discovered via ucdsocieties.ie scrape ---
        {"name": "UCD Arts Society", "instagram_handle": "artssocucd"},
        {"name": "Belfield FM", "instagram_handle": "belfield.fm"},
        {"name": "UCD Chinese Society", "instagram_handle": "chinesesoc.ucd"},
        {"name": "UCD Erasmus Student Network", "instagram_handle": "esnucd"},
        {"name": "UCD International Students Society", "instagram_handle": "issucd"},
        {"name": "UCD Kevin Barry Cumann", "instagram_handle": "kevinbarrycumann"},
        {"name": "UCD Nursing & Midwifery Society", "instagram_handle": "namsocucd"},
        {"name": "UCD Nordic Society", "instagram_handle": "nordicsocietyucd"},
        {"name": "UCD Pharmacy & Toxicology Society", "instagram_handle": "pharmtoxucd"},
        {"name": "UCD Physics Society", "instagram_handle": "physics_society_ucd"},
        {"name": "UCD Psychological Society", "instagram_handle": "psychsocietyucd"},
        {"name": "UCD Actuarial Society", "instagram_handle": "ucdactuarial"},
        {"name": "UCD Architecture Society", "instagram_handle": "ucdarcsoc"},
        {"name": "UCD Biological Society", "instagram_handle": "ucdbiosoc"},
        {"name": "UCD Commerce & Economics Society", "instagram_handle": "ucdcesoc"},
        {"name": "UCD Chemical Society", "instagram_handle": "ucdchemsoc"},
        {"name": "UCD Chess Society", "instagram_handle": "ucdchess"},
        {"name": "UCD Civil & Structural Engineering Society", "instagram_handle": "ucd_civil_structural"},
        {"name": "UCD Classical Society", "instagram_handle": "ucdclassicssoc"},
        {"name": "UCD Christian Union", "instagram_handle": "ucdcu"},
        {"name": "UCD Drama Society", "instagram_handle": "ucddramsoc"},
        {"name": "UCD Draw Society", "instagram_handle": "ucddrawsoc"},
        {"name": "UCD Eastern European Society", "instagram_handle": "ucdees"},
        {"name": "UCD Geography Society", "instagram_handle": "ucdgeogsoc"},
        {"name": "UCD German Society", "instagram_handle": "ucdgermansoc"},
        {"name": "UCD Gospel Choir", "instagram_handle": "ucdgospelchoir"},
        {"name": "UCD History Society", "instagram_handle": "ucdhistorysoc"},
        {"name": "UCD Horse Racing Society", "instagram_handle": "ucdhrs"},
        {"name": "UCD Horticulture Society", "instagram_handle": "ucd_hortsoc"},
        {"name": "UCD Investors & Entrepreneurs", "instagram_handle": "ucdie"},
        {"name": "UCD Italian Society", "instagram_handle": "ucditaliansoc"},
        {"name": "UCD Juggling Society", "instagram_handle": "ucdjuggling"},
        {"name": "UCD LGBTQ+ Society", "instagram_handle": "ucd_lgbtqplus"},
        {"name": "UCD Literary Society", "instagram_handle": "ucdlitsoc"},
        {"name": "UCD Livingstone's Christian Society", "instagram_handle": "ucdlivingstones"},
        {"name": "UCD Literary & Historical Society", "instagram_handle": "ucdlnh"},
        {"name": "UCD NetSoc", "instagram_handle": "ucdnetsoc"},
        {"name": "UCD Newman Catholic Society", "instagram_handle": "ucdnewmansoc"},
        {"name": "UCD PhD Society", "instagram_handle": "ucdphdsociety"},
        {"name": "UCD Philosophy Society", "instagram_handle": "ucdphilsoc"},
        {"name": "UCD Harry Potter Society", "instagram_handle": "ucdpottersoc"},
        {"name": "UCD Geology Society", "instagram_handle": "ucdrocsoc"},
        {"name": "UCD Sci-Fi Society", "instagram_handle": "ucdscifi"},
        {"name": "UCD Sinn Féin", "instagram_handle": "ucdsinnfein"},
        {"name": "UCD Social Democrats", "instagram_handle": "ucdsocdems"},
        {"name": "UCD Student Legal Service", "instagram_handle": "ucdstudentlegalservice"},
        {"name": "UCD Sustainability Society", "instagram_handle": "ucdsussoc"},
        {"name": "UCD TV Society", "instagram_handle": "ucdtvsoc"},
        {"name": "UCD Veterinary Society", "instagram_handle": "ucdvetsoc"},
        {"name": "UCD Women in STEM", "instagram_handle": "womeninstem_ucd"},
        {"name": "UCD Young Fine Gael", "instagram_handle": "ucd_yfg"},
    ]
    
    added = 0
    skipped = 0
    
    for society_data in societies_data:
        # Check if society already exists
        result = await db.execute(
            select(Society).where(Society.instagram_handle == society_data["instagram_handle"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        # Create new society
        society = Society(
            name=society_data["name"],
            instagram_handle=society_data["instagram_handle"],
            is_active=True,
            scrape_posts=True,
            scrape_stories=False
        )
        db.add(society)
        added += 1
    
    await db.commit()
    
    return {
        "message": "Societies seeded successfully",
        "added": added,
        "skipped": skipped,
        "total": len(societies_data)
    }


@router.post("/scrape-now")
async def trigger_scrape(
    society_handle: Optional[str] = None,
    force_reprocess: bool = False,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Trigger immediate scraping with database saving and NLP processing.
    Set force_reprocess=true to reprocess existing posts with NLP.
    """
    from app.services.scraper.instaloader_scraper import InstaLoaderScraper
    from app.services.nlp.extractor import EventExtractor
    from app.db.models import Post, Event
    from datetime import datetime

    if society_handle:
        # Scrape specific society
        result = await db.execute(
            select(Society).where(Society.instagram_handle == society_handle)
        )
        society = result.scalar_one_or_none()

        if not society:
            raise HTTPException(status_code=404, detail=f"Society @{society_handle} not found")

        # Scrape posts using working logic
        scraper = InstaLoaderScraper()
        posts_data = await scraper.scrape_posts(society_handle, max_posts=3)
        
        new_posts = 0
        new_events = 0
        new_event_ids = []
        extractor = EventExtractor()
        
        for post_data in posts_data:
            # Extract post ID
            post_id = post_data['url'].split('/p/')[-1].rstrip('/')
            
            # Check if post exists (by instagram_post_id only, since it's unique)
            existing_result = await db.execute(
                select(Post).where(Post.instagram_post_id == post_id)
            )
            existing_post = existing_result.scalar_one_or_none()
            
            if existing_post and not force_reprocess:
                # Post already exists, skip it
                continue
            
            # If force_reprocess and post exists, use existing post
            if existing_post and force_reprocess:
                post = existing_post
            elif not existing_post:
                # Save new post only if it doesn't exist
                post = Post(
                    society_id=society.id,
                    instagram_post_id=post_id,
                    caption=post_data['caption'],
                    media_urls=[post_data.get('image_url')] if post_data.get('image_url') else [],
                    source_url=post_data['url'],
                    detected_at=post_data['timestamp'],
                    processed=True
                )
                db.add(post)
                await db.flush()
                new_posts += 1
            else:
                # Post exists but not force_reprocess, skip
                continue
            
            # NLP processing (runs for new or force-reprocessed posts)
            print(f"[DEBUG] Running NLP on post: {post_data['url']}")
            
            # Combine caption with OCR text from images
            combined_text = post_data['caption']
            if post_data.get('image_url'):
                try:
                    from app.services.ocr.image_text_extractor import ImageTextExtractor
                    ocr = ImageTextExtractor()
                    ocr_text = ocr.extract_text_from_urls([post_data['image_url']])
                    if ocr_text:
                        combined_text = f"{combined_text}\n\n[Image Text]\n{ocr_text}"
                        print(f"[DEBUG] Added OCR text ({len(ocr_text)} chars)")
                except Exception as ocr_error:
                    print(f"[DEBUG] OCR failed: {ocr_error}")
            
            print(f"[DEBUG] Caption preview: {combined_text[:100]}...")
            print(f"[DEBUG] Full text length: {len(combined_text)} chars")
            event_data = extractor.extract_event(combined_text)
            print(f"[DEBUG] NLP result: {event_data}")
            
            if event_data and event_data.get('confidence_score', 0) >= 0.3:
                print(f"[DEBUG] Creating event with confidence {event_data.get('confidence_score')}")

                # Check if an event already exists for this post
                existing_event_result = await db.execute(
                    select(Event).where(Event.source_id == post.id, Event.source_type == 'post')
                )
                existing_event = existing_event_result.scalar_one_or_none()

                if existing_event and force_reprocess:
                    # Update existing event instead of creating a duplicate
                    existing_event.title = event_data.get('title', f"Free Food from {society.name}")
                    existing_event.description = post_data['caption'][:500]
                    existing_event.location = event_data.get('location')
                    existing_event.start_time = event_data.get('start_time')
                    existing_event.end_time = event_data.get('end_time')
                    existing_event.confidence_score = event_data.get('confidence_score')
                    existing_event.raw_text = post_data['caption']
                    existing_event.is_active = True
                elif not existing_event:
                    event = Event(
                        society_id=society.id,
                        title=event_data.get('title', f"Free Food from {society.name}"),
                        description=post_data['caption'][:500],
                        location=event_data.get('location'),
                        start_time=event_data.get('start_time'),
                        end_time=event_data.get('end_time'),
                        source_type='post',
                        source_id=post.id,
                        confidence_score=event_data.get('confidence_score'),
                        raw_text=post_data['caption'],
                        is_active=True
                    )
                    db.add(event)
                    await db.flush()
                    new_event_ids.append(str(event.id))
                    new_events += 1

                # Mark post as accepted free food
                post.is_free_food = True
                post.processed = True
            else:
                print(f"[DEBUG] Event rejected - confidence too low or None")
                post.processed = True
        
        await db.commit()

        # Send discovery notifications for newly created events
        if new_event_ids:
            from app.workers.notification_tasks import _notify_event_async
            for event_id in new_event_ids:
                try:
                    await _notify_event_async(event_id)
                except Exception as e:
                    logger.error(f"Failed to send notification for event {event_id}: {e}")

        return {
            "message": f"Scraping completed for @{society_handle}",
            "society": society.name,
            "result": {
                "society": society_handle,
                "posts_found": len(posts_data),
                "new_posts": new_posts,
                "new_events": new_events,
                "status": "success"
            },
            "status": "completed"
        }
    else:
        # Dispatch batch scrape as a Celery task (fire-and-forget).
        # Running all 78 societies synchronously in a single HTTP request would
        # exceed Railway's request timeout; Celery tasks have a 30-min limit.
        from app.workers.celery_app import celery_app
        task = celery_app.send_task(
            'app.workers.scraping_tasks.scrape_all_posts',
            queue='scraping',
        )
        return {
            "message": "Batch scrape queued — check Celery logs for results",
            "task_id": task.id,
            "status": "queued",
        }


@router.get("/scrape-test")
async def test_scrape(
    society_handle: str = "ucdlawsoc",
    _: bool = Depends(verify_admin_key)
):
    """
    Test scraping without saving to database.
    Returns raw scraped data for inspection.
    """
    from app.services.scraper.instaloader_scraper import InstaLoaderScraper

    try:
        scraper = InstaLoaderScraper()
        posts = await scraper.scrape_posts(society_handle, max_posts=3)
        
        return {
            "message": f"Successfully scraped @{society_handle}",
            "posts_found": len(posts),
            "posts": [
                {
                    "url": post["url"],
                    "caption_preview": post["caption"][:200] + "..." if len(post["caption"]) > 200 else post["caption"],
                    "caption_length": len(post["caption"]),
                    "has_image": bool(post.get("image_url")),
                    "timestamp": post["timestamp"].isoformat() if post.get("timestamp") else None
                }
                for post in posts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.put("/societies/{society_id}")
async def update_society(
    society_id: str,
    name: Optional[str] = None,
    instagram_handle: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Update society details.
    Provide only the fields you want to update.
    """
    result = await db.execute(select(Society).where(Society.id == society_id))
    society = result.scalar_one_or_none()
    
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    # Update provided fields
    if name is not None:
        society.name = name
    if instagram_handle is not None:
        society.instagram_handle = instagram_handle
    if is_active is not None:
        society.is_active = is_active
    
    await db.commit()
    await db.refresh(society)
    
    return {
        "message": "Society updated successfully",
        "society": {
            "id": society.id,
            "name": society.name,
            "instagram_handle": society.instagram_handle,
            "is_active": society.is_active
        }
    }


@router.get("/societies")
async def list_societies(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """List all societies with their IDs."""
    result = await db.execute(select(Society))
    societies = result.scalars().all()
    
    return {
        "total": len(societies),
        "societies": [
            {
                "id": society.id,
                "name": society.name,
                "instagram_handle": society.instagram_handle,
                "is_active": society.is_active
            }
            for society in societies
        ]
    }


@router.get("/scraping-logs")
async def get_scraping_logs(
    limit: int = 50,
    society_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get recent scraping logs with optional filters."""
    query = select(ScrapingLog).order_by(desc(ScrapingLog.created_at))
    
    if society_id:
        query = query.where(ScrapingLog.society_id == society_id)
    if status:
        query = query.where(ScrapingLog.status == status)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get society names
    logs_with_society = []
    for log in logs:
        society_result = await db.execute(
            select(Society).where(Society.id == log.society_id)
        )
        society = society_result.scalar_one_or_none()
        
        logs_with_society.append({
            "id": str(log.id),
            "society_name": society.name if society else "Unknown",
            "society_handle": society.instagram_handle if society else "unknown",
            "scrape_type": log.scrape_type,
            "status": log.status,
            "items_found": log.items_found,
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "total": len(logs_with_society),
        "logs": logs_with_society
    }


@router.get("/posts")
async def get_posts(
    limit: int = 50,
    society_id: Optional[str] = None,
    is_free_food: Optional[bool] = None,
    processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get recent posts with optional filters."""
    query = select(Post).order_by(desc(Post.detected_at))
    
    if society_id:
        query = query.where(Post.society_id == society_id)
    if is_free_food is not None:
        query = query.where(Post.is_free_food == is_free_food)
    if processed is not None:
        query = query.where(Post.processed == processed)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Get society names and event info
    posts_with_details = []
    for post in posts:
        society_result = await db.execute(
            select(Society).where(Society.id == post.society_id)
        )
        society = society_result.scalar_one_or_none()
        
        # Check if post has associated event (get first one if multiple exist)
        event_result = await db.execute(
            select(Event).where(Event.source_id == post.id, Event.source_type == 'post').limit(1)
        )
        event = event_result.scalar_one_or_none()
        
        posts_with_details.append({
            "id": str(post.id),
            "society_name": society.name if society else "Unknown",
            "society_handle": society.instagram_handle if society else "unknown",
            "instagram_post_id": post.instagram_post_id,
            "caption": post.caption[:200] + "..." if post.caption and len(post.caption) > 200 else post.caption,
            "caption_full": post.caption,
            "source_url": post.source_url,
            "media_urls": post.media_urls,
            "detected_at": post.detected_at.isoformat() if post.detected_at else None,
            "is_free_food": post.is_free_food,
            "processed": post.processed,
            "has_event": event is not None,
            "event_id": str(event.id) if event else None,
            "event_title": event.title if event else None
        })
    
    return {
        "total": len(posts_with_details),
        "posts": posts_with_details
    }


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get comprehensive dashboard statistics."""
    # Get basic counts
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()
    
    societies_result = await db.execute(select(Society))
    societies = societies_result.scalars().all()
    
    events_result = await db.execute(select(Event).where(Event.is_active == True))
    events = events_result.scalars().all()
    
    posts_result = await db.execute(select(Post))
    posts = posts_result.scalars().all()
    
    # Get recent scraping activity (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_logs_result = await db.execute(
        select(ScrapingLog).where(ScrapingLog.created_at >= yesterday)
    )
    recent_logs = recent_logs_result.scalars().all()
    
    # Calculate success rate
    if recent_logs:
        successful = sum(1 for log in recent_logs if log.status == 'success')
        success_rate = (successful / len(recent_logs)) * 100
    else:
        success_rate = 0
    
    # Get upcoming events (next 7 days)
    now = datetime.now()
    next_week = now + timedelta(days=7)
    upcoming_events_result = await db.execute(
        select(Event).where(
            Event.start_time >= now,
            Event.start_time <= next_week,
            Event.is_active == True
        )
    )
    upcoming_events = upcoming_events_result.scalars().all()
    
    return {
        "users": {
            "total": len(users),
            "whatsapp_verified": sum(1 for u in users if u.whatsapp_verified),
            "email_verified": sum(1 for u in users if u.email_verified),
            "active": sum(1 for u in users if u.is_active),
        },
        "societies": {
            "total": len(societies),
            "active": sum(1 for s in societies if s.is_active),
            "scraping_posts": sum(1 for s in societies if s.scrape_posts),
        },
        "events": {
            "total": len(events),
            "upcoming": len(upcoming_events),
        },
        "posts": {
            "total": len(posts),
            "free_food": sum(1 for p in posts if p.is_free_food),
            "processed": sum(1 for p in posts if p.processed),
        },
        "scraping": {
            "last_24h_attempts": len(recent_logs),
            "success_rate": round(success_rate, 1),
            "last_scrape": recent_logs[0].created_at.isoformat() if recent_logs else None,
        }
    }

@router.get("/upcoming-events")
async def get_upcoming_events(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get upcoming events within specified days with reminder status."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=days)
    
    query = select(Event).where(
        Event.start_time >= now,
        Event.start_time <= future,
        Event.is_active == True
    ).order_by(Event.start_time)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Get society names and user counts
    events_with_details = []
    for event in events:
        society_result = await db.execute(
            select(Society).where(Society.id == event.society_id)
        )
        society = society_result.scalar_one_or_none()
        
        # Count users who will be notified
        users_result = await db.execute(select(User).where(User.is_active == True))
        total_users = len(users_result.scalars().all())
        
        # Calculate time until event
        time_until = event.start_time - now
        hours_until = time_until.total_seconds() / 3600
        
        events_with_details.append({
            "id": str(event.id),
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "society_name": society.name if society else "Unknown",
            "society_handle": society.instagram_handle if society else "unknown",
            "confidence_score": event.confidence_score,
            "notified": event.notified,
            "notification_sent_at": event.notification_sent_at.isoformat() if event.notification_sent_at else None,
            "reminder_sent": event.reminder_sent,
            "reminder_sent_at": event.reminder_sent_at.isoformat() if event.reminder_sent_at else None,
            "hours_until": round(hours_until, 1),
            "users_to_notify": total_users,
            "is_active": event.is_active
        })
    
    return {
        "total": len(events_with_details),
        "events": events_with_details
    }


@router.post("/event/{event_id}/notify")
async def send_event_discovery_notification(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Manually trigger discovery notification for an existing event."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from app.workers.notification_tasks import _notify_event_async
    result = await _notify_event_async(event_id)
    return {"message": f"Discovery notification sent for event: {event.title}", **result}


@router.post("/event/{event_id}/send-reminder")
async def send_event_reminder(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Manually trigger reminder notification for an event (does not affect automatic 1-hour reminder)."""
    from app.services.notifications.brevo import BrevoEmailService
    
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get society
    society_result = await db.execute(
        select(Society).where(Society.id == event.society_id)
    )
    society = society_result.scalar_one_or_none()
    
    # Get active users
    users_result = await db.execute(select(User).where(User.is_active == True))
    users = users_result.scalars().all()
    
    if not users:
        return {"message": "No active users to notify", "users_notified": 0}
    
    # Prepare event data for reminder
    event_data = {
        "society_name": society.name if society else "Unknown Society",
        "title": event.title,
        "location": event.location or "TBA",
        "start_time": event.start_time.strftime("%I:%M %p") if event.start_time else "TBA",
    }
    
    # Send reminder notifications (email only for now)
    email_service = BrevoEmailService()
    
    whatsapp_count = 0
    email_count = 0
    
    for user in users:
        # Send email reminder if verified
        if user.email_verified and user.email:
            try:
                await email_service.send_event_reminder(user.email, event_data)
                email_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder email to {user.email}: {e}")
        
        # Skip WhatsApp for now (credentials not configured)
        # if user.whatsapp_verified and user.phone_number:
        #     try:
        #         whatsapp_service = WhatsAppService()
        #         await whatsapp_service.send_event_reminder(user.phone_number, event_data)
        #         whatsapp_count += 1
        #     except Exception as e:
        #         logger.error(f"Failed to send WhatsApp to {user.phone_number}: {e}")
    
    # DO NOT mark reminder_sent as True - this allows automatic 1-hour reminder to still fire
    # Manual reminders are independent of automatic reminders
    await db.commit()
    
    return {
        "message": f"Manual reminder sent for event: {event.title}",
        "users_notified": len(users),
        "whatsapp_sent": whatsapp_count,
        "email_sent": email_count
    }


@router.put("/event/{event_id}")
async def update_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Update event details."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update provided fields
    if title is not None:
        event.title = title
    if description is not None:
        event.description = description
    if location is not None:
        event.location = location
    if start_time is not None:
        from dateutil import parser
        event.start_time = parser.parse(start_time)
    if end_time is not None:
        from dateutil import parser
        event.end_time = parser.parse(end_time)
    if is_active is not None:
        event.is_active = is_active
    
    await db.commit()
    await db.refresh(event)
    
    return {
        "message": "Event updated successfully",
        "event": {
            "id": str(event.id),
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "is_active": event.is_active
        }
    }


@router.delete("/event/{event_id}")
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Delete an event."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await db.delete(event)
    await db.commit()
    
    return {"message": f"Event '{event.title}' deleted successfully"}


@router.post("/societies")
async def create_society(
    name: str,
    instagram_handle: str,
    is_active: bool = True,
    scrape_posts: bool = True,
    scrape_stories: bool = False,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Create a new society."""
    # Check if handle already exists
    existing_result = await db.execute(
        select(Society).where(Society.instagram_handle == instagram_handle)
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Society with handle @{instagram_handle} already exists")
    
    society = Society(
        name=name,
        instagram_handle=instagram_handle,
        is_active=is_active,
        scrape_posts=scrape_posts,
        scrape_stories=scrape_stories
    )
    
    db.add(society)
    await db.commit()
    await db.refresh(society)
    
    return {
        "message": "Society created successfully",
        "society": {
            "id": str(society.id),
            "name": society.name,
            "instagram_handle": society.instagram_handle,
            "is_active": society.is_active
        }
    }


@router.delete("/societies/{society_id}")
async def delete_society(
    society_id: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Delete a society and all associated data."""
    society = await db.get(Society, society_id)
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    society_name = society.name
    await db.delete(society)
    await db.commit()
    
    return {"message": f"Society '{society_name}' deleted successfully"}


@router.get("/notification-logs")
async def get_notification_logs(
    limit: int = 100,
    status: Optional[str] = None,
    notification_type: Optional[str] = None,
    event_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get notification logs with optional filters."""
    query = select(NotificationLog).order_by(desc(NotificationLog.sent_at))
    
    if status:
        query = query.where(NotificationLog.status == status)
    if notification_type:
        query = query.where(NotificationLog.notification_type == notification_type)
    if event_id:
        query = query.where(NotificationLog.event_id == event_id)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get related data
    logs_with_details = []
    for log in logs:
        # Get user
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        user = user_result.scalar_one_or_none()
        
        # Get event
        event_result = await db.execute(select(Event).where(Event.id == log.event_id))
        event = event_result.scalar_one_or_none()
        
        # Get society
        society = None
        if event:
            society_result = await db.execute(select(Society).where(Society.id == event.society_id))
            society = society_result.scalar_one_or_none()
        
        logs_with_details.append({
            "id": str(log.id),
            "event_title": event.title if event else "Unknown Event",
            "society_name": society.name if society else "Unknown",
            "user_email": user.email if user else "Unknown",
            "user_phone": user.phone_number if user else "Unknown",
            "notification_type": log.notification_type,
            "status": log.status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "error_message": log.error_message
        })
    
    return {
        "total": len(logs_with_details),
        "logs": logs_with_details
    }


@router.get("/notification-stats")
async def get_notification_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get notification statistics for the specified period."""
    from datetime import timezone
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all logs in period
    result = await db.execute(
        select(NotificationLog).where(NotificationLog.sent_at >= since)
    )
    logs = result.scalars().all()
    
    # Calculate stats
    total_sent = len(logs)
    whatsapp_sent = sum(1 for log in logs if log.notification_type == 'whatsapp')
    email_sent = sum(1 for log in logs if log.notification_type == 'email')
    
    successful = sum(1 for log in logs if log.status == 'sent')
    failed = sum(1 for log in logs if log.status == 'failed')
    
    delivery_rate = (successful / total_sent * 100) if total_sent > 0 else 0
    
    # Get failed logs for retry
    failed_logs_result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.status == 'failed')
        .where(NotificationLog.sent_at >= since)
        .order_by(desc(NotificationLog.sent_at))
        .limit(20)
    )
    failed_logs = failed_logs_result.scalars().all()
    
    return {
        "period_days": days,
        "total_sent": total_sent,
        "by_channel": {
            "whatsapp": whatsapp_sent,
            "email": email_sent
        },
        "by_status": {
            "successful": successful,
            "failed": failed,
            "pending": total_sent - successful - failed
        },
        "delivery_rate": round(delivery_rate, 1),
        "recent_failures": len(failed_logs)
    }


@router.post("/retry-failed-notifications")
async def retry_failed_notifications(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Retry failed notifications from the last N hours (email only)."""
    from app.services.notifications.email import EmailService
    from datetime import timezone
    
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get failed notifications (email only)
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.status == 'failed')
        .where(NotificationLog.notification_type == 'email')
        .where(NotificationLog.sent_at >= since)
    )
    failed_logs = result.scalars().all()
    
    if not failed_logs:
        return {"message": "No failed email notifications to retry", "retried": 0}
    
    email_service = EmailService()
    
    retried = 0
    success = 0
    
    for log in failed_logs:
        # Get user and event
        user = await db.get(User, log.user_id)
        event = await db.get(Event, log.event_id)
        
        if not user or not event:
            continue
        
        # Get society
        society_result = await db.execute(select(Society).where(Society.id == event.society_id))
        society = society_result.scalar_one_or_none()
        
        # Prepare event data
        event_data = {
            "society_name": society.name if society else "Unknown",
            "title": event.title,
            "location": event.location or "TBA",
            "start_time": event.start_time.strftime("%I:%M %p") if event.start_time else "TBA",
            "date": event.start_time.strftime("%A, %B %d, %Y") if event.start_time else "TBA",
            "source_type": event.source_type or "post"
        }
        
        try:
            # Only retry email notifications (WhatsApp not configured)
            if log.notification_type == 'email' and user.email:
                await email_service.send_event_notification(user.email, event_data)
                log.status = 'sent'
                log.error_message = None
                success += 1
                retried += 1
            # Skip WhatsApp retries
        except Exception as e:
            log.error_message = str(e)
            logger.error(f"Retry failed for notification {log.id}: {e}")
            retried += 1
    
    await db.commit()
    
    return {
        "message": f"Retried {retried} notifications, {success} successful",
        "retried": retried,
        "successful": success,
        "failed": retried - success
    }


@router.get("/system-health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get system health status."""
    health_status = {
        "database": "healthy",
        "celery_worker": "unknown",
        "celery_beat": "unknown",
        "services": {}
    }
    
    # Test database
    try:
        await db.execute(select(User).limit(1))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = "unhealthy"
        health_status["database_error"] = str(e)
    
    # Check recent scraping activity (indicates workers are running)
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        recent_logs_result = await db.execute(
            select(ScrapingLog)
            .where(ScrapingLog.created_at >= now - timedelta(hours=24))
            .order_by(desc(ScrapingLog.created_at))
            .limit(1)
        )
        recent_log = recent_logs_result.scalar_one_or_none()
        
        if recent_log:
            hours_since = (now - recent_log.created_at).total_seconds() / 3600
            if hours_since < 2:
                health_status["celery_worker"] = "healthy"
            elif hours_since < 24:
                health_status["celery_worker"] = "warning"
            else:
                health_status["celery_worker"] = "unhealthy"
        else:
            health_status["celery_worker"] = "no_recent_activity"
    except Exception as e:
        health_status["celery_worker"] = "error"
        health_status["worker_error"] = str(e)
    
    # Check if beat schedule is working (check for events with reminders)
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        upcoming_events_result = await db.execute(
            select(Event)
            .where(Event.start_time >= now)
            .where(Event.start_time <= now + timedelta(days=1))
            .where(Event.is_active == True)
        )
        upcoming_events = upcoming_events_result.scalars().all()
        
        if upcoming_events:
            reminded = sum(1 for e in upcoming_events if e.reminder_sent)
            health_status["celery_beat"] = "healthy" if reminded > 0 else "warning"
        else:
            health_status["celery_beat"] = "no_upcoming_events"
    except Exception as e:
        health_status["celery_beat"] = "error"
        health_status["beat_error"] = str(e)
    
    # Service status (basic checks)
    health_status["services"]["instaloader"] = "active"
    health_status["services"]["twilio"] = "configured" if settings.TWILIO_ACCOUNT_SID else "not_configured"
    health_status["services"]["resend"] = "configured" if settings.RESEND_API_KEY else "not_configured"
    
    return health_status


@router.get("/error-logs")
async def get_error_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get recent error logs from scraping and notifications."""
    errors = []
    
    # Get failed scraping logs
    scraping_errors_result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.status == 'failed')
        .order_by(desc(ScrapingLog.created_at))
        .limit(limit // 2)
    )
    scraping_errors = scraping_errors_result.scalars().all()
    
    for log in scraping_errors:
        society_result = await db.execute(select(Society).where(Society.id == log.society_id))
        society = society_result.scalar_one_or_none()
        
        errors.append({
            "type": "scraping",
            "timestamp": log.created_at.isoformat(),
            "source": f"@{society.instagram_handle}" if society else "Unknown",
            "error": log.error_message,
            "details": f"Scrape type: {log.scrape_type}"
        })
    
    # Get failed notifications
    notification_errors_result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.status == 'failed')
        .order_by(desc(NotificationLog.sent_at))
        .limit(limit // 2)
    )
    notification_errors = notification_errors_result.scalars().all()
    
    for log in notification_errors:
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        user = user_result.scalar_one_or_none()
        
        errors.append({
            "type": "notification",
            "timestamp": log.sent_at.isoformat() if log.sent_at else None,
            "source": f"{log.notification_type} to {user.email or user.phone_number}" if user else "Unknown",
            "error": log.error_message,
            "details": f"Event ID: {log.event_id}"
        })
    
    # Sort by timestamp
    errors.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "", reverse=True)
    
    return {
        "total": len(errors),
        "errors": errors[:limit]
    }


@router.post("/test-notification")
async def send_test_notification(
    user_id: str,
    channel: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Send a test notification to a specific user."""
    from app.services.notifications.whatsapp import WhatsAppService
    from app.services.notifications.email import EmailService
    from datetime import timezone
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    test_event_data = {
        "society_name": "Test Society",
        "title": "Test Free Food Event",
        "location": "Test Location",
        "start_time": "12:00 PM",
        "date": datetime.now(timezone.utc).strftime("%A, %B %d, %Y"),
        "source_type": "test"
    }
    
    try:
        if channel == "whatsapp":
            if not user.phone_number:
                raise HTTPException(status_code=400, detail="User has no phone number")
            whatsapp_service = WhatsAppService()
            await whatsapp_service.send_event_notification(user.phone_number, test_event_data)
            return {"message": f"Test WhatsApp sent to {user.phone_number}"}
        
        elif channel == "email":
            if not user.email:
                raise HTTPException(status_code=400, detail="User has no email")
            email_service = EmailService()
            await email_service.send_event_notification(user.email, test_event_data)
            return {"message": f"Test email sent to {user.email}"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid channel. Use 'whatsapp' or 'email'")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")


@router.get("/societies-detailed")
async def get_societies_detailed(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get detailed information about all societies including performance metrics."""
    result = await db.execute(select(Society))
    societies = result.scalars().all()
    
    societies_with_stats = []
    for society in societies:
        # Count posts
        posts_result = await db.execute(
            select(Post).where(Post.society_id == society.id)
        )
        posts = posts_result.scalars().all()
        
        # Count events
        events_result = await db.execute(
            select(Event).where(Event.society_id == society.id)
        )
        events = events_result.scalars().all()
        
        # Get recent scraping logs
        logs_result = await db.execute(
            select(ScrapingLog)
            .where(ScrapingLog.society_id == society.id)
            .order_by(desc(ScrapingLog.created_at))
            .limit(10)
        )
        logs = logs_result.scalars().all()
        
        # Calculate success rate
        if logs:
            successful = sum(1 for log in logs if log.status == 'success')
            success_rate = (successful / len(logs)) * 100
        else:
            success_rate = 0
        
        societies_with_stats.append({
            "id": str(society.id),
            "name": society.name,
            "instagram_handle": society.instagram_handle,
            "is_active": society.is_active,
            "scrape_posts": society.scrape_posts,
            "scrape_stories": society.scrape_stories,
            "last_post_check": society.last_post_check.isoformat() if society.last_post_check else None,
            "last_story_check": society.last_story_check.isoformat() if society.last_story_check else None,
            "stats": {
                "total_posts": len(posts),
                "total_events": len(events),
                "recent_scrapes": len(logs),
                "success_rate": round(success_rate, 1)
            }
        })
    
    return {
        "total": len(societies_with_stats),
        "societies": societies_with_stats
    }



@router.get("/recent-activity")
async def get_recent_activity(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get recent scraping activity and new events for the dashboard."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    # Last 8 scrape attempts
    logs_result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.scrape_type == 'post')
        .order_by(desc(ScrapingLog.created_at))
        .limit(8)
    )
    recent_logs = logs_result.scalars().all()

    scrape_feed = []
    for log in recent_logs:
        society_result = await db.execute(select(Society).where(Society.id == log.society_id))
        society = society_result.scalar_one_or_none()

        # Count events created within 5 minutes of this scrape
        window_end = log.created_at + timedelta(minutes=10)
        events_result = await db.execute(
            select(Event).where(
                Event.created_at >= log.created_at,
                Event.created_at <= window_end,
                Event.society_id == log.society_id
            )
        )
        events_from_scrape = events_result.scalars().all()

        scrape_feed.append({
            "time": log.created_at.isoformat(),
            "society": society.name if society else "Unknown",
            "handle": society.instagram_handle if society else "unknown",
            "status": log.status,
            "posts_found": log.items_found or 0,
            "events_created": len(events_from_scrape),
            "new_event_titles": [e.title for e in events_from_scrape],
        })

    # Events created in last 24h
    new_events_result = await db.execute(
        select(Event)
        .where(Event.created_at >= since_24h, Event.is_active == True)
        .order_by(desc(Event.created_at))
    )
    new_events = new_events_result.scalars().all()

    new_events_data = []
    for event in new_events:
        society_result = await db.execute(select(Society).where(Society.id == event.society_id))
        society = society_result.scalar_one_or_none()
        new_events_data.append({
            "title": event.title,
            "society": society.name if society else "Unknown",
            "location": event.location,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "notified": event.notified,
        })

    # Scrapes in last 24h
    scrapes_24h_result = await db.execute(
        select(ScrapingLog).where(
            ScrapingLog.created_at >= since_24h,
            ScrapingLog.scrape_type == 'post'
        )
    )
    scrapes_24h = scrapes_24h_result.scalars().all()

    return {
        "scrapes_24h": len(scrapes_24h),
        "new_events_24h": len(new_events),
        "new_events": new_events_data,
        "scrape_feed": scrape_feed,
    }


# Made with Bob
