from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.db.base import get_db
from app.db.models import User, UserSocietyPreference

router = APIRouter()


# Pydantic schemas
class UserSignupRequest(BaseModel):
    """User signup request schema."""
    phone_number: Optional[str] = Field(None, description="Phone number with country code (e.g., +353871234567)")
    email: Optional[EmailStr] = Field(None, description="Email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+353871234567",
                "email": "student@ucd.ie"
            }
        }


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_verified: bool
    email_verified: bool
    notification_preferences: dict
    is_active: bool
    
    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """Update user notification preferences."""
    notification_preferences: dict = Field(
        ...,
        description="Notification preferences",
        example={"whatsapp": True, "email": False}
    )


class SocietyPreferenceUpdate(BaseModel):
    """Update society notification preferences."""
    society_id: UUID
    notify: bool


@router.post("/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(
    user_data: UserSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sign up a new user for notifications.
    
    At least one of phone_number or email must be provided.
    """
    if not user_data.phone_number and not user_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of phone_number or email must be provided"
        )
    
    # Check if user already exists
    if user_data.phone_number:
        query = select(User).where(User.phone_number == user_data.phone_number)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists"
            )
    
    if user_data.email:
        query = select(User).where(User.email == user_data.email)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
    
    # Create new user
    new_user = User(
        phone_number=user_data.phone_number,
        email=user_data.email,
        whatsapp_verified=False,
        email_verified=False,
        notification_preferences={"whatsapp": True, "email": True}
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # TODO: Send verification code via WhatsApp/Email
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        phone_number=new_user.phone_number,
        whatsapp_verified=new_user.whatsapp_verified,
        email_verified=new_user.email_verified,
        notification_preferences=new_user.notification_preferences,
        is_active=new_user.is_active
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get user details by ID."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        phone_number=user.phone_number,
        whatsapp_verified=user.whatsapp_verified,
        email_verified=user.email_verified,
        notification_preferences=user.notification_preferences,
        is_active=user.is_active
    )


@router.put("/users/{user_id}/preferences", response_model=UserResponse)
async def update_user_preferences(
    user_id: UUID,
    preferences: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user notification preferences."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.notification_preferences = preferences.notification_preferences
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        phone_number=user.phone_number,
        whatsapp_verified=user.whatsapp_verified,
        email_verified=user.email_verified,
        notification_preferences=user.notification_preferences,
        is_active=user.is_active
    )


@router.post("/users/{user_id}/society-preferences")
async def update_society_preference(
    user_id: UUID,
    preference: SocietyPreferenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update notification preference for a specific society."""
    # Check if user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if preference exists
    pref_query = select(UserSocietyPreference).where(
        UserSocietyPreference.user_id == user_id,
        UserSocietyPreference.society_id == preference.society_id
    )
    pref_result = await db.execute(pref_query)
    existing_pref = pref_result.scalar_one_or_none()
    
    if existing_pref:
        # Update existing preference
        existing_pref.notify = preference.notify
    else:
        # Create new preference
        new_pref = UserSocietyPreference(
            user_id=user_id,
            society_id=preference.society_id,
            notify=preference.notify
        )
        db.add(new_pref)
    
    await db.commit()
    
    return {"message": "Society preference updated successfully"}

# Made with Bob
