from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
import random
import string

from app.db.base import get_db
from app.db.models import User, UserSocietyPreference
from app.services.notifications import brevo

router = APIRouter()


# Pydantic schemas
class UserSignupRequest(BaseModel):
    """User signup request schema."""
    email: EmailStr = Field(..., description="Email address")
    
    class Config:
        json_schema_extra = {
            "example": {
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


class VerifyCodeRequest(BaseModel):
    """Verification code request."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(
    user_data: UserSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sign up a new user for email notifications.
    Sends verification code via email.
    """
    # Check if user already exists
    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    # Generate verification code
    verification_code = generate_verification_code()
    code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    if existing_user:
        # If user exists but is not verified, resend verification code
        if not existing_user.email_verified:
            existing_user.verification_code = verification_code
            existing_user.verification_code_expires = code_expires
            await db.commit()
            await db.refresh(existing_user)
            
            # Resend verification code
            try:
                await brevo.send_verification_email(user_data.email, verification_code)
            except Exception as e:
                print(f"Error sending verification code: {e}")
            
            return UserResponse(
                id=existing_user.id,
                email=existing_user.email,
                phone_number=existing_user.phone_number,
                whatsapp_verified=existing_user.whatsapp_verified,
                email_verified=existing_user.email_verified,
                notification_preferences=existing_user.notification_preferences,
                is_active=existing_user.is_active
            )
        else:
            # User is already verified
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="already_signed_up"
            )
    
    # Create new user
    new_user = User(
        phone_number=None,
        email=user_data.email,
        whatsapp_verified=False,
        email_verified=False,
        verification_code=verification_code,
        verification_code_expires=code_expires,
        notification_preferences={"email": True}
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Send verification code via Brevo
    try:
        await brevo.send_verification_email(user_data.email, verification_code)
    except Exception as e:
        # Log error but don't fail signup
        print(f"Error sending verification code: {e}")
    
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


@router.post("/users/verify")
async def verify_user(
    verify_data: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user with code sent via email.
    """
    # Find user
    query = select(User).where(User.email == verify_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already verified
    if user.email_verified:
        return {"message": "Already verified", "verified": True}
    
    # Check verification code
    if not user.verification_code or not user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one."
        )
    
    # Check if code expired
    if datetime.now(timezone.utc) > user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired. Please request a new one."
        )
    
    # Verify code
    if user.verification_code != verify_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Mark as verified
    user.email_verified = True
    
    # Clear verification code
    user.verification_code = None
    user.verification_code_expires = None
    
    await db.commit()
    await db.refresh(user)
    
    # Send welcome email
    try:
        await brevo.send_welcome_email(verify_data.email)
    except Exception as e:
        print(f"Error sending welcome message: {e}")
    
    return {
        "message": "Verification successful",
        "verified": True,
        "user_id": str(user.id)
    }
