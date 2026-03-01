-- Migration: Extend sessions table for Enhanced Interview Experience
-- Date: 2024
-- Description: Adds onboarding tracking, progress tracking, and overall score fields

-- Add onboarding tracking fields
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS onboarding_duration_seconds INTEGER;

-- Add progress tracking fields
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS current_question_number INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_questions INTEGER;

-- Add overall score fields (using DECIMAL for precision)
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS average_confidence DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS average_relevance DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS average_completeness DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS overall_performance DECIMAL(3,2);

-- Add status field with enum-like constraint
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'in_progress';

-- Add constraint for status values (drop first if exists to avoid errors)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_status_values'
    ) THEN
        ALTER TABLE sessions
        ADD CONSTRAINT check_status_values 
        CHECK (status IN ('onboarding', 'in_progress', 'completed', 'abandoned'));
    END IF;
END $$;

-- Add last_update_timestamp for session state persistence
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS last_update_timestamp TIMESTAMPTZ DEFAULT NOW();

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- Create index on user_id and created_at for user history queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at DESC);

-- Add comment to table
COMMENT ON TABLE sessions IS 'Interview sessions with enhanced tracking for onboarding, progress, and multi-modal analysis';

-- Add comments to new columns
COMMENT ON COLUMN sessions.onboarding_completed IS 'Whether the onboarding flow (greeting, introduction, readiness) was completed';
COMMENT ON COLUMN sessions.onboarding_duration_seconds IS 'Duration of onboarding flow in seconds';
COMMENT ON COLUMN sessions.current_question_number IS 'Current question number (0-based index)';
COMMENT ON COLUMN sessions.total_questions IS 'Total number of questions in the interview';
COMMENT ON COLUMN sessions.average_confidence IS 'Average confidence score across all questions (0.00-1.00)';
COMMENT ON COLUMN sessions.average_relevance IS 'Average relevance score across all questions (0.00-1.00)';
COMMENT ON COLUMN sessions.average_completeness IS 'Average completeness score across all questions (0.00-1.00)';
COMMENT ON COLUMN sessions.overall_performance IS 'Overall performance score (0.00-1.00)';
COMMENT ON COLUMN sessions.status IS 'Current session status: onboarding, in_progress, completed, abandoned';
COMMENT ON COLUMN sessions.last_update_timestamp IS 'Last time the session state was updated';

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'sessions'
ORDER BY ordinal_position;
