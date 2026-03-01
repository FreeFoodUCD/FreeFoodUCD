from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    
    # Redis
    REDIS_URL: str
    
    # Apify (Instagram scraping)
    APIFY_API_TOKEN: str

    # Instagram credentials (unused — kept for reference)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None

    # Twilio (WhatsApp) - Optional, not used anymore
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # Resend (Old) - Optional, not used anymore
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = None
    
    # Email Service (Brevo/Sendinblue)
    BREVO_API_KEY: str
    BREVO_FROM_EMAIL: str
    BREVO_FROM_NAME: str = "FreeFood UCD"
    
    # AWS S3 (Optional - for production)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "eu-west-1"
    
    # Application
    SECRET_KEY: str
    ADMIN_API_KEY: str = "change-this-in-production"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Scraping
    SCRAPE_MAX_POSTS_PER_SOCIETY: int = 3

    # Email allowlist (comma-separated; if set, only these addresses receive event emails)
    NOTIFICATION_TEST_EMAILS: str = ""

    # NLP / Classification (Phase E — Gemini-first)
    # Gemini Flash is the primary classifier. Set USE_GEMINI=true in Railway env vars to activate.
    # Set USE_GEMINI=false as an emergency kill switch — all posts will be rejected (no LLM).
    GEMINI_API_KEY: Optional[str] = None
    USE_GEMINI: bool = False
    # Plausibility window for Gemini datetime validation (days)
    GEMINI_MAX_FUTURE_DAYS: int = 30

    # Langfuse observability (F1 — Phase F)
    # Optional: if keys are absent, Langfuse is silently disabled (graceful degradation).
    # Sign up free at https://cloud.langfuse.com — 50k events/month free tier.
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    @model_validator(mode='after')
    def check_admin_key(self):
        if self.ADMIN_API_KEY == "change-this-in-production":
            raise ValueError("ADMIN_API_KEY must be set to a strong secret — do not use the default value")
        return self

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()

# Made with Bob
