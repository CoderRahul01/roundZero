# Implementation Plan: Vision Agents Integration

## Overview

This implementation plan follows vertical slice development (Schema → API → UI) to integrate Vision Agents into RoundZero AI Interview Coach. The system enables live video interviews with real-time emotion detection, body language analysis, speech pattern monitoring, and intelligent AI-driven interview orchestration using Gemini Flash-8B, Claude Sonnet 4, and Stream.io WebRTC.

The implementation is broken down into atomic, incremental tasks that build on each other, with testing integrated throughout. Each task references specific requirements and can be completed independently.

## Tasks

### 1. Backend Dependencies and Environment Setup

- [x] 1.1 Install Vision Agents library and dependencies
  - Install vision-agents package with Stream.io integration
  - Install google-generativeai for Gemini Flash-8B
  - Install stream-chat for Stream.io WebRTC
  - Install anthropic for Claude Sonnet 4
  - Update pyproject.toml with all dependencies
  - _Requirements: 20.7, 20.8_

- [x] 1.2 Configure environment variables for Vision Agents services
  - Add STREAM_API_KEY and STREAM_API_SECRET to .env
  - Add GEMINI_API_KEY for emotion detection
  - Add vision-agents specific configuration
  - Create .env.example with placeholder values
  - _Requirements: 20.1, 20.2, 20.3, 19.15_

- [x] 1.3 Create project structure for Vision Agents integration
  - Create backend/agent/vision/ directory
  - Create backend/agent/vision/processors/ for EmotionProcessor and SpeechProcessor
  - Create backend/agent/vision/core/ for RoundZeroAgent
  - Create backend/agent/vision/utils/ for helpers
  - _Requirements: 19.1_

- [x] 1.4 Implement environment validation on startup
  - Create validate_environment() function
  - Check all required API keys are present
  - Log error and exit if missing required variables
  - Add validation to application lifespan
  - _Requirements: 20.3, 20.4_

### 2. MongoDB Schema and Repository Layer

- [x] 2.1 Create live_sessions collection schema
  - Define live_sessions document structure with all required fields
  - Include session_id, candidate_id, call_id, role, topics, difficulty, mode
  - Include transcript array with speaker, text, timestamp, is_final
  - Include emotion_timeline array with emotion snapshots
  - Include speech_metrics object per question
  - Include decisions array with decision records
  - Include session_summary field
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 8.13, 8.14, 8.15, 8.16_

- [x] 2.2 Create question_results collection schema
  - Define question_results document structure
  - Include session_id, question_id, question_text, answer_text
  - Include evaluation scores (relevance, completeness, correctness)
  - Include context fields (emotion, confidence, filler_count, speech_pace)
  - _Requirements: 8.1_

- [x] 2.3 Create MongoDB indexes for performance
  - Create unique index on live_sessions.session_id
  - Create compound index on live_sessions (candidate_id, started_at)
  - Create index on live_sessions.started_at for time-based queries
  - Create compound index on question_results (session_id, timestamp)
  - _Requirements: 8.17, 8.18_


- [x] 2.4 Implement LiveSessionRepository class
  - Create create_session() method to initialize session document
  - Create add_transcript_segment() method to append transcript
  - Create add_emotion_snapshot() method to append emotion data
  - Create add_speech_metrics() method to store speech metrics per question
  - Create add_decision_record() method to log decisions
  - Create finalize_session() method to set ended_at and summary
  - Create get_session() method to retrieve session by ID
  - Use Motor async MongoDB driver
  - _Requirements: 8.1, 8.8, 8.10, 8.12, 8.14, 8.16_

- [ ]* 2.5 Write unit tests for LiveSessionRepository
  - Test session creation with all required fields
  - Test transcript segment appending
  - Test emotion snapshot storage
  - Test speech metrics storage
  - Test decision record logging
  - Test session finalization
  - _Requirements: 8.1_

### 3. EmotionProcessor Implementation

- [x] 3.1 Create EmotionSnapshot data class
  - Define EmotionSnapshot with emotion, confidence_score, engagement_level, body_language_observations, timestamp
  - Add validation for confidence_score (0-100 range)
  - Add validation for emotion enum values
  - Add validation for engagement_level enum values
  - _Requirements: 1.3, 1.4, 1.5, 1.6_

- [x] 3.2 Implement EmotionProcessor class extending VideoProcessor
  - Create EmotionProcessor class inheriting from vision_agents.VideoProcessor
  - Initialize with gemini_client, session_id, mongo_repository, frame_sample_rate, rate_limit_threshold
  - Implement frame_count tracking and emotion_snapshots list
  - Implement daily_request_count tracking with reset logic
  - _Requirements: 1.1, 1.8_

- [x] 3.3 Implement frame sampling logic in EmotionProcessor
  - Implement process_frame() method with frame sampling
  - Sample every Nth frame based on frame_sample_rate
  - Check rate limit before processing
  - Adjust sampling frequency when approaching limit (>900 calls)
  - _Requirements: 1.1, 1.8_

- [x] 3.4 Implement Gemini Flash-8B integration for emotion analysis
  - Create _analyze_with_gemini() method
  - Build prompt for emotion analysis (emotion, confidence_score, engagement_level, body_language)
  - Call Gemini Flash-8B API with frame and prompt
  - Parse JSON response and extract emotion data
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 3.5 Implement emotion data storage and retrieval
  - Create _store_snapshot() method to save to MongoDB
  - Implement get_latest_emotion() to return most recent snapshot
  - Implement get_average_confidence() to calculate average score
  - Implement reset_daily_counter() for midnight UTC reset
  - _Requirements: 1.9, 1.10_

- [x] 3.6 Implement error handling for EmotionProcessor
  - Wrap Gemini API calls in try-except
  - Log errors but continue processing without throwing exceptions
  - Return None on processing failure
  - Reduce sampling frequency on rate limit exceeded
  - _Requirements: 1.7, 1.8_

- [ ]* 3.7 Write property test for frame sampling consistency
  - **Property 1: Frame Sampling Consistency**
  - **Validates: Requirements 1.1**
  - Generate random frame sequences (100-200 frames)
  - Verify sampling occurs exactly every Nth frame
  - Test with different sampling rates (10, 15, 20)
  - Use Hypothesis for property-based testing

- [ ]* 3.8 Write property test for emotion data completeness
  - **Property 2: Emotion Data Completeness**
  - **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
  - Generate random Gemini API responses
  - Verify all required fields are extracted or defaulted
  - Test with missing fields, invalid values, malformed JSON

- [ ]* 3.9 Write property test for graceful degradation
  - **Property 3: Graceful Emotion Processing Degradation**
  - **Validates: Requirements 1.7**
  - Simulate various Gemini API failures
  - Verify no exceptions are thrown
  - Verify neutral emotion data is provided
  - Verify errors are logged

- [ ]* 3.10 Write property test for adaptive rate limiting
  - **Property 4: Adaptive Rate Limiting**
  - **Validates: Requirements 1.8**
  - Simulate daily request counts approaching limit
  - Verify sampling frequency is reduced at >900 calls
  - Verify processing continues with adjusted rate

### 4. SpeechProcessor Implementation

- [x] 4.1 Create SpeechMetrics data class
  - Define SpeechMetrics with filler_word_count, speech_pace, long_pause_count, average_filler_rate, rapid_speech, slow_speech
  - Add validation for numeric fields
  - Add boolean flags for rapid/slow speech
  - _Requirements: 2.3, 2.8, 2.9, 2.10_


- [x] 4.2 Implement SpeechProcessor class extending AudioProcessor
  - Create SpeechProcessor class inheriting from vision_agents.AudioProcessor
  - Initialize with session_id, mongo_repository
  - Define filler word regex patterns (um, uh, like, basically, you know, sort of, kind of)
  - Initialize counters for current question metrics
  - _Requirements: 2.1, 2.2_

- [x] 4.3 Implement transcript segment processing
  - Create process_transcript_segment() method
  - Process only final transcript segments
  - Detect long pauses (3+ seconds since last speech)
  - Count filler words using regex patterns
  - Count total words in segment
  - Update timing information
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4.4 Implement speech pace calculation
  - Calculate elapsed time from start_time to current timestamp
  - Calculate speech_pace as (word_count / elapsed_time) * 60
  - Flag rapid_speech when pace > 180 WPM
  - Flag slow_speech when pace < 100 WPM
  - _Requirements: 2.3, 2.8, 2.9_

- [x] 4.5 Implement filler rate calculation
  - Calculate average_filler_rate as (filler_count / word_count) * 100
  - Return metrics with all calculated values
  - _Requirements: 2.10_

- [x] 4.6 Implement question reset and metrics storage
  - Create reset_for_new_question() method
  - Store previous question metrics before reset
  - Reset all counters to zero for new question
  - Create _store_metrics() method to save to MongoDB
  - Create get_current_metrics() for real-time access
  - _Requirements: 2.5, 2.7_

- [ ]* 4.7 Write property test for filler word detection accuracy
  - **Property 5: Filler Word Detection Accuracy**
  - **Validates: Requirements 2.1, 2.2**
  - Generate random transcripts with known filler word counts
  - Verify all filler words are correctly detected
  - Test with various filler word patterns and combinations

- [ ]* 4.8 Write property test for speech pace calculation
  - **Property 6: Speech Pace Calculation**
  - **Validates: Requirements 2.3**
  - Generate random transcript sequences with timestamps
  - Verify speech pace formula: (words / seconds) * 60
  - Test with various word counts and time intervals

- [ ]* 4.9 Write property test for pause detection timing
  - **Property 7: Pause Detection Timing**
  - **Validates: Requirements 2.4**
  - Generate random timestamp sequences with gaps
  - Verify long_pause is recorded for gaps >= 3 seconds
  - Verify no pause recorded for gaps < 3 seconds

- [ ]* 4.10 Write property test for speech metrics reset
  - **Property 8: Speech Metrics Reset**
  - **Validates: Requirements 2.5**
  - Process multiple questions with metrics
  - Verify counters reset to zero on new question
  - Verify previous metrics are stored before reset

- [ ]* 4.11 Write property test for speech pace threshold flagging
  - **Property 9: Speech Pace Threshold Flagging**
  - **Validates: Requirements 2.8, 2.9**
  - Generate random speech pace values
  - Verify rapid_speech flag when pace > 180
  - Verify slow_speech flag when pace < 100

### 5. DecisionEngine Implementation

- [x] 5.1 Create DecisionEngine class for Claude integration
  - Initialize with Claude API key
  - Set model to "claude-3-5-sonnet-20241022"
  - Create AsyncAnthropic client
  - _Requirements: 4.1, 4.2_

- [x] 5.2 Implement decision-making with multimodal context
  - Create make_decision() method accepting context dict
  - Build prompt with question_text, transcript_so_far, emotion, confidence_score, engagement_level, filler_word_count, speech_pace, long_pause_count
  - Call Claude API with structured prompt
  - Parse JSON response for action and message
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11_

- [x] 5.3 Implement decision response parsing
  - Create _parse_decision_response() method
  - Parse JSON from Claude response
  - Validate action is one of (CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT)
  - Extract optional message text
  - Default to CONTINUE if parsing fails
  - _Requirements: 4.12, 4.13, 4.14_

- [x] 5.4 Implement fallback decision logic
  - Create _fallback_decision() method for Claude API failures
  - Implement rule-based logic using filler count, pauses, confidence
  - Return ENCOURAGE for high filler count (>10)
  - Return ENCOURAGE for low confidence (<30)
  - Return HINT for multiple long pauses (>3)
  - Default to CONTINUE
  - _Requirements: 3.20, 4.14_

- [x] 5.5 Implement answer evaluation
  - Create evaluate_answer() method
  - Build evaluation prompt with question and answer
  - Request relevance_score, completeness_score, correctness_score, feedback
  - Parse JSON response with scores and feedback
  - Handle evaluation errors gracefully
  - _Requirements: 3.13_

- [x] 5.6 Implement session summary generation
  - Create generate_summary() method
  - Accept prompt with session context
  - Call Claude API for summary generation
  - Return summary text
  - Handle generation errors with fallback message
  - _Requirements: 3.15, 3.16_


- [ ]* 5.7 Write property test for decision context completeness
  - **Property 11: Decision Context Completeness**
  - **Validates: Requirements 4.1-4.10**
  - Generate random context dictionaries
  - Verify all required fields are present in prompt
  - Test with missing optional fields

- [ ]* 5.8 Write property test for fallback decision logic
  - **Property 13: Fallback Decision Logic**
  - **Validates: Requirements 3.20, 4.14**
  - Simulate Claude API failures
  - Verify valid decision is returned using rules
  - Test with various context values

### 6. QuestionManager Implementation

- [x] 6.1 Create QuestionManager class for Pinecone integration
  - Initialize with pinecone_client, gemini_embedding_service, mongo_repository
  - Set index_name to "interview-questions"
  - _Requirements: 9.1, 9.3_

- [x] 6.2 Implement semantic question retrieval
  - Create fetch_questions() method with query_text, difficulty, limit
  - Generate embedding using Gemini embedding service
  - Query Pinecone with embedding and difficulty filter
  - Extract question data from results
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 6.3 Implement question shuffling and selection
  - Shuffle Pinecone results for variety
  - Select first N questions (default 5)
  - _Requirements: 9.7, 9.8_

- [x] 6.4 Implement fallback to MongoDB default questions
  - Create _fetch_default_questions() method
  - Query MongoDB for questions by difficulty
  - Use when Pinecone fails
  - Log fallback usage
  - _Requirements: 9.9, 10.13_

- [ ]* 6.5 Write property test for question retrieval fallback
  - **Property 17: Question Retrieval Fallback**
  - **Validates: Requirements 9.9, 10.13**
  - Simulate Pinecone failures
  - Verify fallback to MongoDB occurs
  - Verify questions are still returned

### 7. RoundZeroAgent Core Implementation

- [x] 7.1 Create RoundZeroAgent class extending Vision Agents Agent
  - Create RoundZeroAgent inheriting from vision_agents.Agent
  - Initialize with session parameters and all processors/services
  - Set up state variables (questions, current_question_index, transcript_buffer, word_count)
  - _Requirements: 3.1, 3.2_

- [x] 7.2 Implement agent initialization
  - Create initialize() method
  - Fetch questions from Pinecone via QuestionManager
  - Fetch candidate memory from Supermemory
  - Store session metadata to MongoDB
  - Handle initialization failures gracefully
  - _Requirements: 3.1, 3.2, 10.1, 10.2_

- [x] 7.3 Implement interview start flow
  - Create start_interview() method
  - Generate personalized greeting using candidate memory
  - Speak greeting via ElevenLabs TTS
  - Ask first question via TTS
  - _Requirements: 3.3, 3.4_

- [x] 7.4 Implement transcript handling
  - Create handle_transcript_segment() method
  - Accumulate transcript in buffer
  - Count words in transcript
  - Forward to SpeechProcessor for analysis
  - Request decision when word_count >= 20
  - _Requirements: 3.5, 3.6, 3.7_

- [x] 7.5 Implement decision request flow
  - Create _request_decision() method
  - Get latest emotion data from EmotionProcessor
  - Get current speech metrics from SpeechProcessor
  - Build context dictionary with all multimodal data
  - Call DecisionEngine.make_decision()
  - Execute returned action
  - _Requirements: 3.6, 3.7, 3.8_

- [x] 7.6 Implement action execution
  - Create _execute_action() method
  - Handle CONTINUE action (no interruption)
  - Handle INTERRUPT action (speak message, clear buffer)
  - Handle ENCOURAGE action (speak encouragement)
  - Handle HINT action (speak hint)
  - Handle NEXT action (evaluate and move to next question)
  - _Requirements: 3.9, 3.10, 3.11, 3.12, 3.13, 3.14_

- [x] 7.7 Implement answer evaluation and question transition
  - Create _evaluate_and_next() method
  - Call DecisionEngine.evaluate_answer()
  - Store question result to MongoDB
  - Reset transcript buffer and word count
  - Reset SpeechProcessor for new question
  - Move to next question or complete interview
  - _Requirements: 3.13, 3.17_

- [x] 7.8 Implement TTS integration
  - Create _speak() method
  - Call ElevenLabs TTS service
  - Play audio through Stream.io call
  - Handle TTS failures gracefully
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 7.9 Implement interview completion flow
  - Create _complete_interview() method
  - Generate session summary via DecisionEngine
  - Write summary to Supermemory
  - Finalize session in MongoDB
  - Speak closing message
  - _Requirements: 3.15, 3.16, 3.17, 3.18, 3.19_

- [x] 7.10 Implement session summary generation
  - Create _generate_session_summary() method
  - Gather emotion timeline and average confidence
  - Build comprehensive summary prompt
  - Call DecisionEngine.generate_summary()
  - Include performance, strengths, improvements, communication style, emotion patterns, speech patterns
  - _Requirements: 10.5, 10.6, 10.7, 10.8, 10.9, 10.10_


- [ ]* 7.11 Write property test for agent initialization completeness
  - **Property 10: Agent Initialization Completeness**
  - **Validates: Requirements 3.1, 3.2**
  - Test with various session parameters
  - Verify questions are fetched (or fallback used)
  - Verify candidate memory is fetched (or handled gracefully)
  - Verify session metadata is stored

- [ ]* 7.12 Write property test for action execution correctness
  - **Property 12: Action Execution Correctness**
  - **Validates: Requirements 3.10-3.14**
  - Test each action type (CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT)
  - Verify correct behavior for each action
  - Verify state changes appropriately

- [ ]* 7.13 Write property test for session summary generation
  - **Property 24: Session Summary Generation**
  - **Validates: Requirements 10.5-10.11**
  - Generate random session data
  - Verify summary contains all required sections
  - Verify summary is written to Supermemory

### 8. Stream.io WebRTC Integration

- [x] 8.1 Create Stream.io client initialization
  - Initialize StreamClient with API key and secret
  - Create helper function to generate Stream tokens
  - Implement token expiry (1 hour)
  - _Requirements: 7.2, 7.3, 15.7_

- [x] 8.2 Implement call creation
  - Create function to create Stream call with call_type="interview"
  - Configure call with audio and video enabled
  - Return call_id for frontend
  - _Requirements: 7.4, 7.5_

- [x] 8.3 Implement video frame streaming to EmotionProcessor
  - Set up frame capture from Stream call
  - Forward frames to EmotionProcessor
  - Handle frame streaming errors
  - _Requirements: 7.7_

- [x] 8.4 Implement audio streaming to Deepgram
  - Set up audio capture from Stream call
  - Forward audio chunks to Deepgram STT
  - Handle audio streaming errors
  - _Requirements: 7.8_

- [x] 8.5 Implement AI audio streaming to candidate
  - Stream ElevenLabs audio to Stream call
  - Handle audio playback errors
  - _Requirements: 7.9_

- [x] 8.6 Implement connection quality monitoring
  - Track connection quality metrics
  - Reduce video quality on degradation
  - Log quality events
  - _Requirements: 7.10, 7.11_

- [x] 8.7 Implement reconnection logic
  - Attempt reconnection on connection drop
  - Retry for 30 seconds with exponential backoff
  - End session gracefully if reconnection fails
  - _Requirements: 7.12, 7.13_

- [x] 8.8 Implement Stream event logging
  - Log all Stream events to MongoDB
  - Include event type, timestamp, session_id
  - Use for debugging and analytics
  - _Requirements: 7.14_

### 9. API Endpoints Implementation

- [x] 9.1 Implement POST /api/interview/start-live-session endpoint
  - Create FastAPI route with authentication
  - Validate request body (role, topics, difficulty, mode)
  - Check rate limit (10 sessions per day)
  - Create Stream.io call
  - Initialize RoundZeroAgent
  - Store session metadata
  - Return call_id, session_id, stream_token
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14, 5.15_

- [x] 9.2 Implement DELETE /api/interview/{session_id}/end-live-session endpoint
  - Create FastAPI route with authentication
  - Validate session ownership
  - Complete interview (generate summary)
  - Store final data
  - Cleanup resources
  - Return completion status
  - _Requirements: 3.15, 3.16, 3.17_

- [x] 9.3 Implement GET /api/interview/{session_id}/live-state endpoint
  - Create FastAPI route with authentication
  - Validate session ownership
  - Get latest emotion from EmotionProcessor
  - Get current speech metrics from SpeechProcessor
  - Return current state, question progress, emotion, metrics
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 6.13, 6.14, 6.15_

- [x] 9.4 Implement GET /api/admin/usage-stats endpoint
  - Create FastAPI route with admin authentication
  - Get daily usage statistics from tracker
  - Return Gemini calls, Claude tokens, Deepgram minutes, ElevenLabs characters
  - Return active sessions and total sessions today
  - _Requirements: 14.8, 14.9_

- [x] 9.5 Implement GET /api/admin/metrics endpoint
  - Create FastAPI route with admin authentication
  - Calculate active sessions count
  - Calculate total sessions today
  - Calculate average session duration
  - Calculate error rate last hour
  - Calculate API latency percentiles (p50, p95, p99)
  - _Requirements: 18.5, 18.6, 18.7, 18.8, 18.9_

- [x] 9.6 Implement GET /api/health endpoint
  - Create FastAPI route (no authentication)
  - Test connectivity to all services (MongoDB, Stream, Gemini, Claude, Deepgram, ElevenLabs, Pinecone, Supermemory)
  - Return overall status (healthy/degraded/unhealthy)
  - Return individual service statuses
  - _Requirements: 18.11, 18.12, 18.13, 18.14_

- [x]* 9.7 Write integration tests for API endpoints
  - Test start-live-session with valid request
  - Test start-live-session with invalid request (400)
  - Test start-live-session with rate limit exceeded (429)
  - Test end-live-session with valid session
  - Test live-state retrieval
  - Test authentication failures (401)
  - _Requirements: 17.1-17.18_


- [ ]* 9.8 Write property test for authentication token validation
  - **Property 21: Authentication Token Validation**
  - **Validates: Requirements 15.1-15.4**
  - Test with missing tokens (401)
  - Test with invalid tokens (401)
  - Test with expired tokens (401)
  - Verify candidate_id extraction from valid tokens

- [ ]* 9.9 Write property test for rate limit enforcement
  - **Property 15: Rate Limit Enforcement**
  - **Validates: Requirements 5.14, 5.15, 14.1**
  - Simulate multiple session requests
  - Verify 10 sessions per day limit
  - Verify 429 status when exceeded

### 10. Error Handling and Resilience

- [x] 10.1 Create ErrorHandler class for centralized error handling
  - Initialize with logger and alert_service
  - Track error counts per service
  - _Requirements: 13.10_

- [x] 10.2 Implement Gemini error handling
  - Create handle_gemini_error() method
  - Log error with context
  - Increment error count
  - Send alert if error rate is high
  - Return neutral emotion data
  - _Requirements: 13.1_

- [x] 10.3 Implement Claude error handling
  - Create handle_claude_error() method
  - Log error with context
  - Use fallback decision logic
  - _Requirements: 13.2_

- [x] 10.4 Implement Deepgram error handling
  - Create handle_deepgram_error() method
  - Attempt reconnection (3 attempts with exponential backoff)
  - End session gracefully if reconnection fails
  - _Requirements: 13.3_

- [x] 10.5 Implement ElevenLabs error handling
  - Create handle_elevenlabs_error() method
  - Switch to text-only mode
  - Continue interview without voice
  - _Requirements: 13.4_

- [x] 10.6 Implement MongoDB storage error handling
  - Create handle_storage_error() method
  - Retry 3 times with exponential backoff
  - Store in memory if all retries fail
  - Attempt batch write at session end
  - _Requirements: 13.7_

- [x] 10.7 Implement CircuitBreaker pattern
  - Create CircuitBreaker class
  - Track failure count and state (CLOSED/OPEN/HALF_OPEN)
  - Open circuit after threshold failures
  - Attempt recovery after timeout
  - _Requirements: 13.1-13.13_

- [ ]* 10.8 Write property test for error logging completeness
  - **Property 20: Error Logging Completeness**
  - **Validates: Requirements 13.10, 18.2**
  - Simulate various service failures
  - Verify errors are logged with error_type, timestamp, context
  - Verify logs are stored to MongoDB

### 11. Performance Optimization

- [x] 11.1 Implement AdaptiveFrameSampler for rate limit management
  - Create AdaptiveFrameSampler class
  - Track daily calls and adjust sampling rate
  - Reduce sampling at 70% usage (rate=15)
  - Reduce sampling at 90% usage (rate=20)
  - _Requirements: 14.2, 14.3, 14.4, 16.4_

- [x] 11.2 Implement TTS audio caching with Redis
  - Create TTSCache class
  - Generate cache key from text hash
  - Check Redis cache before API call
  - Store generated audio with 24-hour TTL
  - _Requirements: 11.2, 11.6, 16.3_

- [ ]* 11.3 Write property test for TTS cache hit rate
  - **Property 18: TTS Cache Hit Rate**
  - **Validates: Requirements 11.2, 11.6**
  - Test with repeated text inputs
  - Verify cache hits on subsequent requests
  - Verify cache misses on first request

- [x] 11.4 Implement concurrent operations for answer completion
  - Use asyncio.gather() for parallel processing
  - Run evaluation, storage, and next question prep concurrently
  - Handle exceptions in parallel operations
  - _Requirements: 16.2_

- [x] 11.5 Configure MongoDB connection pooling
  - Set min pool size to 10
  - Set max pool size to 50
  - Set connection timeout to 5 seconds
  - _Requirements: 16.1_

- [x] 11.6 Implement WebSocket for real-time state updates
  - Create WebSocket endpoint for session updates
  - Push confidence updates to frontend
  - Push state changes to frontend
  - Push question updates to frontend
  - _Requirements: 16.6_

- [ ]* 11.7 Write property test for decision latency requirement
  - **Property 22: Decision Latency Requirement**
  - **Validates: Requirements 16.2**
  - Generate random decision contexts
  - Measure decision latency
  - Verify latency < 2 seconds

### 12. Rate Limiting and Cost Control

- [ ] 12.1 Create SessionRateLimiter class
  - Initialize with Redis client
  - Set max_sessions_per_day to 10
  - _Requirements: 14.1_

- [ ] 12.2 Implement rate limit checking
  - Create check_rate_limit() method
  - Check Redis for user's session count today
  - Return false if limit exceeded
  - _Requirements: 14.1_

- [ ] 12.3 Implement session count tracking
  - Create increment_session_count() method
  - Increment Redis counter for user
  - Set 24-hour expiry on counter
  - Reset at midnight UTC
  - _Requirements: 14.1, 14.10_

- [ ] 12.4 Implement usage tracking for all services
  - Track Gemini API calls per day
  - Track Claude token consumption
  - Track Deepgram minutes
  - Track ElevenLabs characters
  - Store metrics in Redis
  - _Requirements: 14.2, 14.5, 14.6, 14.7_

- [ ] 12.5 Implement usage alerts
  - Check if services approach limits
  - Send alert to admin when threshold reached
  - _Requirements: 14.11_

- [ ]* 12.6 Write property test for Gemini rate limit tracking
  - **Property 23: Gemini Rate Limit Tracking**
  - **Validates: Requirements 14.2, 14.3, 14.4**
  - Simulate daily API calls
  - Verify tracking of call count
  - Verify sampling frequency reduction at >900 calls
  - Verify emotion processing disabled at 1000 calls


### 13. Security Implementation

- [ ] 13.1 Implement JWT token validation
  - Create get_current_user_id() dependency
  - Decode JWT token with secret
  - Extract user_id from payload
  - Return 401 for missing/invalid/expired tokens
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 13.2 Implement Stream token generation
  - Create generate_stream_token() function
  - Use Stream API key and secret
  - Set 1-hour expiry
  - _Requirements: 15.7_

- [ ] 13.3 Implement input validation with Pydantic
  - Create StartLiveSessionRequest model
  - Validate role (1-100 characters)
  - Validate topics (1-10 items, 1-50 characters each)
  - Validate difficulty (easy/medium/hard)
  - Validate mode (practice/mock/coaching)
  - _Requirements: 15.10_

- [ ] 13.4 Create Settings class for environment variables
  - Use pydantic_settings.BaseSettings
  - Define all required API keys
  - Load from .env file
  - Validate on startup
  - _Requirements: 15.9, 20.1, 20.2_

- [ ] 13.5 Implement CORS restrictions
  - Configure allowed origins
  - Set allowed methods
  - Set allowed headers
  - _Requirements: 15.12_

- [ ] 13.6 Implement authentication failure logging
  - Log all authentication failures
  - Include timestamp, IP, reason
  - Store to MongoDB
  - _Requirements: 15.13_

- [ ] 13.7 Implement rate limiting for authentication attempts
  - Limit authentication attempts per IP
  - Prevent brute force attacks
  - _Requirements: 15.14_

### 14. Frontend Components

- [x] 14.1 Create LiveInterviewScreen component
  - Create React component with TypeScript
  - Accept sessionId, callId, streamToken props
  - Set up state for aiState, confidenceScore, currentQuestion, questionNumber, totalQuestions
  - _Requirements: 6.1, 6.2, 6.6, 6.7, 6.8, 6.9_

- [x] 14.2 Implement Stream Video SDK initialization
  - Create initializeStream() function
  - Initialize StreamVideoClient with API key and token
  - Join call with callId
  - Handle initialization errors
  - _Requirements: 6.3, 6.4, 6.5_

- [x] 14.3 Implement WebSocket connection for real-time updates
  - Create setupWebSocket() function
  - Connect to WebSocket endpoint
  - Handle state_change events
  - Handle confidence_update events
  - Handle question_asked events
  - Handle interview_complete events
  - _Requirements: 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 6.13_

- [x] 14.4 Implement video display
  - Display candidate video feed from Stream
  - Display AI status badge
  - Handle video load failures
  - _Requirements: 6.5, 6.6, 6.14, 6.15_

- [x] 14.5 Implement end session functionality
  - Create handleEndSession() function
  - Call DELETE /api/interview/{session_id}/end-live-session
  - Leave Stream call
  - Navigate to session summary screen
  - _Requirements: 6.11, 6.12, 6.13_

- [x] 14.6 Implement cleanup on unmount
  - Create cleanup() function
  - Leave Stream call
  - Disconnect WebSocket
  - Disconnect Stream client
  - _Requirements: 6.12_

- [x] 14.7 Create ConfidenceMeter component
  - Accept score prop (0-100)
  - Display meter bar with fill percentage
  - Use color gradient (red: 0-40, yellow: 41-70, green: 71-100)
  - Display numeric score
  - _Requirements: 6.8, 6.9, 6.10_

- [x] 14.8 Create StatusBadge component
  - Accept state prop (listening/thinking/speaking/idle)
  - Display appropriate icon and text
  - Use color coding for each state
  - _Requirements: 6.7_

- [x] 14.9 Create QuestionDisplay component
  - Display current question number and total
  - Display question text
  - Update in real-time via WebSocket
  - _Requirements: 6.8, 6.9_

- [ ]* 14.10 Write unit tests for frontend components
  - Test LiveInterviewScreen rendering
  - Test WebSocket event handling
  - Test Stream SDK initialization
  - Test ConfidenceMeter color logic
  - Test StatusBadge state display

### 15. Monitoring and Observability

- [ ] 15.1 Implement structured logging with structlog
  - Configure structlog for JSON logging
  - Log all API calls with timestamp, endpoint, status_code, latency
  - Log all AI service calls with model, tokens, latency, success/failure
  - Log all session events with session_id, event_type, timestamp
  - _Requirements: 18.1, 18.2, 18.3_

- [ ] 15.2 Create MetricsCollector class
  - Initialize with Redis client
  - Create record_api_call() method
  - Track call count, latency, success/failure per service
  - Store metrics in Redis with daily keys
  - _Requirements: 18.4, 18.10_

- [ ] 15.3 Implement metrics calculation
  - Calculate active sessions count
  - Calculate total sessions today
  - Calculate average session duration
  - Calculate error rate last hour
  - Calculate API latency percentiles (p50, p95, p99)
  - _Requirements: 18.5, 18.6, 18.7, 18.8, 18.9_

- [ ] 15.4 Create AlertService class
  - Implement send_alert() method
  - Check error rate threshold (5% in 5-minute window)
  - Send alerts via configured channel
  - _Requirements: 18.15_

- [ ]* 15.5 Write property test for health check service status
  - **Property 25: Health Check Service Status**
  - **Validates: Requirements 18.11-18.14**
  - Simulate various service availability scenarios
  - Verify overall status calculation (healthy/degraded/unhealthy)
  - Verify individual service status reporting

### 16. Deployment and Configuration

- [ ] 16.1 Create comprehensive .env.example file
  - Include all required environment variables with placeholders
  - Add comments explaining each variable
  - Include Stream.io, Gemini, Claude, Deepgram, ElevenLabs, Pinecone, Supermemory, MongoDB, Redis, JWT
  - _Requirements: 19.15, 20.2_

- [ ] 16.2 Implement application lifespan management
  - Create lifespan context manager
  - Validate environment variables on startup
  - Initialize all services (MongoDB, Redis, Stream)
  - Create MongoDB indexes
  - Cleanup resources on shutdown
  - _Requirements: 20.3, 20.4, 20.13, 20.14_


- [ ] 16.3 Implement graceful shutdown handling
  - Create GracefulShutdown class
  - Set up signal handlers for SIGTERM and SIGINT
  - Save in-progress sessions on shutdown
  - Close all connections
  - _Requirements: 20.13, 20.14, 20.15_

- [ ] 16.4 Create Procfile for deployment
  - Define web process with uvicorn
  - Use PORT environment variable
  - _Requirements: 20.6_

- [ ] 16.5 Update pyproject.toml with all dependencies
  - Add vision-agents with version
  - Add stream-chat, google-generativeai, anthropic
  - Add deepgram-sdk, elevenlabs, pinecone-client
  - Add motor, redis, pydantic, pydantic-settings
  - Add python-jose for JWT
  - Specify Python version >=3.11
  - _Requirements: 20.7, 20.8_

- [ ] 16.6 Create installation script
  - Document uv installation steps
  - Document dependency installation
  - Document environment setup
  - _Requirements: 20.8_

### 17. Documentation

- [ ] 17.1 Create README.md for Vision Agents integration
  - Document RoundZeroAgent class and methods
  - Document EmotionProcessor configuration
  - Document SpeechProcessor configuration
  - Document required environment variables
  - Provide example usage code
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

- [ ] 17.2 Document API endpoints
  - Create API documentation with request/response examples
  - Document POST /api/interview/start-live-session
  - Document DELETE /api/interview/{session_id}/end-live-session
  - Document GET /api/interview/{session_id}/live-state
  - Document GET /api/admin/usage-stats
  - Document GET /api/admin/metrics
  - Document GET /api/health
  - _Requirements: 19.7, 19.13_

- [ ] 17.3 Document MongoDB schema
  - Document live_sessions collection with field descriptions
  - Document question_results collection with field descriptions
  - Document indexes and their purposes
  - _Requirements: 19.8_

- [ ] 17.4 Document error codes and handling strategies
  - List all error codes and meanings
  - Document recovery procedures
  - Document fallback behaviors
  - _Requirements: 19.9_

- [ ] 17.5 Create architecture diagram
  - Show component interactions
  - Show data flow
  - Show service dependencies
  - _Requirements: 19.10_

- [ ] 17.6 Add inline code comments
  - Comment complex logic in all classes
  - Explain multimodal context building
  - Explain decision-making flow
  - _Requirements: 19.11_

- [ ] 17.7 Add type hints to all functions
  - Add parameter type hints
  - Add return type hints
  - Use typing module for complex types
  - _Requirements: 19.12_

- [ ] 17.8 Create DEPLOYMENT_GUIDE.md
  - Provide step-by-step deployment instructions
  - Document Railway/Render deployment
  - Include troubleshooting section
  - Document minimum versions (Python 3.11+, Node 18+)
  - _Requirements: 20.5, 20.8, 20.9, 20.10, 20.11, 20.12_

### 18. Integration Testing

- [ ] 18.1 Create test endpoint POST /api/interview/test-live-session
  - Accept mock video frames
  - Accept mock audio
  - Return emotion analysis results
  - Return speech metrics
  - Return Claude decisions
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

- [ ] 18.2 Implement mock mode for testing
  - Use pre-recorded responses
  - Skip external API calls
  - _Requirements: 17.7, 17.8_

- [ ] 18.3 Create validation endpoint GET /api/interview/validate-config
  - Check all required API keys are present
  - Test connectivity to all services
  - Return health status for each service
  - _Requirements: 17.9, 17.10, 17.11, 17.12_

- [ ]* 18.4 Write integration test for complete interview flow
  - Test emotion processing pipeline
  - Test speech processing pipeline
  - Test decision engine logic
  - Test MongoDB storage operations
  - Test error handling scenarios
  - _Requirements: 17.13, 17.14, 17.15, 17.16, 17.17, 17.18_

- [ ]* 18.5 Write property test for MongoDB schema compliance
  - **Property 16: MongoDB Schema Compliance**
  - **Validates: Requirements 8.2-8.15**
  - Generate random session data
  - Verify all required fields are present
  - Verify field types match schema

- [ ]* 18.6 Write property test for transcript segment processing
  - **Property 19: Transcript Segment Processing**
  - **Validates: Requirements 12.6, 12.7**
  - Generate random transcript segments
  - Verify final segments are added to buffer
  - Verify word count is updated correctly

### 19. Final Integration and Wiring

- [ ] 19.1 Wire EmotionProcessor to RoundZeroAgent
  - Connect frame streaming from Stream.io to EmotionProcessor
  - Connect emotion data to decision-making flow
  - Test end-to-end emotion detection
  - _Requirements: 1.9, 3.6_

- [ ] 19.2 Wire SpeechProcessor to RoundZeroAgent
  - Connect Deepgram transcripts to SpeechProcessor
  - Connect speech metrics to decision-making flow
  - Test end-to-end speech analysis
  - _Requirements: 2.6, 3.7_

- [ ] 19.3 Wire DecisionEngine to RoundZeroAgent
  - Connect multimodal context to DecisionEngine
  - Connect decisions to action execution
  - Test end-to-end decision flow
  - _Requirements: 3.8, 3.9_

- [ ] 19.4 Wire QuestionManager to RoundZeroAgent
  - Connect Pinecone queries to agent initialization
  - Test question retrieval and fallback
  - _Requirements: 3.1, 9.10_

- [x] 19.5 Wire all API endpoints to agent lifecycle
  - Connect start-live-session to agent initialization
  - Connect end-live-session to agent completion
  - Connect live-state to agent state queries
  - Test complete API flow
  - _Requirements: 5.1-5.15_

- [ ] 19.6 Wire frontend components to backend APIs
  - Connect LiveInterviewScreen to start-live-session API
  - Connect WebSocket to real-time updates
  - Connect Stream SDK to video call
  - Test complete frontend-backend integration
  - _Requirements: 6.1-6.15_

### 20. Checkpoint - System Validation

- [ ] 20.1 Run all property-based tests
  - Verify all 25 correctness properties pass
  - Review any failures and fix
  - Ensure 100+ iterations per property test

- [ ] 20.2 Run all unit tests
  - Verify all component tests pass
  - Verify all integration tests pass
  - Check test coverage

- [ ] 20.3 Run end-to-end interview simulation
  - Start live session via API
  - Simulate candidate speaking
  - Verify emotion detection works
  - Verify speech analysis works
  - Verify AI decisions are made
  - Verify questions progress
  - Complete interview and verify summary
  - Check all data stored in MongoDB

- [ ] 20.4 Validate error handling
  - Simulate Gemini API failure
  - Simulate Claude API failure
  - Simulate Deepgram failure
  - Simulate ElevenLabs failure
  - Simulate MongoDB failure
  - Verify graceful degradation in all cases

- [ ] 20.5 Validate rate limiting
  - Test session rate limit (10 per day)
  - Test Gemini rate limit (1000 per day)
  - Verify limits are enforced correctly

- [ ] 20.6 Validate security
  - Test authentication with invalid tokens
  - Test authorization for session access
  - Verify API keys are not exposed
  - Test CORS restrictions

- [ ] 20.7 Validate performance
  - Measure decision latency (<2s)
  - Measure transcript latency (<500ms)
  - Measure TTS latency (<1s)
  - Verify WebSocket latency (<200ms)

- [ ] 20.8 Review documentation
  - Verify README is complete
  - Verify API documentation is accurate
  - Verify deployment guide is clear
  - Verify code comments are helpful

- [ ] 20.9 Final checkpoint - Ensure all tests pass, ask the user if questions arise
  - All property tests passing
  - All unit tests passing
  - All integration tests passing
  - End-to-end flow working
  - Error handling validated
  - Performance requirements met
  - Security validated
  - Documentation complete

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Follow vertical slice development: complete MongoDB schema → API → UI for each feature
- Property-based tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Checkpoints ensure incremental validation throughout implementation
- All code should use Python 3.11+ with type hints
- Use `uv` for backend dependency management as per AGENTS.md
- All secrets must be in .env file, never hardcoded
- Maintain high code quality with comprehensive error handling
