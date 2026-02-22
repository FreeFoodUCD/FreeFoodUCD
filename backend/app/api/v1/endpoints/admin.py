from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from app.db.base import get_db
from app.db.models import User, Society, Event
from app.core.config import settings

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
    user_id: int,
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
    society_id: int,
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
        {"name": "UCD Mechsoc", "instagram_handle": "ucdmechsoc"},
        {"name": "UCD IndSoc", "instagram_handle": "ucdindsoc"},
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
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Trigger immediate scraping (runs synchronously for Railway).
    Uses same logic as scrape-test but saves to database.
    """
    from app.services.scraper.apify_scraper import ApifyInstagramScraper
    from app.core.config import settings
    
    if society_handle:
        # Scrape specific society using working scrape-test logic
        result = await db.execute(
            select(Society).where(Society.instagram_handle == society_handle)
        )
        society = result.scalar_one_or_none()
        
        if not society:
            raise HTTPException(status_code=404, detail=f"Society @{society_handle} not found")
        
        # Use same scraper logic as scrape-test (which works!)
        scraper = ApifyInstagramScraper(api_token=settings.APIFY_API_TOKEN)
        posts = await scraper.scrape_posts(society_handle, max_posts=3)
        
        return {
            "message": f"Scraping completed for @{society_handle}",
            "society": society.name,
            "result": {
                "society": society_handle,
                "posts_found": len(posts),
                "posts": posts[:3]  # Return first 3 for inspection
            },
            "status": "completed"
        }
    else:
        # Scrape all societies synchronously
        query = select(Society).where(Society.is_active == True, Society.scrape_posts == True)
        result = await db.execute(query)
        societies = result.scalars().all()
        
        results = []
        for society in societies:
            try:
                scrape_result = await _scrape_society_posts_async(str(society.id))
                results.append(scrape_result)
            except Exception as e:
                results.append({"society": society.instagram_handle, "error": str(e)})
        
        return {
            "message": f"Scraping completed for {len(societies)} societies",
            "results": results,
            "status": "completed"
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
    from app.services.scraper.apify_scraper import ApifyInstagramScraper
    from app.core.config import settings
    
    try:
        scraper = ApifyInstagramScraper(api_token=settings.APIFY_API_TOKEN)
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


# Made with Bob
