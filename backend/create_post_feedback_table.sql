-- Create post_feedback table for tracking admin feedback on NLP accuracy
-- Run this on Railway database if alembic migration hasn't been applied

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

-- Verify table was created
SELECT 'post_feedback table created successfully' AS status;

-- Made with Bob
