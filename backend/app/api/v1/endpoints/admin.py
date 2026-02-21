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

# Made with Bob
