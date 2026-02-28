import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

# Initialise Sentry before anything else (no-op if SENTRY_DSN is unset)
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

# Create FastAPI application
from app.core.config import settings as _settings
_is_prod = _settings.ENVIRONMENT == "production"

app = FastAPI(
    title="FreeFood UCD API",
    description="API for FreeFood UCD - Never miss free food on campus",
    version="1.0.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"https://freefooducd.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key", "Authorization"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FreeFood UCD API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/debug-rl")
async def debug_rate_limit(request: Request):
    """Temporary: shows Redis rate limit key count for this IP. Remove after testing."""
    import redis.asyncio as aioredis
    ip = request.client.host if request.client else "unknown"
    key = f"rl:signup:{ip}"
    client = aioredis.from_url(settings.REDIS_URL)
    try:
        count = await client.incr(key)
        ttl = await client.ttl(key)
        if count == 1:
            await client.expire(key, 600)
    finally:
        await client.aclose()
    return {"ip": ip, "key": key, "count": count, "ttl_seconds": ttl}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "service": "freefood-ucd-api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )

# Made with Bob
