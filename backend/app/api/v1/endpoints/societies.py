from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.db.base import get_db
from app.db.models import Society

router = APIRouter()


# Pydantic schemas
class SocietyResponse(BaseModel):
    """Society response schema."""
    id: UUID
    name: str
    instagram_handle: str
    is_active: bool
    
    class Config:
        from_attributes = True


@router.get("/societies", response_model=List[SocietyResponse])
async def get_societies(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all societies.
    
    - **active_only**: Only return active societies (default: True)
    """
    query = select(Society)
    
    if active_only:
        query = query.where(Society.is_active == True)
    
    query = query.order_by(Society.name.asc())
    
    result = await db.execute(query)
    societies = result.scalars().all()
    
    return [
        SocietyResponse(
            id=society.id,
            name=society.name,
            instagram_handle=society.instagram_handle,
            is_active=society.is_active
        )
        for society in societies
    ]


@router.get("/societies/{society_id}", response_model=SocietyResponse)
async def get_society(
    society_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific society by ID."""
    query = select(Society).where(Society.id == society_id)
    
    result = await db.execute(query)
    society = result.scalar_one_or_none()
    
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    return SocietyResponse(
        id=society.id,
        name=society.name,
        instagram_handle=society.instagram_handle,
        is_active=society.is_active
    )

# Made with Bob
