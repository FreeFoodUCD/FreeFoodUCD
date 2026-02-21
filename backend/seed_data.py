"""
Seed initial data for FreeFoodUCD database
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import Society
from app.core.config import settings

async def seed_societies():
    """Seed UCD societies into the database"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    societies = [
        {
            "name": "UCD Law Society",
            "instagram_handle": "ucdlawsoc",
            "is_active": True
        },
        {
            "name": "UCD Computer Science Society",
            "instagram_handle": "ucdcompsci",
            "is_active": True
        },
        {
            "name": "UCD Business Society",
            "instagram_handle": "ucdbusiness",
            "is_active": True
        },
        {
            "name": "UCD Engineering Society",
            "instagram_handle": "ucdengineering",
            "is_active": True
        },
        {
            "name": "UCD Medical Society",
            "instagram_handle": "ucdmedsoc",
            "is_active": True
        },
        {
            "name": "UCD Drama Society",
            "instagram_handle": "ucddramasoc",
            "is_active": True
        },
        {
            "name": "UCD Music Society",
            "instagram_handle": "ucdmusicsoc",
            "is_active": True
        },
        {
            "name": "UCD Entrepreneurship Society",
            "instagram_handle": "ucdentre",
            "is_active": True
        },
    ]
    
    async with async_session() as session:
        for society_data in societies:
            society = Society(**society_data)
            session.add(society)
        await session.commit()
    
    await engine.dispose()
    print("✅ Successfully seeded {} societies!".format(len(societies)))

if __name__ == "__main__":
    print("🌱 Seeding database with UCD societies...")
    asyncio.run(seed_societies())

# Made with Bob
