# Enhanced Interview Experience - Design Document

## Overview

The Enhanced Interview Experience transforms RoundZero's real-time voice interaction system into a complete, natural interview experience. This design extends the existing VoiceFlowController with intelligent onboarding, countdown timers, question progression, follow-up question generation, and multi-modal analysis (tone, pitch, facial expressions).

### Key Enhancements

1. **Personal Onboarding Flow**: Greets candidates by name, explains the process, confirms readiness
2. **Visual Countdown Timer**: 5-second countdown before first question
3. **Question Progression Engine**: Sequential movement through questions with smooth transitions
4. **Follow-Up Generator**: AI-powered contextual follow-up questions
5. **Multi-Modal Analysis**: Analyzes tone, pitch, and facial expressions
6. **Comprehensive Storage**: Complete transcripts and analysis results

### Design Principles

- **Extend, Don't Replace**: Build on existing VoiceFlowController
- **Graceful Degradation**: System continues if analysis features fail
- **Performance First**: Maintain <5s total latency
- **Privacy by Design**: Explicit consent, encryption, data retention
- **Vertical Slice Development**: Schema → API → UI


## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│           Enhanced Interview System                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐    ┌──────────────────────────┐  │
│  │OnboardingManager │────│  VoiceFlowController     │  │
│  │ - Greeting       │    │  (Existing Core)         │  │
│  │ - Introduction   │    │  - State Machine         │  │
│  │ - Readiness      │    │  - Speech Buffer         │  │
│  └──────────────────┘    │  - Silence Detection     │  │
│                           └──────────────────────────┘  │
│  ┌──────────────────┐    ┌──────────────────────────┐  │
│  │CountdownTimer    │    │QuestionProgressionEngine │  │
│  └──────────────────┘    │ - Next Question Logic    │  │
│                           │ - Feedback Generation    │  │
│  ┌──────────────────┐    │ - Progress Tracking      │  │
│  │FollowUpGenerator │────┘                            │  │
│  │ - Claude API     │                                  │  │
│  │ - Reasoning      │    ┌──────────────────────────┐  │
│  └──────────────────┘    │ MultiModalAnalyzer       │  │
│                           │ - ToneAnalyzer           │  │
│  ┌──────────────────┐    │ - PitchAnalyzer          │  │
│  │ Storage Layer    │────│ - FacialAnalyzer         │  │
│  │ - MongoDB        │    │ - Concurrent Execution   │  │
│  │ - Postgres       │    └──────────────────────────┘  │
│  └──────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

### Integration with Existing VoiceFlowController

The enhanced system extends VoiceFlowController without modifying its core:

- **New States Added**: ONBOARDING, COUNTDOWN, FOLLOW_UP
- **Existing States Reused**: ASKING_QUESTION, LISTENING, EVALUATING
- **Hooks Added**: Pre-question hooks, post-answer hooks
- **Backward Compatible**: Existing functionality unchanged


## Components and Interfaces

### 1. OnboardingManager

Manages the initial greeting and readiness confirmation flow.

```python
class OnboardingManager:
    """
    Handles personalized greeting, introduction, and readiness confirmation.
    """
    
    def __init__(
        self,
        tts_service: TTSService,
        user_repository: UserRepository,
        claude_client: AsyncAnthropic
    ):
        self.tts_service = tts_service
        self.user_repository = user_repository
        self.claude_client = claude_client
    
    async def start_onboarding(
        self, 
        user_id: str, 
        session_id: str
    ) -> OnboardingResult:
        """Execute complete onboarding flow."""
        pass
    
    async def generate_greeting(self, first_name: str) -> str:
        """Generate personalized greeting with time-of-day."""
        pass
    
    async def generate_introduction(
        self, 
        question_count: int
    ) -> str:
        """Generate interview process introduction."""
        pass
    
    async def confirm_readiness(self) -> ReadinessResult:
        """Wait for and interpret readiness confirmation."""
        pass
```

**Key Methods:**
- `start_onboarding()`: Orchestrates greeting → introduction → readiness
- `generate_greeting()`: Creates personalized greeting with time-based salutation
- `generate_introduction()`: Explains interview process
- `confirm_readiness()`: Listens for affirmative/negative responses


### 2. QuestionProgressionEngine

Manages sequential movement through interview questions.

```python
class QuestionProgressionEngine:
    """
    Handles question sequencing, transitions, and progress tracking.
    """
    
    def __init__(
        self,
        question_repository: MongoQuestionRepository,
        tts_service: TTSService,
        claude_client: AsyncAnthropic
    ):
        self.question_repository = question_repository
        self.tts_service = tts_service
        self.claude_client = claude_client
        self.current_index = 0
        self.questions = []
    
    async def load_questions(
        self, 
        session_id: str, 
        criteria: QuestionCriteria
    ) -> list[Question]:
        """Load question set for interview."""
        pass
    
    async def get_next_question(self) -> Optional[Question]:
        """Get next question in sequence."""
        pass
    
    async def generate_feedback(
        self, 
        question: str, 
        answer: str
    ) -> str:
        """Generate brief encouraging feedback."""
        pass
    
    def get_progress(self) -> ProgressInfo:
        """Get current progress (N of Total)."""
        pass
```

**Key Methods:**
- `load_questions()`: Retrieves question set based on role/difficulty
- `get_next_question()`: Returns next question, None if complete
- `generate_feedback()`: Creates 1-2 sentence encouraging feedback
- `get_progress()`: Returns current question number and total


### 3. FollowUpGenerator

Generates contextual follow-up questions using Claude API.

```python
class FollowUpGenerator:
    """
    Analyzes answers and generates intelligent follow-up questions.
    """
    
    def __init__(
        self,
        claude_client: AsyncAnthropic,
        max_followups_per_question: int = 2
    ):
        self.claude_client = claude_client
        self.max_followups = max_followups_per_question
        self.followup_count = 0
    
    async def should_ask_followup(
        self,
        question: str,
        answer: str,
        context: dict
    ) -> FollowUpDecision:
        """Determine if follow-up would add value."""
        pass
    
    async def generate_followup(
        self,
        question: str,
        answer: str,
        decision: FollowUpDecision
    ) -> FollowUpQuestion:
        """Generate contextual follow-up question."""
        pass
    
    def reset_for_new_question(self):
        """Reset follow-up counter for next main question."""
        self.followup_count = 0
```

**Decision Criteria:**
- Answer completeness (incomplete answers trigger follow-ups)
- Interesting points mentioned (deep dive opportunities)
- Clarification needs (ambiguous statements)
- Maximum 2 follow-ups per main question

**Follow-Up Quality:**
- References specific points from candidate's answer
- Feels conversational, not scripted
- Adds value to assessment


### 4. MultiModalAnalyzer

Coordinates tone, pitch, and facial analysis concurrently.

```python
class MultiModalAnalyzer:
    """
    Orchestrates concurrent multi-modal analysis.
    """
    
    def __init__(
        self,
        tone_analyzer: ToneAnalyzer,
        pitch_analyzer: PitchAnalyzer,
        facial_analyzer: FacialExpressionAnalyzer
    ):
        self.tone_analyzer = tone_analyzer
        self.pitch_analyzer = pitch_analyzer
        self.facial_analyzer = facial_analyzer
    
    async def analyze_answer(
        self,
        audio_stream: bytes,
        video_stream: bytes,
        answer_text: str
    ) -> MultiModalResult:
        """Run all analyses concurrently."""
        results = await asyncio.gather(
            self.tone_analyzer.analyze(audio_stream, answer_text),
            self.pitch_analyzer.analyze(audio_stream),
            self.facial_analyzer.analyze(video_stream),
            return_exceptions=True
        )
        return self._combine_results(results)
    
    def _combine_results(
        self, 
        results: tuple
    ) -> MultiModalResult:
        """Combine and weight analysis results."""
        # Weight: tone (40%), pitch (30%), facial (30%)
        pass
```

**Concurrent Execution:**
- All three analyses run in parallel using `asyncio.gather()`
- Total analysis time: max(tone_time, pitch_time, facial_time)
- Target: <2 seconds total

**Graceful Degradation:**
- `return_exceptions=True` prevents one failure from blocking others
- Missing analysis results are handled gracefully
- System continues with partial data


### 5. ToneAnalyzer

Analyzes emotional tone and confidence from voice.

```python
class ToneAnalyzer:
    """
    Analyzes tone of voice using Deepgram audio intelligence.
    """
    
    def __init__(self, deepgram_client):
        self.deepgram_client = deepgram_client
    
    async def analyze(
        self, 
        audio_stream: bytes, 
        transcript: str
    ) -> ToneAnalysisResult:
        """
        Analyze tone from audio stream.
        
        Returns:
            ToneAnalysisResult with:
            - tone_category: confident, nervous, uncertain, enthusiastic, monotone
            - confidence_score: 0.0 to 1.0
            - hesitation_count: number of pauses/fillers
            - speech_pace: words per minute
        """
        pass
```

**Analysis Features:**
- Emotional tone detection (5 categories)
- Confidence scoring (0.0-1.0 scale)
- Hesitation pattern detection (pauses, "um", "uh")
- Speech pace measurement (WPM)

**Technology:**
- Deepgram audio intelligence API
- Real-time processing during answer
- Results available within 1 second of completion


### 6. PitchAnalyzer

Measures voice pitch patterns and variations.

```python
class PitchAnalyzer:
    """
    Analyzes voice pitch using librosa audio processing.
    """
    
    def __init__(self):
        self.sample_rate = 16000
    
    async def analyze(self, audio_stream: bytes) -> PitchAnalysisResult:
        """
        Extract pitch features from audio.
        
        Returns:
            PitchAnalysisResult with:
            - average_pitch_hz: mean pitch in Hz
            - pitch_range: max - min pitch
            - pitch_pattern: rising, falling, stable
            - stress_indicators: abnormal spikes
        """
        pass
    
    def _extract_pitch(self, audio_data: np.ndarray) -> np.ndarray:
        """Use librosa to extract pitch contour."""
        pass
    
    def _detect_pattern(self, pitch_contour: np.ndarray) -> str:
        """Classify pitch pattern."""
        pass
```

**Analysis Features:**
- Average pitch calculation (Hz)
- Pitch range and variation
- Pattern classification (rising/falling/stable)
- Stress indicator detection (abnormal spikes)

**Technology:**
- librosa for pitch extraction
- NumPy for signal processing
- Runs in background thread to avoid blocking


### 7. FacialExpressionAnalyzer

Analyzes facial expressions and engagement from video.

```python
class FacialExpressionAnalyzer:
    """
    Analyzes facial expressions using MediaPipe and OpenCV.
    """
    
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh()
        self.consent_given = False
    
    async def request_consent(self) -> bool:
        """Request explicit video recording consent."""
        pass
    
    async def analyze(
        self, 
        video_stream: bytes
    ) -> FacialAnalysisResult:
        """
        Analyze facial expressions from video.
        
        Returns:
            FacialAnalysisResult with:
            - dominant_expression: smile, frown, neutral, surprised, confused
            - eye_contact_percentage: 0.0 to 1.0
            - head_movements: list of detected movements
            - engagement_score: 0.0 to 1.0
        """
        if not self.consent_given:
            return FacialAnalysisResult.disabled()
        pass
    
    def _detect_expression(self, landmarks) -> str:
        """Classify facial expression from landmarks."""
        pass
```

**Analysis Features:**
- Expression detection (5 categories)
- Eye contact measurement (camera gaze)
- Head movement tracking (nodding, shaking)
- Engagement scoring (0.0-1.0)

**Privacy:**
- Explicit consent required before activation
- If consent denied, returns disabled result
- Raw video not stored, only analysis results


## Data Models

### Enhanced State Machine

```python
class EnhancedConversationState(Enum):
    """Extended conversation states."""
    # Existing states
    IDLE = "IDLE"
    ASKING_QUESTION = "ASKING_QUESTION"
    LISTENING = "LISTENING"
    ANALYZING = "ANALYZING"
    EVALUATING = "EVALUATING"
    
    # New states
    ONBOARDING = "ONBOARDING"
    COUNTDOWN = "COUNTDOWN"
    FOLLOW_UP = "FOLLOW_UP"
    COMPLETING = "COMPLETING"

@dataclass
class EnhancedVoiceFlowState:
    """Extended state with onboarding and follow-up tracking."""
    # Existing fields
    conversation_state: EnhancedConversationState
    current_question: Optional[str]
    speech_buffer: str
    
    # New fields
    onboarding_complete: bool = False
    current_question_number: int = 0
    total_questions: int = 0
    followup_count: int = 0
    is_followup: bool = False
    main_question_id: Optional[str] = None
```

### Analysis Results

```python
@dataclass
class ToneAnalysisResult:
    tone_category: str  # confident, nervous, uncertain, enthusiastic, monotone
    confidence_score: float  # 0.0 to 1.0
    hesitation_count: int
    speech_pace: float  # words per minute
    timestamp: float

@dataclass
class PitchAnalysisResult:
    average_pitch_hz: float
    pitch_range: float
    pitch_pattern: str  # rising, falling, stable
    stress_indicators: list[float]
    timestamp: float
```


@dataclass
class FacialAnalysisResult:
    dominant_expression: str  # smile, frown, neutral, surprised, confused
    eye_contact_percentage: float  # 0.0 to 1.0
    head_movements: list[str]
    engagement_score: float  # 0.0 to 1.0
    timestamp: float
    enabled: bool = True

@dataclass
class MultiModalResult:
    tone_result: Optional[ToneAnalysisResult]
    pitch_result: Optional[PitchAnalysisResult]
    facial_result: Optional[FacialAnalysisResult]
    overall_confidence: float  # weighted combination
    consistency_score: float  # cross-modal consistency
    notable_patterns: list[str]
    timestamp: float

@dataclass
class FollowUpQuestion:
    question_text: str
    reasoning: str
    main_question_id: str
    timestamp: float

@dataclass
class OnboardingResult:
    greeting_played: bool
    introduction_played: bool
    readiness_confirmed: bool
    total_duration: float
    timestamp: float
```


## Database Schema

### MongoDB Collections

#### 1. interview_transcripts

```javascript
{
  _id: ObjectId,
  session_id: String,  // indexed
  user_id: String,     // indexed
  entries: [
    {
      speaker: String,  // "AI" or "Candidate"
      text: String,
      timestamp: Number,
      question_number: Number,
      is_followup: Boolean
    }
  ],
  started_at: Date,
  completed_at: Date,
  created_at: Date
}
```

**Indexes:**
- `session_id` (unique)
- `user_id, started_at` (compound for user history)

#### 2. analysis_results

```javascript
{
  _id: ObjectId,
  session_id: String,  // indexed
  question_id: String,
  question_number: Number,
  answer_text: String,
  
  // Tone analysis
  tone_data: {
    tone_category: String,
    confidence_score: Number,
    hesitation_count: Number,
    speech_pace: Number
  },
  
  // Pitch analysis
  pitch_data: {
    average_pitch_hz: Number,
    pitch_range: Number,
    pitch_pattern: String,
    stress_indicators: [Number]
  },
  
  // Facial analysis
  facial_data: {
    dominant_expression: String,
    eye_contact_percentage: Number,
    head_movements: [String],
    engagement_score: Number,
    enabled: Boolean
  },
  
  // Combined analysis
  multi_modal_summary: {
    overall_confidence: Number,
    consistency_score: Number,
    notable_patterns: [String]
  },
  
  // Answer evaluation
  evaluation: {
    relevance_score: Number,
    completeness_score: Number,
    correctness_score: Number,
    feedback: String
  },
  
  timestamp: Date,
  created_at: Date
}
```

**Indexes:**
- `session_id, question_number` (compound)
- `session_id` (for retrieval)


#### 3. follow_up_questions

```javascript
{
  _id: ObjectId,
  session_id: String,  // indexed
  main_question_id: String,
  main_question_number: Number,
  follow_up_text: String,
  reasoning: String,
  answer_text: String,
  
  evaluation: {
    relevance_score: Number,
    completeness_score: Number,
    feedback: String
  },
  
  timestamp: Date,
  created_at: Date
}
```

**Indexes:**
- `session_id, main_question_number` (compound)

### Postgres Tables

#### 1. interview_sessions (extended)

```sql
CREATE TABLE interview_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  status VARCHAR(50) NOT NULL,  -- 'onboarding', 'in_progress', 'completed', 'abandoned'
  
  -- Progress tracking
  current_question_number INT DEFAULT 0,
  total_questions INT NOT NULL,
  
  -- Onboarding tracking
  onboarding_completed BOOLEAN DEFAULT FALSE,
  onboarding_duration_seconds INT,
  
  -- Overall scores
  average_confidence DECIMAL(3,2),
  average_relevance DECIMAL(3,2),
  average_completeness DECIMAL(3,2),
  overall_performance DECIMAL(3,2),
  
  -- Metadata
  last_update_timestamp TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_started ON interview_sessions(user_id, started_at DESC);
CREATE INDEX idx_sessions_status ON interview_sessions(status);
```


## API Design

### REST Endpoints

#### POST /api/interview/start
Start interview with onboarding flow.

**Request:**
```json
{
  "user_id": "uuid",
  "role": "Software Engineer",
  "difficulty": "medium",
  "question_count": 5
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "greeting_audio_url": "string",
  "greeting_text": "string",
  "status": "onboarding"
}
```

#### POST /api/interview/{session_id}/confirm-readiness
Confirm candidate readiness.

**Request:**
```json
{
  "response_text": "Yes, let's go"
}
```

**Response:**
```json
{
  "readiness_confirmed": true,
  "countdown_start": true
}
```

#### GET /api/interview/{session_id}/current-question
Get current question.

**Response:**
```json
{
  "question_number": 1,
  "total_questions": 5,
  "question_text": "string",
  "question_audio_url": "string",
  "is_followup": false
}
```

#### POST /api/interview/{session_id}/answer
Submit answer for analysis.

**Request:**
```json
{
  "answer_text": "string",
  "audio_stream": "base64",
  "video_stream": "base64",
  "question_number": 1
}
```

**Response:**
```json
{
  "analysis_complete": true,
  "feedback": "string",
  "has_followup": false,
  "next_question_number": 2
}
```


#### GET /api/interview/{session_id}/follow-up
Get follow-up question if available.

**Response:**
```json
{
  "has_followup": true,
  "followup_text": "string",
  "followup_audio_url": "string",
  "reasoning": "string"
}
```

#### GET /api/interview/{session_id}/transcript
Get complete interview transcript.

**Response:**
```json
{
  "session_id": "uuid",
  "entries": [
    {
      "speaker": "AI",
      "text": "string",
      "timestamp": 1234567890,
      "question_number": 1
    }
  ]
}
```

#### GET /api/interview/{session_id}/analysis
Get all analysis results.

**Response:**
```json
{
  "session_id": "uuid",
  "results": [
    {
      "question_number": 1,
      "tone_data": {...},
      "pitch_data": {...},
      "facial_data": {...},
      "multi_modal_summary": {...},
      "evaluation": {...}
    }
  ]
}
```

#### POST /api/interview/{session_id}/complete
Mark interview as complete.

**Response:**
```json
{
  "status": "completed",
  "overall_scores": {
    "average_confidence": 0.75,
    "average_relevance": 0.82,
    "overall_performance": 0.78
  },
  "dashboard_url": "/dashboard/results/{session_id}"
}
```


### WebSocket Events

#### Client → Server

```javascript
// Audio stream chunk
{
  "type": "audio_chunk",
  "data": "base64_audio",
  "timestamp": 1234567890
}

// Video stream chunk (if consent given)
{
  "type": "video_chunk",
  "data": "base64_video",
  "timestamp": 1234567890
}

// Readiness response
{
  "type": "readiness_response",
  "text": "Yes, I'm ready"
}
```

#### Server → Client

```javascript
// State change notification
{
  "type": "state_change",
  "old_state": "ONBOARDING",
  "new_state": "COUNTDOWN",
  "timestamp": 1234567890
}

// Countdown tick
{
  "type": "countdown_tick",
  "count": 3
}

// Question presentation
{
  "type": "question",
  "text": "string",
  "audio_url": "string",
  "question_number": 1,
  "total_questions": 5
}

// Follow-up question
{
  "type": "followup",
  "text": "string",
  "audio_url": "string"
}

// Feedback after answer
{
  "type": "feedback",
  "text": "string",
  "audio_url": "string"
}

// Analysis progress
{
  "type": "analysis_progress",
  "stage": "tone_analysis",
  "progress": 0.33
}

// Interview completion
{
  "type": "interview_complete",
  "message": "string",
  "overall_scores": {...}
}
```


## Multi-Modal Analysis Pipeline

### Concurrent Execution Flow

```
Answer Complete
    ↓
    ├─→ ToneAnalyzer.analyze(audio, text)     [~1s]
    ├─→ PitchAnalyzer.analyze(audio)          [~1s]
    └─→ FacialAnalyzer.analyze(video)         [~1s]
    ↓
asyncio.gather() waits for all
    ↓
MultiModalAnalyzer.combine_results()
    ↓
Store to MongoDB
    ↓
Total Time: ~2s (concurrent)
```

### Weighting Formula

```python
overall_confidence = (
    tone_confidence * 0.40 +
    pitch_stability * 0.30 +
    facial_engagement * 0.30
)
```

### Consistency Detection

Detects mismatches between modalities:
- Confident words but nervous tone → Flag inconsistency
- Enthusiastic tone but low facial engagement → Flag inconsistency
- Stable pitch but high hesitation count → Flag inconsistency

### Graceful Degradation Strategy

```python
async def analyze_answer(self, audio, video, text):
    results = await asyncio.gather(
        self.tone_analyzer.analyze(audio, text),
        self.pitch_analyzer.analyze(audio),
        self.facial_analyzer.analyze(video),
        return_exceptions=True  # Don't fail if one analyzer fails
    )
    
    # Handle partial results
    tone_result = results[0] if not isinstance(results[0], Exception) else None
    pitch_result = results[1] if not isinstance(results[1], Exception) else None
    facial_result = results[2] if not isinstance(results[2], Exception) else None
    
    # Calculate with available data
    return self._combine_partial_results(tone_result, pitch_result, facial_result)
```


## Integration Points

### Extending VoiceFlowController

```python
class EnhancedVoiceFlowController(VoiceFlowController):
    """
    Extended controller with onboarding and multi-modal analysis.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # New components
        self.onboarding_manager = OnboardingManager(...)
        self.question_progression = QuestionProgressionEngine(...)
        self.followup_generator = FollowUpGenerator(...)
        self.multimodal_analyzer = MultiModalAnalyzer(...)
    
    async def start_interview(self, first_question: str):
        """Override to add onboarding flow."""
        # Run onboarding first
        onboarding_result = await self.onboarding_manager.start_onboarding(
            self.session_id, 
            self.user_id
        )
        
        # Show countdown
        await self._show_countdown()
        
        # Then proceed with original flow
        await super().start_interview(first_question)
    
    async def _evaluate_answer(self):
        """Override to add multi-modal analysis and follow-ups."""
        # Original evaluation
        await super()._evaluate_answer()
        
        # Multi-modal analysis (concurrent)
        analysis_result = await self.multimodal_analyzer.analyze_answer(
            audio_stream=self.audio_buffer,
            video_stream=self.video_buffer,
            answer_text=self.state.speech_buffer
        )
        
        # Store analysis
        await self._store_analysis(analysis_result)
        
        # Check for follow-up
        followup_decision = await self.followup_generator.should_ask_followup(
            question=self.state.current_question,
            answer=self.state.speech_buffer,
            context={"analysis": analysis_result}
        )
        
        if followup_decision.should_ask:
            await self._ask_followup(followup_decision)
        else:
            await self._progress_to_next_question()
```


### State Machine Extensions

```
New State Flow:

IDLE
  ↓
ONBOARDING (new)
  ↓
COUNTDOWN (new)
  ↓
ASKING_QUESTION (existing)
  ↓
LISTENING (existing)
  ↓
EVALUATING (existing)
  ↓
FOLLOW_UP (new) ──→ LISTENING (if follow-up asked)
  ↓
ASKING_QUESTION (next question)
  ↓
...repeat...
  ↓
COMPLETING (new)
```

### Hooks System

```python
class HookManager:
    """Manages lifecycle hooks for extensibility."""
    
    def __init__(self):
        self.pre_question_hooks = []
        self.post_answer_hooks = []
        self.pre_evaluation_hooks = []
    
    def register_pre_question_hook(self, hook: Callable):
        """Register hook to run before each question."""
        self.pre_question_hooks.append(hook)
    
    def register_post_answer_hook(self, hook: Callable):
        """Register hook to run after each answer."""
        self.post_answer_hooks.append(hook)
    
    async def run_pre_question_hooks(self, context: dict):
        """Execute all pre-question hooks."""
        for hook in self.pre_question_hooks:
            await hook(context)
    
    async def run_post_answer_hooks(self, context: dict):
        """Execute all post-answer hooks."""
        for hook in self.post_answer_hooks:
            await hook(context)
```

**Usage:**
```python
# Register multi-modal analysis as post-answer hook
hook_manager.register_post_answer_hook(
    multimodal_analyzer.analyze_answer
)

# Register follow-up generation as post-answer hook
hook_manager.register_post_answer_hook(
    followup_generator.check_and_generate
)
```


## Performance Optimizations

### 1. TTS Audio Caching

```python
class TTSCacheService:
    """Cache generated TTS audio to reduce API calls."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 86400  # 24 hours
    
    async def get_or_generate(self, text: str, voice_settings: dict) -> bytes:
        """Get from cache or generate new audio."""
        cache_key = self._generate_key(text, voice_settings)
        
        # Try cache first
        cached_audio = await self.redis.get(cache_key)
        if cached_audio:
            return cached_audio
        
        # Generate and cache
        audio = await self.tts_service.synthesize(text, voice_settings)
        await self.redis.setex(cache_key, self.cache_ttl, audio)
        return audio
```

**Benefits:**
- Questions asked repeatedly are cached
- Reduces ElevenLabs API costs
- Faster audio delivery (<100ms from cache)

### 2. Concurrent Analysis Execution

All three analyzers run in parallel:
```python
# Sequential (slow): 3 seconds total
tone_result = await tone_analyzer.analyze()      # 1s
pitch_result = await pitch_analyzer.analyze()    # 1s
facial_result = await facial_analyzer.analyze()  # 1s

# Concurrent (fast): 1 second total
results = await asyncio.gather(
    tone_analyzer.analyze(),
    pitch_analyzer.analyze(),
    facial_analyzer.analyze()
)
```

**Performance Gain:** 3x faster (3s → 1s)


### 3. Database Connection Pooling

```python
# MongoDB connection pool (already configured in MongoQuestionRepository)
mongo_client = AsyncIOMotorClient(
    uri,
    maxPoolSize=50,      # Handle high concurrency
    minPoolSize=10,      # Warm connections
    serverSelectionTimeoutMS=5000
)

# Postgres connection pool (using asyncpg)
postgres_pool = await asyncpg.create_pool(
    dsn=database_url,
    min_size=10,
    max_size=50,
    command_timeout=5.0
)
```

### 4. Batch Database Writes

```python
class BatchWriter:
    """Batch multiple writes to reduce database round trips."""
    
    def __init__(self, mongo_db, batch_size=10):
        self.mongo_db = mongo_db
        self.batch_size = batch_size
        self.pending_writes = []
    
    async def add_transcript_entry(self, session_id: str, entry: dict):
        """Add entry to batch."""
        self.pending_writes.append({
            "collection": "interview_transcripts",
            "operation": "update",
            "filter": {"session_id": session_id},
            "update": {"$push": {"entries": entry}}
        })
        
        if len(self.pending_writes) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        """Write all pending operations."""
        if not self.pending_writes:
            return
        
        # Execute batch operations
        bulk_ops = []
        for write in self.pending_writes:
            bulk_ops.append(pymongo.UpdateOne(
                write["filter"],
                write["update"]
            ))
        
        await self.mongo_db[write["collection"]].bulk_write(bulk_ops)
        self.pending_writes.clear()
```


## Error Handling

### Graceful Degradation Strategy

```python
class ErrorHandler:
    """Centralized error handling with graceful degradation."""
    
    async def handle_analysis_failure(
        self, 
        analyzer_name: str, 
        error: Exception,
        context: dict
    ) -> Optional[AnalysisResult]:
        """Handle analysis failure gracefully."""
        
        # Log error with context
        logger.error(
            f"{analyzer_name} failed: {error}",
            extra={
                "session_id": context.get("session_id"),
                "question_number": context.get("question_number"),
                "error_type": type(error).__name__
            }
        )
        
        # Send monitoring alert for critical failures
        if isinstance(error, (APIError, TimeoutError)):
            await self.monitoring.alert(
                severity="high",
                message=f"{analyzer_name} API failure",
                context=context
            )
        
        # Return None to indicate missing data
        return None
    
    async def handle_tts_failure(
        self, 
        text: str, 
        error: Exception
    ) -> TTSFallbackResult:
        """Handle TTS failure with text-only fallback."""
        
        logger.error(f"TTS generation failed: {error}")
        
        return TTSFallbackResult(
            audio_available=False,
            text=text,
            display_message="Audio unavailable. Please read the text."
        )
    
    async def handle_database_failure(
        self, 
        operation: str, 
        data: dict,
        error: Exception
    ) -> bool:
        """Handle database failure with local caching."""
        
        logger.error(f"Database {operation} failed: {error}")
        
        # Cache locally for retry
        await self.local_cache.store(
            key=f"failed_{operation}_{uuid.uuid4()}",
            value=data,
            ttl=3600  # 1 hour
        )
        
        # Schedule retry
        await self.retry_queue.add(operation, data)
        
        return False
```


### Error Recovery Flows

#### 1. Analysis Failure Recovery

```
ToneAnalyzer fails
    ↓
Log error + alert monitoring
    ↓
Continue with pitch and facial analysis
    ↓
Calculate overall_confidence with available data
    ↓
Store partial results with "tone_analysis_failed" flag
    ↓
Interview continues normally
```

#### 2. TTS Failure Recovery

```
ElevenLabs API fails
    ↓
Log error
    ↓
Display text-only message to candidate
    ↓
Show "Audio unavailable" notice
    ↓
Interview continues with text display
```

#### 3. Database Failure Recovery

```
MongoDB write fails
    ↓
Cache data locally (Redis/memory)
    ↓
Add to retry queue
    ↓
Continue interview
    ↓
Background worker retries write every 30s
    ↓
Success: clear from retry queue
```

### User-Facing Error Messages

```python
ERROR_MESSAGES = {
    "analysis_partial": "Some analysis features are temporarily unavailable. Your interview will continue normally.",
    "audio_unavailable": "Audio playback is unavailable. Please read the text on screen.",
    "video_consent_required": "Video analysis requires camera permission. You can continue without it.",
    "connection_unstable": "Your connection is unstable. We're saving your progress automatically.",
    "system_error": "We encountered a technical issue. Your progress is saved. Please refresh to continue."
}
```


## Security & Privacy

### 1. Video Consent Management

```python
class ConsentManager:
    """Manages video recording consent."""
    
    async def request_video_consent(self, user_id: str) -> ConsentResult:
        """Request explicit video consent before interview."""
        
        consent_text = """
        RoundZero uses video analysis to assess your engagement and 
        non-verbal communication during the interview.
        
        - Your video is analyzed in real-time
        - Only analysis results (scores) are stored
        - Raw video is NOT stored permanently
        - You can opt out and continue without video analysis
        
        Do you consent to video analysis?
        """
        
        # Display consent dialog
        response = await self.display_consent_dialog(consent_text)
        
        # Store consent decision
        await self.store_consent(user_id, response)
        
        return ConsentResult(
            consent_given=response,
            timestamp=time.time()
        )
    
    async def store_consent(self, user_id: str, consent: bool):
        """Store consent decision in database."""
        await self.db.execute(
            """
            INSERT INTO user_consents (user_id, consent_type, granted, timestamp)
            VALUES ($1, 'video_analysis', $2, NOW())
            """,
            user_id, consent
        )
```

### 2. Data Encryption

```python
class DataEncryption:
    """Encrypt sensitive data at rest."""
    
    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())
    
    def encrypt_audio(self, audio_bytes: bytes) -> bytes:
        """Encrypt audio data before storage."""
        return self.fernet.encrypt(audio_bytes)
    
    def decrypt_audio(self, encrypted_bytes: bytes) -> bytes:
        """Decrypt audio data for playback."""
        return self.fernet.decrypt(encrypted_bytes)
    
    def encrypt_transcript(self, text: str) -> str:
        """Encrypt transcript text."""
        encrypted = self.fernet.encrypt(text.encode())
        return base64.b64encode(encrypted).decode()
```


### 3. Data Retention Policy

```python
class DataRetentionManager:
    """Manages data retention and deletion."""
    
    async def apply_retention_policy(self):
        """Apply 90-day retention for raw data."""
        
        cutoff_date = datetime.now() - timedelta(days=90)
        
        # Delete old raw audio/video from GridFS
        await self.mongo_db.fs.files.delete_many({
            "uploadDate": {"$lt": cutoff_date}
        })
        
        # Keep analysis results indefinitely
        # (only scores, not raw data)
        
        logger.info(f"Deleted raw data older than {cutoff_date}")
    
    async def delete_user_data(self, user_id: str):
        """Delete all user data (GDPR compliance)."""
        
        # Delete from MongoDB
        await self.mongo_db.interview_transcripts.delete_many(
            {"user_id": user_id}
        )
        await self.mongo_db.analysis_results.delete_many(
            {"user_id": user_id}
        )
        
        # Delete from Postgres
        await self.postgres.execute(
            "DELETE FROM interview_sessions WHERE user_id = $1",
            user_id
        )
        
        logger.info(f"Deleted all data for user {user_id}")
```

### 4. API Security

```python
# Rate limiting
@app.post("/api/interview/start")
@limiter.limit("5 per minute")
async def start_interview(request: Request):
    pass

# Authentication required
@app.get("/api/interview/{session_id}/transcript")
async def get_transcript(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    # Verify user owns this session
    session = await get_session(session_id)
    if session.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    return await get_transcript_data(session_id)

# Input validation
class AnswerRequest(BaseModel):
    answer_text: str = Field(..., max_length=10000)
    question_number: int = Field(..., ge=1, le=100)
```


## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific behaviors and property-based tests for universal correctness properties.

**Unit Tests:**
- Specific examples and edge cases
- Integration points between components
- Error conditions and graceful degradation
- API endpoint contracts

**Property-Based Tests:**
- Universal properties across all inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Each test references design document property

### Unit Testing Focus Areas

#### 1. Onboarding Flow Tests

```python
def test_greeting_generation_with_name():
    """Test greeting includes user's first name."""
    manager = OnboardingManager(...)
    greeting = await manager.generate_greeting("Rahul")
    assert "Rahul" in greeting
    assert greeting.startswith("Hey Rahul")

def test_greeting_fallback_without_name():
    """Test greeting uses 'there' when name missing."""
    manager = OnboardingManager(...)
    greeting = await manager.generate_greeting(None)
    assert "there" in greeting

def test_time_of_day_morning():
    """Test morning greeting between 5:00-11:59."""
    with freeze_time("2024-01-01 09:00:00"):
        greeting = await manager.generate_greeting("Test")
        assert "Good morning" in greeting
```

#### 2. Question Progression Tests

```python
def test_progress_calculation():
    """Test progress percentage calculation."""
    engine = QuestionProgressionEngine(...)
    engine.current_index = 2
    engine.questions = [q1, q2, q3, q4, q5]
    
    progress = engine.get_progress()
    assert progress.current == 3
    assert progress.total == 5
    assert progress.percentage == 60.0
```


#### 3. Multi-Modal Analysis Tests

```python
def test_concurrent_analysis_execution():
    """Test all analyzers run concurrently."""
    analyzer = MultiModalAnalyzer(...)
    
    start = time.time()
    result = await analyzer.analyze_answer(audio, video, text)
    duration = time.time() - start
    
    # Should complete in ~2s, not 3s (sequential)
    assert duration < 2.5

def test_graceful_degradation_tone_failure():
    """Test system continues when tone analysis fails."""
    tone_analyzer = Mock(side_effect=Exception("API Error"))
    analyzer = MultiModalAnalyzer(tone_analyzer, pitch_analyzer, facial_analyzer)
    
    result = await analyzer.analyze_answer(audio, video, text)
    
    assert result.tone_result is None
    assert result.pitch_result is not None
    assert result.facial_result is not None
    assert result.overall_confidence is not None  # Calculated with partial data
```

#### 4. Database Storage Tests

```python
def test_transcript_entry_storage():
    """Test transcript entries stored with all required fields."""
    await storage.add_transcript_entry(
        session_id="test-123",
        entry={
            "speaker": "AI",
            "text": "Test question",
            "timestamp": 1234567890,
            "question_number": 1
        }
    )
    
    transcript = await storage.get_transcript("test-123")
    assert len(transcript.entries) == 1
    assert transcript.entries[0]["speaker"] == "AI"
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:

**Consolidations Made:**
1. Greeting, introduction, and readiness audio generation all follow the same TTS pattern → Combined into single TTS property
2. Time-of-day logic is a pure function → Single property covers all time ranges
3. Question audio presentation and follow-up audio presentation use same mechanism → Combined
4. All three analyzers (tone, pitch, facial) follow same result format pattern → Combined into analysis result property
5. Transcript storage and analysis storage follow same MongoDB pattern → Combined into storage property

**Redundancies Eliminated:**
- Multiple properties about audio generation timing (all use same TTS service)
- Multiple properties about database field presence (covered by schema validation)
- Multiple properties about state transitions (covered by state machine property)

### Property 1: Time-Based Greeting Selection

*For any* time of day (0-23 hours), the greeting generator should return exactly one of the four valid greetings: "Good morning" for 5:00-11:59, "Good afternoon" for 12:00-16:59, "Good evening" for 17:00-20:59, or "Hello" for all other times.

**Validates: Requirements 1.4**


### Property 2: Greeting Format Consistency

*For any* first name (including None/empty), the greeting message should follow the format "Hey [Name], nice to meet you. [TimeOfDay]." where [Name] is the first name or "there" if unavailable.

**Validates: Requirements 1.2, 1.3, 1.9**

### Property 3: TTS Audio Generation Performance

*For any* text input under 500 characters, TTS audio generation should complete within the specified time limit (1.5s for questions/greetings, 2s for introductions).

**Validates: Requirements 1.8, 2.7, 5.7**

### Property 4: Readiness Confirmation Interpretation

*For any* verbal response, the system should correctly classify it as affirmative (e.g., "yes", "ready", "let's go") or negative/uncertain (e.g., "wait", "not yet"), using Claude API for interpretation.

**Validates: Requirements 3.5, 3.6, 3.7**

### Property 5: Countdown Timer Precision

*For any* countdown execution, each number (5, 4, 3, 2, 1) should be displayed for exactly 1 second, resulting in a total duration of exactly 5 seconds.

**Validates: Requirements 4.2, 4.4, 4.9**

### Property 6: Question Progression Sequence

*For any* question set with N questions, progressing through all questions should visit each question exactly once in order (1, 2, 3, ..., N) without skipping or repeating.

**Validates: Requirements 6.1, 6.5, 6.9**

### Property 7: Progress Calculation Accuracy

*For any* current question number Q and total questions T, the progress percentage should equal (Q / T) * 100, and the display format should be "Question Q of T".

**Validates: Requirements 7.2, 7.7**


### Property 8: Follow-Up Question Limit

*For any* main question, the system should generate at most 2 follow-up questions, regardless of how many times the follow-up generator is invoked.

**Validates: Requirements 8.8**

### Property 9: Follow-Up Contextual Reference

*For any* generated follow-up question, the question text should reference at least one specific point from the candidate's answer to the main question.

**Validates: Requirements 8.5, 8.6**

### Property 10: Multi-Modal Analysis Concurrency

*For any* answer with audio and video streams, running tone, pitch, and facial analysis concurrently should complete in approximately max(tone_time, pitch_time, facial_time), not the sum of all three times.

**Validates: Requirements 13.2, 13.8**

### Property 11: Overall Confidence Weighting

*For any* set of analysis results with tone confidence T, pitch stability P, and facial engagement F (all in range 0.0-1.0), the overall confidence should equal (T * 0.40) + (P * 0.30) + (F * 0.30).

**Validates: Requirements 13.4**

### Property 12: Analysis Result Validity

*For any* completed analysis (tone, pitch, or facial), the result should contain all required fields with values in valid ranges: scores between 0.0-1.0, categories from predefined sets, and non-negative counts.

**Validates: Requirements 10.9, 11.9, 12.9**

### Property 13: Transcript Entry Ordering

*For any* interview session, retrieving the transcript should return entries in the exact chronological order they were added, preserving the sequence of all questions, answers, and follow-ups.

**Validates: Requirements 14.7**


### Property 14: Database Storage Completeness

*For any* analysis result, the stored MongoDB document should contain all required fields: session_id, question_id, answer_text, tone_data, pitch_data, facial_data, evaluation, and timestamp.

**Validates: Requirements 15.2, 15.3, 15.4, 15.5, 15.6**

### Property 15: Follow-Up Reasoning Storage

*For any* generated follow-up question, the stored record should include the reasoning field with a non-empty explanation of why the follow-up was asked.

**Validates: Requirements 16.2, 16.3, 16.4**

### Property 16: Session State Persistence Round-Trip

*For any* interview session state, saving the state to the database and then retrieving it should produce an equivalent state with the same current_question_number, completed_questions, and status.

**Validates: Requirements 18.1, 18.2, 18.5**

### Property 17: Performance Latency Bounds

*For any* answer completion, the total time from answer end to next question presentation should be less than 5 seconds, including analysis, follow-up generation, and question progression.

**Validates: Requirements 19.10**

### Property 18: Graceful Degradation Continuation

*For any* single analyzer failure (tone, pitch, or facial), the interview should continue without interruption, storing partial results and proceeding to the next question.

**Validates: Requirements 20.1, 20.2, 20.3**

### Property 19: Video Consent Enforcement

*For any* interview session, if video consent is denied, the facial analyzer should return a disabled result and no video data should be processed or stored.

**Validates: Requirements 21.2**


### Property 20: State Machine Transition Validity

*For any* state transition in the enhanced state machine, the transition should only occur between valid state pairs as defined in the state flow diagram (e.g., ONBOARDING → COUNTDOWN → ASKING_QUESTION).

**Validates: Requirements 23.2, 23.3**

### Property 21: API Endpoint Response Format

*For any* API endpoint call with valid authentication, the response should match the documented schema with all required fields present and correctly typed.

**Validates: Requirements 25.1-25.9**

### Property 22: TTS Audio Caching Round-Trip

*For any* text input, generating audio, caching it, and retrieving from cache should produce identical audio bytes.

**Validates: Requirements 5.8**

### Property 23: Concurrent Analysis Exception Handling

*For any* set of analysis tasks where one or more fail with exceptions, the `asyncio.gather(return_exceptions=True)` should return results for successful tasks and Exception objects for failed tasks, without raising an exception.

**Validates: Requirements 13.2, 20.1-20.3**

### Property 24: Data Encryption Round-Trip

*For any* audio or transcript data, encrypting and then decrypting should produce data identical to the original input.

**Validates: Requirements 21.3**

### Property 25: Batch Write Atomicity

*For any* batch of database writes, either all writes in the batch should succeed, or none should be applied (atomic batch operation).

**Validates: Requirements 14.1-14.10, 15.1-15.10**


## Implementation Roadmap

### Phase 1: Database Schema & Storage (Week 1)

**Vertical Slice: Schema → API → UI**

1. Create MongoDB collections (interview_transcripts, analysis_results, follow_up_questions)
2. Extend Postgres interview_sessions table
3. Create indexes for performance
4. Implement storage repository classes
5. Write unit tests for storage operations
6. Create API endpoints for data retrieval

**Deliverable:** Working storage layer with API endpoints

### Phase 2: Onboarding Flow (Week 2)

**Vertical Slice: Schema → API → UI**

1. Implement OnboardingManager class
2. Add greeting generation with time-of-day logic
3. Add introduction generation
4. Add readiness confirmation with Claude interpretation
5. Create onboarding API endpoints
6. Build frontend onboarding UI components
7. Integrate with TTS service

**Deliverable:** Complete onboarding flow from greeting to readiness

### Phase 3: Question Progression (Week 3)

**Vertical Slice: Schema → API → UI**

1. Implement QuestionProgressionEngine
2. Add question loading and sequencing
3. Add feedback generation
4. Add progress tracking
5. Create countdown timer component
6. Build question display UI
7. Integrate with existing VoiceFlowController

**Deliverable:** Working question progression with countdown and feedback


### Phase 4: Follow-Up Generation (Week 4)

**Vertical Slice: Schema → API → UI**

1. Implement FollowUpGenerator class
2. Add decision logic for follow-up necessity
3. Add contextual follow-up generation with Claude
4. Add reasoning generation
5. Store follow-ups in MongoDB
6. Create follow-up API endpoints
7. Build follow-up UI display

**Deliverable:** Intelligent follow-up questions with reasoning

### Phase 5: Multi-Modal Analysis - Tone & Pitch (Week 5)

**Vertical Slice: Schema → API → UI**

1. Implement ToneAnalyzer with Deepgram
2. Implement PitchAnalyzer with librosa
3. Add concurrent execution with asyncio.gather
4. Store analysis results in MongoDB
5. Create analysis API endpoints
6. Build analysis results display UI
7. Add graceful degradation for failures

**Deliverable:** Working tone and pitch analysis

### Phase 6: Multi-Modal Analysis - Facial (Week 6)

**Vertical Slice: Schema → API → UI**

1. Implement ConsentManager for video consent
2. Implement FacialExpressionAnalyzer with MediaPipe
3. Add facial analysis to concurrent execution
4. Implement MultiModalAnalyzer to combine results
5. Store combined results in MongoDB
6. Build facial analysis UI display
7. Add privacy controls

**Deliverable:** Complete multi-modal analysis with consent management


### Phase 7: Integration & Performance Optimization (Week 7)

**Vertical Slice: Integration → Testing → Optimization**

1. Integrate all components with EnhancedVoiceFlowController
2. Add TTS audio caching
3. Implement batch database writes
4. Add connection pooling optimization
5. Implement error handling and monitoring
6. Add session state persistence
7. Performance testing and optimization

**Deliverable:** Fully integrated system with optimizations

### Phase 8: Security, Privacy & Testing (Week 8)

**Vertical Slice: Security → Testing → Documentation**

1. Implement data encryption at rest
2. Add data retention policies
3. Implement GDPR compliance features
4. Add rate limiting and input validation
5. Write property-based tests for all properties
6. Write integration tests for complete flows
7. Security audit and penetration testing

**Deliverable:** Production-ready system with security and testing

## Deployment Considerations

### Environment Variables Required

```bash
# AI Services
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
DEEPGRAM_API_KEY=...

# Databases
MONGODB_URI=mongodb+srv://...
POSTGRES_URL=postgresql://...

# Encryption
DATA_ENCRYPTION_KEY=...

# Performance
REDIS_URL=redis://...
TTS_CACHE_TTL=86400

# Privacy
VIDEO_CONSENT_REQUIRED=true
DATA_RETENTION_DAYS=90
```


### Monitoring & Observability

```python
# Key metrics to monitor
METRICS = {
    "onboarding_duration": "histogram",
    "question_progression_latency": "histogram",
    "analysis_duration_tone": "histogram",
    "analysis_duration_pitch": "histogram",
    "analysis_duration_facial": "histogram",
    "analysis_failure_rate": "counter",
    "tts_cache_hit_rate": "gauge",
    "followup_generation_rate": "gauge",
    "video_consent_rate": "gauge",
    "interview_completion_rate": "gauge"
}

# Alerts to configure
ALERTS = {
    "analysis_failure_rate > 10%": "high",
    "question_progression_latency > 5s": "high",
    "tts_generation_failure": "critical",
    "database_connection_failure": "critical",
    "video_consent_rate < 50%": "low"
}
```

### Scaling Considerations

**Horizontal Scaling:**
- FastAPI servers: Scale to N instances behind load balancer
- WebSocket connections: Use Redis pub/sub for cross-server communication
- Analysis workers: Separate worker pool for CPU-intensive tasks

**Database Scaling:**
- MongoDB: Use replica sets for read scaling
- Postgres: Use read replicas for analytics queries
- Redis: Use Redis Cluster for cache distribution

**Cost Optimization:**
- TTS caching reduces ElevenLabs API costs by ~70%
- Batch database writes reduce connection overhead
- Concurrent analysis reduces total processing time by 3x


## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Multi-modal analysis latency exceeds 5s | High | Concurrent execution, caching, performance monitoring |
| TTS API rate limits | Medium | Audio caching, fallback to text-only |
| Video analysis accuracy issues | Medium | Explicit consent, graceful degradation, human review option |
| Database connection failures | High | Connection pooling, local caching, retry queues |
| Claude API costs escalate | Medium | Prompt optimization, response caching, usage monitoring |

### Privacy Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unauthorized video access | Critical | Explicit consent, encryption at rest, access controls |
| Data retention violations | High | Automated retention policies, audit logs |
| GDPR non-compliance | Critical | User data deletion API, consent management, privacy notices |
| Cross-user data leakage | Critical | Session-based access control, user ID validation |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| System downtime during interviews | High | Graceful degradation, local state caching, auto-resume |
| Analysis feature failures | Medium | Independent failure handling, partial results storage |
| Scaling bottlenecks | Medium | Horizontal scaling, load testing, capacity planning |
| Monitoring blind spots | Medium | Comprehensive metrics, alerting, log aggregation |


## Success Metrics

### User Experience Metrics

- **Onboarding Completion Rate**: >95% of users complete onboarding flow
- **Interview Completion Rate**: >90% of started interviews are completed
- **Average Interview Duration**: 15-25 minutes for 5 questions
- **User Satisfaction Score**: >4.5/5.0 for interview experience
- **Video Consent Rate**: >70% of users consent to video analysis

### Technical Performance Metrics

- **Onboarding Duration**: <15 seconds (greeting + introduction + readiness)
- **Question Progression Latency**: <5 seconds (answer → next question)
- **Analysis Completion Time**: <2 seconds (concurrent multi-modal)
- **TTS Cache Hit Rate**: >60% (reduces API costs)
- **System Uptime**: >99.5% availability

### Business Metrics

- **Follow-Up Quality Score**: >4.0/5.0 (human evaluation)
- **Analysis Accuracy**: >85% agreement with human evaluators
- **API Cost per Interview**: <$2.00 (TTS + Claude + Deepgram)
- **Database Storage per Interview**: <50MB (with 90-day retention)
- **Support Ticket Rate**: <5% of interviews require support

## Conclusion

This design provides a comprehensive blueprint for implementing the Enhanced Interview Experience feature. The architecture extends the existing VoiceFlowController while maintaining backward compatibility, adds intelligent onboarding and question progression, implements multi-modal analysis with graceful degradation, and ensures privacy and security through explicit consent and data encryption.

The vertical slice development approach (Schema → API → UI) ensures each component is fully functional before moving to the next, reducing integration risks. The concurrent execution of analysis components and TTS caching optimize performance to meet the <5s latency requirement.

Key design decisions:
- **Extend, don't replace**: Builds on existing VoiceFlowController
- **Graceful degradation**: System continues if analysis features fail
- **Privacy first**: Explicit consent, encryption, data retention
- **Performance optimized**: Concurrent execution, caching, connection pooling
- **Testable**: Clear properties for property-based testing

The 8-week implementation roadmap provides a realistic timeline for delivering this feature to production.
