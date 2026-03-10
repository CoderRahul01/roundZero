-- Neon Postgres Database Indexes
-- Purpose: Optimize lookup times for the 10k+ scalability mandate.

-- 1. Index on sessions.user_id 
-- Accelerates "View past sessions" and fetching cross-session history for the active user.
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- 2. Index on question_results.session_id
-- Crucial for generating session report cards quickly (fetches all answers for one session)
CREATE INDEX IF NOT EXISTS idx_question_results_session_id ON question_results(session_id);

-- (Assuming a users table exists as per standard template)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add an AuditLog table (if not exists) for tracking trigger events as requested
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index the audit logs by user for fast retrieval
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
