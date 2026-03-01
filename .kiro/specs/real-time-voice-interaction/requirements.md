# Requirements Document

## Introduction

The Real-Time Voice Interaction feature enhances RoundZero's AI interview system with intelligent, bidirectional voice communication capabilities. This feature enables natural conversation flow between the AI interviewer and candidate through real-time speech recognition, intelligent silence detection, presence verification, and context-aware answer analysis with immediate interruption capabilities.

This enhancement builds upon the existing voice-ai-interview-system by adding sophisticated real-time interaction logic that mimics human interviewer behavior: detecting when candidates are silent, verifying their presence, analyzing answer relevance in real-time, and intelligently interrupting when responses drift off-topic.

## Glossary

- **Real_Time_Voice_System**: The complete bidirectional voice interaction system including STT, TTS, silence detection, and intelligent interruption
- **Silence_Detector**: Component that monitors audio input and detects periods of no speech activity
- **Presence_Verifier**: Logic that confirms candidate is present and listening when prolonged silence is detected
- **Answer_Analyzer**: Real-time component that evaluates answer relevance as the candidate speaks
- **Interruption_Engine**: AI-powered logic that determines when and how to interrupt off-topic responses
- **Voice_Flow_Controller**: Orchestrator managing the conversation flow between AI and candidate
- **Speech_Buffer**: Temporary storage for accumulating speech segments during real-time transcription
- **Relevance_Scorer**: Component that calculates semantic similarity between question and answer in real-time
- **Context_Tracker**: Maintains conversation context including question history and answer patterns
- **Deepgram_STT**: Speech-to-text service using Deepgram API for real-time transcription
- **ElevenLabs_TTS**: Text-to-speech service using ElevenLabs API for AI voice output
- **Claude_API**: Anthropic Claude-3.5-Sonnet for intelligent answer analysis and decision-making
- **Vertex_AI**: Google Vertex AI for embeddings and semantic similarity calculations
- **Interview_Session**: A single interview instance with real-time voice interaction
- **Candidate**: The user being interviewed
- **AI_Interviewer**: The AI agent conducting the interview

## Requirements

### Requirement 1: Simple Interview Start Flow

**User Story:** As a candidate, I want to start an interview with minimal steps so that I can quickly begin practicing without friction.

#### Acceptance Criteria

1. WHEN the Candidate clicks "Start Interview", THE Real_Time_Voice_System SHALL navigate to the interviewer panel
2. WHEN the interviewer panel loads, THE Real_Time_Voice_System SHALL request camera and microphone permissions from the browser
3. IF the Candidate grants both permissions, THEN THE Real_Time_Voice_System SHALL initialize the Deepgram_STT connection
4. WHEN the Deepgram_STT connection is established, THE Real_Time_Voice_System SHALL initialize the ElevenLabs_TTS service
5. WHEN both services are initialized, THE Real_Time_Voice_System SHALL create a new Interview_Session in the database
6. WHEN the Interview_Session is created, THE AI_Interviewer SHALL begin the interview immediately
7. THE Real_Time_Voice_System SHALL display visual indicators showing camera and microphone are active
8. THE Real_Time_Voice_System SHALL display a "Ready" status when all systems are initialized
9. IF either permission is denied, THEN THE Real_Time_Voice_System SHALL display an error message with instructions to enable permissions
10. THE entire initialization process SHALL complete within 3 seconds of permission grant

### Requirement 2: 10-Second Silence Detection

**User Story:** As an AI interviewer, I want to detect when the candidate hasn't spoken for 10 seconds so that I can handle the silence appropriately.

#### Acceptance Criteria

1. WHEN the AI_Interviewer asks a question via voice, THE Silence_Detector SHALL start monitoring audio input
2. THE Silence_Detector SHALL measure the duration of continuous silence in the audio stream
3. WHEN the Candidate starts speaking, THE Silence_Detector SHALL reset the silence timer to zero
4. WHEN the Candidate stops speaking, THE Silence_Detector SHALL restart the silence timer
5. IF the silence duration reaches 10 seconds, THEN THE Silence_Detector SHALL emit a "silence_detected" event
6. THE Silence_Detector SHALL distinguish between silence and background noise using a volume threshold of -40dB
7. THE Silence_Detector SHALL ignore brief pauses of less than 2 seconds as normal speech patterns
8. WHEN a "silence_detected" event is emitted, THE Voice_Flow_Controller SHALL trigger the presence verification flow
9. THE Silence_Detector SHALL continue monitoring throughout the entire interview session
10. THE Silence_Detector SHALL log all silence events with timestamps for session analysis

### Requirement 3: Presence Verification Flow

**User Story:** As an AI interviewer, I want to verify the candidate is present and listening when they don't respond so that I can confirm they're engaged before continuing.

#### Acceptance Criteria

1. WHEN a "silence_detected" event occurs, THE Presence_Verifier SHALL generate a presence check message
2. THE presence check message SHALL be: "Hey, can you hear me?"
3. WHEN the presence check message is generated, THE ElevenLabs_TTS SHALL convert it to audio
4. WHEN the audio is ready, THE Real_Time_Voice_System SHALL play the presence check through speakers
5. WHEN the presence check audio completes, THE Silence_Detector SHALL monitor for a response with a 10-second timeout
6. IF the Candidate responds with affirmative phrases (e.g., "Yes", "Yes I can", "I can hear you"), THEN THE Presence_Verifier SHALL mark presence as confirmed
7. WHEN presence is confirmed, THE AI_Interviewer SHALL proceed with the actual interview question
8. IF the Candidate does not respond within 10 seconds, THEN THE Presence_Verifier SHALL repeat the presence check up to 2 additional times
9. IF presence is not confirmed after 3 attempts, THEN THE Real_Time_Voice_System SHALL pause the interview and display a "Connection Lost" message
10. THE Presence_Verifier SHALL use Claude_API to interpret various affirmative responses beyond exact phrase matching

### Requirement 4: Real-Time Answer Transcription

**User Story:** As a candidate, I want to see my spoken words transcribed in real-time so that I can verify the system is capturing my responses accurately.

#### Acceptance Criteria

1. WHEN the Candidate starts speaking, THE Deepgram_STT SHALL begin streaming transcription
2. THE Deepgram_STT SHALL use the "nova-2" model with interim results enabled
3. WHEN interim transcription results are received, THE Real_Time_Voice_System SHALL display them in the transcript area
4. THE transcript display SHALL update every 200 milliseconds with new interim results
5. WHEN final transcription results are received, THE Real_Time_Voice_System SHALL replace interim text with final text
6. THE Speech_Buffer SHALL accumulate all final transcription segments for answer analysis
7. THE transcript display SHALL show a visual indicator (e.g., pulsing cursor) when the Candidate is speaking
8. THE transcript display SHALL auto-scroll to keep the latest text visible
9. IF the Deepgram_STT connection fails, THEN THE Real_Time_Voice_System SHALL display an error and fall back to text input
10. THE Real_Time_Voice_System SHALL display transcription confidence scores when they fall below 0.7

### Requirement 5: Intelligent Answer Relevance Analysis

**User Story:** As an AI interviewer, I want to analyze answer relevance in real-time so that I can detect when the candidate is going off-topic.

#### Acceptance Criteria

1. WHEN the Speech_Buffer accumulates at least 20 words, THE Answer_Analyzer SHALL begin relevance analysis
2. THE Answer_Analyzer SHALL send the current question and accumulated answer to Claude_API for analysis
3. THE Claude_API SHALL evaluate whether the answer is addressing the question asked
4. THE Relevance_Scorer SHALL calculate semantic similarity between question and answer using Vertex_AI embeddings
5. THE Answer_Analyzer SHALL combine Claude's evaluation with the semantic similarity score
6. IF the semantic similarity score is below 0.3, THEN THE Answer_Analyzer SHALL flag the answer as potentially off-topic
7. IF Claude_API determines the answer is off-topic, THEN THE Answer_Analyzer SHALL trigger the Interruption_Engine
8. THE Answer_Analyzer SHALL perform relevance checks every 5 seconds during the Candidate's response
9. THE Answer_Analyzer SHALL maintain context of the original question throughout the analysis
10. THE Answer_Analyzer SHALL log all relevance scores for post-interview analysis

### Requirement 6: Intelligent Interruption for Off-Topic Answers

**User Story:** As an AI interviewer, I want to interrupt the candidate when they go off-topic so that I can redirect them to answer the actual question.

#### Acceptance Criteria

1. WHEN the Answer_Analyzer flags an answer as off-topic, THE Interruption_Engine SHALL generate an interruption message
2. THE interruption message SHALL reference the original question explicitly
3. THE interruption message format SHALL be: "Wait, I asked about [question topic], please focus on that"
4. WHEN the interruption message is generated, THE ElevenLabs_TTS SHALL convert it to audio with high priority
5. WHEN the interruption audio is ready, THE Real_Time_Voice_System SHALL immediately play it, overriding any ongoing speech
6. WHEN the interruption audio starts playing, THE Deepgram_STT SHALL temporarily pause transcription
7. WHEN the interruption audio completes, THE Deepgram_STT SHALL resume transcription
8. THE Speech_Buffer SHALL clear the off-topic content after interruption
9. THE Silence_Detector SHALL reset and begin monitoring for the Candidate's redirected response
10. THE Interruption_Engine SHALL limit interruptions to a maximum of 2 per question to avoid frustrating the Candidate

### Requirement 7: Context-Aware Question Extraction

**User Story:** As an AI interviewer, I want to extract the core topic from my questions so that I can provide specific feedback when interrupting.

#### Acceptance Criteria

1. WHEN the AI_Interviewer generates a question, THE Context_Tracker SHALL extract the core topic using Claude_API
2. THE core topic SHALL be a concise phrase (3-7 words) summarizing what the question asks
3. EXAMPLE: For "What is the value of four plus two?", the core topic SHALL be "the mathematical calculation"
4. EXAMPLE: For "Describe your experience with React", the core topic SHALL be "your React experience"
5. THE Context_Tracker SHALL store the core topic alongside the full question text
6. WHEN generating interruption messages, THE Interruption_Engine SHALL use the core topic for clarity
7. THE core topic extraction SHALL complete within 500 milliseconds
8. IF core topic extraction fails, THEN THE Interruption_Engine SHALL use the first 10 words of the question
9. THE Context_Tracker SHALL maintain a history of the last 5 questions and their core topics
10. THE core topic SHALL be displayed in the UI for the Candidate's reference

### Requirement 8: Voice-Based Question Delivery

**User Story:** As a candidate, I want the AI to ask questions using natural voice so that the interview feels conversational.

#### Acceptance Criteria

1. WHEN the AI_Interviewer is ready to ask a question, THE Real_Time_Voice_System SHALL fetch the next question from the database
2. WHEN the question is fetched, THE ElevenLabs_TTS SHALL convert the question text to audio
3. THE ElevenLabs_TTS SHALL use voice settings optimized for clarity: stability 0.5, similarity_boost 0.75
4. WHEN the question audio is ready, THE Real_Time_Voice_System SHALL play it through speakers
5. THE Real_Time_Voice_System SHALL display the question text on screen while the audio plays
6. WHEN the question audio completes, THE Silence_Detector SHALL begin monitoring for the Candidate's response
7. THE Real_Time_Voice_System SHALL display a visual indicator showing "Listening for your answer..."
8. IF the ElevenLabs_TTS fails, THEN THE Real_Time_Voice_System SHALL display the question text without audio
9. THE Real_Time_Voice_System SHALL cache common question audio to reduce API calls
10. THE question audio generation SHALL complete within 1.5 seconds

### Requirement 9: Answer Completion Detection

**User Story:** As an AI interviewer, I want to detect when the candidate has finished answering so that I can evaluate their response and move forward.

#### Acceptance Criteria

1. WHEN the Candidate stops speaking, THE Silence_Detector SHALL start a completion timer
2. IF the silence duration reaches 3 seconds, THEN THE Voice_Flow_Controller SHALL consider the answer potentially complete
3. WHEN the answer is potentially complete, THE Answer_Analyzer SHALL perform a final completeness check using Claude_API
4. THE Claude_API SHALL evaluate whether the answer sufficiently addresses the question
5. IF the answer is complete and on-topic, THEN THE Voice_Flow_Controller SHALL proceed to answer evaluation
6. IF the answer is incomplete, THEN THE AI_Interviewer SHALL ask a follow-up question for clarification
7. IF the answer is off-topic, THEN THE Interruption_Engine SHALL have already interrupted (per Requirement 6)
8. THE Candidate SHALL have the option to manually indicate completion by clicking a "Done Answering" button
9. WHEN the "Done Answering" button is clicked, THE Voice_Flow_Controller SHALL immediately proceed to evaluation
10. THE completion detection SHALL not trigger during brief pauses of less than 3 seconds

### Requirement 10: Error Handling and Graceful Degradation

**User Story:** As a candidate, I want the system to handle technical failures gracefully so that my interview can continue even if some features fail.

#### Acceptance Criteria

1. IF the Deepgram_STT connection fails, THEN THE Real_Time_Voice_System SHALL display an error and enable text input mode
2. IF the ElevenLabs_TTS fails, THEN THE Real_Time_Voice_System SHALL display questions as text without audio
3. IF the Claude_API fails during answer analysis, THEN THE Answer_Analyzer SHALL retry up to 3 times with exponential backoff
4. IF all Claude_API retries fail, THEN THE Real_Time_Voice_System SHALL accept the answer without real-time analysis
5. IF the Vertex_AI embedding service fails, THEN THE Relevance_Scorer SHALL rely solely on Claude_API evaluation
6. IF the network connection is lost, THEN THE Real_Time_Voice_System SHALL save the current session state locally
7. WHEN the network connection is restored, THE Real_Time_Voice_System SHALL sync the local session state to the database
8. IF the microphone permission is revoked during the interview, THEN THE Real_Time_Voice_System SHALL switch to text-only mode
9. THE Real_Time_Voice_System SHALL log all errors with sufficient context for debugging
10. THE Real_Time_Voice_System SHALL display user-friendly error messages without exposing technical details

### Requirement 11: Performance and Latency Requirements

**User Story:** As a candidate, I want the AI to respond quickly so that the conversation feels natural and engaging.

#### Acceptance Criteria

1. THE Silence_Detector SHALL detect silence within 100 milliseconds of speech stopping
2. THE Answer_Analyzer SHALL complete relevance analysis within 2 seconds of receiving 20 words
3. THE Interruption_Engine SHALL generate and play interruption audio within 1.5 seconds of detecting off-topic content
4. THE Deepgram_STT SHALL provide transcription with less than 500 milliseconds latency
5. THE ElevenLabs_TTS SHALL generate question audio within 1.5 seconds of receiving text
6. THE Presence_Verifier SHALL generate presence check audio within 1 second of silence detection
7. THE Real_Time_Voice_System SHALL update the transcript display within 200 milliseconds of receiving interim results
8. THE Claude_API calls SHALL complete within 2 seconds for answer analysis
9. THE Vertex_AI embedding generation SHALL complete within 1 second
10. THE overall system response time from answer completion to next question SHALL be less than 5 seconds

### Requirement 12: Session State Management

**User Story:** As a system administrator, I want all voice interactions tracked and stored so that candidates can review their performance later.

#### Acceptance Criteria

1. WHEN an Interview_Session starts, THE Real_Time_Voice_System SHALL create a session record in NeonDB
2. THE session record SHALL include: session_id, user_id, started_at, voice_enabled flag
3. WHEN a question is asked, THE Real_Time_Voice_System SHALL log the question text and timestamp
4. WHEN the Candidate answers, THE Real_Time_Voice_System SHALL store the complete transcript
5. WHEN an interruption occurs, THE Real_Time_Voice_System SHALL log the interruption reason and timestamp
6. WHEN a presence check is triggered, THE Real_Time_Voice_System SHALL log the event and outcome
7. WHEN the interview completes, THE Real_Time_Voice_System SHALL calculate and store overall metrics
8. THE Real_Time_Voice_System SHALL store audio recordings in MongoDB GridFS if the Candidate consents
9. THE Real_Time_Voice_System SHALL maintain a complete transcript history with speaker labels (AI vs Candidate)
10. THE session data SHALL be retrievable for post-interview review and analysis

### Requirement 13: Rate Limiting and Resource Management

**User Story:** As a system administrator, I want to protect API resources and control costs so that the system remains sustainable.

#### Acceptance Criteria

1. THE Real_Time_Voice_System SHALL enforce a limit of 10 interview sessions per Candidate per day
2. THE Real_Time_Voice_System SHALL use Redis cache to track rate limits per user
3. WHEN a Candidate exceeds the rate limit, THE Real_Time_Voice_System SHALL display a message indicating when they can retry
4. THE Real_Time_Voice_System SHALL cache common TTS audio (greetings, presence checks) to reduce API calls
5. THE Real_Time_Voice_System SHALL cache question audio for 24 hours to reduce repeated TTS calls
6. THE Real_Time_Voice_System SHALL limit Claude_API calls to a maximum of 5 per minute per session
7. THE Real_Time_Voice_System SHALL limit Vertex_AI embedding calls to a maximum of 10 per minute per session
8. THE Real_Time_Voice_System SHALL implement exponential backoff for all API retry logic
9. THE Real_Time_Voice_System SHALL monitor API usage and log warnings when approaching rate limits
10. THE Real_Time_Voice_System SHALL gracefully degrade features when rate limits are reached

### Requirement 14: Security and Privacy

**User Story:** As a candidate, I want my voice data and responses protected so that my privacy is maintained.

#### Acceptance Criteria

1. THE Real_Time_Voice_System SHALL store all API keys in environment variables
2. THE Real_Time_Voice_System SHALL never expose API keys to the frontend
3. THE Real_Time_Voice_System SHALL use HTTPS for all API communications
4. THE Real_Time_Voice_System SHALL encrypt audio recordings at rest in MongoDB
5. THE Real_Time_Voice_System SHALL require user authentication before starting an interview
6. THE Real_Time_Voice_System SHALL validate user authorization for accessing session data
7. THE Real_Time_Voice_System SHALL sanitize all user input before sending to AI services
8. THE Real_Time_Voice_System SHALL automatically delete audio recordings older than 90 days
9. THE Real_Time_Voice_System SHALL provide a mechanism for Candidates to delete their session data
10. THE Real_Time_Voice_System SHALL comply with GDPR and data privacy regulations

### Requirement 15: Example Scenario - Mathematical Question

**User Story:** As a candidate, I want the system to handle a simple mathematical question correctly so that I can verify the real-time interaction works as expected.

#### Acceptance Criteria

1. WHEN the AI_Interviewer asks "What is the value of four plus two?", THE ElevenLabs_TTS SHALL speak the question
2. WHEN the question audio completes, THE Silence_Detector SHALL begin monitoring
3. IF the Candidate says "I have interviewed people...", THE Answer_Analyzer SHALL detect this is off-topic
4. WHEN off-topic content is detected, THE Interruption_Engine SHALL interrupt with: "Wait, I asked about the mathematical calculation, please focus on that"
5. WHEN the interruption completes, THE Silence_Detector SHALL reset and monitor for the correct answer
6. IF the Candidate then says "Six", THE Answer_Analyzer SHALL recognize this as on-topic and correct
7. WHEN the correct answer is detected, THE Voice_Flow_Controller SHALL proceed to answer evaluation
8. THE AI_Interviewer SHALL provide positive feedback for the correct answer
9. THE session SHALL log both the off-topic attempt and the correct answer
10. THE entire interaction SHALL complete within 30 seconds from question to feedback

### Requirement 16: Presence Verification Example Scenario

**User Story:** As a candidate, I want the system to verify my presence when I'm silent so that the interview doesn't proceed without me.

#### Acceptance Criteria

1. WHEN the AI_Interviewer asks a question and the Candidate doesn't respond for 10 seconds, THE Silence_Detector SHALL emit "silence_detected"
2. WHEN "silence_detected" is emitted, THE Presence_Verifier SHALL generate "Hey, can you hear me?"
3. WHEN the presence check audio plays, THE Silence_Detector SHALL monitor for a response
4. IF the Candidate responds "Yes I can", THE Presence_Verifier SHALL mark presence as confirmed
5. WHEN presence is confirmed, THE AI_Interviewer SHALL say: "Great! Let me ask you the question again"
6. THE AI_Interviewer SHALL repeat the original question
7. THE Silence_Detector SHALL reset and monitor for the Candidate's answer
8. THE entire presence verification flow SHALL complete within 15 seconds
9. THE session SHALL log the presence verification event
10. THE Candidate SHALL see visual feedback indicating presence was confirmed

### Requirement 17: Multi-Interruption Handling

**User Story:** As an AI interviewer, I want to limit interruptions per question so that I don't frustrate the candidate with excessive corrections.

#### Acceptance Criteria

1. THE Interruption_Engine SHALL track the number of interruptions per question
2. WHEN the first off-topic response is detected, THE Interruption_Engine SHALL interrupt with specific feedback
3. WHEN the second off-topic response is detected, THE Interruption_Engine SHALL interrupt with more direct guidance
4. IF a third off-topic response is detected, THEN THE Interruption_Engine SHALL NOT interrupt
5. WHEN the maximum interruptions are reached, THE Voice_Flow_Controller SHALL accept the answer as-is
6. THE AI_Interviewer SHALL provide feedback noting the answer was off-topic in the evaluation
7. THE session SHALL log all interruption attempts including those that were suppressed
8. THE Interruption_Engine SHALL reset the counter when moving to the next question
9. THE Real_Time_Voice_System SHALL display a subtle indicator showing remaining interruptions available
10. THE interruption limit SHALL be configurable per interview mode (buddy vs strict)

### Requirement 18: Concurrent Operation Handling

**User Story:** As a system, I want to handle multiple concurrent operations efficiently so that the real-time interaction remains responsive.

#### Acceptance Criteria

1. THE Real_Time_Voice_System SHALL use async operations for all API calls
2. THE Answer_Analyzer SHALL perform Claude_API evaluation and Vertex_AI embedding generation concurrently
3. THE Real_Time_Voice_System SHALL preload the next question while the Candidate is answering the current question
4. THE ElevenLabs_TTS SHALL generate audio in the background without blocking transcription
5. THE Real_Time_Voice_System SHALL use connection pooling for MongoDB (max 50 connections)
6. THE Real_Time_Voice_System SHALL use connection pooling for NeonDB (max 20 connections)
7. THE Real_Time_Voice_System SHALL use Redis connection pooling (max 50 connections)
8. THE Real_Time_Voice_System SHALL handle WebSocket connections for real-time transcription streaming
9. THE Real_Time_Voice_System SHALL implement proper error handling for all concurrent operations
10. THE Real_Time_Voice_System SHALL prevent race conditions in state updates using proper locking mechanisms
