"""
Run database migration for post_feedback table
This script connects to Railway PostgreSQL and creates the table
"""
import asyncio
import asyncpg
from app.core.config import settings

async def run_migration():
    """Create post_feedback table in Railway database"""
    
    # SQL to create the table
    sql = """
    -- Create post_feedback table for tracking admin feedback on NLP accuracy
    CREATE TABLE IF NOT EXISTS post_feedback (
        id UUID PRIMARY KEY,
        post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
        admin_email VARCHAR(255),
        is_correct BOOLEAN,
        correct_classification BOOLEAN,
        classification_notes TEXT,
        correct_date TIMESTAMP WITH TIME ZONE,
        correct_time VARCHAR(10),
        correct_location VARCHAR(255),
        extraction_notes TEXT,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS ix_post_feedback_post_id ON post_feedback(post_id);
    CREATE INDEX IF NOT EXISTS ix_post_feedback_created_at ON post_feedback(created_at);
    """
    
    print(f"Connecting to database...")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        print("Connected! Running migration...")
        
        # Execute the SQL
        await conn.execute(sql)
        
        print("✅ Migration completed successfully!")
        print("✅ post_feedback table created with indexes")
        
        # Verify the table exists
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'post_feedback'"
        )
        
        if result > 0:
            print("✅ Verified: post_feedback table exists in database")
        else:
            print("❌ Warning: Could not verify table creation")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())

# Made with Bob
