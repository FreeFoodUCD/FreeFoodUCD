from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
import secrets
import string
import hmac
import hashlib
import time

from collections import defaultdict

from app.db.base import get_db
from app.db.models import User, UserSocietyPreference
from app.services.notifications import brevo
from app.core.config import settings

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory sliding-window rate limiter (single uvicorn worker — no shared state needed)
_rl_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limit(request: Request, key_suffix: str, limit: int, window: int):
    """Sliding-window rate limit. Raises 429 if IP exceeds `limit` calls in `window` seconds."""
    ip = request.client.host if request.client else "unknown"
    key = f"{key_suffix}:{ip}"
    now = time.time()
    cutoff = now - window
    hits = _rl_hits[key]
    # Evict timestamps outside the current window
    hits[:] = [t for t in hits if t > cutoff]
    logger.warning(f"RATE_LIMIT key={key} hits_in_window={len(hits)} limit={limit}")
    if len(hits) >= limit:
        logger.warning(f"RATE_LIMIT BLOCKED key={key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    hits.append(now)


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
    """Generate a 6-digit verification code using a CSPRNG."""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def _make_user_token(user_id: str) -> str:
    """Create a short-lived HMAC-signed token for user authentication."""
    expires = int(time.time()) + 3600  # 1 hour
    message = f"{user_id}:{expires}"
    sig = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}:{sig}"


def _verify_user_token(token: str) -> Optional[str]:
    """Verify HMAC token. Returns user_id if valid, else None."""
    parts = token.split(":")
    if len(parts) != 3:
        return None
    user_id, expires_str, sig = parts
    try:
        expires = int(expires_str)
    except ValueError:
        return None
    if time.time() > expires:
        return None
    message = f"{user_id}:{expires}"
    expected = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id


async def _require_user_token(authorization: Optional[str] = Header(None)) -> str:
    """Dependency: validates Bearer token and returns user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = _verify_user_token(authorization[7:])
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


@router.post("/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(
    request: Request,
    user_data: UserSignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Sign up a new user for email notifications.
    Sends verification code via email.
    """
    _rate_limit(request, "signup", limit=3, window=600)
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

            # Resend verification code in background
            background_tasks.add_task(brevo.send_verification_email, user_data.email, verification_code)

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

    # Send verification code via Brevo in background (returns immediately)
    background_tasks.add_task(brevo.send_verification_email, user_data.email, verification_code)

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
    token_user_id: str = Depends(_require_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Get user details by ID."""
    if str(user_id) != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    token_user_id: str = Depends(_require_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Update user notification preferences."""
    if str(user_id) != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    token_user_id: str = Depends(_require_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Update notification preference for a specific society."""
    if str(user_id) != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    request: Request,
    verify_data: VerifyCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user with code sent via email.
    Returns a short-lived Bearer token for use on authenticated user endpoints.
    """
    _rate_limit(request, "verify", limit=5, window=600)
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
        return {
            "message": "Already verified",
            "verified": True,
            "user_id": str(user.id),
            "token": _make_user_token(str(user.id)),
        }

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

    # Send welcome email in background (returns immediately)
    background_tasks.add_task(brevo.send_welcome_email, verify_data.email)

    return {
        "message": "Verification successful",
        "verified": True,
        "user_id": str(user.id),
        "token": _make_user_token(str(user.id)),
    }
