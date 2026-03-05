-- RoundZero Schema Migration
-- Run this in Supabase Dashboard → SQL Editor

-- Drop existing tables (safe for dev — no production data yet)
DROP TABLE IF EXISTS question_results CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- User Profiles table
CREATE TABLE user_profiles (
  id TEXT PRIMARY KEY, -- user_id from Neon Auth
  full_name TEXT,
  bio TEXT,
  resume_url TEXT,
  skills TEXT[],
  experience_level TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Sessions table
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  role TEXT,
  topics TEXT[],
  difficulty TEXT,
  mode TEXT DEFAULT 'buddy',
  overall_score INT,
  confidence_avg INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ
);

-- Question results table
CREATE TABLE question_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  question_text TEXT,
  user_answer TEXT,
  ideal_answer TEXT,
  score INT,
  filler_word_count INT,
  emotion_log JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_user_profiles_id ON user_profiles(id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_question_results_session_id ON question_results(session_id);
