# Implementation Plan: Enhanced Interview Experience

## Overview

This implementation plan transforms RoundZero's real-time voice interaction system into a complete, natural interview experience with intelligent onboarding, countdown timers, question progression, follow-up generation, and multi-modal analysis (tone, pitch, facial expressions).

The plan follows an 8-week vertical slice development approach (Schema → API → UI) with atomic tasks that can be completed independently. Each phase delivers working functionality before moving to the next.

## Tasks

- [x] 1. Phase 1: Database Schema & Storage Layer (Week 1)
  - [x] 1.1 Create MongoDB collections and indexes
    - Create interview_transcripts collection with schema
    - Create analysis_results collection with schema
    - Create follow_up_questions collection with schema
    - Add indexes on session_id, user_id, and timestamps
    - _Requirements: 24.2, 24.3, 24.4, 24.5, 24.6_
  
  - [x] 1.2 Extend Postgres interview_sessions table
    - Add onboarding tracking fields (onboarding_completed, onboarding_duration_seconds)
    - Add progress tracking fields (current_question_number, total_questions)
    - Add overall score fields (average_confidence, average_relevance, average_completeness, overall_performance)
    - Add status field with enum values
    - Create migration script
    - _Requirements: 24.1, 18.1_

  - [x] 1.3 Implement MongoTranscriptRepository class
    - Create repository class for interview_transcripts collection
    - Implement add_entry() method for appending transcript entries
    - Implement get_transcript() method for retrieval
    - Implement create_transcript() method for new sessions
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [ ]* 1.4 Write unit tests for MongoTranscriptRepository
    - Test transcript creation with session_id
    - Test entry appending with all required fields
    - Test transcript retrieval and ordering
    - Test error handling for invalid session_id
    - _Requirements: 14.1-14.10_
  
  - [x] 1.5 Implement MongoAnalysisRepository class
    - Create repository class for analysis_results collection
    - Implement store_analysis() method for saving results
    - Implement get_analysis() method for retrieval by session
    - Implement get_question_analysis() method for specific question
    - _Requirements: 15.1, 15.2, 15.8_
  
  - [ ]* 1.6 Write unit tests for MongoAnalysisRepository
    - Test analysis result storage with all fields
    - Test retrieval by session_id
    - Test retrieval by question_number
    - Test partial result storage (missing analyzers)
    - _Requirements: 15.1-15.10_
  
  - [x] 1.7 Implement MongoFollowUpRepository class
    - Create repository class for follow_up_questions collection
    - Implement store_followup() method for saving follow-ups
    - Implement get_followups() method for retrieval
    - Implement update_followup_answer() method
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ]* 1.8 Write unit tests for MongoFollowUpRepository
    - Test follow-up storage with reasoning
    - Test follow-up retrieval by session and question
    - Test answer update for follow-ups
    - Test effectiveness tracking
    - _Requirements: 9.1-9.10_
  
  - [x] 1.9 Create storage API endpoints
    - Create GET /api/interview/{session_id}/transcript endpoint
    - Create GET /api/interview/{session_id}/analysis endpoint
    - Create GET /api/interview/{session_id}/follow-ups endpoint
    - Add authentication and authorization checks
    - _Requirements: 25.6, 25.7_

- [ ] 2. Checkpoint - Verify storage layer works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [x] 3. Phase 2: Onboarding Flow (Week 2)
  - [x] 3.1 Implement OnboardingManager class structure
    - Create OnboardingManager class with dependencies (TTS, UserRepository, Claude)
    - Define start_onboarding() orchestration method
    - Define generate_greeting() method signature
    - Define generate_introduction() method signature
    - Define confirm_readiness() method signature
    - _Requirements: 1.1, 2.1, 3.1_
  
  - [x] 3.2 Implement time-of-day greeting logic
    - Create get_time_of_day() helper function
    - Implement logic for "Good morning" (5:00-11:59)
    - Implement logic for "Good afternoon" (12:00-16:59)
    - Implement logic for "Good evening" (17:00-20:59)
    - Implement fallback "Hello" for other times
    - _Requirements: 1.4_
  
  - [ ]* 3.3 Write property test for time-based greeting selection
    - **Property 1: Time-Based Greeting Selection**
    - **Validates: Requirements 1.4**
    - Generate random hours (0-23)
    - Verify correct greeting returned for each time range
    - Run 100 iterations with different times
  
  - [x] 3.4 Implement greeting message generation
    - Create format_greeting() method with first_name parameter
    - Handle None/empty first_name with "there" fallback
    - Combine name and time-of-day into greeting format
    - Set voice tone settings (stability: 0.6, similarity_boost: 0.8)
    - _Requirements: 1.2, 1.3, 1.9, 1.10_
  
  - [ ]* 3.5 Write property test for greeting format consistency
    - **Property 2: Greeting Format Consistency**
    - **Validates: Requirements 1.2, 1.3, 1.9**
    - Generate random first names including None/empty
    - Verify format "Hey [Name], nice to meet you. [TimeOfDay]."
    - Verify "there" used when name unavailable
  
  - [x] 3.6 Implement introduction message generation
    - Create generate_introduction() method with question_count parameter
    - Build introduction text explaining interview process
    - Include question count in message
    - Use same warm voice tone as greeting
    - _Requirements: 2.2, 2.6, 2.8_
  
  - [x] 3.7 Implement readiness confirmation with Claude
    - Create confirm_readiness() method
    - Generate readiness question audio
    - Listen for candidate response using VoiceFlowController
    - Use Claude API to interpret affirmative/negative responses
    - Handle wait requests with acknowledgment
    - Implement 60-second timeout with retry
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_
  
  - [ ]* 3.8 Write property test for readiness confirmation interpretation
    - **Property 4: Readiness Confirmation Interpretation**
    - **Validates: Requirements 3.5, 3.6, 3.7**
    - Generate various affirmative phrases
    - Generate various negative/uncertain phrases
    - Verify correct classification using Claude

  
  - [x] 3.9 Integrate onboarding with TTS service
    - Connect OnboardingManager to existing TTSService
    - Generate audio for greeting message
    - Generate audio for introduction message
    - Generate audio for readiness question
    - Verify audio generation completes within time limits
    - _Requirements: 1.5, 1.6, 1.8, 2.3, 2.4, 2.7, 3.2_
  
  - [ ]* 3.10 Write property test for TTS audio generation performance
    - **Property 3: TTS Audio Generation Performance**
    - **Validates: Requirements 1.8, 2.7, 5.7**
    - Generate random text inputs under 500 characters
    - Measure TTS generation time
    - Verify completion within specified limits (1.5s or 2s)
  
  - [x] 3.11 Create onboarding API endpoints
    - Create POST /api/interview/start endpoint
    - Create POST /api/interview/{session_id}/confirm-readiness endpoint
    - Add request/response validation
    - Store onboarding results in database
    - _Requirements: 25.1, 25.2_
  
  - [x] 3.12 Build frontend onboarding UI components
    - Create OnboardingScreen component
    - Create GreetingDisplay component with audio playback
    - Create ReadinessConfirmation component
    - Add microphone permission request
    - Style with high design aesthetics
    - _Requirements: 1.7, 2.5, 3.3_
  
  - [ ]* 3.13 Write integration tests for complete onboarding flow
    - Test greeting → introduction → readiness sequence
    - Test audio playback for each step
    - Test readiness confirmation with various responses
    - Test timeout and retry behavior
    - _Requirements: 22.1, 22.2, 22.3_

- [ ] 4. Checkpoint - Verify onboarding flow works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [x] 5. Phase 3: Question Progression & Countdown (Week 3)
  - [x] 5.1 Implement QuestionProgressionEngine class structure
    - Create QuestionProgressionEngine class with dependencies
    - Define load_questions() method for question retrieval
    - Define get_next_question() method for sequencing
    - Define generate_feedback() method for post-answer feedback
    - Define get_progress() method for tracking
    - _Requirements: 6.1, 6.5, 7.1_
  
  - [x] 5.2 Implement question loading and sequencing logic
    - Create load_questions() to retrieve question set from MongoDB
    - Implement get_next_question() with index tracking
    - Handle end-of-questions detection
    - Track current_index and questions list
    - _Requirements: 6.1, 6.5, 6.9_
  
  - [ ]* 5.3 Write property test for question progression sequence
    - **Property 6: Question Progression Sequence**
    - **Validates: Requirements 6.1, 6.5, 6.9**
    - Generate question sets of varying sizes (1-20 questions)
    - Verify each question visited exactly once in order
    - Verify no skipping or repeating
  
  - [x] 5.4 Implement progress tracking and calculation
    - Create get_progress() method returning current/total
    - Calculate progress percentage: (completed / total) * 100
    - Format display string: "Question N of Total"
    - Detect final question for special display
    - _Requirements: 7.2, 7.3, 7.7, 7.10_
  
  - [ ]* 5.5 Write property test for progress calculation accuracy
    - **Property 7: Progress Calculation Accuracy**
    - **Validates: Requirements 7.2, 7.7**
    - Generate random question numbers and totals
    - Verify percentage calculation: (Q / T) * 100
    - Verify display format correctness
  
  - [x] 5.6 Implement feedback generation with Claude
    - Create generate_feedback() method using Claude API
    - Generate 1-2 sentence encouraging feedback
    - Keep feedback concise and positive
    - Use same voice tone for audio conversion
    - _Requirements: 6.2, 6.3_
  
  - [x] 5.7 Create countdown timer component
    - Implement CountdownTimer React component
    - Display numbers 5, 4, 3, 2, 1 with 1-second intervals
    - Add smooth fade-in/fade-out animations
    - Use calming color scheme (soft blue/green)
    - Display "Let's begin!" after countdown
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_
  
  - [ ]* 5.8 Write property test for countdown timer precision
    - **Property 5: Countdown Timer Precision**
    - **Validates: Requirements 4.2, 4.4, 4.9**
    - Measure actual display time for each number
    - Verify each number displays for exactly 1 second
    - Verify total duration is exactly 5 seconds

  
  - [x] 5.9 Implement question audio presentation
    - Retrieve question text from Question_Set
    - Convert question to audio using ElevenLabs TTS
    - Use professional voice settings (stability: 0.5, similarity_boost: 0.75)
    - Display question text on screen during audio playback
    - Show "Listening for your answer..." indicator after audio
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [x] 5.10 Implement TTS audio caching
    - Create TTSCacheService class with Redis client
    - Implement get_or_generate() method
    - Generate cache key from text and voice settings
    - Set 24-hour TTL for cached audio
    - _Requirements: 5.8_
  
  - [ ]* 5.11 Write property test for TTS audio caching round-trip
    - **Property 22: TTS Audio Caching Round-Trip**
    - **Validates: Requirements 5.8**
    - Generate random text inputs
    - Cache audio and retrieve from cache
    - Verify cached audio bytes identical to original
  
  - [x] 5.12 Implement question transition display
    - Create transition message: "Moving to question [N+1]..."
    - Display transition for 2 seconds
    - Update progress bar after each question
    - Show current question number prominently
    - _Requirements: 6.6, 6.7, 7.4, 7.5, 7.6_
  
  - [x] 5.13 Create question progression API endpoints
    - Create GET /api/interview/{session_id}/current-question endpoint
    - Create POST /api/interview/{session_id}/answer endpoint
    - Return question number, total, text, and audio URL
    - Handle question progression after answer submission
    - _Requirements: 25.3, 25.4_
  
  - [x] 5.14 Build frontend question display UI
    - Create QuestionDisplay component
    - Create ProgressBar component
    - Create QuestionNumber component
    - Create TransitionScreen component
    - Add audio playback controls
    - Style with high design aesthetics
    - _Requirements: 5.5, 7.1, 7.2, 7.3_
  
  - [x] 5.15 Integrate with existing VoiceFlowController
    - Extend VoiceFlowController with question progression
    - Add COUNTDOWN state to state machine
    - Add hooks for pre-question and post-answer
    - Maintain backward compatibility
    - _Requirements: 23.1, 23.2, 23.3_
  
  - [ ]* 5.16 Write integration tests for question progression
    - Test complete flow: countdown → question → answer → feedback → next
    - Test progress tracking across multiple questions
    - Test final question detection
    - Test audio caching effectiveness
    - _Requirements: 6.1-6.10, 7.1-7.10_

- [ ] 6. Checkpoint - Verify question progression works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 7. Phase 4: Follow-Up Question Generation (Week 4)
  - [ ] 7.1 Implement FollowUpGenerator class structure
    - Create FollowUpGenerator class with Claude client
    - Define should_ask_followup() decision method
    - Define generate_followup() generation method
    - Define reset_for_new_question() counter reset
    - Track followup_count per main question
    - _Requirements: 8.1, 8.8_
  
  - [ ] 7.2 Implement follow-up decision logic
    - Create should_ask_followup() using Claude API
    - Analyze answer completeness
    - Identify interesting points for deep dive
    - Detect areas needing clarification
    - Enforce maximum 2 follow-ups per main question
    - _Requirements: 8.2, 8.3, 8.8_
  
  - [ ] 7.3 Implement contextual follow-up generation
    - Create generate_followup() using Claude API
    - Reference specific points from candidate's answer
    - Generate natural, conversational questions
    - Avoid scripted or generic follow-ups
    - Complete generation within 2 seconds
    - _Requirements: 8.4, 8.5, 8.6, 8.9_
  
  - [ ]* 7.4 Write property test for follow-up question limit
    - **Property 8: Follow-Up Question Limit**
    - **Validates: Requirements 8.8**
    - Generate multiple follow-up requests for same question
    - Verify maximum 2 follow-ups generated
    - Test counter reset for new main question
  
  - [ ]* 7.5 Write property test for follow-up contextual reference
    - **Property 9: Follow-Up Contextual Reference**
    - **Validates: Requirements 8.5, 8.6**
    - Generate various candidate answers
    - Generate follow-ups for each answer
    - Verify follow-up references specific points from answer
  
  - [ ] 7.6 Implement follow-up reasoning generation
    - Create reasoning generation using Claude API
    - Format: "Asked because [trigger]. Seeking [information]. Relates to [connection]."
    - Keep reasoning concise (2-3 sentences)
    - Generate reasoning alongside follow-up question
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_
  
  - [ ] 7.7 Store follow-ups in MongoDB
    - Use MongoFollowUpRepository to store follow-ups
    - Include session_id, main_question_id, follow_up_text, reasoning
    - Store timestamp and question number
    - Link follow-up answers to follow-up questions
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  
  - [ ] 7.8 Implement follow-up evaluation storage
    - Store evaluation results for follow-up answers
    - Include relevance_score, completeness_score, feedback
    - Track follow-up effectiveness
    - Link evaluation to follow-up record
    - _Requirements: 9.8, 9.9, 9.10_
  
  - [ ]* 7.9 Write property test for follow-up reasoning storage
    - **Property 15: Follow-Up Reasoning Storage**
    - **Validates: Requirements 16.2, 16.3, 16.4**
    - Generate follow-ups with reasoning
    - Store in database
    - Verify reasoning field non-empty and properly formatted

  
  - [ ] 7.10 Create follow-up API endpoint
    - Create GET /api/interview/{session_id}/follow-up endpoint
    - Return has_followup flag, followup_text, audio_url, reasoning
    - Handle case when no follow-up needed
    - _Requirements: 25.5_
  
  - [ ] 7.11 Build frontend follow-up display UI
    - Create FollowUpQuestion component
    - Display follow-up with visual distinction from main questions
    - Show reasoning in expandable section (optional)
    - Play follow-up audio automatically
    - _Requirements: 8.7_
  
  - [ ] 7.12 Integrate follow-ups with VoiceFlowController
    - Add FOLLOW_UP state to state machine
    - Add post-answer hook for follow-up generation
    - Handle follow-up answers same as main answers
    - Track is_followup flag in state
    - _Requirements: 23.4, 23.8_
  
  - [ ]* 7.13 Write integration tests for follow-up flow
    - Test follow-up generation after incomplete answer
    - Test follow-up generation after interesting point
    - Test maximum 2 follow-ups enforcement
    - Test follow-up reasoning storage
    - Test no follow-up when answer complete
    - _Requirements: 8.1-8.10, 9.1-9.10_

- [ ] 8. Checkpoint - Verify follow-up generation works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Phase 5: Multi-Modal Analysis - Tone & Pitch (Week 5)
  - [ ] 9.1 Implement ToneAnalyzer class structure
    - Create ToneAnalyzer class with Deepgram client
    - Define analyze() method signature
    - Define tone categories: confident, nervous, uncertain, enthusiastic, monotone
    - Set up audio stream processing
    - _Requirements: 10.1, 10.2_
  
  - [ ] 9.2 Implement tone detection with Deepgram
    - Use Deepgram audio intelligence API
    - Detect emotional tone categories
    - Calculate confidence score (0.0-1.0)
    - Detect hesitation patterns (pauses, filler words)
    - Measure speech pace (words per minute)
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.7_
  
  - [ ] 9.3 Implement PitchAnalyzer class structure
    - Create PitchAnalyzer class
    - Define analyze() method signature
    - Set sample_rate to 16000
    - Define pitch pattern categories: rising, falling, stable
    - _Requirements: 11.1, 11.4_
  
  - [ ] 9.4 Implement pitch extraction with librosa
    - Use librosa for pitch contour extraction
    - Calculate average pitch in Hz
    - Calculate pitch range (max - min)
    - Classify pitch pattern (rising/falling/stable)
    - Detect stress indicators (abnormal spikes)
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.7_

  
  - [ ] 9.5 Implement concurrent tone and pitch analysis
    - Create MultiModalAnalyzer class structure
    - Implement analyze_answer() with asyncio.gather()
    - Run tone and pitch analysis concurrently
    - Set return_exceptions=True for graceful degradation
    - _Requirements: 13.2_
  
  - [ ]* 9.6 Write property test for multi-modal analysis concurrency
    - **Property 10: Multi-Modal Analysis Concurrency**
    - **Validates: Requirements 13.2, 13.8**
    - Measure concurrent execution time
    - Verify time ≈ max(tone_time, pitch_time), not sum
    - Test with various audio lengths
  
  - [ ]* 9.7 Write property test for analysis result validity
    - **Property 12: Analysis Result Validity**
    - **Validates: Requirements 10.9, 11.9**
    - Generate various audio inputs
    - Run tone and pitch analysis
    - Verify all required fields present
    - Verify scores in range 0.0-1.0
    - Verify categories from predefined sets
  
  - [ ] 9.8 Store tone and pitch analysis in MongoDB
    - Use MongoAnalysisRepository to store results
    - Store tone_data with all fields
    - Store pitch_data with all fields
    - Include timestamp and session_id
    - _Requirements: 10.9, 11.9, 15.3, 15.4_
  
  - [ ] 9.9 Implement graceful degradation for analysis failures
    - Handle tone analyzer failures without blocking
    - Handle pitch analyzer failures without blocking
    - Log errors with context
    - Continue interview with partial results
    - _Requirements: 20.1, 20.2_
  
  - [ ]* 9.10 Write property test for graceful degradation continuation
    - **Property 18: Graceful Degradation Continuation**
    - **Validates: Requirements 20.1, 20.2**
    - Simulate analyzer failures
    - Verify interview continues
    - Verify partial results stored
    - Verify no exceptions raised
  
  - [ ] 9.11 Create analysis results API endpoint
    - Extend GET /api/interview/{session_id}/analysis endpoint
    - Return tone and pitch data per question
    - Include timestamps and scores
    - _Requirements: 25.7_
  
  - [ ] 9.12 Build frontend analysis display UI
    - Create ToneAnalysisDisplay component
    - Create PitchAnalysisDisplay component
    - Show confidence scores with visual indicators
    - Display tone categories and pitch patterns
    - Style with high design aesthetics
    - _Requirements: 10.9, 11.9_
  
  - [ ]* 9.13 Write integration tests for tone and pitch analysis
    - Test complete analysis flow with real audio
    - Test concurrent execution performance
    - Test graceful degradation with failures
    - Test storage and retrieval
    - _Requirements: 10.1-10.10, 11.1-11.10_

- [ ] 10. Checkpoint - Verify tone and pitch analysis works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 11. Phase 6: Multi-Modal Analysis - Facial (Week 6)
  - [ ] 11.1 Implement ConsentManager class
    - Create ConsentManager class
    - Define request_video_consent() method
    - Create consent dialog text explaining video analysis
    - Store consent decision in database
    - _Requirements: 21.1, 21.2_
  
  - [ ] 11.2 Create user_consents table in Postgres
    - Add user_consents table with user_id, consent_type, granted, timestamp
    - Create migration script
    - Add index on user_id
    - _Requirements: 21.1_
  
  - [ ] 11.3 Implement FacialExpressionAnalyzer class structure
    - Create FacialExpressionAnalyzer class
    - Initialize MediaPipe FaceMesh
    - Define analyze() method signature
    - Define expression categories: smile, frown, neutral, surprised, confused
    - Track consent_given flag
    - _Requirements: 12.1, 12.2_
  
  - [ ] 11.4 Implement facial expression detection
    - Use MediaPipe for face landmark detection
    - Classify expressions from landmarks
    - Measure eye contact (camera gaze detection)
    - Detect head movements (nodding, shaking, tilting)
    - Calculate engagement score (0.0-1.0)
    - _Requirements: 12.2, 12.3, 12.4, 12.5_
  
  - [ ] 11.5 Implement consent enforcement
    - Check consent_given before processing video
    - Return disabled result if consent denied
    - Skip video processing entirely without consent
    - _Requirements: 21.2_
  
  - [ ]* 11.6 Write property test for video consent enforcement
    - **Property 19: Video Consent Enforcement**
    - **Validates: Requirements 21.2**
    - Test with consent denied
    - Verify facial analyzer returns disabled result
    - Verify no video data processed or stored
  
  - [ ] 11.7 Integrate facial analysis with MultiModalAnalyzer
    - Add facial_analyzer to MultiModalAnalyzer
    - Include facial analysis in asyncio.gather()
    - Run all three analyses concurrently
    - Handle facial analyzer failures gracefully
    - _Requirements: 13.1, 13.2_
  
  - [ ] 11.8 Implement overall confidence weighting
    - Calculate overall_confidence with weights: tone (40%), pitch (30%), facial (30%)
    - Handle missing analysis results (partial data)
    - Adjust weights when analyzers disabled/failed
    - _Requirements: 13.4_
  
  - [ ]* 11.9 Write property test for overall confidence weighting
    - **Property 11: Overall Confidence Weighting**
    - **Validates: Requirements 13.4**
    - Generate random tone, pitch, facial scores (0.0-1.0)
    - Calculate expected: (T * 0.40) + (P * 0.30) + (F * 0.30)
    - Verify actual matches expected

  
  - [ ] 11.10 Implement consistency detection
    - Detect mismatches between modalities
    - Flag confident words but nervous tone
    - Flag enthusiastic tone but low facial engagement
    - Flag stable pitch but high hesitation
    - Calculate consistency_score
    - _Requirements: 13.5_
  
  - [ ] 11.11 Generate multi-modal summary assessment
    - Create summary per question with overall_confidence
    - Include consistency_score
    - List notable_patterns detected
    - Store summary in MongoDB
    - _Requirements: 13.6, 13.7, 13.9_
  
  - [ ] 11.12 Store facial analysis in MongoDB
    - Use MongoAnalysisRepository to store facial_data
    - Store multi_modal_summary with combined results
    - Include all required fields
    - _Requirements: 12.9, 15.5, 15.7_
  
  - [ ]* 11.13 Write property test for database storage completeness
    - **Property 14: Database Storage Completeness**
    - **Validates: Requirements 15.2, 15.3, 15.4, 15.5, 15.6**
    - Generate analysis results with all fields
    - Store in MongoDB
    - Retrieve and verify all fields present
  
  - [ ] 11.14 Build frontend consent dialog UI
    - Create VideoConsentDialog component
    - Display consent text clearly
    - Add Accept/Decline buttons
    - Show privacy notice
    - _Requirements: 21.1, 21.9_
  
  - [ ] 11.15 Build frontend facial analysis display UI
    - Create FacialAnalysisDisplay component
    - Show dominant expression with icon
    - Display eye contact percentage
    - Show engagement score
    - Display multi-modal summary
    - Style with high design aesthetics
    - _Requirements: 12.9, 13.7_
  
  - [ ]* 11.16 Write integration tests for complete multi-modal analysis
    - Test all three analyzers running concurrently
    - Test overall confidence calculation
    - Test consistency detection
    - Test consent enforcement
    - Test graceful degradation with partial failures
    - _Requirements: 12.1-12.10, 13.1-13.10_

- [ ] 12. Checkpoint - Verify complete multi-modal analysis works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 13. Phase 7: Integration & Performance Optimization (Week 7)
  - [ ] 13.1 Create EnhancedVoiceFlowController class
    - Extend existing VoiceFlowController
    - Add onboarding_manager, question_progression, followup_generator, multimodal_analyzer
    - Override start_interview() to add onboarding
    - Override _evaluate_answer() to add multi-modal analysis
    - Maintain backward compatibility
    - _Requirements: 23.1, 23.9_
  
  - [ ] 13.2 Add new states to state machine
    - Add ONBOARDING state
    - Add COUNTDOWN state
    - Add FOLLOW_UP state
    - Add COMPLETING state
    - Update state transition logic
    - _Requirements: 23.2_
  
  - [ ]* 13.3 Write property test for state machine transition validity
    - **Property 20: State Machine Transition Validity**
    - **Validates: Requirements 23.2, 23.3**
    - Generate random state transition sequences
    - Verify only valid transitions occur
    - Test ONBOARDING → COUNTDOWN → ASKING_QUESTION flow
  
  - [ ] 13.4 Implement hooks system for extensibility
    - Create HookManager class
    - Add pre_question_hooks list
    - Add post_answer_hooks list
    - Register multi-modal analysis as post-answer hook
    - Register follow-up generation as post-answer hook
    - _Requirements: 23.4, 23.5_
  
  - [ ] 13.5 Implement interview completion flow
    - Detect when all questions answered
    - Generate completion message with candidate name
    - Calculate overall interview scores
    - Display "Processing Results..." message
    - Show completion confirmation with dashboard link
    - Mark session as completed in database
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.10_
  
  - [ ] 13.6 Implement session state persistence
    - Save session state after each question
    - Store current_question_number, completed_questions, status
    - Implement local storage backup for connection drops
    - Implement state sync on reconnection
    - Offer resume or restart on page refresh
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.10_
  
  - [ ]* 13.7 Write property test for session state persistence round-trip
    - **Property 16: Session State Persistence Round-Trip**
    - **Validates: Requirements 18.1, 18.2, 18.5**
    - Generate random session states
    - Save to database and retrieve
    - Verify state equivalence
  
  - [ ] 13.8 Optimize database connection pooling
    - Configure MongoDB connection pool (maxPoolSize: 50, minPoolSize: 10)
    - Configure Postgres connection pool (min: 10, max: 50)
    - Set appropriate timeouts
    - _Requirements: 19.1-19.10_

  
  - [ ] 13.9 Implement batch database writes
    - Create BatchWriter class
    - Batch transcript entries (batch_size: 10)
    - Batch analysis results
    - Implement flush() for bulk operations
    - Auto-flush on batch size or timeout
    - _Requirements: 19.1-19.10_
  
  - [ ] 13.10 Implement comprehensive error handling
    - Create ErrorHandler class
    - Handle analysis failures gracefully
    - Handle TTS failures with text-only fallback
    - Handle database failures with local caching and retry
    - Display user-friendly error messages
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.9, 20.10_
  
  - [ ] 13.11 Add monitoring and alerting
    - Implement metrics collection (onboarding_duration, analysis_duration, etc.)
    - Add error rate monitoring
    - Configure alerts for critical failures
    - Log all errors with context
    - _Requirements: 20.9, 20.10_
  
  - [ ] 13.12 Implement performance optimizations
    - Verify TTS caching reduces API calls
    - Verify concurrent analysis reduces latency
    - Optimize database queries with proper indexes
    - Implement Redis caching for frequently accessed data
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10_
  
  - [ ]* 13.13 Write property test for performance latency bounds
    - **Property 17: Performance Latency Bounds**
    - **Validates: Requirements 19.10**
    - Measure time from answer completion to next question
    - Include analysis, follow-up generation, progression
    - Verify total time < 5 seconds
  
  - [ ] 13.14 Create interview completion API endpoint
    - Create POST /api/interview/{session_id}/complete endpoint
    - Calculate and return overall scores
    - Return dashboard URL
    - _Requirements: 25.8_
  
  - [ ] 13.15 Build frontend completion screen UI
    - Create InterviewCompleteScreen component
    - Display "Processing Results..." animation
    - Show completion message
    - Display overall scores summary
    - Add "View Results" button to dashboard
    - Style with high design aesthetics
    - _Requirements: 17.4, 17.5, 17.8, 17.9_
  
  - [ ]* 13.16 Write integration tests for complete interview flow
    - Test full flow: onboarding → countdown → questions → follow-ups → completion
    - Test session state persistence and resume
    - Test error handling and graceful degradation
    - Test performance meets latency requirements
    - _Requirements: 22.1-22.10_

- [ ] 14. Checkpoint - Verify complete integration works end-to-end
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 15. Phase 8: Security, Privacy & Testing (Week 8)
  - [ ] 15.1 Implement data encryption at rest
    - Create DataEncryption class with Fernet
    - Implement encrypt_audio() method
    - Implement decrypt_audio() method
    - Implement encrypt_transcript() method
    - Use encryption key from environment variable
    - _Requirements: 21.3_
  
  - [ ]* 15.2 Write property test for data encryption round-trip
    - **Property 24: Data Encryption Round-Trip**
    - **Validates: Requirements 21.3**
    - Generate random audio and transcript data
    - Encrypt and decrypt
    - Verify decrypted data identical to original
  
  - [ ] 15.3 Implement data retention policies
    - Create DataRetentionManager class
    - Implement apply_retention_policy() for 90-day deletion
    - Delete old raw audio/video from GridFS
    - Keep analysis results indefinitely
    - Schedule automated retention job
    - _Requirements: 21.5, 21.6_
  
  - [ ] 15.4 Implement GDPR compliance features
    - Implement delete_user_data() method
    - Delete from MongoDB (transcripts, analysis, follow-ups)
    - Delete from Postgres (sessions, consents)
    - Create API endpoint for data deletion requests
    - Add audit logging for deletions
    - _Requirements: 21.7, 21.8_
  
  - [ ] 15.5 Implement API security measures
    - Add rate limiting (5 requests per minute for start endpoint)
    - Add authentication checks on all endpoints
    - Add authorization checks (user owns session)
    - Implement input validation with Pydantic models
    - Add HTTPS enforcement
    - _Requirements: 21.4_
  
  - [ ] 15.6 Add privacy notice display
    - Create PrivacyNotice component
    - Display before interview starts
    - Explain data collection and usage
    - Link to full privacy policy
    - Require acknowledgment before proceeding
    - _Requirements: 21.9, 21.10_
  
  - [ ] 15.7 Create WebSocket endpoint for real-time updates
    - Implement WebSocket connection handler
    - Handle audio_chunk and video_chunk events
    - Send state_change, countdown_tick, question events
    - Send feedback, analysis_progress, interview_complete events
    - Add connection authentication
    - _Requirements: 25.9_
  
  - [ ]* 15.8 Write property test for API endpoint response format
    - **Property 21: API Endpoint Response Format**
    - **Validates: Requirements 25.1-25.9**
    - Test all API endpoints with valid auth
    - Verify response schemas match documentation
    - Verify all required fields present and correctly typed
  
  - [ ] 15.9 Create OpenAPI/Swagger documentation
    - Document all REST endpoints with schemas
    - Document WebSocket events
    - Include request/response examples
    - Add authentication requirements
    - Generate interactive API docs
    - _Requirements: 25.10_

  
  - [ ]* 15.10 Write property test for transcript entry ordering
    - **Property 13: Transcript Entry Ordering**
    - **Validates: Requirements 14.7**
    - Add entries in random order with timestamps
    - Retrieve transcript
    - Verify entries in exact chronological order
  
  - [ ]* 15.11 Write property test for concurrent analysis exception handling
    - **Property 23: Concurrent Analysis Exception Handling**
    - **Validates: Requirements 13.2, 20.1-20.3**
    - Simulate one or more analyzer failures
    - Use asyncio.gather(return_exceptions=True)
    - Verify successful tasks return results
    - Verify failed tasks return Exception objects
    - Verify no exception raised to caller
  
  - [ ]* 15.12 Write property test for batch write atomicity
    - **Property 25: Batch Write Atomicity**
    - **Validates: Requirements 14.1-14.10, 15.1-15.10**
    - Create batch of database writes
    - Simulate partial failure
    - Verify either all writes succeed or none applied
  
  - [ ] 15.13 Write comprehensive integration tests
    - Test complete interview flow from start to finish
    - Test onboarding → countdown → questions → follow-ups → analysis → completion
    - Test session persistence and resume functionality
    - Test error recovery and graceful degradation
    - Test multi-user concurrent interviews
    - _Requirements: 22.1-22.10_
  
  - [ ] 15.14 Perform security audit
    - Review authentication and authorization implementation
    - Test rate limiting effectiveness
    - Verify input validation prevents injection attacks
    - Test encryption implementation
    - Review API security headers
    - _Requirements: 21.1-21.10_
  
  - [ ] 15.15 Perform performance testing
    - Load test with 50 concurrent interviews
    - Measure onboarding duration (<15s target)
    - Measure question progression latency (<5s target)
    - Measure analysis completion time (<2s target)
    - Verify TTS cache hit rate (>60% target)
    - _Requirements: 19.1-19.10_
  
  - [ ] 15.16 Set up monitoring and alerting
    - Configure metrics collection (Prometheus/Grafana)
    - Set up error tracking (Sentry)
    - Configure alerts for high failure rates
    - Configure alerts for latency violations
    - Set up log aggregation
    - _Requirements: 20.9, 20.10_
  
  - [ ] 15.17 Create deployment documentation
    - Document environment variables required
    - Document database setup and migrations
    - Document scaling considerations
    - Document monitoring setup
    - Document backup and recovery procedures
    - _Requirements: All_

- [ ] 16. Final Checkpoint - Production readiness verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at phase boundaries
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Follow vertical slice development: Schema → API → UI for each phase
- Maintain backward compatibility with existing VoiceFlowController
- All AI logic resides in `backend/agent/` per working agreements
- Use `uv` for backend dependencies, `npm` for frontend
- Never hardcode secrets; use `.env` files
- Maintain high design aesthetics in frontend components

## Success Criteria

The enhanced interview experience is complete when:
- All 8 phases are implemented and tested
- Onboarding flow works with personalized greeting and readiness confirmation
- Countdown timer displays before first question
- Questions progress automatically with feedback and transitions
- Follow-up questions are generated contextually with reasoning
- Multi-modal analysis (tone, pitch, facial) runs concurrently
- Complete transcripts and analysis results are stored
- Session state persists and can be resumed
- Performance meets latency requirements (<5s total)
- Security measures are in place (encryption, consent, GDPR)
- All property tests pass (universal correctness)
- All integration tests pass (end-to-end flows)
- System is production-ready with monitoring and documentation
