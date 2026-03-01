# Vision Agents Integration - MongoDB Schemas

This directory contains schema definitions for MongoDB collections used in the Vision Agents integration.

## Live Sessions Collection

The `live_sessions` collection stores complete interview session data including real-time transcript, emotion analysis, speech metrics, AI decisions, and session summaries.

### Schema File

- **File**: `live_session_schema.py`
- **Requirements**: 8.1-8.16

### Document Structure

```python
{
    # Session Identification
    "session_id": "session_abc123",           # Unique session identifier
    "candidate_id": "user_xyz789",            # User ID from JWT token
    "call_id": "call_stream_456",             # Stream.io WebRTC call ID
    
    # Session Configuration
    "role": "Software Engineer",              # Job role
    "topics": ["Python", "System Design"],    # Interview topics
    "difficulty": "medium",                   # easy/medium/hard
    "mode": "practice",                       # practice/mock/coaching
    
    # Timing
    "started_at": "2024-01-15T10:30:00Z",    # ISO 8601 timestamp
    "ended_at": null,                         # null if in progress
    
    # Real-time Data
    "transcript": [
        {
            "speaker": "agent",               # user or agent
            "text": "Hello! Welcome...",
            "timestamp": "2024-01-15T10:30:05Z",
            "is_final": true
        }
    ],
    
    "emotion_timeline": [
        {
            "timestamp": "2024-01-15T10:30:10Z",
            "emotion": "confident",           # confident/nervous/confused/neutral/enthusiastic
            "confidence_score": 75,           # 0-100
            "engagement_level": "high",       # high/medium/low
            "body_language_observations": "Good posture, maintaining eye contact..."
        }
    ],
    
    "speech_metrics": {
        "question_1": {
            "question_id": "question_1",
            "filler_word_count": 3,
            "speech_pace": 145.5,             # words per minute
            "long_pause_count": 1,
            "average_filler_rate": 2.5,       # fillers per 100 words
            "rapid_speech": false,            # pace > 180 WPM
            "slow_speech": false              # pace < 100 WPM
        }
    },
    
    "decisions": [
        {
            "timestamp": "2024-01-15T10:30:15Z",
            "action": "CONTINUE",             # CONTINUE/INTERRUPT/ENCOURAGE/NEXT/HINT
            "context": {
                "emotion": "confident",
                "confidence_score": 75,
                "filler_word_count": 3,
                "speech_pace": 145.5
            },
            "message": null                   # Optional message for actions
        }
    ],
    
    "session_summary": null                   # Populated at completion
}
```

### Usage Example

```python
from backend.agent.vision.schemas import LiveSessionDocument, create_example_live_session

# Create example document
example = create_example_live_session()

# Use in MongoDB operations
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["roundzero"]
collection = db["live_sessions"]

# Insert new session
await collection.insert_one(example)

# Query session
session = await collection.find_one({"session_id": "session_abc123"})
```

### Indexes

The following indexes should be created for optimal performance (Requirements: 8.17, 8.18):

```python
# Unique index on session_id
await collection.create_index("session_id", unique=True)

# Compound index for candidate queries
await collection.create_index([("candidate_id", 1), ("started_at", -1)])

# Index for time-based queries
await collection.create_index("started_at")
```

### Field Validation Rules

| Field | Type | Validation |
|-------|------|------------|
| session_id | string | Unique, non-empty |
| candidate_id | string | Non-empty |
| call_id | string | Non-empty, from Stream.io |
| role | string | 1-100 characters |
| topics | array | 1-10 items, each 1-50 characters |
| difficulty | string | One of: easy, medium, hard |
| mode | string | One of: practice, mock, coaching |
| started_at | string | Valid ISO 8601 timestamp |
| ended_at | string/null | Valid ISO 8601 timestamp or null |
| transcript[].speaker | string | One of: user, agent |
| transcript[].is_final | boolean | true or false |
| emotion_timeline[].emotion | string | One of: confident, nervous, confused, neutral, enthusiastic |
| emotion_timeline[].confidence_score | integer | 0-100 |
| emotion_timeline[].engagement_level | string | One of: high, medium, low |
| speech_metrics.filler_word_count | integer | Non-negative |
| speech_metrics.speech_pace | float | Non-negative (WPM) |
| speech_metrics.long_pause_count | integer | Non-negative |
| speech_metrics.average_filler_rate | float | Non-negative |
| decisions[].action | string | One of: CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT |

### Real-time Updates

The schema supports real-time updates during interview sessions:

1. **Transcript Updates**: Append new segments as they arrive from Deepgram
2. **Emotion Updates**: Append snapshots every 10 frames from Gemini
3. **Speech Metrics**: Update per question as analysis completes
4. **Decisions**: Append decision records as Claude makes decisions
5. **Session Summary**: Set once at session completion

### Data Flow

```
Interview Session Start
    ↓
Create session document with metadata
    ↓
Real-time updates:
    - Append transcript segments (Deepgram)
    - Append emotion snapshots (Gemini)
    - Update speech metrics (SpeechProcessor)
    - Append decision records (Claude)
    ↓
Interview Session End
    ↓
Generate and store session_summary
Set ended_at timestamp
```

### Related Files

- **Repository**: `backend/data/mongo_repository.py` (to be created in Task 2.4)
- **Processors**: `backend/agent/vision/processors/` (Tasks 3.x, 4.x)
- **Agent**: `backend/agent/vision/core/` (Tasks 7.x)

## Type Safety

The schema uses TypedDict for type safety in Python. All fields are typed and documented with their requirements.

```python
from typing import TypedDict, List, Optional, Literal

# Literal types ensure only valid values
EmotionType = Literal["confident", "nervous", "confused", "neutral", "enthusiastic"]
DifficultyLevel = Literal["easy", "medium", "hard"]
```

## Testing

Example document creation is provided via `create_example_live_session()` for testing purposes.

```python
from backend.agent.vision.schemas import create_example_live_session

# Get example document
example = create_example_live_session()

# Use in tests
assert example["session_id"] == "session_abc123"
assert example["difficulty"] == "medium"
assert len(example["transcript"]) == 2
```


## Question Results Collection

The `question_results` collection stores individual question results with evaluation scores and multimodal context captured during each answer.

### Schema File

- **File**: `question_result_schema.py`
- **Requirements**: 8.1

### Document Structure

```python
{
    # Session and Question Identification
    "session_id": "session_abc123",           # Reference to live_sessions
    "question_id": "question_1",              # Unique question identifier
    
    # Question and Answer Content
    "question_text": "Can you explain...",    # The question asked
    "answer_text": "A list is a mutable...", # Candidate's answer
    
    # Evaluation Results
    "evaluation": {
        "relevance_score": 95,                # 0-100
        "completeness_score": 85,             # 0-100
        "correctness_score": 90,              # 0-100
        "feedback": "Excellent answer! You correctly identified..."
    },
    
    # Multimodal Context
    "context": {
        "emotion": "confident",               # confident/nervous/confused/neutral/enthusiastic
        "confidence_score": 78,               # 0-100
        "filler_word_count": 2,               # Number of filler words
        "speech_pace": 145.5                  # Words per minute
    },
    
    # Timing
    "timestamp": "2024-01-15T10:35:30Z"      # ISO 8601 timestamp
}
```

### Usage Example

```python
from backend.agent.vision.schemas import QuestionResultDocument, create_example_question_result

# Create example document
example = create_example_question_result()

# Use in MongoDB operations
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["roundzero"]
collection = db["question_results"]

# Insert question result
await collection.insert_one(example)

# Query results for a session
results = await collection.find({"session_id": "session_abc123"}).to_list(length=None)
```

### Indexes

The following indexes should be created for optimal performance:

```python
# Index on session_id for fast session queries
await collection.create_index("session_id")

# Index on timestamp for time-based queries
await collection.create_index("timestamp")

# Compound index for session timeline queries
await collection.create_index([("session_id", 1), ("timestamp", 1)])
```

### Field Validation Rules

| Field | Type | Validation |
|-------|------|------------|
| session_id | string | Non-empty, references live_sessions.session_id |
| question_id | string | Non-empty, unique within session |
| question_text | string | Non-empty |
| answer_text | string | Non-empty |
| evaluation.relevance_score | integer | 0-100 |
| evaluation.completeness_score | integer | 0-100 |
| evaluation.correctness_score | integer | 0-100 |
| evaluation.feedback | string | Non-empty |
| context.emotion | string | One of: confident, nervous, confused, neutral, enthusiastic |
| context.confidence_score | integer | 0-100 |
| context.filler_word_count | integer | Non-negative |
| context.speech_pace | float | Non-negative (WPM) |
| timestamp | string | Valid ISO 8601 timestamp |

### Relationship to Live Sessions

Each question result document references a parent live session:

```
live_sessions (1) ----< (many) question_results
    session_id              session_id (foreign key)
```

This allows:
- Querying all question results for a session
- Analyzing performance across questions
- Tracking improvement over time
- Correlating multimodal context with answer quality

### Data Flow

```
Question Asked
    ↓
Candidate Answers
    ↓
Capture multimodal context:
    - Emotion from EmotionProcessor
    - Confidence score from EmotionProcessor
    - Filler word count from SpeechProcessor
    - Speech pace from SpeechProcessor
    ↓
Evaluate answer with Claude:
    - Relevance score
    - Completeness score
    - Correctness score
    - Detailed feedback
    ↓
Store question result document
```

### Use Cases

1. **Session Analysis**: Retrieve all question results for a session to analyze overall performance
2. **Performance Tracking**: Track scores across multiple sessions to measure improvement
3. **Context Correlation**: Analyze relationship between emotion/speech patterns and answer quality
4. **Feedback Generation**: Use evaluation scores and feedback for post-interview reports
5. **Training Data**: Collect data for improving evaluation algorithms

### Related Files

- **Repository**: `backend/data/mongo_repository.py` (Task 2.4)
- **Agent**: `backend/agent/vision/core/round_zero_agent.py` (Task 7.7)
- **Decision Engine**: `backend/agent/vision/core/decision_engine.py` (Task 5.5)
