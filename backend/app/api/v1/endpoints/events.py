from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from pydantic import BaseModel, Field

from app.db.base import get_db
from app.db.models import Event, Society

router = APIRouter()


# Pydantic schemas
class SocietyInfo(BaseModel):
    """Society information in event response."""
    id: UUID
    name: str
    instagram_handle: str
    
    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Event response schema."""
    id: UUID
    title: str
    description: Optional[str] = None
    location: str
    location_building: Optional[str] = None
    location_room: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    source_type: str
    confidence_score: Optional[float] = None
    members_only: bool = False
    society: SocietyInfo
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Paginated event list response (matches frontend PaginatedResponse<Event>)."""
    items: List[EventResponse]
    total: int
    page: int
    size: int
    pages: int


@router.get("/events", response_model=EventListResponse)
async def get_events(
    date_filter: Optional[str] = Query(None, description="Filter by date: 'today', 'tomorrow', '24h', 'week', or YYYY-MM-DD"),
    society_id: Optional[UUID] = Query(None, description="Filter by society ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of free food events with filters.
    
    - **date_filter**: Filter by date ('today', 'tomorrow', '24h', 'week', or specific date)
    - **society_id**: Filter by specific society
    - **page**: Page number for pagination
    - **page_size**: Number of items per page
    """
    # Build query
    query = select(Event).join(Society).where(Event.is_active == True)
    
    # Apply date filter
    if date_filter:
        now = datetime.now(timezone.utc)
        if date_filter.lower() == "today":
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            query = query.where(
                and_(
                    Event.start_time >= start_of_day,
                    Event.start_time < end_of_day
                )
            )
        elif date_filter.lower() == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start_of_day = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            query = query.where(
                and_(
                    Event.start_time >= start_of_day,
                    Event.start_time < end_of_day
                )
            )
        elif date_filter.lower() == "24h":
            # Show events that started up to 2h ago (still ongoing) or start within next 24h
            lookback = now - timedelta(hours=2)
            end_of_24h = now + timedelta(hours=24)
            query = query.where(
                and_(
                    Event.start_time >= lookback,
                    Event.start_time <= end_of_24h
                )
            )
        elif date_filter.lower() == "week":
            end_of_week = now + timedelta(days=7)
            query = query.where(
                and_(
                    Event.start_time >= now - timedelta(hours=2),
                    Event.start_time <= end_of_week
                )
            )
        else:
            # Try to parse as date
            try:
                filter_date = datetime.strptime(date_filter, "%Y-%m-%d")
                start_of_day = filter_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                query = query.where(
                    and_(
                        Event.start_time >= start_of_day,
                        Event.start_time < end_of_day
                    )
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD or 'today', 'tomorrow', '24h', 'week'")
    
    # Apply society filter
    if society_id:
        query = query.where(Event.society_id == society_id)
    
    # Order by start time (upcoming first)
    query = query.order_by(Event.start_time.asc())
    
    # Get total count
    count_query = select(func.count()).select_from(Event).where(Event.is_active == True)
    if date_filter or society_id:
        # Apply same filters to count
        count_query = query.with_only_columns(func.count()).order_by(None)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    # Eagerly load society relationship to avoid lazy loading issues
    query = query.options(selectinload(Event.society))
    
    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()
    
    pages = max(1, -(-total // page_size))  # ceiling division

    # Build response
    return EventListResponse(
        items=[
            EventResponse(
                id=event.id,
                title=event.title,
                description=event.description,
                location=event.location,
                location_building=event.location_building,
                location_room=event.location_room,
                start_time=event.start_time,
                end_time=event.end_time,
                source_type=event.source_type,
                confidence_score=event.confidence_score,
                members_only=bool((event.extracted_data or {}).get('members_only', False)),
                society=SocietyInfo(
                    id=event.society.id,
                    name=event.society.name,
                    instagram_handle=event.society.instagram_handle
                ),
                created_at=event.created_at
            )
            for event in events
        ],
        total=total,
        page=page,
        size=page_size,
        pages=pages,
    )


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific event by ID."""
    query = select(Event).join(Society).where(
        and_(
            Event.id == event_id,
            Event.is_active == True
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        location=event.location,
        location_building=event.location_building,
        location_room=event.location_room,
        start_time=event.start_time,
        end_time=event.end_time,
        source_type=event.source_type,
        confidence_score=event.confidence_score,
        members_only=bool((event.extracted_data or {}).get('members_only', False)),
        society=SocietyInfo(
            id=event.society.id,
            name=event.society.name,
            instagram_handle=event.society.instagram_handle
        ),
        created_at=event.created_at
    )


# Import func for count query
from sqlalchemy import func

# Made with Bob
