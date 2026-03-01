# Implementation Plan: Real-Time Voice Interaction

## Overview

This implementation plan breaks down the real-time voice interaction feature into atomic, sequential tasks. The feature adds intelligent bidirectional voice communication with silence detection, presence verification, real-time answer analysis, and context-aware interruptions to RoundZero's AI interview system.

The implementation follows vertical slice development: building complete flows from backend to frontend before adding new features. Each task is designed to be completed independently with clear validation criteria.

## Tasks

- [x] 1. Set up core data models and state machine
  - Create ConversationState enum with all states (IDLE, ASKING_QUESTION, LISTENING, etc.)
  - Create VoiceFlowState dataclass with all state fields
  - Create VoiceSessionState extended model for database storage
  - Create all event dataclasses (SilenceEvent, PresenceCheckResult, AnalysisResult, etc.)
  - _Requirements: 12.1, 12.2_

- [ ] 2. Implement SilenceDetector component
  - [x] 2.1 Create SilenceDetector class with audio level monitoring
    - Implement start_monitoring, stop_monitoring, reset methods
    - Implement process_audio_level method with threshold checking (-40dB)
    - Implement background monitoring loop with 100ms check interval
    - _Requirements: 2.2, 2.3, 2.4, 2.6_
  
  - [ ]* 2.2 Write property test for silence detection state management
    - **Property 1: Silence Detection State Management**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.6**
  
  - [x] 2.3 Implement silence event emission logic
    - Distinguish between brief pauses (<2s) and prolonged silence (10s)
    - Emit "answer_complete" event at 3s silence
    - Emit "prolonged" event at 10s silence
    - _Requirements: 2.5, 2.7, 9.1_
  
  - [ ]* 2.4 Write property test for silence event emission
    - **Property 2: Silence Event Emission**
    - **Validates: Requirements 2.5, 2.7**

- [ ] 3. Implement SpeechBuffer component
  - [x] 3.1 Create SpeechBuffer class with segment accumulation
    - Implement add_final_segment method
    - Implement get_accumulated_text and word_count methods
    - Implement should_trigger_analysis method (20-word threshold)
    - Implement clear method
    - _Requirements: 4.6, 5.1_
  
  - [ ]* 3.2 Write property test for speech buffer accumulation
    - **Property 7: Speech Buffer Accumulation**
    - **Validates: Requirements 4.6**
  
  - [ ]* 3.3 Write property test for analysis trigger threshold
    - **Property 8: Analysis Trigger Threshold**
    - **Validates: Requirements 5.1**

- [ ] 4. Implement ContextTracker component
  - [x] 4.1 Create ContextTracker class with Claude integration
    - Implement extract_topic method with Claude API call
    - Implement 500ms timeout with fallback to first 10 words
    - Implement question history management (last 5 questions)
    - _Requirements: 7.1, 7.2, 7.5, 7.9_
  
  - [ ]* 4.2 Write property test for topic extraction
    - **Property 16: Topic Extraction**
    - **Validates: Requirements 7.1, 7.2, 7.5**
  
  - [ ]* 4.3 Write property test for context history management
    - **Property 18: Context History Management**
    - **Validates: Requirements 7.9**

- [ ] 5. Implement VertexAIEmbeddingService
  - [x] 5.1 Create VertexAIEmbeddingService class
    - Initialize Vertex AI with project ID and location
    - Implement get_embedding method using textembedding-gecko@003
    - Implement async wrapper with thread pool executor
    - Implement get_embeddings_batch for concurrent requests
    - _Requirements: 5.4_
  
  - [ ]* 5.2 Write unit tests for embedding generation
    - Test single embedding generation
    - Test batch embedding generation
    - Test error handling

- [ ] 6. Implement AnswerAnalyzer component
  - [x] 6.1 Create AnswerAnalyzer class with dual analysis
    - Implement analyze_relevance method
    - Implement _evaluate_with_claude method for relevance checking
    - Implement _calculate_semantic_similarity with Vertex AI
    - Implement concurrent execution of both analyses
    - Implement 5-second rate limiting between analyses
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.8_
  
  - [ ]* 6.2 Write property test for dual analysis execution
    - **Property 9: Dual Analysis Execution**
    - **Validates: Requirements 5.2, 5.4, 5.5**
  
  - [x] 6.3 Implement off-topic detection logic
    - Check semantic similarity threshold (0.3)
    - Check Claude evaluation result
    - Generate interruption message when off-topic
    - _Requirements: 5.6, 5.7_
  
  - [ ]* 6.4 Write property test for off-topic detection
    - **Property 10: Off-Topic Detection**
    - **Validates: Requirements 5.6, 5.7**
  
  - [x] 6.5 Implement evaluate_final_answer method
    - Use Claude for completeness check
    - Return score and feedback
    - _Requirements: 9.3, 9.4_
  
  - [ ]* 6.6 Write property test for question context preservation
    - **Property 11: Question Context Preservation**
    - **Validates: Requirements 5.9**

- [ ] 7. Checkpoint - Ensure all core components compile and unit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement InterruptionEngine component
  - [x] 8.1 Create InterruptionEngine class with attempt limiting
    - Implement can_interrupt method (max 2 per question)
    - Implement generate_interruption method with context
    - Implement _generate_first_interruption (gentle redirect)
    - Implement _generate_second_interruption (more direct)
    - Implement reset_for_new_question method
    - _Requirements: 6.1, 6.2, 6.10, 17.1-17.4_
  
  - [ ]* 8.2 Write property test for interruption message generation
    - **Property 12: Interruption Message Generation**
    - **Validates: Requirements 6.1, 6.2**
  
  - [ ]* 8.3 Write property test for interruption limiting
    - **Property 15: Interruption Limiting**
    - **Validates: Requirements 6.10, 17.1-17.4**

- [ ] 9. Implement PresenceVerifier component
  - [x] 9.1 Create PresenceVerifier class with retry logic
    - Implement verify_presence method with max 3 attempts
    - Implement _listen_for_response with 10s timeout
    - Implement _is_affirmative_response using Claude
    - Integrate with TTS and STT services
    - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.8, 3.10_
  
  - [ ]* 9.2 Write property test for presence verification trigger
    - **Property 3: Presence Verification Trigger**
    - **Validates: Requirements 2.8, 3.1**
  
  - [ ]* 9.3 Write property test for affirmative response recognition
    - **Property 4: Affirmative Response Recognition**
    - **Validates: Requirements 3.6, 3.10**
  
  - [ ]* 9.4 Write property test for presence confirmation flow
    - **Property 5: Presence Confirmation Flow**
    - **Validates: Requirements 3.7**

- [ ] 10. Implement VoiceFlowController orchestrator
  - [x] 10.1 Create VoiceFlowController class with state machine
    - Initialize all component dependencies
    - Implement state transition method with event handlers
    - Implement start_interview method
    - _Requirements: State machine architecture_
  
  - [x] 10.2 Implement speech input handling
    - Implement handle_speech_input method
    - Reset silence detector on speech
    - Add to speech buffer
    - Trigger analysis at 20-word threshold
    - _Requirements: 4.1, 4.3, 4.5, 4.6, 5.1_
  
  - [ ]* 10.3 Write property test for speech transcription pipeline
    - **Property 6: Speech Transcription Pipeline**
    - **Validates: Requirements 4.1, 4.3, 4.5**
  
  - [x] 10.4 Implement silence handling
    - Implement handle_silence_detected method
    - Trigger presence check at 10s
    - Trigger answer evaluation at 3s
    - _Requirements: 2.8, 9.1, 9.2_
  
  - [x] 10.5 Implement interruption handling
    - Implement handle_off_topic_detected method
    - Pause STT during interruption
    - Play interruption audio
    - Clear speech buffer
    - Resume STT after interruption
    - _Requirements: 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_
  
  - [ ]* 10.6 Write property test for interruption delivery pipeline
    - **Property 13: Interruption Delivery Pipeline**
    - **Validates: Requirements 6.4, 6.5, 6.6, 6.7**
  
  - [ ]* 10.7 Write property test for interruption cleanup
    - **Property 14: Interruption Cleanup**
    - **Validates: Requirements 6.8, 6.9**
  
  - [x] 10.8 Implement answer evaluation flow
    - Implement _evaluate_answer method
    - Call AnswerAnalyzer for final evaluation
    - Reset state for next question
    - _Requirements: 9.3, 9.4, 9.5_
  
  - [ ]* 10.9 Write property test for state transition validity
    - **Property 35: State Transition Validity**
    - **Validates: State machine architecture requirements**

- [ ] 11. Checkpoint - Ensure backend orchestration works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement FastAPI endpoints
  - [x] 12.1 Create POST /session/{session_id}/voice/realtime/start endpoint
    - Implement rate limiting check (10 sessions per day)
    - Initialize VoiceFlowController
    - Register session in Redis
    - Return WebSocket URL and config
    - _Requirements: 1.1, 13.1, 13.2, 13.3_
  
  - [ ]* 12.2 Write property test for rate limiting enforcement
    - **Property 32: Rate Limiting Enforcement**
    - **Validates: Requirements 13.1, 13.2, 13.3**
  
  - [x] 12.2 Create WebSocket /session/{session_id}/voice/realtime/stream endpoint
    - Implement WebSocket connection handling
    - Handle transcript_segment messages
    - Handle audio_chunk messages for silence detection
    - Handle answer_complete messages
    - Send state_change, question, interruption, presence_check messages
    - _Requirements: 4.1, 4.2, 4.3, 8.4, 8.5_
  
  - [x] 12.3 Create POST /session/{session_id}/voice/realtime/interrupt endpoint
    - Implement manual interruption trigger
    - Return success status and new state
    - _Requirements: Testing support_
  
  - [x] 12.4 Create GET /session/{session_id}/voice/realtime/status endpoint
    - Return current conversation state
    - Return performance metrics
    - Return buffer and interruption counts
    - _Requirements: Monitoring support_

- [ ] 13. Implement session data persistence
  - [ ] 13.1 Create database schema for voice session state
    - Extend existing session table with voice fields
    - Create transcript_segments table
    - Create interruption_events table
    - Create presence_check_events table
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [ ] 13.2 Implement session event logging
    - Log question asked events
    - Log answer given events
    - Log interruption events
    - Log presence check events
    - _Requirements: 12.3, 12.4, 12.5, 12.6_
  
  - [ ]* 13.3 Write property test for session data persistence
    - **Property 29: Session Data Persistence**
    - **Validates: Requirements 12.3, 12.4, 12.5, 12.6**
  
  - [ ] 13.4 Implement audio recording storage
    - Store audio in MongoDB GridFS with encryption
    - Store metadata (session_id, question_index, duration)
    - Implement consent checking
    - _Requirements: 12.8, 14.4_
  
  - [ ]* 13.5 Write property test for audio recording storage
    - **Property 30: Audio Recording Storage**
    - **Validates: Requirements 12.8**
  
  - [ ] 13.6 Implement transcript history maintenance
    - Store complete transcript with speaker labels
    - Store timestamps and confidence scores
    - Implement retrieval for post-interview review
    - _Requirements: 12.9_
  
  - [ ]* 13.7 Write property test for transcript history maintenance
    - **Property 31: Transcript History Maintenance**
    - **Validates: Requirements 12.9**

- [ ] 14. Implement TTS caching and optimization
  - [x] 14.1 Create TTS cache service
    - Implement Redis-based audio caching
    - Cache common phrases (presence checks, greetings)
    - Implement LRU eviction (50MB limit)
    - Cache question audio for 24 hours
    - _Requirements: 8.9, 13.4, 13.5_
  
  - [ ]* 14.2 Write property test for TTS caching
    - **Property 21: TTS Caching**
    - **Validates: Requirements 8.9**
  
  - [x] 14.3 Implement TTS audio pipeline
    - Generate audio via ElevenLabs
    - Store in cache
    - Return audio URL or base64
    - Handle TTS failures with text fallback
    - _Requirements: 8.2, 8.3, 8.4, 10.2_
  
  - [ ]* 14.4 Write property test for TTS audio pipeline
    - **Property 19: TTS Audio Pipeline**
    - **Validates: Requirements 3.3, 3.4, 6.4, 8.2, 8.4**

- [ ] 15. Checkpoint - Ensure backend API and persistence work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement React frontend components
  - [ ] 16.1 Create RealTimeVoicePanel component
    - Implement WebSocket connection hook
    - Implement state management for conversation state
    - Implement audio recording with MediaRecorder
    - Handle incoming WebSocket messages (state_change, question, interruption, etc.)
    - Implement audio playback for questions and interruptions
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.7, 1.8_
  
  - [ ] 16.2 Create SilenceIndicator component
    - Display silence duration with progress bar
    - Change color based on threshold proximity (green → red)
    - Show "Speaking..." when duration is 0
    - _Requirements: 2.1, 2.5_
  
  - [ ] 16.3 Create TranscriptStream component
    - Display accumulated transcript text
    - Auto-scroll to bottom on new text
    - Show recording indicator with pulse animation
    - _Requirements: 4.3, 4.4, 4.7, 4.8_
  
  - [ ] 16.4 Create InterruptionOverlay component
    - Display interruption message with warning icon
    - Auto-close after 3 seconds
    - Animate entrance and exit
    - _Requirements: 6.1, 6.2_
  
  - [ ] 16.5 Create PresenceCheckDialog component
    - Display "Can you hear me?" message
    - Show listening animation
    - Display during presence verification
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 17. Implement frontend WebSocket integration
  - [ ] 17.1 Create useWebSocket custom hook
    - Implement WebSocket connection management
    - Implement reconnection logic with exponential backoff
    - Implement message sending and receiving
    - Handle connection errors
    - _Requirements: WebSocket communication_
  
  - [ ] 17.2 Implement audio recording and streaming
    - Request microphone permissions
    - Capture audio with MediaRecorder
    - Send audio chunks via WebSocket
    - Calculate audio levels for silence detection
    - _Requirements: 1.2, 1.3, 2.2_
  
  - [ ] 17.3 Implement audio playback system
    - Play question audio from URL
    - Play interruption audio with priority
    - Handle audio completion events
    - _Requirements: 8.4, 6.5_

- [ ] 18. Implement error handling and graceful degradation
  - [x] 18.1 Implement STT failure handling
    - Detect Deepgram connection failures
    - Switch to text-only input mode
    - Display user-friendly error message
    - Implement retry logic (3 attempts, 30s interval)
    - _Requirements: 10.1, 10.9_
  
  - [x] 18.2 Implement TTS failure handling
    - Detect ElevenLabs failures
    - Display questions as text without audio
    - Implement retry for next question
    - _Requirements: 10.2, 10.9_
  
  - [x] 18.3 Implement Claude API failure handling
    - Implement exponential backoff (1s, 2s, 4s)
    - Accept answers without analysis after 3 failures
    - Store answers for later evaluation
    - _Requirements: 10.3, 10.9_
  
  - [x] 18.4 Implement Vertex AI failure handling
    - Fall back to Claude-only evaluation
    - Continue without semantic similarity scoring
    - _Requirements: 10.5_
  
  - [x] 18.5 Implement network connection loss handling
    - Persist state in localStorage
    - Auto-sync when connection restored
    - Resume from last known state
    - _Requirements: 10.6, 10.7_

- [ ] 19. Implement performance monitoring
  - [x] 19.1 Create PerformanceMonitor class
    - Track response cycle latencies
    - Track individual service latencies (STT, TTS, Claude, Vertex AI)
    - Calculate average latencies
    - Calculate cache hit rates
    - _Requirements: 11.1-11.10_
  
  - [x] 19.2 Implement latency alerts
    - Alert when total response time exceeds 5s
    - Alert when individual services exceed thresholds
    - Log alerts to monitoring system
    - _Requirements: 11.10_
  
  - [x] 19.3 Add performance metrics to status endpoint
    - Include average latencies
    - Include cache hit rates
    - Include service failure counts
    - _Requirements: Monitoring support_

- [ ] 20. Implement security measures
  - [x] 20.1 Implement input sanitization
    - Sanitize transcript text before AI service calls
    - Validate audio data format and size
    - Limit transcript segment length (1000 chars)
    - Escape special characters for database queries
    - _Requirements: 14.7_
  
  - [x] 20.2 Implement WebSocket authentication
    - Validate JWT token on WebSocket connection
    - Verify session ownership
    - Close connection on auth failure
    - _Requirements: 14.5, 14.6_
  
  - [x] 20.3 Implement data encryption
    - Encrypt audio recordings at rest (AES-256)
    - Use database-level encryption for transcripts
    - Store encryption keys securely
    - _Requirements: 14.4_
  
  - [x] 20.4 Implement GDPR compliance features
    - Auto-delete audio after 90 days
    - Implement user data export
    - Implement right-to-be-forgotten (data deletion)
    - _Requirements: 14.8, 14.9_

- [ ] 21. Integration testing and end-to-end validation
  - [ ]* 21.1 Write integration test for mathematical question scenario
    - Test complete flow: question → off-topic answer → interruption → correct answer
    - Validate interruption message references question topic
    - Validate answer evaluation and feedback
    - _Requirements: 15.1-15.10_
  
  - [ ]* 21.2 Write integration test for presence verification scenario
    - Test complete flow: silence → presence check → confirmation → question repeat
    - Validate presence check audio playback
    - Validate affirmative response recognition
    - _Requirements: 16.1-16.10_
  
  - [ ]* 21.3 Write integration test for multi-interruption handling
    - Test first interruption (gentle redirect)
    - Test second interruption (more direct)
    - Test third off-topic response (no interruption)
    - Validate interruption counter reset on new question
    - _Requirements: 17.1-17.10_

- [ ] 22. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and integration tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Follow vertical slice development: complete backend components before frontend integration
- Use async/await throughout for non-blocking operations
- Implement proper error handling and graceful degradation at each layer
