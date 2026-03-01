# Implementation Plan: Voice AI Interview System

## Overview

This implementation plan breaks down the Voice AI Interview System into discrete, incremental tasks following vertical slice development. The plan is organized into two major phases: (1) MongoDB dataset migration and (2) voice-enabled interview system. Each task builds on previous work and includes validation steps to ensure correctness.

## Tasks

- [x] 1. Set up MongoDB connection and data access layer
  - Create `backend/data/mongo_repository.py` with MongoQuestionRepository class
  - Implement connection handling using MONGODB_URI from environment
  - Add connection pooling configuration
  - Create basic query methods (get_by_id, get_all)
  - _Requirements: 1.1_

- [ ]* 1.1 Write unit tests for MongoDB connection
  - Test connection with valid URI
  - Test connection failure handling
  - Test connection pooling behavior
  - _Requirements: 1.1_

- [x] 2. Implement dataset migration service
  - [x] 2.1 Create DatasetMigrator class in `backend/data/migrate_to_mongodb.py`
    - Implement CSV parsing for Software Questions
    - Implement JSON parsing for HR questions
    - Implement CSV parsing for LeetCode questions
    - Add bulk upsert operations with batching
    - _Requirements: 1.3, 1.4, 1.5_
  
  - [ ]* 2.2 Write property test for data migration completeness
    - **Property 1: Data Migration Completeness**
    - **Validates: Requirements 1.3, 1.4, 1.5**
  
  - [x] 2.3 Implement index creation
    - Create indexes on category, difficulty, source, id fields
    - Add text index on question field for full-text search
    - _Requirements: 1.10_
  
  - [x] 2.4 Add migration logging and error handling
    - Log record counts for each dataset
    - Log errors with context and halt on failure
    - Implement verification queries post-migration
    - _Requirements: 1.6, 1.7, 1.9_
  
  - [ ]* 2.5 Write property test for migration idempotence
    - **Property 2: Migration Idempotence**
    - **Validates: Requirements 1.3, 1.4, 1.5**
  
  - [ ]* 2.6 Write property test for migration error logging
    - **Property 4: Migration Error Logging**
    - **Validates: Requirements 1.7**

- [ ] 3. Implement MongoDB query methods
  - [x] 3.1 Add query methods to MongoQuestionRepository
    - Implement get_questions_by_category
    - Implement get_questions_by_topics
    - Implement search_questions with text search
    - Add pagination support
    - _Requirements: 1.8_
  
  - [ ]* 3.2 Write property test for query result filtering
    - **Property 3: Query Result Filtering**
    - **Validates: Requirements 1.8**
  
  - [ ]* 3.3 Write unit tests for query methods
    - Test category filtering
    - Test difficulty filtering
    - Test topic matching
    - Test pagination
    - _Requirements: 1.8_

- [x] 4. Integrate MongoDB with existing QuestionBank
  - [x] 4.1 Modify QuestionBank class to use MongoQuestionRepository
    - Replace _load_local_questions with MongoDB queries
    - Update fetch_questions to query MongoDB first
    - Keep Pinecone and Gemini generation as fallbacks
    - _Requirements: 1.8_
  
  - [x] 4.2 Update environment configuration
    - Add MONGODB_URI to .env.example
    - Update settings.py to include MongoDB configuration
    - _Requirements: 1.1_
  
  - [ ]* 4.3 Write integration tests for QuestionBank with MongoDB
    - Test question fetching from MongoDB
    - Test fallback to Pinecone when MongoDB is empty
    - Test fallback to Gemini generation
    - _Requirements: 1.8_

- [ ] 5. Run dataset migration and cleanup
  - [ ] 5.1 Execute migration script
    - Run migrate_to_mongodb.py with production data
    - Verify record counts match source files
    - Verify indexes are created
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.10_
  
  - [ ] 5.2 Update .gitignore and remove dataset files
    - Add dataset file paths to .gitignore
    - Remove Software Questions.csv from repository
    - Remove hr_interview_questions_dataset.json from repository
    - Remove leetcode_dataset - lc.csv from repository
    - _Requirements: 2.1, 2.2_
  
  - [ ] 5.3 Create migration documentation
    - Create backend/data/README.md
    - Document MongoDB setup instructions
    - Document migration script usage
    - Include example queries
    - _Requirements: 2.3, 2.4, 2.5_

- [ ] 6. Checkpoint - Verify MongoDB integration
  - Ensure all tests pass
  - Verify questions are accessible from MongoDB
  - Verify existing interview flow still works
  - Ask the user if questions arise

- [x] 7. Implement Deepgram STT service
  - [x] 7.1 Create DeepgramSTTService class in `backend/services/stt_service.py`
    - Implement transcribe_stream for real-time transcription
    - Implement transcribe_audio for complete audio buffers
    - Add error handling and retry logic
    - _Requirements: 5.2_
  
  - [ ]* 7.2 Write property test for speech-to-text transcription
    - **Property 6: Speech-to-Text Transcription**
    - **Validates: Requirements 5.2, 5.3**
  
  - [ ]* 7.3 Write unit tests for DeepgramSTTService
    - Test transcription with sample audio
    - Test error handling
    - Test retry logic
    - _Requirements: 5.2_

- [x] 8. Implement ElevenLabs TTS service
  - [x] 8.1 Create ElevenLabsTTSService class in `backend/services/tts_service.py`
    - Implement synthesize_speech for audio generation
    - Implement stream_speech for streaming audio
    - Add caching for repeated text
    - Add error handling and retry logic
    - _Requirements: 4.2, 4.5_
  
  - [ ]* 8.2 Write property test for text-to-speech consistency
    - **Property 5: Text-to-Speech Consistency**
    - **Validates: Requirements 4.2, 4.5, 6.8**
  
  - [ ]* 8.3 Write property test for audio response caching
    - **Property 23: Audio Response Caching**
    - **Validates: Requirements 9.6**
  
  - [ ]* 8.4 Write unit tests for ElevenLabsTTSService
    - Test audio synthesis
    - Test caching behavior
    - Test error handling
    - _Requirements: 4.2, 4.5_

- [ ] 9. Enhance DecisionEngine with semantic matching
  - [x] 9.1 Create EnhancedDecisionEngine class extending DecisionEngine
    - Add evaluate_answer method with semantic similarity
    - Integrate Gemini embedding service
    - Add should_interrupt method for follow-up logic
    - Implement follow-up question limiting (max 2 per question)
    - _Requirements: 6.2, 6.3, 6.4, 6.10_
  
  - [ ]* 9.2 Write property test for answer evaluation consistency
    - **Property 8: Answer Evaluation Consistency**
    - **Validates: Requirements 6.2, 6.3**
  
  - [ ]* 9.3 Write property test for semantic matching
    - **Property 9: Semantic Matching**
    - **Validates: Requirements 6.4**
  
  - [ ]* 9.4 Write property test for follow-up question limiting
    - **Property 10: Follow-up Question Limiting**
    - **Validates: Requirements 6.10**
  
  - [ ]* 9.5 Write property test for context preservation
    - **Property 11: Context Preservation**
    - **Validates: Requirements 6.9**

- [ ] 10. Extend SessionState for voice interviews
  - [ ] 10.1 Create VoiceSessionState dataclass extending SessionState
    - Add audio_recordings field
    - Add transcript_history field
    - Add voice_enabled flag
    - Add stt_failures and tts_failures counters
    - _Requirements: 7.1, 7.2_
  
  - [ ] 10.2 Update MongoDB schema for voice sessions
    - Add audio_recordings array field to sessions collection
    - Add transcript_history array field to sessions collection
    - Add voice_enabled boolean field
    - Update question_results to include semantic_similarity
    - _Requirements: 7.3, 7.4, 7.5_
  
  - [ ]* 10.3 Write property test for session data persistence
    - **Property 12: Session Data Persistence**
    - **Validates: Requirements 7.3, 7.4, 7.5**
  
  - [ ]* 10.4 Write property test for question-answer ordering
    - **Property 13: Question-Answer Ordering**
    - **Validates: Requirements 7.9**

- [ ] 11. Implement voice interview backend endpoints
  - [ ] 11.1 Add voice-specific endpoints to main.py
    - POST /session/{session_id}/voice/start - Initialize voice interview
    - POST /session/{session_id}/voice/transcript - Submit transcript chunk
    - GET /session/{session_id}/voice/audio/{question_id} - Get TTS audio
    - POST /session/{session_id}/voice/consent - Update audio recording consent
    - _Requirements: 4.1, 5.2, 5.7_
  
  - [ ] 11.2 Integrate STT and TTS services with InterviewerAgent
    - Update InterviewerAgent to use DeepgramSTTService
    - Update InterviewerAgent to use ElevenLabsTTSService
    - Add greeting generation logic
    - _Requirements: 4.1, 4.2, 5.2_
  
  - [ ]* 11.3 Write integration tests for voice endpoints
    - Test voice interview start flow
    - Test transcript submission
    - Test audio retrieval
    - _Requirements: 4.1, 5.2, 5.7_

- [ ] 12. Checkpoint - Verify backend voice services
  - Ensure all tests pass
  - Test STT and TTS services with sample data
  - Verify answer evaluation with semantic matching
  - Ask the user if questions arise

- [ ] 13. Implement frontend permission management
  - [ ] 13.1 Create PermissionHandler component
    - Request camera and microphone permissions
    - Handle permission grant/deny states
    - Display permission status indicators
    - Provide instructions for enabling permissions
    - _Requirements: 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 13.2 Write unit tests for PermissionHandler
    - Test permission request flow
    - Test grant state handling
    - Test deny state handling
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 14. Implement voice interface components
  - [ ] 14.1 Create VoiceInterviewPanel component
    - Integrate PermissionHandler
    - Add camera preview window
    - Add microphone level indicator
    - Add real-time transcript display
    - Add text input fallback
    - Add "Submit Answer" button with state management
    - _Requirements: 3.6, 3.7, 5.3, 5.4, 5.6_
  
  - [ ] 14.2 Create AudioPlayer component
    - Handle audio playback for AI responses
    - Display loading state during audio generation
    - Show visual feedback during playback
    - _Requirements: 4.3, 4.6_
  
  - [ ] 14.3 Create TranscriptDisplay component
    - Display real-time transcript as user speaks
    - Show confidence indicators
    - Highlight final vs interim transcripts
    - _Requirements: 5.3_
  
  - [ ]* 14.4 Write unit tests for voice interface components
    - Test VoiceInterviewPanel rendering
    - Test AudioPlayer playback
    - Test TranscriptDisplay updates
    - _Requirements: 3.6, 3.7, 5.3_

- [ ] 15. Implement WebSocket connection for real-time updates
  - [ ] 15.1 Add WebSocket endpoint for session events
    - Extend existing /session/{session_id}/events endpoint
    - Add voice-specific event types (transcript, audio_ready, evaluation_complete)
    - _Requirements: 5.3, 5.8_
  
  - [ ] 15.2 Create WebSocket client in frontend
    - Connect to session events endpoint
    - Handle transcript events
    - Handle audio_ready events
    - Handle evaluation_complete events
    - _Requirements: 5.3, 5.8_
  
  - [ ]* 15.3 Write integration tests for WebSocket communication
    - Test event broadcasting
    - Test client reconnection
    - Test event handling
    - _Requirements: 5.3, 5.8_

- [ ] 16. Implement error handling and fallback mechanisms
  - [ ] 16.1 Add service failure detection and fallback
    - Detect Deepgram failures and switch to text-only
    - Detect ElevenLabs failures and display text without audio
    - Detect Anthropic failures and use heuristic evaluation
    - Display user-friendly error messages
    - _Requirements: 4.8, 5.9, 8.3, 8.4_
  
  - [ ]* 16.2 Write property test for service failure graceful degradation
    - **Property 15: Service Failure Graceful Degradation**
    - **Validates: Requirements 8.3, 8.4, 8.7, 8.8**
  
  - [ ] 16.3 Implement retry logic with exponential backoff
    - Add retry decorator for Anthropic API calls
    - Configure backoff timing (1s, 2s, 4s)
    - Log retry attempts
    - _Requirements: 8.2_
  
  - [ ]* 16.4 Write property test for retry with exponential backoff
    - **Property 16: Retry with Exponential Backoff**
    - **Validates: Requirements 8.2**
  
  - [ ] 16.5 Implement offline session persistence
    - Save session state to localStorage on network loss
    - Sync to MongoDB when connection restored
    - _Requirements: 8.5, 8.6_
  
  - [ ]* 16.6 Write property test for offline session persistence
    - **Property 17: Offline Session Persistence**
    - **Validates: Requirements 8.5, 8.6**
  
  - [ ]* 16.7 Write property test for error logging completeness
    - **Property 18: Error Logging Completeness**
    - **Validates: Requirements 8.9**
  
  - [ ]* 16.8 Write property test for user-friendly error messages
    - **Property 19: User-Friendly Error Messages**
    - **Validates: Requirements 8.10**

- [ ] 17. Implement performance optimizations
  - [ ] 17.1 Add question preloading
    - Fetch next question while user is answering current question
    - Cache question in session state
    - _Requirements: 9.5_
  
  - [ ]* 17.2 Write property test for question preloading
    - **Property 22: Question Preloading**
    - **Validates: Requirements 9.5**
  
  - [ ] 17.3 Add performance monitoring
    - Log evaluation latency
    - Log query latency
    - Log STT latency
    - Log TTS latency
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [ ]* 17.4 Write property tests for latency requirements
    - **Property 20: Answer Evaluation Latency**
    - **Property 21: Question Retrieval Latency**
    - **Validates: Requirements 9.1, 9.2**

- [ ] 18. Implement security features
  - [ ] 18.1 Add input sanitization
    - Sanitize user input before sending to AI services
    - Remove SQL injection patterns
    - Remove XSS patterns
    - Remove prompt injection patterns
    - _Requirements: 10.6_
  
  - [ ]* 18.2 Write property test for input sanitization
    - **Property 24: Input Sanitization**
    - **Validates: Requirements 10.6**
  
  - [ ] 18.3 Add authentication enforcement
    - Validate JWT tokens on all voice endpoints
    - Return 401 for unauthenticated requests
    - _Requirements: 10.3_
  
  - [ ]* 18.4 Write property test for authentication enforcement
    - **Property 25: Authentication Enforcement**
    - **Validates: Requirements 10.3**
  
  - [ ] 18.5 Implement user-level rate limiting
    - Add rate limit of 10 sessions per user per day
    - Store rate limit state in Redis/Upstash
    - Return 429 for exceeded limits
    - _Requirements: 10.7_
  
  - [ ]* 18.6 Write property test for rate limiting enforcement
    - **Property 26: Rate Limiting Enforcement**
    - **Validates: Requirements 10.7**
  
  - [ ] 18.7 Add API call audit logging
    - Log all external API calls with context
    - Include timestamp, service, endpoint, user_id, session_id
    - _Requirements: 10.8_
  
  - [ ]* 18.8 Write property test for API call audit logging
    - **Property 27: API Call Audit Logging**
    - **Validates: Requirements 10.8**
  
  - [ ] 18.9 Implement audio recording consent management
    - Add consent flag to session state
    - Only store audio when consent is true
    - _Requirements: 7.8_
  
  - [ ]* 18.10 Write property test for audio recording consent
    - **Property 14: Audio Recording Consent**
    - **Validates: Requirements 7.8**
  
  - [ ] 18.11 Implement data retention policy
    - Add scheduled job to delete audio recordings older than 90 days
    - Log deletion operations
    - _Requirements: 10.9_
  
  - [ ]* 18.12 Write property test for data retention policy
    - **Property 28: Data Retention Policy**
    - **Validates: Requirements 10.9**

- [ ] 19. Integration and end-to-end testing
  - [ ]* 19.1 Write end-to-end test for complete voice interview flow
    - Test permissions → greeting → questions → answers → evaluation → completion
    - Test voice input and text fallback
    - Test error handling and recovery
    - _Requirements: All_
  
  - [ ]* 19.2 Write integration test for MongoDB + voice services
    - Test question fetching from MongoDB
    - Test STT + evaluation + TTS pipeline
    - Test session persistence
    - _Requirements: 1.8, 4.2, 5.2, 6.2, 7.3_

- [ ] 20. Final checkpoint - Complete system validation
  - Ensure all tests pass (unit, integration, property, e2e)
  - Verify performance meets latency requirements
  - Verify security features are working
  - Test complete interview flow manually
  - Ask the user if questions arise

- [ ] 21. Documentation and deployment preparation
  - [ ] 21.1 Update API documentation
    - Document new voice endpoints
    - Document WebSocket events
    - Document error responses
    - _Requirements: All_
  
  - [ ] 21.2 Update frontend documentation
    - Document voice interface components
    - Document permission handling
    - Document error states
    - _Requirements: All_
  
  - [ ] 21.3 Create deployment guide
    - Document MongoDB Atlas setup
    - Document environment variables
    - Document API key configuration
    - Document migration steps
    - _Requirements: 1.1, 2.3_

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- Follow vertical slice development: complete MongoDB migration before starting voice features
- Ensure backward compatibility: existing interview flow should continue working throughout implementation
