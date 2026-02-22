-- Add reminder fields to events table
-- Run this SQL directly on your database

-- Add the new columns
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMP WITH TIME ZONE;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS ix_events_reminder_sent ON events(reminder_sent);

-- Set default value for existing rows
UPDATE events SET reminder_sent = false WHERE reminder_sent IS NULL;

-- Make reminder_sent NOT NULL
ALTER TABLE events ALTER COLUMN reminder_sent SET NOT NULL;
ALTER TABLE events ALTER COLUMN reminder_sent SET DEFAULT false;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'events' 
AND column_name IN ('reminder_sent', 'reminder_sent_at');

-- Made with Bob
