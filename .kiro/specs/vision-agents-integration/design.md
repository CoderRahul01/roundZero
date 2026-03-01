# Design Document: Vision Agents Integration

## Overview

The Vision Agents Integration transforms RoundZero AI Interview Coach into a multimodal, real-time interview platform by integrating the Vision Agents library with Stream.io WebRTC infrastructure. This design enables live video interviews with real-time emotion detection, body language analysis, speech pattern monitoring, and intelligent AI-driven interview orchestration.

The system uses Gemini Flash-8B for emotion detection, Claude Sonnet 4 for interview decision-making, and integrates with existing RoundZero infrastructure (MongoDB, Pinecone, Supermemory, ElevenLabs, Deepgram) to provide a comprehensive, multimodal interview coaching experience.

### Key Design Principles

1. **Multimodal Analysis**: Combine video (emotion, body language), audio (speech patterns), and text (content) for comprehensive assessment
2. **Real-Time Processing**: Process video frames and audio streams in real-time with minimal latency
3. **Graceful Degradation**: System continues functioning even if individual services fail
4. **Cost Optimization**: Respect free tier limits (Gemini 1000 RPD) through intelligent sampling
5. **Privacy First**: Explicit consent, secure storage, data retention policies
6. **Async Throughout**: Non-blocking operations for maximum responsiveness

### Design Goals

- Enable live video interviews with AI agent
- Detect emotions and body language in real-time
- Track speech patterns (fillers, pace, pauses)
- Make intelligent intervention decisions based on multimodal context
- Maintain <2s decision latency from context to action
- Store complete session data for post-interview analysis
- Provide personalized coaching through Supermemory integration

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Stream SDK)                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │LiveInterviewScreen│  │ConfidenceMeter   │  │StatusBadge   │  │
│  │- Video Feed      │  │- Real-time Score │  │- AI State    │  │
│  │- Stream SDK      │  │- Color Gradient  │  │- Listening   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ WebRTC + WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend (FastAPI - Vision Agents)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              RoundZeroAgent (Main Orchestrator)          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │ Question   │  │ Decision   │  │ Context    │        │   │
│  │  │ Manager    │  │ Engine     │  │ Tracker    │        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Vision Agents Processors (Async)                 │   │
│  │  ┌────────────────┐         ┌────────────────┐          │   │
│  │  │EmotionProcessor│         │SpeechProcessor │          │   │
│  │  │- Frame Sampling│         │- Filler Words  │          │   │
│  │  │- Gemini Flash  │         │- Speech Pace   │          │   │
│  │  │- Confidence    │         │- Pause Detection│         │   │
│  │  └────────────────┘         └────────────────┘          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Stream.io   │   │   Gemini     │   │   Claude     │
│  WebRTC      │   │  Flash-8B    │   │  Sonnet 4    │
│              │   │              │   │              │
│ - Video Call │   │ - Emotion    │   │ - Decisions  │
│ - Audio      │   │ - Confidence │   │ - Summaries  │
│ - Streaming  │   │ - Body Lang  │   │ - Feedback   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Deepgram    │   │  ElevenLabs  │   │  Pinecone    │
│  STT         │   │  TTS         │   │  Questions   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  MongoDB     │   │ Supermemory  │   │  Upstash     │
│  Sessions    │   │  Candidate   │   │  Redis       │
│  Transcripts │   │  Memory      │   │  Cache       │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Data Flow Architecture

**Live Interview Session Flow:**

```
1. Frontend: User clicks "Start Live Interview"
   ↓
2. Backend: POST /api/interview/start-live-session
   ↓
3. Backend: Create Stream.io call with call_id
   ↓
4. Backend: Initialize RoundZeroAgent with session parameters
   ↓
5. Backend: Fetch questions from Pinecone (semantic search)
   ↓
6. Backend: Fetch candidate memory from Supermemory
   ↓
7. Backend: Return call_id and session_id to frontend
   ↓
8. Frontend: Initialize Stream React SDK with call_id
   ↓
9. Frontend: Join video call, display video feed
   ↓
10. Backend: AI greets candidate via ElevenLabs TTS
   ↓
11. Backend: AI asks first question via ElevenLabs TTS
   ↓
12. Candidate speaks → Deepgram STT → Transcript segments
   ↓
13. EmotionProcessor: Sample frames (every 10) → Gemini Flash-8B
   ↓
14. SpeechProcessor: Analyze transcript → Filler words, pace, pauses
   ↓
15. RoundZeroAgent: Accumulate 20+ words → Request decision
   ↓
16. DecisionEngine: Send context to Claude Sonnet 4
   ↓
17. Claude returns: CONTINUE | INTERRUPT | ENCOURAGE | NEXT | HINT
   ↓
18. If INTERRUPT/ENCOURAGE/HINT: Generate message → ElevenLabs TTS
   ↓
19. If NEXT: Evaluate answer → Store results → Next question
   ↓
20. Repeat steps 11-19 until all questions complete
   ↓
21. Backend: Generate session summary via Claude
   ↓
22. Backend: Write summary to Supermemory
   ↓
23. Backend: Store complete session data to MongoDB
   ↓
24. Frontend: Display session summary screen
```

### Technology Stack Integration

**Vision Agents Library:**
- Python library for multimodal AI agents
- Integrates with Stream.io WebRTC for video/audio
- Provides VideoProcessor and AudioProcessor base classes
- Handles frame sampling and audio streaming

**Stream.io WebRTC:**
- Video call infrastructure
- Peer-to-peer connections
- Audio/video streaming
- Connection quality management
- Automatic reconnection

**Gemini Flash-8B:**
- Lightweight multimodal model
- Emotion detection from video frames
- Confidence scoring
- Body language analysis
- Free tier: 1000 requests per day

**Claude Sonnet 4:**
- Advanced reasoning model
- Interview decision-making
- Context-aware interventions
- Session summary generation
- Feedback message creation

**Existing RoundZero Infrastructure:**
- MongoDB: Session storage, transcripts, emotion timeline
- Pinecone: Question retrieval via semantic search
- Supermemory: Candidate memory and session summaries
- Deepgram: Real-time speech-to-text
- ElevenLabs: Text-to-speech for AI voice
- Upstash Redis: Caching and rate limiting

## Components and Interfaces

### 1. EmotionProcessor (VideoProcessor)

**Purpose**: Process webcam frames to detect emotions, confidence levels, and body language using Gemini Flash-8B.

**Class Definition:**

```python
from vision_agents import VideoProcessor
from typing import Optional, Dict, Any
import asyncio
import time

class EmotionSnapshot:
    """Data class for emotion analysis results."""
    def __init__(
        self,
        emotion: str,
        confidence_score: int,
        engagement_level: str,
        body_language_observations: str,
        timestamp: float
    ):
        self.emotion = emotion
        self.confidence_score = confidence_score
        self.engagement_level = engagement_level
        self.body_language_observations = body_language_observations
        self.timestamp = timestamp

class EmotionProcessor(VideoProcessor):
    """
    Processes video frames for emotion detection using Gemini Flash-8B.
    Samples every 10 frames to respect rate limits.
    """
    
    def __init__(
        self,
        gemini_client,
        session_id: str,
        mongo_repository,
        frame_sample_rate: int = 10,
        rate_limit_threshold: int = 900
    ):
        super().__init__()
        self.gemini_client = gemini_client
        self.session_id = session_id
        self.mongo_repository = mongo_repository
        self.frame_sample_rate = frame_sample_rate
        self.rate_limit_threshold = rate_limit_threshold
        
        self.frame_count = 0
        self.emotion_snapshots = []
        self.daily_request_count = 0
        self.last_reset_time = time.time()
    
    async def process_frame(self, frame: bytes) -> Optional[EmotionSnapshot]:
        """
        Process video frame for emotion detection.
        Samples every Nth frame based on frame_sample_rate.
        """
        self.frame_count += 1
        
        # Sample every 10 frames (or adjusted rate)
        if self.frame_count % self.frame_sample_rate != 0:
            return None
        
        # Check rate limit
        if self.daily_request_count >= self.rate_limit_threshold:
            # Reduce sampling frequency
            self.frame_sample_rate = 20
            return None
        
        try:
            # Send frame to Gemini Flash-8B
            analysis = await self._analyze_with_gemini(frame)
            
            # Extract emotion data
            snapshot = EmotionSnapshot(
                emotion=analysis.get("emotion", "neutral"),
                confidence_score=analysis.get("confidence_score", 50),
                engagement_level=analysis.get("engagement_level", "medium"),
                body_language_observations=analysis.get("body_language", ""),
                timestamp=time.time()
            )
            
            # Store snapshot
            self.emotion_snapshots.append(snapshot)
            await self._store_snapshot(snapshot)
            
            self.daily_request_count += 1
            return snapshot
            
        except Exception as e:
            # Log error but continue processing
            print(f"Emotion processing error: {e}")
            return None
    
    async def _analyze_with_gemini(self, frame: bytes) -> Dict[str, Any]:
        """
        Send frame to Gemini Flash-8B for analysis.
        
        Prompt: "Analyze this person's emotional state. Provide:
        1. Emotion (confident/nervous/confused/neutral/enthusiastic)
        2. Confidence score (0-100)
        3. Engagement level (high/medium/low)
        4. Body language observations (brief text)
        
        Return as JSON."
        """
        prompt = """Analyze this person's emotional state during an interview. Provide:
        1. emotion: One of (confident, nervous, confused, neutral, enthusiastic)
        2. confidence_score: Integer from 0 to 100
        3. engagement_level: One of (high, medium, low)
        4. body_language: Brief observations about posture, gestures, facial expressions
        
        Return as JSON format."""
        
        response = await self.gemini_client.generate_content(
            model="gemini-1.5-flash-8b",
            contents=[
                {"mime_type": "image/jpeg", "data": frame},
                {"text": prompt}
            ]
        )
        
        # Parse JSON response
        import json
        result = json.loads(response.text)
        return result
    
    async def _store_snapshot(self, snapshot: EmotionSnapshot):
        """Store emotion snapshot to MongoDB."""
        await self.mongo_repository.add_emotion_snapshot(
            session_id=self.session_id,
            snapshot={
                "emotion": snapshot.emotion,
                "confidence_score": snapshot.confidence_score,
                "engagement_level": snapshot.engagement_level,
                "body_language_observations": snapshot.body_language_observations,
                "timestamp": snapshot.timestamp
            }
        )
    
    def get_latest_emotion(self) -> Optional[EmotionSnapshot]:
        """Get most recent emotion snapshot."""
        return self.emotion_snapshots[-1] if self.emotion_snapshots else None
    
    def get_average_confidence(self) -> float:
        """Calculate average confidence score across all snapshots."""
        if not self.emotion_snapshots:
            return 0.0
        return sum(s.confidence_score for s in self.emotion_snapshots) / len(self.emotion_snapshots)
    
    def reset_daily_counter(self):
        """Reset daily request counter (called at midnight UTC)."""
        current_time = time.time()
        if current_time - self.last_reset_time >= 86400:  # 24 hours
            self.daily_request_count = 0
            self.last_reset_time = current_time
            self.frame_sample_rate = 10  # Reset to normal sampling
```

**Integration Points:**
- Receives video frames from Stream.io WebRTC
- Sends frames to Gemini Flash-8B API
- Stores snapshots to MongoDB
- Provides emotion data to RoundZeroAgent for decision-making

**Performance Requirements:**
- Frame processing: <1s per sampled frame
- Sampling rate: Every 10 frames (adjustable based on rate limit)
- Memory usage: Minimal (no frame buffering)
- Rate limit handling: Automatic frequency adjustment

**Error Handling:**
- Gemini API failures: Log error, continue without emotion data
- Rate limit exceeded: Reduce sampling frequency to 20 frames
- Network errors: Retry with exponential backoff (3 attempts)

### 2. SpeechProcessor (AudioProcessor)

**Purpose**: Analyze speech patterns including filler words, speech pace, and pauses from Deepgram transcripts.

**Class Definition:**

```python
from vision_agents import AudioProcessor
from typing import List, Dict
import time
import re

class SpeechMetrics:
    """Data class for speech analysis results."""
    def __init__(
        self,
        filler_word_count: int,
        speech_pace: float,
        long_pause_count: int,
        average_filler_rate: float,
        rapid_speech: bool,
        slow_speech: bool
    ):
        self.filler_word_count = filler_word_count
        self.speech_pace = speech_pace
        self.long_pause_count = long_pause_count
        self.average_filler_rate = average_filler_rate
        self.rapid_speech = rapid_speech
        self.slow_speech = slow_speech

class SpeechProcessor(AudioProcessor):
    """
    Processes transcript segments to analyze speech patterns.
    Detects filler words, calculates pace, tracks pauses.
    """
    
    def __init__(self, session_id: str, mongo_repository):
        super().__init__()
        self.session_id = session_id
        self.mongo_repository = mongo_repository
        
        # Filler word patterns
        self.filler_patterns = [
            r'\bum\b', r'\buh\b', r'\blike\b', r'\bbasically\b',
            r'\byou know\b', r'\bsort of\b', r'\bkind of\b'
        ]
        
        # Current question metrics
        self.current_question_id = None
        self.filler_word_count = 0
        self.word_count = 0
        self.start_time = None
        self.last_speech_time = None
        self.long_pause_count = 0
    
    async def process_transcript_segment(
        self,
        text: str,
        is_final: bool,
        timestamp: float
    ) -> Optional[SpeechMetrics]:
        """
        Process transcript segment for speech pattern analysis.
        """
        if not is_final:
            return None
        
        # Initialize timing if first segment
        if self.start_time is None:
            self.start_time = timestamp
        
        # Detect long pauses (3+ seconds since last speech)
        if self.last_speech_time and (timestamp - self.last_speech_time) >= 3.0:
            self.long_pause_count += 1
        
        self.last_speech_time = timestamp
        
        # Count filler words
        fillers_in_segment = self._count_fillers(text)
        self.filler_word_count += fillers_in_segment
        
        # Count words
        words_in_segment = len(text.split())
        self.word_count += words_in_segment
        
        # Calculate speech pace (words per minute)
        elapsed_time = timestamp - self.start_time
        speech_pace = (self.word_count / elapsed_time) * 60 if elapsed_time > 0 else 0
        
        # Calculate average filler rate (fillers per 100 words)
        average_filler_rate = (self.filler_word_count / self.word_count) * 100 if self.word_count > 0 else 0
        
        # Detect rapid or slow speech
        rapid_speech = speech_pace > 180
        slow_speech = speech_pace < 100
        
        metrics = SpeechMetrics(
            filler_word_count=self.filler_word_count,
            speech_pace=speech_pace,
            long_pause_count=self.long_pause_count,
            average_filler_rate=average_filler_rate,
            rapid_speech=rapid_speech,
            slow_speech=slow_speech
        )
        
        return metrics
    
    def _count_fillers(self, text: str) -> int:
        """Count filler words in text using regex patterns."""
        count = 0
        text_lower = text.lower()
        for pattern in self.filler_patterns:
            matches = re.findall(pattern, text_lower)
            count += len(matches)
        return count
    
    async def reset_for_new_question(self, question_id: str):
        """Reset metrics for new question."""
        # Store previous question metrics if exists
        if self.current_question_id:
            await self._store_metrics()
        
        # Reset counters
        self.current_question_id = question_id
        self.filler_word_count = 0
        self.word_count = 0
        self.start_time = None
        self.last_speech_time = None
        self.long_pause_count = 0
    
    async def _store_metrics(self):
        """Store speech metrics to MongoDB."""
        if self.word_count == 0:
            return
        
        elapsed_time = self.last_speech_time - self.start_time if self.last_speech_time and self.start_time else 0
        speech_pace = (self.word_count / elapsed_time) * 60 if elapsed_time > 0 else 0
        average_filler_rate = (self.filler_word_count / self.word_count) * 100
        
        await self.mongo_repository.add_speech_metrics(
            session_id=self.session_id,
            question_id=self.current_question_id,
            metrics={
                "filler_word_count": self.filler_word_count,
                "speech_pace": speech_pace,
                "long_pause_count": self.long_pause_count,
                "average_filler_rate": average_filler_rate,
                "rapid_speech": speech_pace > 180,
                "slow_speech": speech_pace < 100
            }
        )
    
    def get_current_metrics(self) -> Dict:
        """Get current speech metrics for decision-making."""
        elapsed_time = self.last_speech_time - self.start_time if self.last_speech_time and self.start_time else 0
        speech_pace = (self.word_count / elapsed_time) * 60 if elapsed_time > 0 else 0
        average_filler_rate = (self.filler_word_count / self.word_count) * 100 if self.word_count > 0 else 0
        
        return {
            "filler_word_count": self.filler_word_count,
            "speech_pace": speech_pace,
            "long_pause_count": self.long_pause_count,
            "average_filler_rate": average_filler_rate
        }
```

**Integration Points:**
- Receives transcript segments from Deepgram STT
- Analyzes speech patterns in real-time
- Stores metrics to MongoDB per question
- Provides metrics to RoundZeroAgent for decision-making

**Performance Requirements:**
- Segment processing: <100ms per segment
- Real-time analysis during speech
- Minimal memory footprint

**Error Handling:**
- Invalid transcript segments: Skip and log
- Storage failures: Retry with exponential backoff


### 3. RoundZeroAgent (Main Orchestrator)

**Purpose**: Main Vision Agents agent that orchestrates the complete interview session, coordinating all processors and making decisions.

**Class Definition:**

```python
from vision_agents import Agent
from typing import Optional, List, Dict
import asyncio

class InterviewAction:
    """Enum for interview actions."""
    CONTINUE = "CONTINUE"
    INTERRUPT = "INTERRUPT"
    ENCOURAGE = "ENCOURAGE"
    NEXT = "NEXT"
    HINT = "HINT"

class RoundZeroAgent(Agent):
    """
    Main orchestrator for live interview sessions.
    Coordinates EmotionProcessor, SpeechProcessor, and DecisionEngine.
    """
    
    def __init__(
        self,
        session_id: str,
        candidate_id: str,
        role: str,
        topics: List[str],
        difficulty: str,
        mode: str,
        emotion_processor: EmotionProcessor,
        speech_processor: SpeechProcessor,
        decision_engine: 'DecisionEngine',
        question_manager: 'QuestionManager',
        tts_service,
        stt_service,
        mongo_repository,
        pinecone_client,
        supermemory_client
    ):
        super().__init__()
        self.session_id = session_id
        self.candidate_id = candidate_id
        self.role = role
        self.topics = topics
        self.difficulty = difficulty
        self.mode = mode
        
        # Processors
        self.emotion_processor = emotion_processor
        self.speech_processor = speech_processor
        self.decision_engine = decision_engine
        self.question_manager = question_manager
        
        # Services
        self.tts_service = tts_service
        self.stt_service = stt_service
        self.mongo_repository = mongo_repository
        self.pinecone_client = pinecone_client
        self.supermemory_client = supermemory_client
        
        # State
        self.questions = []
        self.current_question_index = 0
        self.transcript_buffer = ""
        self.word_count = 0
        self.candidate_memory = None
    
    async def initialize(self):
        """
        Initialize agent: fetch questions and candidate memory.
        """
        # Fetch questions from Pinecone
        self.questions = await self._fetch_questions_from_pinecone()
        
        # Fetch candidate memory from Supermemory
        self.candidate_memory = await self._fetch_candidate_memory()
        
        # Store session metadata
        await self.mongo_repository.create_session(
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            role=self.role,
            topics=self.topics,
            difficulty=self.difficulty,
            mode=self.mode,
            question_count=len(self.questions)
        )
    
    async def start_interview(self):
        """
        Start interview with greeting and first question.
        """
        # Generate and speak greeting
        greeting = await self._generate_greeting()
        await self._speak(greeting)
        
        # Ask first question
        await self._ask_question(0)
    
    async def handle_transcript_segment(self, text: str, is_final: bool):
        """
        Handle incoming transcript segment from Deepgram.
        """
        if is_final:
            self.transcript_buffer += " " + text
            self.word_count += len(text.split())
            
            # Process with SpeechProcessor
            await self.speech_processor.process_transcript_segment(
                text=text,
                is_final=is_final,
                timestamp=time.time()
            )
            
            # Check if we have enough content for decision
            if self.word_count >= 20:
                await self._request_decision()
    
    async def _request_decision(self):
        """
        Request decision from DecisionEngine based on current context.
        """
        # Get latest emotion data
        emotion_data = self.emotion_processor.get_latest_emotion()
        
        # Get current speech metrics
        speech_metrics = self.speech_processor.get_current_metrics()
        
        # Get current question
        current_question = self.questions[self.current_question_index]
        
        # Build context
        context = {
            "question_text": current_question["text"],
            "transcript_so_far": self.transcript_buffer,
            "emotion": emotion_data.emotion if emotion_data else "neutral",
            "confidence_score": emotion_data.confidence_score if emotion_data else 50,
            "engagement_level": emotion_data.engagement_level if emotion_data else "medium",
            "filler_word_count": speech_metrics["filler_word_count"],
            "speech_pace": speech_metrics["speech_pace"],
            "long_pause_count": speech_metrics["long_pause_count"]
        }
        
        # Request decision from Claude
        decision = await self.decision_engine.make_decision(context)
        
        # Execute action
        await self._execute_action(decision)
    
    async def _execute_action(self, decision: Dict):
        """
        Execute action based on decision from DecisionEngine.
        """
        action = decision["action"]
        message = decision.get("message", "")
        
        if action == InterviewAction.CONTINUE:
            # Continue listening, no interruption
            pass
        
        elif action == InterviewAction.INTERRUPT:
            # Generate and speak interruption message
            await self._speak(message)
            # Clear transcript buffer for fresh start
            self.transcript_buffer = ""
            self.word_count = 0
        
        elif action == InterviewAction.ENCOURAGE:
            # Generate and speak encouragement
            await self._speak(message)
        
        elif action == InterviewAction.HINT:
            # Generate and speak hint
            await self._speak(message)
        
        elif action == InterviewAction.NEXT:
            # Evaluate current answer and move to next question
            await self._evaluate_and_next()
    
    async def _evaluate_and_next(self):
        """
        Evaluate current answer and move to next question.
        """
        current_question = self.questions[self.current_question_index]
        
        # Evaluate answer with Claude
        evaluation = await self.decision_engine.evaluate_answer(
            question=current_question["text"],
            answer=self.transcript_buffer
        )
        
        # Store result
        await self.mongo_repository.store_question_result(
            session_id=self.session_id,
            question_id=current_question["id"],
            question_text=current_question["text"],
            answer=self.transcript_buffer,
            evaluation=evaluation
        )
        
        # Reset for next question
        self.transcript_buffer = ""
        self.word_count = 0
        await self.speech_processor.reset_for_new_question(
            question_id=current_question["id"]
        )
        
        # Move to next question
        self.current_question_index += 1
        
        if self.current_question_index < len(self.questions):
            await self._ask_question(self.current_question_index)
        else:
            await self._complete_interview()
    
    async def _ask_question(self, index: int):
        """
        Ask question at given index.
        """
        question = self.questions[index]
        await self._speak(question["text"])
    
    async def _speak(self, text: str):
        """
        Generate speech and play audio.
        """
        audio = await self.tts_service.synthesize_speech(text)
        # Play audio through Stream.io
        await self._play_audio(audio)
    
    async def _play_audio(self, audio_bytes: bytes):
        """
        Play audio through Stream.io call.
        """
        # Integration with Stream.io audio streaming
        pass
    
    async def _fetch_questions_from_pinecone(self) -> List[Dict]:
        """
        Fetch relevant questions from Pinecone using semantic search.
        """
        # Create query embedding from role and topics
        query_text = f"{self.role} {' '.join(self.topics)}"
        
        # Query Pinecone
        results = await self.question_manager.fetch_questions(
            query_text=query_text,
            difficulty=self.difficulty,
            limit=10
        )
        
        # Shuffle and select first 5
        import random
        random.shuffle(results)
        return results[:5]
    
    async def _fetch_candidate_memory(self) -> Optional[Dict]:
        """
        Fetch candidate memory from Supermemory.
        """
        try:
            memory = await self.supermemory_client.get_memory(
                key=f"candidate_{self.candidate_id}",
                limit=5  # Last 5 sessions
            )
            return memory
        except Exception as e:
            print(f"Failed to fetch candidate memory: {e}")
            return None
    
    async def _generate_greeting(self) -> str:
        """
        Generate personalized greeting.
        """
        greeting = f"Hello! Welcome to your {self.role} interview. "
        
        if self.candidate_memory:
            greeting += "I see you've practiced with us before. Let's build on that experience. "
        
        greeting += f"I'll be asking you {len(self.questions)} questions today. Let's begin!"
        return greeting
    
    async def _complete_interview(self):
        """
        Complete interview: generate summary and store to Supermemory.
        """
        # Generate session summary with Claude
        summary = await self._generate_session_summary()
        
        # Write to Supermemory
        await self.supermemory_client.write_memory(
            key=f"candidate_{self.candidate_id}",
            content=summary
        )
        
        # Store complete transcript
        await self.mongo_repository.finalize_session(
            session_id=self.session_id,
            summary=summary
        )
        
        # Thank candidate
        closing = "Great job! Your interview is complete. You'll receive detailed feedback shortly."
        await self._speak(closing)
    
    async def _generate_session_summary(self) -> str:
        """
        Generate comprehensive session summary using Claude.
        """
        # Gather all data
        emotion_timeline = self.emotion_processor.emotion_snapshots
        avg_confidence = self.emotion_processor.get_average_confidence()
        
        # Build summary prompt
        prompt = f"""Generate a comprehensive interview session summary:

Role: {self.role}
Topics: {', '.join(self.topics)}
Difficulty: {self.difficulty}

Average Confidence: {avg_confidence}/100

Include:
1. Overall performance assessment
2. Key strengths demonstrated
3. Areas for improvement
4. Communication style observations
5. Emotion patterns observed
6. Speech pattern observations
7. Specific recommendations for next session

Keep it constructive and encouraging."""
        
        summary = await self.decision_engine.generate_summary(prompt)
        return summary
```

**Integration Points:**
- Coordinates EmotionProcessor and SpeechProcessor
- Uses DecisionEngine for Claude API calls
- Integrates with Pinecone for question retrieval
- Integrates with Supermemory for candidate memory
- Uses ElevenLabs TTS for speech generation
- Uses Deepgram STT for transcription
- Stores all data to MongoDB

**Performance Requirements:**
- Decision latency: <2s from context to action
- Question transition: <3s from answer completion to next question
- Memory usage: Efficient buffering of transcript and emotion data

### 4. DecisionEngine (Claude Integration)

**Purpose**: Interface with Claude Sonnet 4 for intelligent decision-making based on multimodal context.

**Class Definition:**

```python
from anthropic import AsyncAnthropic
from typing import Dict, Optional
import json

class DecisionEngine:
    """
    Makes intelligent interview decisions using Claude Sonnet 4.
    Analyzes multimodal context and returns structured actions.
    """
    
    def __init__(self, claude_api_key: str):
        self.client = AsyncAnthropic(api_key=claude_api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def make_decision(self, context: Dict) -> Dict:
        """
        Make decision based on multimodal context.
        
        Returns:
            {
                "action": "CONTINUE" | "INTERRUPT" | "ENCOURAGE" | "NEXT" | "HINT",
                "message": "Optional message text",
                "reasoning": "Brief explanation"
            }
        """
        prompt = self._build_decision_prompt(context)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse structured response
            decision = self._parse_decision_response(response.content[0].text)
            return decision
            
        except Exception as e:
            print(f"Claude API error: {e}")
            # Fallback to rule-based decision
            return self._fallback_decision(context)
    
    def _build_decision_prompt(self, context: Dict) -> str:
        """
        Build prompt for Claude with multimodal context.
        """
        prompt = f"""You are an AI interview coach. Analyze the candidate's response and decide the next action.

QUESTION: {context['question_text']}

CANDIDATE'S ANSWER SO FAR: {context['transcript_so_far']}

MULTIMODAL CONTEXT:
- Emotion: {context['emotion']}
- Confidence Score: {context['confidence_score']}/100
- Engagement Level: {context['engagement_level']}
- Filler Words: {context['filler_word_count']}
- Speech Pace: {context['speech_pace']} words/minute
- Long Pauses: {context['long_pause_count']}

ACTIONS:
- CONTINUE: Let them keep talking (answer is on track)
- INTERRUPT: Redirect if off-topic or rambling
- ENCOURAGE: Provide encouragement if nervous/struggling
- NEXT: Move to next question (answer is complete)
- HINT: Provide subtle hint if stuck

Return JSON:
{{
    "action": "ACTION_NAME",
    "message": "Message to speak (if needed)",
    "reasoning": "Brief explanation"
}}"""
        return prompt
    
    def _parse_decision_response(self, response_text: str) -> Dict:
        """
        Parse Claude's JSON response.
        """
        try:
            decision = json.loads(response_text)
            
            # Validate action
            valid_actions = ["CONTINUE", "INTERRUPT", "ENCOURAGE", "NEXT", "HINT"]
            if decision.get("action") not in valid_actions:
                decision["action"] = "CONTINUE"
            
            return decision
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "action": "CONTINUE",
                "message": "",
                "reasoning": "Failed to parse response"
            }
    
    def _fallback_decision(self, context: Dict) -> Dict:
        """
        Rule-based fallback when Claude API fails.
        """
        # Simple rules based on context
        if context['filler_word_count'] > 10:
            return {
                "action": "ENCOURAGE",
                "message": "Take your time. You're doing great.",
                "reasoning": "High filler word count"
            }
        
        if context['confidence_score'] < 30:
            return {
                "action": "ENCOURAGE",
                "message": "You've got this. Take a deep breath.",
                "reasoning": "Low confidence"
            }
        
        if context['long_pause_count'] > 3:
            return {
                "action": "HINT",
                "message": "Think about the key concepts we discussed.",
                "reasoning": "Multiple long pauses"
            }
        
        # Default: continue listening
        return {
            "action": "CONTINUE",
            "message": "",
            "reasoning": "No intervention needed"
        }
    
    async def evaluate_answer(self, question: str, answer: str) -> Dict:
        """
        Evaluate final answer quality.
        
        Returns:
            {
                "relevance_score": 0-100,
                "completeness_score": 0-100,
                "correctness_score": 0-100,
                "feedback": "Detailed feedback text"
            }
        """
        prompt = f"""Evaluate this interview answer:

QUESTION: {question}

ANSWER: {answer}

Provide:
1. Relevance Score (0-100): How well does it address the question?
2. Completeness Score (0-100): Is the answer thorough?
3. Correctness Score (0-100): Is the information accurate?
4. Feedback: 2-3 sentences of constructive feedback

Return as JSON:
{{
    "relevance_score": 85,
    "completeness_score": 75,
    "correctness_score": 90,
    "feedback": "Your feedback here"
}}"""
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            evaluation = json.loads(response.content[0].text)
            return evaluation
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            return {
                "relevance_score": 50,
                "completeness_score": 50,
                "correctness_score": 50,
                "feedback": "Unable to evaluate at this time."
            }
    
    async def generate_summary(self, prompt: str) -> str:
        """
        Generate session summary.
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return "Session completed successfully. Detailed feedback will be available shortly."
```

**Integration Points:**
- Called by RoundZeroAgent for decision-making
- Uses Claude Sonnet 4 API
- Provides structured JSON responses
- Includes fallback logic for API failures

**Performance Requirements:**
- Decision latency: <1.5s per request
- Evaluation latency: <2s per answer
- Summary generation: <3s

### 5. QuestionManager (Pinecone Integration)

**Purpose**: Fetch relevant interview questions from Pinecone using semantic search.

**Class Definition:**

```python
from typing import List, Dict
import asyncio

class QuestionManager:
    """
    Manages question retrieval from Pinecone.
    Uses semantic search to find relevant questions.
    """
    
    def __init__(
        self,
        pinecone_client,
        gemini_embedding_service,
        mongo_repository
    ):
        self.pinecone_client = pinecone_client
        self.gemini_embedding_service = gemini_embedding_service
        self.mongo_repository = mongo_repository
        self.index_name = "interview-questions"
    
    async def fetch_questions(
        self,
        query_text: str,
        difficulty: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Fetch questions using semantic search.
        
        Args:
            query_text: Text to search for (e.g., "Software Engineer Python")
            difficulty: Filter by difficulty (easy/medium/hard)
            limit: Number of questions to retrieve
        
        Returns:
            List of question dictionaries
        """
        try:
            # Generate embedding for query
            query_embedding = await self.gemini_embedding_service.generate_embedding(
                text=query_text
            )
            
            # Query Pinecone
            results = await self._query_pinecone(
                embedding=query_embedding,
                difficulty=difficulty,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            print(f"Pinecone query error: {e}")
            # Fallback to MongoDB default questions
            return await self._fetch_default_questions(difficulty, limit)
    
    async def _query_pinecone(
        self,
        embedding: List[float],
        difficulty: str,
        limit: int
    ) -> List[Dict]:
        """
        Query Pinecone index with embedding.
        """
        index = self.pinecone_client.Index(self.index_name)
        
        results = await index.query(
            vector=embedding,
            filter={"difficulty": difficulty},
            top_k=limit,
            include_metadata=True
        )
        
        # Extract questions from results
        questions = []
        for match in results.matches:
            questions.append({
                "id": match.id,
                "text": match.metadata.get("question_text", ""),
                "difficulty": match.metadata.get("difficulty", "medium"),
                "topics": match.metadata.get("topics", []),
                "score": match.score
            })
        
        return questions
    
    async def _fetch_default_questions(
        self,
        difficulty: str,
        limit: int
    ) -> List[Dict]:
        """
        Fallback: fetch default questions from MongoDB.
        """
        questions = await self.mongo_repository.get_questions_by_difficulty(
            difficulty=difficulty,
            limit=limit
        )
        return questions
```

**Integration Points:**
- Used by RoundZeroAgent during initialization
- Queries Pinecone for semantic search
- Uses Gemini embedding service
- Falls back to MongoDB on failure

## Data Models

### MongoDB Schema

#### 1. live_sessions Collection

```javascript
{
  _id: ObjectId,
  session_id: String,  // UUID, indexed
  candidate_id: String,  // indexed
  call_id: String,  // Stream.io call ID
  
  // Session parameters
  role: String,
  topics: [String],
  difficulty: String,  // easy, medium, hard
  mode: String,  // practice, mock, coaching
  
  // Timestamps
  started_at: ISODate,
  ended_at: ISODate,
  
  // Transcript
  transcript: [
    {
      speaker: String,  // "user" or "agent"
      text: String,
      timestamp: Number,
      is_final: Boolean
    }
  ],
  
  // Emotion timeline
  emotion_timeline: [
    {
      timestamp: Number,
      emotion: String,  // confident, nervous, confused, neutral, enthusiastic
      confidence_score: Number,  // 0-100
      engagement_level: String,  // high, medium, low
      body_language_observations: String
    }
  ],
  
  // Speech metrics per question
  speech_metrics: {
    "question_1": {
      filler_word_count: Number,
      speech_pace: Number,  // words per minute
      long_pause_count: Number,
      average_filler_rate: Number,  // fillers per 100 words
      rapid_speech: Boolean,
      slow_speech: Boolean
    }
  },
  
  // Decisions made during interview
  decisions: [
    {
      timestamp: Number,
      action: String,  // CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT
      context: {
        question_text: String,
        transcript_so_far: String,
        emotion: String,
        confidence_score: Number,
        engagement_level: String,
        filler_word_count: Number,
        speech_pace: Number,
        long_pause_count: Number
      },
      message: String  // Optional
    }
  ],
  
  // Session summary
  session_summary: String,
  
  // Metadata
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
- `session_id` (unique)
- `candidate_id, started_at` (compound, for user history)
- `started_at` (for time-based queries)

#### 2. question_results Collection

```javascript
{
  _id: ObjectId,
  session_id: String,  // indexed
  question_id: String,
  question_text: String,
  answer_text: String,
  
  // Evaluation scores
  relevance_score: Number,  // 0-100
  completeness_score: Number,  // 0-100
  correctness_score: Number,  // 0-100
  feedback: String,
  
  // Context at time of answer
  emotion_at_answer: String,
  confidence_at_answer: Number,
  filler_count: Number,
  speech_pace: Number,
  
  timestamp: ISODate,
  created_at: ISODate
}
```

**Indexes:**
- `session_id, timestamp` (compound)
- `session_id` (for retrieval)

### Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EmotionSnapshot(BaseModel):
    timestamp: float
    emotion: str  # confident, nervous, confused, neutral, enthusiastic
    confidence_score: int = Field(ge=0, le=100)
    engagement_level: str  # high, medium, low
    body_language_observations: str

class SpeechMetrics(BaseModel):
    filler_word_count: int
    speech_pace: float
    long_pause_count: int
    average_filler_rate: float
    rapid_speech: bool
    slow_speech: bool

class TranscriptSegment(BaseModel):
    speaker: str  # "user" or "agent"
    text: str
    timestamp: float
    is_final: bool

class DecisionRecord(BaseModel):
    timestamp: float
    action: str  # CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT
    context: dict
    message: Optional[str] = None

class LiveSession(BaseModel):
    session_id: str
    candidate_id: str
    call_id: str
    role: str
    topics: List[str]
    difficulty: str
    mode: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    transcript: List[TranscriptSegment] = []
    emotion_timeline: List[EmotionSnapshot] = []
    speech_metrics: dict = {}
    decisions: List[DecisionRecord] = []
    session_summary: Optional[str] = None

class QuestionResult(BaseModel):
    session_id: str
    question_id: str
    question_text: str
    answer_text: str
    relevance_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    correctness_score: int = Field(ge=0, le=100)
    feedback: str
    emotion_at_answer: str
    confidence_at_answer: int
    filler_count: int
    speech_pace: float
    timestamp: datetime
```


## API Design

### REST Endpoints

#### POST /api/interview/start-live-session

Start a new live interview session with video call.

**Authentication**: Required (JWT token)

**Request Body:**
```json
{
  "role": "Software Engineer",
  "topics": ["Python", "System Design", "Algorithms"],
  "difficulty": "medium",
  "mode": "practice"
}
```

**Response (200 OK):**
```json
{
  "session_id": "uuid-string",
  "call_id": "stream-call-id",
  "stream_token": "jwt-token-for-stream",
  "status": "initialized",
  "question_count": 5
}
```

**Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Maximum 10 live sessions per day reached",
  "retry_after": 3600
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Session creation failed",
  "message": "Unable to initialize interview session"
}
```

**Implementation:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/interview", tags=["interview"])

class StartLiveSessionRequest(BaseModel):
    role: str
    topics: List[str]
    difficulty: str  # easy, medium, hard
    mode: str  # practice, mock, coaching

class StartLiveSessionResponse(BaseModel):
    session_id: str
    call_id: str
    stream_token: str
    status: str
    question_count: int

@router.post("/start-live-session", response_model=StartLiveSessionResponse)
async def start_live_session(
    request: StartLiveSessionRequest,
    candidate_id: str = Depends(get_current_user_id),
    rate_limiter = Depends(get_rate_limiter),
    stream_client = Depends(get_stream_client),
    mongo_repo = Depends(get_mongo_repository)
):
    """
    Start a new live interview session.
    
    1. Validate authentication
    2. Check rate limit (10 sessions per day)
    3. Create Stream.io call
    4. Initialize RoundZeroAgent
    5. Store session metadata
    6. Return call_id and session_id
    """
    # Check rate limit
    session_count_today = await rate_limiter.get_session_count_today(candidate_id)
    if session_count_today >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum 10 live sessions per day reached"
        )
    
    # Validate request
    if not request.role or not request.topics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role and topics are required"
        )
    
    if request.difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Difficulty must be easy, medium, or hard"
        )
    
    if request.mode not in ["practice", "mock", "coaching"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be practice, mock, or coaching"
        )
    
    try:
        # Create Stream.io call
        call = await stream_client.create_call(
            call_type="interview",
            call_id=f"interview_{uuid.uuid4()}"
        )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Initialize RoundZeroAgent
        agent = await initialize_agent(
            session_id=session_id,
            candidate_id=candidate_id,
            role=request.role,
            topics=request.topics,
            difficulty=request.difficulty,
            mode=request.mode,
            call_id=call.id
        )
        
        # Store session metadata
        await mongo_repo.create_session(
            session_id=session_id,
            candidate_id=candidate_id,
            call_id=call.id,
            role=request.role,
            topics=request.topics,
            difficulty=request.difficulty,
            mode=request.mode
        )
        
        # Generate Stream token for frontend
        stream_token = stream_client.create_token(candidate_id)
        
        return StartLiveSessionResponse(
            session_id=session_id,
            call_id=call.id,
            stream_token=stream_token,
            status="initialized",
            question_count=5
        )
        
    except Exception as e:
        logger.error(f"Failed to start live session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to initialize interview session"
        )
```

#### DELETE /api/interview/{session_id}/end-live-session

End a live interview session.

**Authentication**: Required (JWT token)

**Response (200 OK):**
```json
{
  "session_id": "uuid-string",
  "status": "completed",
  "summary_available": true
}
```

**Implementation:**
```python
@router.delete("/{session_id}/end-live-session")
async def end_live_session(
    session_id: str,
    candidate_id: str = Depends(get_current_user_id),
    agent_manager = Depends(get_agent_manager),
    mongo_repo = Depends(get_mongo_repository)
):
    """
    End live interview session.
    
    1. Validate session ownership
    2. Complete interview (generate summary)
    3. Store final data
    4. Cleanup resources
    """
    # Get agent for session
    agent = await agent_manager.get_agent(session_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if agent.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this session"
        )
    
    # Complete interview
    await agent._complete_interview()
    
    # Cleanup
    await agent_manager.remove_agent(session_id)
    
    return {
        "session_id": session_id,
        "status": "completed",
        "summary_available": True
    }
```

#### GET /api/interview/{session_id}/live-state

Get current state of live interview session.

**Authentication**: Required (JWT token)

**Response (200 OK):**
```json
{
  "session_id": "uuid-string",
  "status": "in_progress",
  "current_question_index": 2,
  "total_questions": 5,
  "latest_emotion": {
    "emotion": "confident",
    "confidence_score": 75,
    "engagement_level": "high"
  },
  "speech_metrics": {
    "filler_word_count": 3,
    "speech_pace": 145.5,
    "long_pause_count": 1
  }
}
```

**Implementation:**
```python
@router.get("/{session_id}/live-state")
async def get_live_state(
    session_id: str,
    candidate_id: str = Depends(get_current_user_id),
    agent_manager = Depends(get_agent_manager)
):
    """
    Get current state of live interview.
    Used by frontend for real-time updates.
    """
    agent = await agent_manager.get_agent(session_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if agent.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Get latest emotion
    latest_emotion = agent.emotion_processor.get_latest_emotion()
    
    # Get current speech metrics
    speech_metrics = agent.speech_processor.get_current_metrics()
    
    return {
        "session_id": session_id,
        "status": "in_progress",
        "current_question_index": agent.current_question_index,
        "total_questions": len(agent.questions),
        "latest_emotion": {
            "emotion": latest_emotion.emotion if latest_emotion else "neutral",
            "confidence_score": latest_emotion.confidence_score if latest_emotion else 50,
            "engagement_level": latest_emotion.engagement_level if latest_emotion else "medium"
        },
        "speech_metrics": speech_metrics
    }
```

#### GET /api/admin/usage-stats

Get API usage statistics for cost monitoring.

**Authentication**: Required (Admin role)

**Response (200 OK):**
```json
{
  "date": "2024-01-15",
  "gemini_calls_today": 450,
  "gemini_limit": 1000,
  "claude_tokens_today": 125000,
  "deepgram_minutes_today": 45.5,
  "elevenlabs_characters_today": 8500,
  "active_sessions": 3,
  "total_sessions_today": 12
}
```

**Implementation:**
```python
@router.get("/admin/usage-stats")
async def get_usage_stats(
    admin_user = Depends(require_admin),
    usage_tracker = Depends(get_usage_tracker)
):
    """
    Get API usage statistics for monitoring.
    Admin only endpoint.
    """
    stats = await usage_tracker.get_daily_stats()
    
    return {
        "date": stats["date"],
        "gemini_calls_today": stats["gemini_calls"],
        "gemini_limit": 1000,
        "claude_tokens_today": stats["claude_tokens"],
        "deepgram_minutes_today": stats["deepgram_minutes"],
        "elevenlabs_characters_today": stats["elevenlabs_characters"],
        "active_sessions": stats["active_sessions"],
        "total_sessions_today": stats["total_sessions"]
    }
```

#### GET /api/admin/metrics

Get system performance metrics.

**Authentication**: Required (Admin role)

**Response (200 OK):**
```json
{
  "active_sessions_count": 3,
  "total_sessions_today": 12,
  "average_session_duration": 1245.5,
  "error_rate_last_hour": 0.02,
  "api_latency_p50": 450,
  "api_latency_p95": 1200,
  "api_latency_p99": 2500
}
```

#### GET /api/health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "services": {
    "mongodb": "operational",
    "stream": "operational",
    "gemini": "operational",
    "claude": "operational",
    "deepgram": "operational",
    "elevenlabs": "operational",
    "pinecone": "operational",
    "supermemory": "operational"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Implementation:**
```python
@router.get("/health")
async def health_check(
    service_checker = Depends(get_service_checker)
):
    """
    Health check endpoint.
    Tests connectivity to all external services.
    """
    services = await service_checker.check_all_services()
    
    # Determine overall status
    all_operational = all(s["status"] == "operational" for s in services.values())
    some_degraded = any(s["status"] == "degraded" for s in services.values())
    
    if all_operational:
        overall_status = "healthy"
    elif some_degraded:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### WebSocket Events

#### Client → Server Events

**audio_chunk**: Stream audio data
```json
{
  "type": "audio_chunk",
  "session_id": "uuid",
  "data": "base64_audio_data",
  "timestamp": 1234567890
}
```

**video_frame**: Stream video frame (handled by Stream.io)
```json
{
  "type": "video_frame",
  "session_id": "uuid",
  "data": "base64_frame_data",
  "timestamp": 1234567890
}
```

#### Server → Client Events

**state_change**: Notify state changes
```json
{
  "type": "state_change",
  "session_id": "uuid",
  "state": "listening",
  "timestamp": 1234567890
}
```

**confidence_update**: Real-time confidence score
```json
{
  "type": "confidence_update",
  "session_id": "uuid",
  "confidence_score": 75,
  "emotion": "confident",
  "timestamp": 1234567890
}
```

**ai_speaking**: AI is speaking
```json
{
  "type": "ai_speaking",
  "session_id": "uuid",
  "text": "Great answer! Let's move to the next question.",
  "audio_url": "https://...",
  "timestamp": 1234567890
}
```

**question_asked**: New question presented
```json
{
  "type": "question_asked",
  "session_id": "uuid",
  "question_number": 2,
  "total_questions": 5,
  "question_text": "Explain the difference between...",
  "timestamp": 1234567890
}
```

**interview_complete**: Interview finished
```json
{
  "type": "interview_complete",
  "session_id": "uuid",
  "summary_available": true,
  "timestamp": 1234567890
}
```

## Frontend Integration

### LiveInterviewScreen Component

**Purpose**: Main component for live video interview with AI agent.

**Component Structure:**

```typescript
import React, { useEffect, useState } from 'react';
import { StreamVideoClient, Call } from '@stream-io/video-react-sdk';

interface LiveInterviewScreenProps {
  sessionId: string;
  callId: string;
  streamToken: string;
}

export const LiveInterviewScreen: React.FC<LiveInterviewScreenProps> = ({
  sessionId,
  callId,
  streamToken
}) => {
  const [client, setClient] = useState<StreamVideoClient | null>(null);
  const [call, setCall] = useState<Call | null>(null);
  const [aiState, setAiState] = useState<string>('idle');
  const [confidenceScore, setConfidenceScore] = useState<number>(50);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [questionNumber, setQuestionNumber] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(5);

  useEffect(() => {
    initializeStream();
    setupWebSocket();
    
    return () => {
      cleanup();
    };
  }, []);

  const initializeStream = async () => {
    // Initialize Stream Video Client
    const videoClient = new StreamVideoClient({
      apiKey: process.env.REACT_APP_STREAM_API_KEY!,
      token: streamToken,
      user: {
        id: 'candidate-id',
        name: 'Candidate'
      }
    });

    setClient(videoClient);

    // Join call
    const videoCall = videoClient.call('interview', callId);
    await videoCall.join();
    
    setCall(videoCall);
  };

  const setupWebSocket = () => {
    const ws = new WebSocket(`ws://localhost:8000/ws/interview/${sessionId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'state_change':
          setAiState(data.state);
          break;
        
        case 'confidence_update':
          setConfidenceScore(data.confidence_score);
          break;
        
        case 'question_asked':
          setCurrentQuestion(data.question_text);
          setQuestionNumber(data.question_number);
          setTotalQuestions(data.total_questions);
          break;
        
        case 'interview_complete':
          handleInterviewComplete();
          break;
      }
    };
  };

  const handleEndSession = async () => {
    await fetch(`/api/interview/${sessionId}/end-live-session`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    // Leave call
    await call?.leave();
    
    // Navigate to summary
    navigate(`/interview/summary/${sessionId}`);
  };

  const cleanup = async () => {
    await call?.leave();
    await client?.disconnectUser();
  };

  return (
    <div className="live-interview-container">
      <div className="video-section">
        <div className="candidate-video">
          {/* Stream Video Component */}
          <StreamVideo call={call} />
        </div>
        
        <div className="ai-status-badge">
          <StatusBadge state={aiState} />
        </div>
      </div>
      
      <div className="info-section">
        <div className="question-display">
          <h3>Question {questionNumber} of {totalQuestions}</h3>
          <p>{currentQuestion}</p>
        </div>
        
        <div className="confidence-meter">
          <ConfidenceMeter score={confidenceScore} />
        </div>
        
        <button onClick={handleEndSession} className="end-session-btn">
          End Interview
        </button>
      </div>
    </div>
  );
};
```

### ConfidenceMeter Component

```typescript
interface ConfidenceMeterProps {
  score: number;  // 0-100
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({ score }) => {
  const getColor = (score: number): string => {
    if (score >= 71) return '#10b981';  // green
    if (score >= 41) return '#f59e0b';  // yellow
    return '#ef4444';  // red
  };

  return (
    <div className="confidence-meter">
      <div className="meter-label">Confidence</div>
      <div className="meter-bar">
        <div 
          className="meter-fill"
          style={{
            width: `${score}%`,
            backgroundColor: getColor(score)
          }}
        />
      </div>
      <div className="meter-value">{score}/100</div>
    </div>
  );
};
```

### StatusBadge Component

```typescript
interface StatusBadgeProps {
  state: string;  // listening, thinking, speaking, idle
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state }) => {
  const getStateInfo = (state: string) => {
    switch (state) {
      case 'listening':
        return { text: 'Listening...', color: '#3b82f6', icon: '🎤' };
      case 'thinking':
        return { text: 'Thinking...', color: '#8b5cf6', icon: '🤔' };
      case 'speaking':
        return { text: 'Speaking...', color: '#10b981', icon: '🗣️' };
      default:
        return { text: 'Ready', color: '#6b7280', icon: '⏸️' };
    }
  };

  const info = getStateInfo(state);

  return (
    <div 
      className="status-badge"
      style={{ backgroundColor: info.color }}
    >
      <span className="status-icon">{info.icon}</span>
      <span className="status-text">{info.text}</span>
    </div>
  );
};
```

## Error Handling and Resilience

### Graceful Degradation Strategy

**Principle**: System continues functioning even when individual services fail.

**Service Failure Handling:**

1. **Gemini API Failure** (Emotion Detection)
   - Continue interview without emotion data
   - Use neutral emotion values (50 confidence, medium engagement)
   - Log failure for monitoring
   - Decision engine uses only speech and text data

2. **Claude API Failure** (Decision Making)
   - Fall back to rule-based decision logic
   - Simple rules based on filler count, pauses, confidence
   - Continue interview with reduced intelligence
   - Log failure and alert admin

3. **Deepgram Failure** (Speech-to-Text)
   - Attempt reconnection (3 attempts with exponential backoff)
   - If reconnection fails, end session gracefully
   - Save partial data
   - Notify candidate of technical issue

4. **ElevenLabs Failure** (Text-to-Speech)
   - Switch to text-only mode
   - Display AI messages as text on screen
   - Continue interview without voice
   - Log failure

5. **Pinecone Failure** (Question Retrieval)
   - Fall back to default questions from MongoDB
   - Use pre-selected question sets
   - Continue interview with fallback questions

6. **Supermemory Failure** (Candidate Memory)
   - Proceed without personalization
   - Skip memory context in prompts
   - Continue interview normally
   - Store summary to MongoDB only

7. **MongoDB Write Failure** (Data Storage)
   - Retry 3 times with exponential backoff
   - If all retries fail, store data in memory
   - Attempt batch write at session end
   - Alert admin of storage issue

8. **Stream.io Connection Drop** (Video Call)
   - Attempt automatic reconnection for 30 seconds
   - Display reconnection UI to candidate
   - If reconnection succeeds, resume interview
   - If reconnection fails, end session and save partial data

### Error Recovery Implementation

```python
class ErrorHandler:
    """
    Centralized error handling for Vision Agents integration.
    """
    
    def __init__(self, logger, alert_service):
        self.logger = logger
        self.alert_service = alert_service
        self.error_counts = {}
    
    async def handle_gemini_error(self, error: Exception, context: dict):
        """Handle Gemini API errors."""
        self.logger.error(f"Gemini API error: {error}", extra=context)
        
        # Increment error count
        self.error_counts['gemini'] = self.error_counts.get('gemini', 0) + 1
        
        # Alert if error rate is high
        if self.error_counts['gemini'] > 10:
            await self.alert_service.send_alert(
                "High Gemini API error rate",
                f"Gemini errors: {self.error_counts['gemini']}"
            )
        
        # Return neutral emotion data
        return {
            "emotion": "neutral",
            "confidence_score": 50,
            "engagement_level": "medium",
            "body_language_observations": "Unable to analyze"
        }
    
    async def handle_claude_error(self, error: Exception, context: dict):
        """Handle Claude API errors."""
        self.logger.error(f"Claude API error: {error}", extra=context)
        
        # Use fallback decision logic
        return self._fallback_decision(context)
    
    def _fallback_decision(self, context: dict) -> dict:
        """Simple rule-based decision when Claude fails."""
        if context.get('filler_word_count', 0) > 10:
            return {
                "action": "ENCOURAGE",
                "message": "Take your time. You're doing great.",
                "reasoning": "High filler count"
            }
        
        if context.get('long_pause_count', 0) > 3:
            return {
                "action": "HINT",
                "message": "Think about the key concepts.",
                "reasoning": "Multiple pauses"
            }
        
        return {
            "action": "CONTINUE",
            "message": "",
            "reasoning": "Fallback: continue"
        }
    
    async def handle_storage_error(
        self,
        error: Exception,
        data: dict,
        retry_count: int = 0
    ):
        """Handle MongoDB storage errors with retry logic."""
        if retry_count >= 3:
            self.logger.error(f"Storage failed after 3 retries: {error}")
            # Store in memory for later batch write
            await self._store_in_memory(data)
            return False
        
        # Exponential backoff
        await asyncio.sleep(2 ** retry_count)
        
        # Retry
        try:
            await self._write_to_mongodb(data)
            return True
        except Exception as e:
            return await self.handle_storage_error(e, data, retry_count + 1)
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    Prevents cascading failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Reset on successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Increment failure count and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```


## Performance Optimization

### 1. Frame Sampling Strategy

**Adaptive Sampling Rate:**
```python
class AdaptiveFrameSampler:
    """
    Adjusts frame sampling rate based on API usage.
    """
    
    def __init__(self, base_rate: int = 10, max_rate: int = 20):
        self.base_rate = base_rate
        self.max_rate = max_rate
        self.current_rate = base_rate
        self.daily_calls = 0
        self.rate_limit = 1000
    
    def should_sample_frame(self, frame_number: int) -> bool:
        """Determine if frame should be sampled."""
        return frame_number % self.current_rate == 0
    
    def adjust_rate(self):
        """Adjust sampling rate based on usage."""
        usage_percentage = self.daily_calls / self.rate_limit
        
        if usage_percentage > 0.9:
            self.current_rate = self.max_rate
        elif usage_percentage > 0.7:
            self.current_rate = 15
        else:
            self.current_rate = self.base_rate
```

**Benefits:**
- Respects Gemini free tier limit (1000 RPD)
- Automatically reduces sampling when approaching limit
- Maintains emotion detection throughout the day

### 2. TTS Audio Caching

**Redis-based Cache:**
```python
class TTSCache:
    """
    Cache TTS audio to reduce API calls and latency.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400  # 24 hours
    
    async def get_or_generate(self, text: str) -> bytes:
        """Get cached audio or generate new."""
        cache_key = f"tts:{hashlib.md5(text.encode()).hexdigest()}"
        
        # Try cache
        cached = await self.redis.get(cache_key)
        if cached:
            return cached
        
        # Generate and cache
        audio = await self.tts_service.synthesize(text)
        await self.redis.setex(cache_key, self.ttl, audio)
        return audio
```

**Benefits:**
- Questions asked repeatedly are cached
- Reduces ElevenLabs API costs
- Faster audio delivery (<100ms from cache vs ~1s from API)

### 3. Concurrent Operations

**Parallel Processing:**
```python
async def process_answer_completion(self):
    """
    Process multiple operations concurrently.
    """
    # Run evaluation, storage, and next question prep in parallel
    evaluation, storage_result, next_question = await asyncio.gather(
        self.decision_engine.evaluate_answer(question, answer),
        self.mongo_repository.store_result(session_id, result),
        self.question_manager.preload_next_question(index + 1),
        return_exceptions=True
    )
    
    # Total time: max(eval_time, storage_time, preload_time)
    # vs sequential: eval_time + storage_time + preload_time
```

**Performance Gain:** 3x faster (6s → 2s)

### 4. Connection Pooling

**MongoDB Connection Pool:**
- Min pool size: 10 (warm connections)
- Max pool size: 50 (handle concurrent sessions)
- Connection timeout: 5s (fail fast)

**Benefits:**
- No connection overhead per request
- Handles multiple concurrent sessions
- Automatic connection management

### 5. WebSocket for Real-Time Updates

**Efficient State Updates:**
```python
# Instead of polling every second
# Use WebSocket push notifications

async def send_confidence_update(self, session_id: str, score: int):
    """Push update to frontend via WebSocket."""
    await self.websocket_manager.send_to_session(
        session_id,
        {
            "type": "confidence_update",
            "confidence_score": score,
            "timestamp": time.time()
        }
    )
```

**Benefits:**
- Real-time updates without polling
- Reduced server load
- Lower latency (<100ms vs 1s polling)

## Security Design

### 1. Authentication Flow

**JWT Token Validation:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Validate JWT token and extract user ID.
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

### 2. Stream Token Generation

**Secure Stream.io Tokens:**
```python
def generate_stream_token(user_id: str) -> str:
    """
    Generate Stream.io token for video call.
    """
    stream_client = StreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET
    )
    
    token = stream_client.create_token(
        user_id=user_id,
        exp=int(time.time()) + 3600  # 1 hour expiry
    )
    
    return token
```

### 3. API Key Management

**Environment Variables:**
```bash
# .env file (never commit to git)
STREAM_API_KEY=your_stream_key
STREAM_API_SECRET=your_stream_secret
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_claude_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
PINECONE_API_KEY=your_pinecone_key
SUPERMEMORY_API_KEY=your_supermemory_key
MONGODB_URI=your_mongodb_uri
JWT_SECRET=your_jwt_secret
```

**Settings Management:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    STREAM_API_KEY: str
    STREAM_API_SECRET: str
    GEMINI_API_KEY: str
    ANTHROPIC_API_KEY: str
    DEEPGRAM_API_KEY: str
    ELEVENLABS_API_KEY: str
    PINECONE_API_KEY: str
    SUPERMEMORY_API_KEY: str
    MONGODB_URI: str
    JWT_SECRET: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 4. Input Validation

**Request Validation:**
```python
from pydantic import BaseModel, Field, validator

class StartLiveSessionRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    topics: List[str] = Field(..., min_items=1, max_items=10)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    mode: str = Field(..., pattern="^(practice|mock|coaching)$")
    
    @validator('topics')
    def validate_topics(cls, v):
        """Validate topic strings."""
        for topic in v:
            if len(topic) < 1 or len(topic) > 50:
                raise ValueError("Topic must be 1-50 characters")
        return v
```

### 5. Rate Limiting

**Session Rate Limiter:**
```python
class SessionRateLimiter:
    """
    Enforce rate limits on live sessions.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.max_sessions_per_day = 10
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        key = f"rate_limit:sessions:{user_id}:{date.today()}"
        count = await self.redis.get(key)
        
        if count and int(count) >= self.max_sessions_per_day:
            return False
        
        return True
    
    async def increment_session_count(self, user_id: str):
        """Increment session count for user."""
        key = f"rate_limit:sessions:{user_id}:{date.today()}"
        await self.redis.incr(key)
        await self.redis.expire(key, 86400)  # 24 hours
```

## Deployment Architecture

### Environment Configuration

**Required Environment Variables:**
```bash
# Stream.io Configuration
STREAM_API_KEY=<your_key>
STREAM_API_SECRET=<your_secret>

# AI Services
GEMINI_API_KEY=<your_key>
ANTHROPIC_API_KEY=<your_key>
DEEPGRAM_API_KEY=<your_key>
ELEVENLABS_API_KEY=<your_key>

# Data Services
MONGODB_URI=<your_uri>
PINECONE_API_KEY=<your_key>
SUPERMEMORY_API_KEY=<your_key>
REDIS_URL=<your_url>

# Security
JWT_SECRET=<your_secret>

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Dependency Management

**Backend (uv):**
```toml
# pyproject.toml
[project]
name = "roundzero-backend"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "vision-agents>=0.1.0",
    "stream-chat>=4.0.0",
    "google-generativeai>=0.3.0",
    "anthropic>=0.7.0",
    "deepgram-sdk>=3.0.0",
    "elevenlabs>=0.2.0",
    "pinecone-client>=2.2.0",
    "motor>=3.3.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.6",
]
```

**Installation:**
```bash
cd backend
uv pip install -e .
```

### Process Management

**Procfile (for Railway/Render):**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Startup Script:**
```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting RoundZero Vision Agents Integration")
    
    # Validate environment variables
    validate_environment()
    
    # Initialize services
    await initialize_mongodb()
    await initialize_redis()
    await initialize_stream_client()
    
    # Create indexes
    await create_mongodb_indexes()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await cleanup_resources()
    logger.info("Shutdown complete")

app = FastAPI(lifespan=lifespan)

def validate_environment():
    """Validate required environment variables."""
    required_vars = [
        "STREAM_API_KEY",
        "STREAM_API_SECRET",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MONGODB_URI",
        "JWT_SECRET"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)
```

### Graceful Shutdown

**Signal Handling:**
```python
import signal
import asyncio

class GracefulShutdown:
    """Handle graceful shutdown of application."""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.active_sessions = {}
    
    def setup_handlers(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown_event.set()
    
    async def shutdown(self):
        """Perform graceful shutdown."""
        logger.info("Saving in-progress sessions...")
        
        # Save all active sessions
        for session_id, agent in self.active_sessions.items():
            try:
                await agent._save_partial_session()
            except Exception as e:
                logger.error(f"Failed to save session {session_id}: {e}")
        
        # Close connections
        logger.info("Closing database connections...")
        await mongo_client.close()
        await redis_client.close()
        
        logger.info("Graceful shutdown complete")
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Frame Sampling Consistency

*For any* sequence of video frames, the EmotionProcessor should sample exactly every Nth frame (where N is the current sampling rate), ensuring consistent emotion detection intervals regardless of frame rate variations.

**Validates: Requirements 1.1**

### Property 2: Emotion Data Completeness

*For any* Gemini API response, the EmotionProcessor should extract all required fields (emotion, confidence_score, engagement_level, body_language_observations) or provide default values if extraction fails, ensuring decision-making always has complete emotion context.

**Validates: Requirements 1.3, 1.4, 1.5, 1.6**

### Property 3: Graceful Emotion Processing Degradation

*For any* Gemini API failure, the EmotionProcessor should continue processing without throwing exceptions, log the error, and provide neutral emotion data, ensuring the interview continues uninterrupted.

**Validates: Requirements 1.7**

### Property 4: Adaptive Rate Limiting

*For any* daily request count approaching the Gemini rate limit (>900 requests), the EmotionProcessor should automatically reduce sampling frequency, ensuring the system stays within free tier limits throughout the day.

**Validates: Requirements 1.8**

### Property 5: Filler Word Detection Accuracy

*For any* transcript segment containing filler words (um, uh, like, basically, you know, sort of, kind of), the SpeechProcessor should correctly identify and count all occurrences using regex patterns, ensuring accurate nervousness detection.

**Validates: Requirements 2.1, 2.2**

### Property 6: Speech Pace Calculation

*For any* sequence of transcript segments with timestamps, the SpeechProcessor should calculate speech pace as (total_words / elapsed_time_seconds) * 60, ensuring accurate words-per-minute measurement.

**Validates: Requirements 2.3**

### Property 7: Pause Detection Timing

*For any* period of silence lasting 3 or more seconds, the SpeechProcessor should record a long_pause event, ensuring accurate detection of candidate hesitation.

**Validates: Requirements 2.4**

### Property 8: Speech Metrics Reset

*For any* new question, the SpeechProcessor should reset filler_word_count and pause_count to zero, ensuring metrics are tracked independently per question.

**Validates: Requirements 2.5**

### Property 9: Speech Pace Threshold Flagging

*For any* calculated speech pace, the SpeechProcessor should flag rapid_speech when pace > 180 WPM and slow_speech when pace < 100 WPM, ensuring detection of abnormal speech patterns.

**Validates: Requirements 2.8, 2.9**

### Property 10: Agent Initialization Completeness

*For any* new interview session, the RoundZeroAgent should successfully fetch questions from Pinecone and candidate memory from Supermemory (or handle failures gracefully), ensuring the agent has necessary context before starting.

**Validates: Requirements 3.1, 3.2**

### Property 11: Decision Context Completeness

*For any* decision request, the DecisionEngine should construct context containing all required fields (question_text, transcript_so_far, emotion, confidence_score, engagement_level, filler_word_count, speech_pace, long_pause_count), ensuring Claude has complete multimodal context.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10**

### Property 12: Action Execution Correctness

*For any* decision action (CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT), the RoundZeroAgent should execute the corresponding behavior (continue listening, speak interruption, speak encouragement, evaluate and move to next, speak hint), ensuring decisions are properly acted upon.

**Validates: Requirements 3.10, 3.11, 3.12, 3.13, 3.14**

### Property 13: Fallback Decision Logic

*For any* Claude API failure, the DecisionEngine should return a valid decision using rule-based logic (based on filler count, pauses, confidence), ensuring the interview continues even when AI services fail.

**Validates: Requirements 3.20, 4.14**

### Property 14: Session Creation Validation

*For any* start-live-session request, the API should validate that role is non-empty, topics is non-empty array, difficulty is one of (easy/medium/hard), and mode is one of (practice/mock/coaching), rejecting invalid requests with 400 status.

**Validates: Requirements 5.4, 5.5, 5.6, 5.7**

### Property 15: Rate Limit Enforcement

*For any* candidate, the system should enforce a maximum of 10 live sessions per day, returning 429 status when limit is exceeded, ensuring cost control and fair usage.

**Validates: Requirements 5.14, 5.15, 14.1**

### Property 16: MongoDB Schema Compliance

*For any* live session document, it should contain all required fields (session_id, candidate_id, call_id, role, topics, difficulty, mode, started_at, transcript, emotion_timeline, speech_metrics, decisions), ensuring complete session data storage.

**Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.8, 8.9, 8.10, 8.11, 8.12, 8.13, 8.14, 8.15**

### Property 17: Question Retrieval with Fallback

*For any* Pinecone query failure, the QuestionManager should fall back to fetching default questions from MongoDB, ensuring interviews can start even when vector search is unavailable.

**Validates: Requirements 9.9, 10.13**

### Property 18: TTS Cache Hit Rate

*For any* repeated text input, the TTS service should return cached audio on subsequent requests, reducing API calls and improving response time.

**Validates: Requirements 11.2, 11.6**

### Property 19: Transcript Segment Processing

*For any* Deepgram transcript segment marked as final, the SpeechProcessor should add it to the transcript buffer and update word count, ensuring complete transcript accumulation.

**Validates: Requirements 12.6, 12.7**

### Property 20: Error Logging Completeness

*For any* service failure (Gemini, Claude, Deepgram, ElevenLabs, Pinecone, Supermemory, MongoDB), the system should log the error with error_type, timestamp, and context to MongoDB, ensuring comprehensive error tracking.

**Validates: Requirements 13.10, 18.2**

### Property 21: Authentication Token Validation

*For any* API request requiring authentication, the system should validate the JWT token and extract candidate_id, returning 401 for missing/invalid/expired tokens, ensuring secure access control.

**Validates: Requirements 15.1, 15.2, 15.3, 15.4**

### Property 22: Decision Latency Requirement

*For any* decision request with complete context, the DecisionEngine should return a decision within 2 seconds, ensuring responsive AI interactions during interviews.

**Validates: Requirements 16.2**

### Property 23: Gemini Rate Limit Tracking

*For any* day, the system should track Gemini API calls and enforce the 1000 requests per day limit, reducing sampling frequency when approaching limit and disabling emotion processing when limit is reached.

**Validates: Requirements 14.2, 14.3, 14.4**

### Property 24: Session Summary Generation

*For any* completed interview, the RoundZeroAgent should generate a session summary via Claude containing overall performance, strengths, areas for improvement, communication style, emotion patterns, and speech patterns, then write it to Supermemory.

**Validates: Requirements 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11**

### Property 25: Health Check Service Status

*For any* health check request, the system should test connectivity to all external services (MongoDB, Stream, Gemini, Claude, Deepgram, ElevenLabs, Pinecone, Supermemory) and return overall status as healthy/degraded/unhealthy based on service availability.

**Validates: Requirements 18.11, 18.12, 18.13, 18.14**

## Testing Strategy

### Dual Testing Approach

The Vision Agents integration requires both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, and integration points
- Specific emotion detection scenarios
- Specific filler word patterns
- API endpoint request/response examples
- Error handling for specific failure modes
- WebSocket event handling

**Property Tests**: Verify universal properties across all inputs
- Frame sampling consistency across random frame sequences
- Filler word detection across generated transcripts
- Speech pace calculation across various timings
- Decision context completeness across random inputs
- Rate limiting enforcement across usage patterns

**Property-Based Testing Configuration:**
- Library: Hypothesis (Python)
- Minimum iterations: 100 per property test
- Each test references design document property
- Tag format: `# Feature: vision-agents-integration, Property {number}: {property_text}`

### Test Implementation Examples

**Property Test Example:**
```python
from hypothesis import given, strategies as st
import pytest

@given(
    frame_sequence=st.lists(st.binary(min_size=1024, max_size=4096), min_size=100, max_size=200)
)
def test_frame_sampling_consistency(frame_sequence):
    """
    Feature: vision-agents-integration
    Property 1: Frame Sampling Consistency
    
    For any sequence of video frames, the EmotionProcessor should sample
    exactly every Nth frame.
    """
    processor = EmotionProcessor(
        gemini_client=mock_gemini,
        session_id="test",
        mongo_repository=mock_repo,
        frame_sample_rate=10
    )
    
    sampled_indices = []
    for i, frame in enumerate(frame_sequence):
        if processor.should_sample_frame(i):
            sampled_indices.append(i)
    
    # Verify sampling consistency
    for i in range(len(sampled_indices) - 1):
        assert sampled_indices[i+1] - sampled_indices[i] == 10
```

**Unit Test Example:**
```python
@pytest.mark.asyncio
async def test_gemini_api_failure_handling():
    """
    Test that EmotionProcessor continues gracefully when Gemini API fails.
    """
    # Mock Gemini client to raise exception
    mock_gemini = Mock()
    mock_gemini.generate_content.side_effect = Exception("API Error")
    
    processor = EmotionProcessor(
        gemini_client=mock_gemini,
        session_id="test",
        mongo_repository=mock_repo
    )
    
    # Process frame should not raise exception
    result = await processor.process_frame(b"fake_frame_data")
    
    # Should return None (no emotion data)
    assert result is None
    
    # Error should be logged
    assert "Gemini API error" in caplog.text
```

### Integration Tests

**Complete Interview Flow Test:**
```python
@pytest.mark.asyncio
async def test_complete_interview_flow():
    """
    Integration test for complete interview session.
    """
    # Start session
    response = await client.post(
        "/api/interview/start-live-session",
        json={
            "role": "Software Engineer",
            "topics": ["Python", "Algorithms"],
            "difficulty": "medium",
            "mode": "practice"
        },
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Simulate interview interaction
    # ... (send transcript segments, verify responses)
    
    # End session
    response = await client.delete(
        f"/api/interview/{session_id}/end-live-session",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    
    assert response.status_code == 200
    
    # Verify session data stored
    session = await mongo_repo.get_session(session_id)
    assert session is not None
    assert session["status"] == "completed"
```

## Monitoring and Logging

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "emotion_processed",
    session_id=session_id,
    emotion=emotion,
    confidence_score=confidence_score,
    processing_time_ms=processing_time
)

logger.error(
    "gemini_api_error",
    session_id=session_id,
    error_type=type(error).__name__,
    error_message=str(error),
    retry_count=retry_count
)
```

### Metrics Collection

```python
class MetricsCollector:
    """Collect application metrics."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record_api_call(
        self,
        service: str,
        latency_ms: float,
        success: bool
    ):
        """Record API call metrics."""
        date_key = date.today().isoformat()
        
        # Increment call count
        await self.redis.incr(f"metrics:{service}:calls:{date_key}")
        
        # Record latency
        await self.redis.lpush(
            f"metrics:{service}:latency:{date_key}",
            latency_ms
        )
        
        # Record success/failure
        if success:
            await self.redis.incr(f"metrics:{service}:success:{date_key}")
        else:
            await self.redis.incr(f"metrics:{service}:failure:{date_key}")
```

### Alert System

```python
class AlertService:
    """Send alerts for critical issues."""
    
    async def send_alert(self, title: str, message: str):
        """Send alert via configured channel."""
        # Implementation depends on alerting system
        # (e.g., email, Slack, PagerDuty)
        pass
    
    async def check_error_rate(self):
        """Check if error rate exceeds threshold."""
        error_count = await self.get_error_count_last_hour()
        total_count = await self.get_total_count_last_hour()
        
        if total_count > 0:
            error_rate = error_count / total_count
            
            if error_rate > 0.05:  # 5% threshold
                await self.send_alert(
                    "High Error Rate",
                    f"Error rate: {error_rate:.2%} in last hour"
                )
```

## Summary

This design document provides a comprehensive technical specification for integrating Vision Agents into RoundZero AI Interview Coach. The system enables live video interviews with real-time multimodal analysis (emotion, body language, speech patterns) and intelligent AI-driven interview orchestration.

Key design decisions:
- **Multimodal Analysis**: Combines video (Gemini Flash-8B), audio (Deepgram), and text (Claude Sonnet 4) for comprehensive assessment
- **Graceful Degradation**: System continues functioning even when individual services fail
- **Cost Optimization**: Adaptive frame sampling respects Gemini free tier limits
- **Real-Time Performance**: <2s decision latency through concurrent operations and caching
- **Security First**: JWT authentication, input validation, secure token generation
- **Comprehensive Storage**: Complete session data in MongoDB for post-interview analysis

The implementation follows vertical slice development (Schema → API → UI) and maintains backward compatibility with existing RoundZero infrastructure.
