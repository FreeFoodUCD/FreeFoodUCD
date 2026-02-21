from fastapi import APIRouter
from app.api.v1.endpoints import events, societies, users, admin

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(events.router, tags=["events"])
api_router.include_router(societies.router, tags=["societies"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Made with Bob
