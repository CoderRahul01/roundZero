# Requirements Document

## Introduction

The Voice AI Interview System is a comprehensive feature for RoundZero that enables real-time voice-based mock interviews with AI-powered question delivery, answer evaluation, and intelligent interruption capabilities. This feature consists of two major components: (1) migrating large interview question datasets from local storage to MongoDB Atlas for team-wide accessibility and deployment readiness, and (2) implementing a voice-enabled interview flow where AI asks questions, listens to user responses, and provides intelligent feedback.

## Glossary

- **Interview_System**: The complete voice-based interview platform including question delivery, answer capture, and evaluation
- **Dataset_Migration_Service**: The backend service responsible for transferring interview questions from local files to MongoDB
- **MongoDB_Atlas**: The cloud-hosted MongoDB database cluster used for storing interview questions
- **Question_Repository**: The MongoDB collections storing Software, HR, and LeetCode interview questions
- **Voice_Interface**: The browser-based UI component that handles microphone and camera permissions
- **Speech_Recognition_Service**: The Deepgram-powered service that converts user speech to text
- **Text_To_Speech_Service**: The ElevenLabs-powered service that converts AI responses to voice
- **Interview_Agent**: The Anthropic Claude-powered AI that conducts interviews and makes decisions
- **Embedding_Service**: The Gemini-powered service for semantic matching and embeddings
- **Interview_Session**: A single interview instance from start to completion
- **Answer_Evaluator**: The component that analyzes user responses for completeness and relevance
- **Interruption_Engine**: The AI logic that determines when to ask follow-up questions

## Requirements

### Requirement 1: Dataset Migration to MongoDB

**User Story:** As a developer, I want to store interview question datasets in MongoDB so that they are accessible from any environment and not stored in the GitHub repository.

#### Acceptance Criteria

1. WHEN the Dataset_Migration_Service connects to MongoDB_Atlas, THE System SHALL use the MONGODB_URI environment variable
2. THE Dataset_Migration_Service SHALL create a "RoundZero" database with separate collections for Software, HR, and LeetCode questions
3. WHEN migrating Software Questions.csv, THE Dataset_Migration_Service SHALL parse CSV format and insert all records into the Software_Questions collection
4. WHEN migrating hr_interview_questions_dataset.json, THE Dataset_Migration_Service SHALL parse JSON format and insert all records into the HR_Questions collection
5. WHEN migrating leetcode_dataset - lc.csv, THE Dataset_Migration_Service SHALL parse CSV format and insert all records into the LeetCode_Questions collection
6. WHEN a migration completes successfully, THE Dataset_Migration_Service SHALL log the number of records migrated for each dataset
7. IF a migration fails, THEN THE Dataset_Migration_Service SHALL log the error details and halt the migration process
8. THE Question_Repository SHALL provide query methods to retrieve questions by category, difficulty, and topic
9. WHEN the migration is complete, THE System SHALL verify data accessibility by executing test queries against each collection
10. THE Dataset_Migration_Service SHALL create appropriate indexes on frequently queried fields for performance optimization

### Requirement 2: Repository Cleanup and Documentation

**User Story:** As a developer, I want to remove large dataset files from the repository so that the codebase remains lightweight and deployable.

#### Acceptance Criteria

1. WHEN dataset files are migrated to MongoDB, THE System SHALL add dataset file paths to .gitignore
2. THE System SHALL remove Software Questions.csv, hr_interview_questions_dataset.json, and leetcode_dataset - lc.csv from the repository
3. THE System SHALL create documentation in backend/data/README.md explaining MongoDB setup and connection instructions
4. THE Documentation SHALL include instructions for running the migration script
5. THE Documentation SHALL include example queries for accessing questions from MongoDB

### Requirement 3: Browser Permission Management

**User Story:** As a user, I want to grant camera and microphone permissions so that I can participate in voice-based interviews.

#### Acceptance Criteria

1. WHEN a user clicks "Start Interview", THE Interview_System SHALL navigate to the interview panel
2. WHEN the interview panel loads, THE Voice_Interface SHALL request camera and microphone permissions from the browser
3. IF the user grants permissions, THEN THE Voice_Interface SHALL display visual indicators showing camera and microphone are active
4. IF the user denies permissions, THEN THE Voice_Interface SHALL display an error message explaining that permissions are required
5. WHEN permissions are denied, THE Voice_Interface SHALL provide instructions for enabling permissions in browser settings
6. THE Voice_Interface SHALL display the camera feed in a preview window when camera permission is granted
7. THE Voice_Interface SHALL display a microphone level indicator when microphone permission is granted

### Requirement 4: AI Greeting and Question Delivery

**User Story:** As a user, I want the AI to greet me and ask questions via voice so that the interview feels natural and conversational.

#### Acceptance Criteria

1. WHEN camera and microphone permissions are granted, THE Interview_Agent SHALL generate a personalized greeting message
2. WHEN the greeting message is generated, THE Text_To_Speech_Service SHALL convert it to audio using ElevenLabs API
3. WHEN the audio is ready, THE Interview_System SHALL play the greeting through the user's speakers
4. WHEN the greeting completes, THE Interview_Agent SHALL fetch the first question from the Question_Repository
5. WHEN a question is fetched, THE Text_To_Speech_Service SHALL convert the question text to audio
6. WHEN the question audio is ready, THE Interview_System SHALL play the question through the user's speakers
7. THE Interview_System SHALL display the question text on screen while the audio plays
8. IF the Text_To_Speech_Service fails, THEN THE Interview_System SHALL display the text and log the error

### Requirement 5: User Answer Capture

**User Story:** As a user, I want to respond to interview questions via voice or text so that I can provide my answers in my preferred format.

#### Acceptance Criteria

1. WHEN a question is asked, THE Voice_Interface SHALL activate the microphone for voice input
2. WHEN the user speaks, THE Speech_Recognition_Service SHALL convert speech to text using Deepgram API
3. THE Voice_Interface SHALL display the transcribed text in real-time as the user speaks
4. THE Voice_Interface SHALL provide a text input field as an alternative to voice input
5. WHEN the user types in the text field, THE Interview_System SHALL accept the typed text as the answer
6. THE Voice_Interface SHALL display a "Submit Answer" button that is enabled when answer text exists
7. WHEN the user clicks "Submit Answer", THE Interview_System SHALL send the answer to the Answer_Evaluator
8. THE Voice_Interface SHALL display a loading indicator while the answer is being evaluated
9. IF the Speech_Recognition_Service fails, THEN THE Interview_System SHALL fall back to text-only input and notify the user

### Requirement 6: Answer Evaluation and Interruption Logic

**User Story:** As a user, I want the AI to evaluate my answers and ask follow-up questions when needed so that I can provide complete and relevant responses.

#### Acceptance Criteria

1. WHEN an answer is submitted, THE Answer_Evaluator SHALL send the answer to the Interview_Agent for analysis
2. THE Interview_Agent SHALL use Anthropic Claude API to evaluate answer completeness
3. THE Interview_Agent SHALL use Anthropic Claude API to evaluate answer relevance to the question
4. THE Interview_Agent SHALL use the Embedding_Service to perform semantic matching between the answer and expected topics
5. IF the answer is incomplete, THEN THE Interruption_Engine SHALL generate a follow-up question requesting more details
6. IF the answer is off-topic, THEN THE Interruption_Engine SHALL generate a clarification question to redirect the user
7. IF the answer is complete and relevant, THEN THE Interview_Agent SHALL proceed to the next question
8. WHEN a follow-up question is generated, THE Text_To_Speech_Service SHALL convert it to audio
9. THE Interview_System SHALL maintain context of previous answers when evaluating follow-up responses
10. THE Interview_System SHALL limit follow-up questions to a maximum of 2 per original question to maintain interview flow

### Requirement 7: Interview Session Management

**User Story:** As a user, I want my interview session to be tracked and saved so that I can review my performance later.

#### Acceptance Criteria

1. WHEN an interview starts, THE Interview_System SHALL create a new Interview_Session record in MongoDB
2. THE Interview_Session SHALL store the user ID, start timestamp, and session status
3. WHEN a question is asked, THE Interview_System SHALL record the question ID and timestamp in the session
4. WHEN an answer is submitted, THE Interview_System SHALL store the answer text, timestamp, and evaluation results in the session
5. WHEN a follow-up question is asked, THE Interview_System SHALL link it to the original question in the session data
6. WHEN all questions are completed, THE Interview_System SHALL update the session status to "completed"
7. THE Interview_System SHALL calculate and store the session end timestamp
8. THE Interview_System SHALL store audio recordings of user responses if the user consents
9. THE Interview_Session SHALL maintain the sequence order of questions and answers

### Requirement 8: Error Handling and Recovery

**User Story:** As a user, I want the system to handle errors gracefully so that technical issues don't completely disrupt my interview.

#### Acceptance Criteria

1. IF the MongoDB connection fails, THEN THE Interview_System SHALL display an error message and prevent interview start
2. IF the Anthropic API fails, THEN THE Interview_System SHALL retry the request up to 3 times with exponential backoff
3. IF the Deepgram API fails, THEN THE Interview_System SHALL fall back to text-only input mode
4. IF the ElevenLabs API fails, THEN THE Interview_System SHALL display questions as text without audio
5. IF the network connection is lost, THEN THE Interview_System SHALL save the current session state locally
6. WHEN network connection is restored, THE Interview_System SHALL sync the local session state to MongoDB
7. IF camera permission is revoked during interview, THEN THE Interview_System SHALL continue with audio-only mode
8. IF microphone permission is revoked during interview, THEN THE Interview_System SHALL switch to text-only mode
9. THE Interview_System SHALL log all errors with sufficient context for debugging
10. THE Interview_System SHALL display user-friendly error messages without exposing technical details

### Requirement 9: Performance and Latency Requirements

**User Story:** As a user, I want the AI to respond quickly so that the interview feels natural and engaging.

#### Acceptance Criteria

1. WHEN an answer is submitted, THE Answer_Evaluator SHALL return evaluation results within 2 seconds
2. WHEN a question is requested, THE Question_Repository SHALL return the question within 500 milliseconds
3. THE Speech_Recognition_Service SHALL provide real-time transcription with less than 1 second latency
4. THE Text_To_Speech_Service SHALL generate audio within 1.5 seconds of receiving text
5. THE Interview_System SHALL preload the next question while the user is answering the current question
6. THE Interview_System SHALL cache frequently used audio responses to reduce API calls
7. THE Voice_Interface SHALL display visual feedback within 100 milliseconds of user actions

### Requirement 10: Security and Rate Limiting

**User Story:** As a system administrator, I want to protect API resources and user data so that the system remains secure and cost-effective.

#### Acceptance Criteria

1. THE Interview_System SHALL store all API keys in environment variables and never expose them to the frontend
2. THE Interview_System SHALL use the existing rate limiting middleware to prevent API abuse
3. THE Interview_System SHALL validate user authentication before starting an interview session
4. THE Interview_System SHALL encrypt audio recordings at rest in MongoDB
5. THE Interview_System SHALL use HTTPS for all API communications
6. THE Interview_System SHALL sanitize user input before sending to AI services
7. THE Interview_System SHALL implement rate limits of 10 interview sessions per user per day
8. THE Interview_System SHALL log all API calls for audit purposes
9. THE Interview_System SHALL automatically delete audio recordings older than 90 days
10. THE Interview_System SHALL comply with data privacy regulations for storing user responses
