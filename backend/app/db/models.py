from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class Society(Base):
    """Society model representing UCD societies."""
    __tablename__ = "societies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    instagram_handle = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    scrape_posts = Column(Boolean, default=True)
    scrape_stories = Column(Boolean, default=True)
    last_post_check = Column(DateTime(timezone=True))
    last_story_check = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    posts = relationship("Post", back_populates="society", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="society", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="society", cascade="all, delete-orphan")


class Post(Base):
    """Post model for Instagram feed posts."""
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"))
    instagram_post_id = Column(String(255), unique=True, index=True)
    caption = Column(Text)
    source_url = Column(Text)
    media_urls = Column(JSONB)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_free_food = Column(Boolean, default=False, index=True)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    society = relationship("Society", back_populates="posts")


class Story(Base):
    """Story model for Instagram stories."""
    __tablename__ = "stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"))
    story_text = Column(Text)
    story_timestamp = Column(DateTime(timezone=True))
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    is_free_food = Column(Boolean, default=False, index=True)
    content_hash = Column(String(64), unique=True, index=True)
    screenshot_url = Column(Text)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    society = relationship("Society", back_populates="stories")


class Event(Base):
    """Event model for processed free food events."""
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"))
    title = Column(String(500))
    description = Column(Text)
    location = Column(String(255))
    location_building = Column(String(100))
    location_room = Column(String(50))
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True))
    source_type = Column(String(20), CheckConstraint("source_type IN ('post', 'story')"))
    source_id = Column(UUID(as_uuid=True))
    confidence_score = Column(Float)
    raw_text = Column(Text)
    extracted_data = Column(JSONB)
    notified = Column(Boolean, default=False, index=True)
    notification_sent_at = Column(DateTime(timezone=True))
    reminder_sent = Column(Boolean, default=False, index=True)
    reminder_sent_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    society = relationship("Society", back_populates="events")
    notification_logs = relationship("NotificationLog", back_populates="event", cascade="all, delete-orphan")


class User(Base):
    """User model for notification subscribers."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)
    phone_number = Column(String(20), unique=True, index=True)
    whatsapp_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    verification_code = Column(String(6))
    verification_code_expires = Column(DateTime(timezone=True))
    notification_preferences = Column(
        JSONB,
        default={"whatsapp": True, "email": True},
        server_default='{"whatsapp": true, "email": true}'
    )
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    society_preferences = relationship("UserSocietyPreference", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")


class UserSocietyPreference(Base):
    """User preferences for specific societies."""
    __tablename__ = "user_society_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"), primary_key=True)
    notify = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="society_preferences")
    society = relationship("Society")


class NotificationLog(Base):
    """Log of all notifications sent."""
    __tablename__ = "notification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    notification_type = Column(String(20))  # 'whatsapp' or 'email'
    status = Column(String(20))  # 'sent', 'failed', 'pending'
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    error_message = Column(Text)
    
    # Relationships
    event = relationship("Event", back_populates="notification_logs")
    user = relationship("User", back_populates="notification_logs")


class ScrapingLog(Base):
    """Log of scraping activities for monitoring."""
    __tablename__ = "scraping_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    society_id = Column(UUID(as_uuid=True), ForeignKey("societies.id", ondelete="SET NULL"), nullable=True)
    scrape_type = Column(String(20))  # 'post' or 'story'
    status = Column(String(20))  # 'success', 'failed', 'partial'
    items_found = Column(Integer)
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    society = relationship("Society")

# Made with Bob
