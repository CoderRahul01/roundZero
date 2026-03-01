# Design Document: Real-Time Voice Interaction

## Overview

The Real-Time Voice Interaction feature transforms RoundZero's AI interview system into a truly conversational experience by adding intelligent, bidirectional voice communication with real-time analysis and context-aware interruption capabilities. This feature enables natural conversation flow between the AI interviewer and candidate through sophisticated silence detection, presence verification, answer relevance analysis, and intelligent interruption when responses drift off-topic.

This enhancement builds upon the existing voice-ai-interview-system by adding a state machine-driven conversation flow that mimics human interviewer behavior: detecting when candidates are silent, verifying their presence, analyzing answer relevance in real-time as they speak, and intelligently interrupting when responses become off-topic.

### Key Design Principles

1. **State Machine Architecture**: Clear conversation flow with well-defined states and transitions
2. **Real-Time Analysis**: Continuous monitoring and evaluation of candidate responses as they speak
3. **Intelligent Interruption**: Context-aware interruptions that redirect without frustrating the candidate
4. **Graceful Degradation**: System continues functioning even if individual services fail
5. **Performance First**: Sub-5s total response time from answer completion to next question
6. **Async Throughout**: Non-blocking operations for maximum responsiveness

### Design Goals

- Enable natural, conversational interview experience
- Detect and handle candidate silence appropriately
- Analyze answer relevance in real-time (not post-answer)
- Interrupt off-topic responses with context-aware feedback
- Maintain <5s total latency from answer completion to next question
- Handle concurrent operations efficiently
- Provide graceful fallbacks for service failures

## Architecture

### High-Level Architecture


```mermaid
graph TB
    subgraph "Frontend (React)"
        UI[RealTimeVoicePanel]
        SI[SilenceIndicator]
        TS[TranscriptStream]
        IO[InterruptionOverlay]
        PCD[PresenceCheckDialog]
    end
    
    subgraph "Backend (FastAPI - Async)"
        VFC[VoiceFlowController]
        SD[SilenceDetector]
        PV[PresenceVerifier]
        AA[AnswerAnalyzer]
        IE[InterruptionEngine]
        CT[ContextTracker]
        SB[SpeechBuffer]
    end
    
    subgraph "External Services"
        DG[Deepgram STT]
        EL[ElevenLabs TTS]
        CL[Claude API]
        VA[Vertex AI]
    end
    
    subgraph "Data Layer"
        MG[MongoDB GridFS]
        ND[NeonDB]
        RD[Upstash Redis]
    end
    
    UI --> VFC
    VFC --> SD
    VFC --> PV
    VFC --> AA
    VFC --> IE
    VFC --> CT
    VFC --> SB
    
    SD --> DG
    AA --> CL
    AA --> VA
    IE --> CL
    CT --> CL
    PV --> CL
    
    VFC --> EL
    VFC --> MG
    VFC --> ND
    VFC --> RD
    
    TS --> UI
    SI --> UI
    IO --> UI
    PCD --> UI
```



### State Machine Architecture

The conversation flow is managed by a finite state machine with the following states:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> ASKING_QUESTION: Start Interview
    ASKING_QUESTION --> LISTENING: Question Audio Complete
    LISTENING --> ANALYZING: Speech Detected (20+ words)
    LISTENING --> SILENCE_DETECTED: 10s Silence
    ANALYZING --> LISTENING: Continue Listening
    ANALYZING --> INTERRUPTING: Off-Topic Detected
    INTERRUPTING --> LISTENING: Interruption Complete
    LISTENING --> EVALUATING: Answer Complete (3s silence)
    SILENCE_DETECTED --> PRESENCE_CHECK: Emit Silence Event
    PRESENCE_CHECK --> ASKING_QUESTION: Presence Confirmed
    PRESENCE_CHECK --> CONNECTION_LOST: 3 Failed Attempts
    EVALUATING --> ASKING_QUESTION: Next Question
    EVALUATING --> [*]: Interview Complete
    CONNECTION_LOST --> [*]
```

**State Descriptions:**

- **IDLE**: Initial state, waiting for interview to start
- **ASKING_QUESTION**: AI is speaking the question via TTS
- **LISTENING**: Monitoring candidate's speech, accumulating transcript
- **ANALYZING**: Real-time relevance analysis of accumulated speech (runs concurrently with LISTENING)
- **SILENCE_DETECTED**: 10 seconds of silence detected, triggering presence check
- **PRESENCE_CHECK**: Verifying candidate is present and listening
- **INTERRUPTING**: Playing interruption message to redirect off-topic answer
- **EVALUATING**: Final answer evaluation and decision on next action
- **CONNECTION_LOST**: Terminal state when presence cannot be confirmed



### Technology Stack Integration

**Existing Infrastructure (from voice-ai-interview-system):**
- MongoDB with Motor (async) for question storage
- NeonDB (Postgres) with asyncpg for session/user data
- Upstash Redis for caching and rate limiting
- Deepgram STT (nova-2 model) for speech recognition
- ElevenLabs TTS (eleven_turbo_v2) for voice synthesis
- Anthropic Claude-3.5-Sonnet for AI decision-making
- Vertex AI for embeddings (NOT paid Gemini API)

**New Components for Real-Time Interaction:**
- WebSocket connection for real-time transcription streaming
- State machine controller for conversation flow
- Silence detection with audio level monitoring
- Real-time answer analysis with buffering
- Context extraction for interruption messages
- Interruption engine with attempt limiting

**Data Flow:**
```
User Speech → Deepgram (WebSocket) → SpeechBuffer → AnswerAnalyzer
                                                    ↓
                                            Claude API (async)
                                                    ↓
                                            Vertex AI (async)
                                                    ↓
                                            InterruptionEngine
                                                    ↓
                                            ElevenLabs TTS
                                                    ↓
                                            Audio Playback
```



## Components and Interfaces

### 1. VoiceFlowController

**Purpose**: Orchestrates the entire real-time voice interaction flow, managing state transitions and coordinating all components.

**Class Definition:**

```python
from enum import Enum
from typing import Optional, Callable
import asyncio
from dataclasses import dataclass

class ConversationState(Enum):
    """Enum for conversation states."""
    IDLE = "IDLE"
    ASKING_QUESTION = "ASKING_QUESTION"
    LISTENING = "LISTENING"
    ANALYZING = "ANALYZING"
    SILENCE_DETECTED = "SILENCE_DETECTED"
    PRESENCE_CHECK = "PRESENCE_CHECK"
    INTERRUPTING = "INTERRUPTING"
    EVALUATING = "EVALUATING"
    CONNECTION_LOST = "CONNECTION_LOST"

@dataclass
class VoiceFlowState:
    """Current state of the voice flow."""
    conversation_state: ConversationState
    current_question: Optional[str]
    current_question_topic: Optional[str]
    speech_buffer: str
    interruption_count: int
    silence_start_time: Optional[float]
    presence_check_attempts: int

class VoiceFlowController:
    """
    Orchestrates real-time voice interaction flow.
    Manages state machine and coordinates all components.
    """
    
    def __init__(
        self,
        session_id: str,
        silence_detector: 'SilenceDetector',
        presence_verifier: 'PresenceVerifier',
        answer_analyzer: 'AnswerAnalyzer',
        interruption_engine: 'InterruptionEngine',
        context_tracker: 'ContextTracker',
        speech_buffer: 'SpeechBuffer',
        tts_service: 'ElevenLabsTTSService',
        stt_service: 'DeepgramSTTService'
    ):
        self.session_id = session_id
        self.silence_detector = silence_detector
        self.presence_verifier = presence_verifier
        self.answer_analyzer = answer_analyzer
        self.interruption_engine = interruption_engine
        self.context_tracker = context_tracker
        self.speech_buffer = speech_buffer
        self.tts_service = tts_service
        self.stt_service = stt_service
        
        self.state = VoiceFlowState(
            conversation_state=ConversationState.IDLE,
            current_question=None,
            current_question_topic=None,
            speech_buffer="",
            interruption_count=0,
            silence_start_time=None,
            presence_check_attempts=0
        )
        
        # Event handlers
        self._state_change_handlers: list[Callable] = []
        self._analysis_task: Optional[asyncio.Task] = None
    
    async def start_interview(self, first_question: str):
        """
        Start the interview with the first question.
        Transitions: IDLE → ASKING_QUESTION
        """
        await self._transition_to(ConversationState.ASKING_QUESTION)
        self.state.current_question = first_question
        
        # Extract question topic for potential interruptions
        self.state.current_question_topic = await self.context_tracker.extract_topic(
            first_question
        )
        
        # Generate and play question audio
        audio = await self.tts_service.synthesize_speech(first_question)
        await self._play_audio(audio)
        
        # Transition to listening
        await self._transition_to(ConversationState.LISTENING)
        await self.silence_detector.start_monitoring()
    
    async def handle_speech_input(self, transcript_segment: str, is_final: bool):
        """
        Handle incoming speech transcription.
        Called by STT service for each transcript segment.
        """
        if self.state.conversation_state != ConversationState.LISTENING:
            return
        
        # Reset silence detector
        await self.silence_detector.reset()
        
        # Add to speech buffer
        if is_final:
            self.speech_buffer.add_final_segment(transcript_segment)
            self.state.speech_buffer = self.speech_buffer.get_accumulated_text()
            
            # Trigger analysis if buffer has enough content
            if self.speech_buffer.word_count() >= 20:
                await self._trigger_analysis()
    
    async def handle_silence_detected(self, duration: float):
        """
        Handle silence detection event.
        Transitions: LISTENING → SILENCE_DETECTED → PRESENCE_CHECK
        """
        if duration >= 10.0:
            await self._transition_to(ConversationState.SILENCE_DETECTED)
            await self._transition_to(ConversationState.PRESENCE_CHECK)
            
            # Trigger presence verification
            result = await self.presence_verifier.verify_presence()
            
            if result.confirmed:
                # Resume with question
                await self._transition_to(ConversationState.ASKING_QUESTION)
                await self._repeat_question()
            else:
                self.state.presence_check_attempts += 1
                if self.state.presence_check_attempts >= 3:
                    await self._transition_to(ConversationState.CONNECTION_LOST)
                else:
                    # Try again
                    await self.handle_silence_detected(duration)
        
        elif duration >= 3.0 and self.speech_buffer.word_count() > 0:
            # Answer potentially complete
            await self._transition_to(ConversationState.EVALUATING)
            await self._evaluate_answer()
    
    async def handle_off_topic_detected(self, interruption_message: str):
        """
        Handle off-topic detection from analyzer.
        Transitions: ANALYZING → INTERRUPTING → LISTENING
        """
        if self.state.interruption_count >= 2:
            # Max interruptions reached, let them continue
            return
        
        await self._transition_to(ConversationState.INTERRUPTING)
        
        # Stop STT temporarily
        await self.stt_service.pause()
        
        # Play interruption
        audio = await self.tts_service.synthesize_speech(interruption_message)
        await self._play_audio(audio)
        
        # Clear off-topic content from buffer
        self.speech_buffer.clear()
        self.state.speech_buffer = ""
        self.state.interruption_count += 1
        
        # Resume listening
        await self.stt_service.resume()
        await self._transition_to(ConversationState.LISTENING)
        await self.silence_detector.reset()
    
    async def _trigger_analysis(self):
        """
        Trigger real-time answer analysis.
        Runs concurrently with listening.
        """
        if self._analysis_task and not self._analysis_task.done():
            # Analysis already running
            return
        
        self._analysis_task = asyncio.create_task(self._run_analysis())
    
    async def _run_analysis(self):
        """
        Run answer analysis in background.
        """
        result = await self.answer_analyzer.analyze_relevance(
            question=self.state.current_question,
            answer_buffer=self.state.speech_buffer,
            question_topic=self.state.current_question_topic
        )
        
        if result.should_interrupt:
            await self.handle_off_topic_detected(result.interruption_message)
    
    async def _evaluate_answer(self):
        """
        Perform final answer evaluation.
        Transitions: EVALUATING → ASKING_QUESTION or [*]
        """
        # Final evaluation with Claude
        evaluation = await self.answer_analyzer.evaluate_final_answer(
            question=self.state.current_question,
            answer=self.state.speech_buffer
        )
        
        # Store result
        # ... (integration with existing session management)
        
        # Reset for next question
        self.speech_buffer.clear()
        self.state.speech_buffer = ""
        self.state.interruption_count = 0
        
        # Move to next question or complete
        # ... (integration with existing interview flow)
    
    async def _transition_to(self, new_state: ConversationState):
        """Handle state transition with event notification."""
        old_state = self.state.conversation_state
        self.state.conversation_state = new_state
        
        # Notify handlers
        for handler in self._state_change_handlers:
            await handler(old_state, new_state)
    
    async def _play_audio(self, audio_bytes: bytes):
        """Play audio through the audio output system."""
        # Integration with frontend audio playback
        pass
    
    async def _repeat_question(self):
        """Repeat the current question after presence confirmation."""
        intro = "Great! Let me ask you the question again."
        intro_audio = await self.tts_service.synthesize_speech(intro)
        await self._play_audio(intro_audio)
        
        question_audio = await self.tts_service.synthesize_speech(
            self.state.current_question
        )
        await self._play_audio(question_audio)
        
        await self._transition_to(ConversationState.LISTENING)
        await self.silence_detector.start_monitoring()
    
    def on_state_change(self, handler: Callable):
        """Register state change event handler."""
        self._state_change_handlers.append(handler)
```

**Integration Points:**
- Coordinates all real-time components
- Manages WebSocket connections for STT
- Handles state transitions and event propagation
- Integrates with existing InterviewerAgent for evaluation



### 2. SilenceDetector

**Purpose**: Monitor audio input stream and detect periods of silence, distinguishing between brief pauses and prolonged silence.

**Class Definition:**

```python
import asyncio
import time
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class SilenceEvent:
    """Event emitted when silence is detected."""
    duration: float
    timestamp: float
    context: str  # "prolonged" or "answer_complete"

class SilenceDetector:
    """
    Monitors audio stream for silence detection.
    Distinguishes between brief pauses (<2s) and prolonged silence (10s).
    """
    
    def __init__(
        self,
        silence_threshold_db: float = -40.0,
        brief_pause_threshold: float = 2.0,
        prolonged_silence_threshold: float = 10.0
    ):
        self.silence_threshold_db = silence_threshold_db
        self.brief_pause_threshold = brief_pause_threshold
        self.prolonged_silence_threshold = prolonged_silence_threshold
        
        self._silence_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self._silence_handlers: list[Callable[[SilenceEvent], None]] = []
    
    async def start_monitoring(self):
        """Start monitoring for silence."""
        self._is_monitoring = True
        self._silence_start_time = time.time()
        self._last_speech_time = time.time()
        
        if not self._monitoring_task or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Stop monitoring for silence."""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    async def reset(self):
        """Reset silence timer when speech is detected."""
        self._last_speech_time = time.time()
        self._silence_start_time = None
    
    async def process_audio_level(self, audio_level_db: float):
        """
        Process audio level from microphone.
        Called continuously by audio capture system.
        """
        if not self._is_monitoring:
            return
        
        if audio_level_db > self.silence_threshold_db:
            # Speech detected
            await self.reset()
        else:
            # Silence detected
            if self._silence_start_time is None:
                self._silence_start_time = time.time()
    
    async def _monitor_loop(self):
        """
        Background monitoring loop.
        Checks silence duration every 100ms.
        """
        while self._is_monitoring:
            await asyncio.sleep(0.1)  # 100ms check interval
            
            if self._silence_start_time is not None:
                silence_duration = time.time() - self._silence_start_time
                
                # Ignore brief pauses
                if silence_duration < self.brief_pause_threshold:
                    continue
                
                # Check for answer completion (3s silence)
                if silence_duration >= 3.0 and silence_duration < self.prolonged_silence_threshold:
                    event = SilenceEvent(
                        duration=silence_duration,
                        timestamp=time.time(),
                        context="answer_complete"
                    )
                    await self._emit_silence_event(event)
                    self._silence_start_time = None  # Reset after emitting
                
                # Check for prolonged silence (10s)
                elif silence_duration >= self.prolonged_silence_threshold:
                    event = SilenceEvent(
                        duration=silence_duration,
                        timestamp=time.time(),
                        context="prolonged"
                    )
                    await self._emit_silence_event(event)
                    self._silence_start_time = None  # Reset after emitting
    
    async def _emit_silence_event(self, event: SilenceEvent):
        """Emit silence event to registered handlers."""
        for handler in self._silence_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
    
    def on_silence_detected(self, handler: Callable[[SilenceEvent], None]):
        """Register silence detection event handler."""
        self._silence_handlers.append(handler)
    
    def get_current_silence_duration(self) -> float:
        """Get current silence duration in seconds."""
        if self._silence_start_time is None:
            return 0.0
        return time.time() - self._silence_start_time
```

**Performance Requirements:**
- Detection latency: <100ms from speech stopping
- Audio level processing: Real-time, non-blocking
- Memory usage: Minimal (no audio buffering)

**Integration:**
- Receives audio level data from Deepgram STT interim results
- Emits events to VoiceFlowController
- Coordinates with SpeechBuffer for context



### 3. PresenceVerifier

**Purpose**: Verify candidate presence when prolonged silence is detected by generating and analyzing responses to "Can you hear me?" prompts.

**Class Definition:**

```python
from typing import Optional
from dataclasses import dataclass
from anthropic import AsyncAnthropic

@dataclass
class PresenceCheckResult:
    """Result of presence verification."""
    confirmed: bool
    attempts: int
    response_text: Optional[str]
    confidence: float

class PresenceVerifier:
    """
    Handles presence verification flow.
    Generates presence check prompts and analyzes responses.
    """
    
    def __init__(
        self,
        tts_service: 'ElevenLabsTTSService',
        stt_service: 'DeepgramSTTService',
        claude_client: AsyncAnthropic,
        max_attempts: int = 3,
        response_timeout: float = 10.0
    ):
        self.tts_service = tts_service
        self.stt_service = stt_service
        self.claude_client = claude_client
        self.max_attempts = max_attempts
        self.response_timeout = response_timeout
        
        self._current_attempt = 0
        self._presence_check_message = "Hey, can you hear me?"
    
    async def verify_presence(self) -> PresenceCheckResult:
        """
        Execute presence verification flow.
        Returns result indicating if presence was confirmed.
        """
        self._current_attempt += 1
        
        # Generate and play presence check audio
        audio = await self.tts_service.synthesize_speech(
            self._presence_check_message
        )
        await self._play_audio(audio)
        
        # Listen for response with timeout
        response_text = await self._listen_for_response(
            timeout=self.response_timeout
        )
        
        if response_text:
            # Analyze response with Claude
            is_affirmative = await self._is_affirmative_response(response_text)
            
            if is_affirmative:
                return PresenceCheckResult(
                    confirmed=True,
                    attempts=self._current_attempt,
                    response_text=response_text,
                    confidence=0.9
                )
        
        # No response or negative response
        if self._current_attempt >= self.max_attempts:
            return PresenceCheckResult(
                confirmed=False,
                attempts=self._current_attempt,
                response_text=response_text,
                confidence=0.0
            )
        
        # Try again
        return await self.verify_presence()
    
    async def _listen_for_response(self, timeout: float) -> Optional[str]:
        """
        Listen for candidate response with timeout.
        Returns transcribed text or None if timeout.
        """
        try:
            response = await asyncio.wait_for(
                self.stt_service.get_next_final_transcript(),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            return None
    
    async def _is_affirmative_response(self, response_text: str) -> bool:
        """
        Use Claude to determine if response is affirmative.
        Handles variations like "Yes", "Yes I can", "I can hear you", etc.
        """
        prompt = f"""
        Analyze if the following response is affirmative to the question "Can you hear me?":
        
        Response: "{response_text}"
        
        Return only "YES" or "NO".
        """
        
        response = await self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.content[0].text.strip().upper()
        return result == "YES"
    
    async def _play_audio(self, audio_bytes: bytes):
        """Play audio through output system."""
        # Integration with audio playback
        pass
    
    def reset(self):
        """Reset attempt counter for new presence check sequence."""
        self._current_attempt = 0
```

**Performance Requirements:**
- Presence check audio generation: <1s
- Response analysis: <500ms
- Total presence verification: <15s (including retries)

**Integration:**
- Uses existing ElevenLabs TTS service
- Uses existing Deepgram STT service
- Uses Claude API for response interpretation
- Coordinates with VoiceFlowController for state management



### 4. AnswerAnalyzer

**Purpose**: Perform real-time relevance analysis of candidate answers as they speak, detecting off-topic responses and triggering interruptions.

**Class Definition:**

```python
from typing import Optional
from dataclasses import dataclass
from anthropic import AsyncAnthropic
import asyncio

@dataclass
class AnalysisResult:
    """Result of answer relevance analysis."""
    is_relevant: bool
    semantic_similarity: float
    should_interrupt: bool
    interruption_message: Optional[str]
    confidence: float

class AnswerAnalyzer:
    """
    Real-time answer relevance analyzer.
    Evaluates answer relevance using Claude API and Vertex AI embeddings.
    """
    
    def __init__(
        self,
        claude_client: AsyncAnthropic,
        vertex_ai_service: 'VertexAIEmbeddingService',
        relevance_threshold: float = 0.3,
        analysis_interval: float = 5.0
    ):
        self.claude_client = claude_client
        self.vertex_ai_service = vertex_ai_service
        self.relevance_threshold = relevance_threshold
        self.analysis_interval = analysis_interval
        
        self._last_analysis_time: Optional[float] = None
    
    async def analyze_relevance(
        self,
        question: str,
        answer_buffer: str,
        question_topic: str
    ) -> AnalysisResult:
        """
        Analyze answer relevance in real-time.
        Runs Claude evaluation and Vertex AI embeddings concurrently.
        """
        # Rate limit analysis (every 5 seconds)
        current_time = time.time()
        if self._last_analysis_time:
            elapsed = current_time - self._last_analysis_time
            if elapsed < self.analysis_interval:
                return AnalysisResult(
                    is_relevant=True,
                    semantic_similarity=1.0,
                    should_interrupt=False,
                    interruption_message=None,
                    confidence=0.0
                )
        
        self._last_analysis_time = current_time
        
        # Run analysis tasks concurrently
        claude_task = self._evaluate_with_claude(question, answer_buffer)
        embedding_task = self._calculate_semantic_similarity(question, answer_buffer)
        
        claude_result, semantic_similarity = await asyncio.gather(
            claude_task,
            embedding_task
        )
        
        # Determine if interruption is needed
        should_interrupt = (
            not claude_result["is_relevant"] or
            semantic_similarity < self.relevance_threshold
        )
        
        interruption_message = None
        if should_interrupt:
            interruption_message = self._generate_interruption_message(
                question_topic,
                answer_buffer
            )
        
        return AnalysisResult(
            is_relevant=claude_result["is_relevant"],
            semantic_similarity=semantic_similarity,
            should_interrupt=should_interrupt,
            interruption_message=interruption_message,
            confidence=claude_result["confidence"]
        )
    
    async def evaluate_final_answer(
        self,
        question: str,
        answer: str
    ) -> dict:
        """
        Perform final answer evaluation after completion.
        More comprehensive than real-time analysis.
        """
        prompt = f"""
        Evaluate the following answer to the question:
        
        Question: {question}
        Answer: {answer}
        
        Provide:
        1. Is the answer complete and addresses the question? (YES/NO)
        2. Score out of 100
        3. Brief feedback
        
        Format as JSON:
        {{
            "is_complete": true/false,
            "score": 85,
            "feedback": "Your feedback here"
        }}
        """
        
        response = await self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_evaluation_response(response.content[0].text)
    
    async def _evaluate_with_claude(
        self,
        question: str,
        answer_buffer: str
    ) -> dict:
        """
        Use Claude to evaluate if answer is addressing the question.
        """
        prompt = f"""
        Question: {question}
        User's answer so far: {answer_buffer}
        
        Is the user addressing the question asked? Consider:
        - Are they talking about the right topic?
        - Is their response relevant to what was asked?
        
        Respond with JSON:
        {{
            "is_relevant": true/false,
            "confidence": 0.0-1.0,
            "reason": "brief explanation"
        }}
        """
        
        response = await self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_relevance_response(response.content[0].text)
    
    async def _calculate_semantic_similarity(
        self,
        question: str,
        answer_buffer: str
    ) -> float:
        """
        Calculate semantic similarity using Vertex AI embeddings.
        """
        # Generate embeddings concurrently
        question_embedding, answer_embedding = await asyncio.gather(
            self.vertex_ai_service.get_embedding(question),
            self.vertex_ai_service.get_embedding(answer_buffer)
        )
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(question_embedding, answer_embedding)
        return similarity
    
    def _generate_interruption_message(
        self,
        question_topic: str,
        off_topic_content: str
    ) -> str:
        """
        Generate context-aware interruption message.
        Format: "Wait, I asked about [topic], please focus on that"
        """
        return f"Wait, I asked about {question_topic}, please focus on that"
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _parse_relevance_response(self, response_text: str) -> dict:
        """Parse Claude's relevance evaluation response."""
        import json
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": "Parse error"
            }
    
    def _parse_evaluation_response(self, response_text: str) -> dict:
        """Parse Claude's final evaluation response."""
        import json
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "is_complete": True,
                "score": 70,
                "feedback": "Unable to parse evaluation"
            }
```

**Performance Requirements:**
- Analysis latency: <2s per 20-word buffer
- Claude API call: <2s
- Vertex AI embedding: <1s
- Concurrent execution: Both APIs called in parallel
- Analysis frequency: Every 5 seconds during speech

**Integration:**
- Uses Claude API (PAID) for relevance evaluation
- Uses Vertex AI (NOT paid Gemini) for embeddings
- Coordinates with SpeechBuffer for text accumulation
- Triggers InterruptionEngine when off-topic detected



### 5. InterruptionEngine

**Purpose**: Generate context-aware interruption messages and manage interruption attempts to avoid frustrating the candidate.

**Class Definition:**

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class InterruptionContext:
    """Context for generating interruption messages."""
    question_topic: str
    off_topic_content: str
    attempt_number: int
    previous_interruptions: list[str]

class InterruptionEngine:
    """
    Manages intelligent interruptions for off-topic responses.
    Limits interruptions to max 2 per question.
    """
    
    def __init__(
        self,
        max_interruptions_per_question: int = 2
    ):
        self.max_interruptions_per_question = max_interruptions_per_question
        self._interruption_count = 0
        self._interruption_history: list[str] = []
    
    def can_interrupt(self) -> bool:
        """Check if interruption is allowed based on attempt count."""
        return self._interruption_count < self.max_interruptions_per_question
    
    def generate_interruption(
        self,
        context: InterruptionContext
    ) -> Optional[str]:
        """
        Generate context-aware interruption message.
        Returns None if max interruptions reached.
        """
        if not self.can_interrupt():
            return None
        
        # Generate message based on attempt number
        if context.attempt_number == 1:
            message = self._generate_first_interruption(context)
        else:
            message = self._generate_second_interruption(context)
        
        self._interruption_count += 1
        self._interruption_history.append(message)
        
        return message
    
    def _generate_first_interruption(
        self,
        context: InterruptionContext
    ) -> str:
        """
        Generate first interruption message (gentle redirect).
        Format: "Wait, I asked about [topic], please focus on that"
        """
        return f"Wait, I asked about {context.question_topic}, please focus on that"
    
    def _generate_second_interruption(
        self,
        context: InterruptionContext
    ) -> str:
        """
        Generate second interruption message (more direct).
        Format: "Let me stop you there. The question is specifically about [topic]"
        """
        return f"Let me stop you there. The question is specifically about {context.question_topic}"
    
    def reset_for_new_question(self):
        """Reset interruption counter for new question."""
        self._interruption_count = 0
        self._interruption_history.clear()
    
    def get_interruption_count(self) -> int:
        """Get current interruption count for this question."""
        return self._interruption_count
    
    def get_interruption_history(self) -> list[str]:
        """Get history of interruption messages for this question."""
        return self._interruption_history.copy()
```

**Interruption Strategy:**
- **First interruption**: Gentle redirect referencing the question topic
- **Second interruption**: More direct guidance to refocus
- **Third+ off-topic**: No interruption, accept answer as-is and note in evaluation

**Performance Requirements:**
- Message generation: <100ms
- Total interruption latency: <1.5s (including TTS)

**Integration:**
- Receives context from ContextTracker
- Coordinates with VoiceFlowController for execution
- Uses ElevenLabs TTS for audio generation



### 6. ContextTracker

**Purpose**: Extract core topics from questions and maintain conversation context for generating specific interruption messages.

**Class Definition:**

```python
from typing import Optional
from anthropic import AsyncAnthropic
from dataclasses import dataclass

@dataclass
class QuestionContext:
    """Context information for a question."""
    full_question: str
    core_topic: str
    keywords: list[str]
    timestamp: float

class ContextTracker:
    """
    Tracks conversation context and extracts question topics.
    Maintains history of recent questions for context-aware interactions.
    """
    
    def __init__(
        self,
        claude_client: AsyncAnthropic,
        history_size: int = 5
    ):
        self.claude_client = claude_client
        self.history_size = history_size
        self._question_history: list[QuestionContext] = []
    
    async def extract_topic(self, question: str) -> str:
        """
        Extract core topic from question using Claude.
        Returns concise phrase (3-7 words) summarizing what the question asks.
        
        Examples:
        - "What is the value of four plus two?" → "the mathematical calculation"
        - "Describe your experience with React" → "your React experience"
        """
        prompt = f"""
        Extract the core topic from this question as a concise phrase (3-7 words):
        
        Question: "{question}"
        
        The topic should complete the sentence: "I asked about ___"
        
        Examples:
        - "What is 4 + 2?" → "the mathematical calculation"
        - "Tell me about React" → "your React experience"
        - "How does async/await work?" → "how async/await works"
        
        Return only the topic phrase, nothing else.
        """
        
        try:
            response = await asyncio.wait_for(
                self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=0.5  # 500ms timeout
            )
            
            topic = response.content[0].text.strip()
            
            # Store in history
            context = QuestionContext(
                full_question=question,
                core_topic=topic,
                keywords=self._extract_keywords(question),
                timestamp=time.time()
            )
            self._add_to_history(context)
            
            return topic
            
        except asyncio.TimeoutError:
            # Fallback: use first 10 words
            words = question.split()[:10]
            fallback_topic = " ".join(words)
            
            context = QuestionContext(
                full_question=question,
                core_topic=fallback_topic,
                keywords=self._extract_keywords(question),
                timestamp=time.time()
            )
            self._add_to_history(context)
            
            return fallback_topic
    
    def get_current_context(self) -> Optional[QuestionContext]:
        """Get context for the current question."""
        if not self._question_history:
            return None
        return self._question_history[-1]
    
    def get_question_history(self) -> list[QuestionContext]:
        """Get history of recent questions."""
        return self._question_history.copy()
    
    def _extract_keywords(self, question: str) -> list[str]:
        """Extract important keywords from question (simple implementation)."""
        # Remove common words
        stop_words = {
            'what', 'is', 'the', 'a', 'an', 'how', 'why', 'when', 'where',
            'who', 'which', 'can', 'you', 'tell', 'me', 'about', 'describe'
        }
        
        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords[:5]  # Top 5 keywords
    
    def _add_to_history(self, context: QuestionContext):
        """Add question context to history with size limit."""
        self._question_history.append(context)
        if len(self._question_history) > self.history_size:
            self._question_history.pop(0)
    
    def clear_history(self):
        """Clear question history."""
        self._question_history.clear()
```

**Performance Requirements:**
- Topic extraction: <500ms
- Fallback on timeout: Use first 10 words
- Memory usage: Store last 5 questions only

**Integration:**
- Uses Claude API for topic extraction
- Provides context to InterruptionEngine
- Maintains conversation history for analysis



### 7. SpeechBuffer

**Purpose**: Accumulate speech transcription segments and provide text for real-time analysis.

**Class Definition:**

```python
from typing import Optional
from dataclasses import dataclass
import time

@dataclass
class TranscriptSegment:
    """A segment of transcribed speech."""
    text: str
    timestamp: float
    is_final: bool
    confidence: float

class SpeechBuffer:
    """
    Accumulates speech transcription segments for analysis.
    Manages interim and final transcripts from STT service.
    """
    
    def __init__(self, analysis_word_threshold: int = 20):
        self.analysis_word_threshold = analysis_word_threshold
        self._segments: list[TranscriptSegment] = []
        self._accumulated_text = ""
        self._word_count = 0
    
    def add_interim_segment(self, text: str, confidence: float = 0.0):
        """
        Add interim transcription segment.
        Interim segments are temporary and replaced by final segments.
        """
        # Don't store interim segments, just update display
        pass
    
    def add_final_segment(self, text: str, confidence: float = 1.0):
        """
        Add final transcription segment.
        Final segments are accumulated for analysis.
        """
        segment = TranscriptSegment(
            text=text,
            timestamp=time.time(),
            is_final=True,
            confidence=confidence
        )
        
        self._segments.append(segment)
        self._accumulated_text += " " + text
        self._accumulated_text = self._accumulated_text.strip()
        self._word_count = len(self._accumulated_text.split())
    
    def get_accumulated_text(self) -> str:
        """Get all accumulated final transcript text."""
        return self._accumulated_text
    
    def word_count(self) -> int:
        """Get current word count of accumulated text."""
        return self._word_count
    
    def should_trigger_analysis(self) -> bool:
        """Check if buffer has enough content for analysis."""
        return self._word_count >= self.analysis_word_threshold
    
    def get_segments(self) -> list[TranscriptSegment]:
        """Get all transcript segments."""
        return self._segments.copy()
    
    def get_recent_segments(self, count: int = 5) -> list[TranscriptSegment]:
        """Get most recent transcript segments."""
        return self._segments[-count:] if len(self._segments) >= count else self._segments.copy()
    
    def clear(self):
        """Clear all accumulated text and segments."""
        self._segments.clear()
        self._accumulated_text = ""
        self._word_count = 0
    
    def get_buffer_stats(self) -> dict:
        """Get buffer statistics for monitoring."""
        return {
            "total_segments": len(self._segments),
            "word_count": self._word_count,
            "accumulated_length": len(self._accumulated_text),
            "average_confidence": self._calculate_average_confidence()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all segments."""
        if not self._segments:
            return 0.0
        
        total_confidence = sum(seg.confidence for seg in self._segments)
        return total_confidence / len(self._segments)
```

**Performance Requirements:**
- Segment addition: O(1) operation
- Memory usage: Minimal (text only, no audio)
- Word count calculation: Cached, not recalculated

**Integration:**
- Receives segments from Deepgram STT service
- Provides text to AnswerAnalyzer
- Coordinates with VoiceFlowController for state management



### 8. Vertex AI Embedding Service

**Purpose**: Generate embeddings for semantic similarity calculations using Vertex AI (NOT paid Gemini API).

**Class Definition:**

```python
from google.cloud import aiplatform
from typing import Optional
import asyncio

class VertexAIEmbeddingService:
    """
    Embedding service using Vertex AI (free tier).
    NOT using paid Gemini API as per requirements.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "textembedding-gecko@003"
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
    
    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using Vertex AI.
        Returns 768-dimensional vector.
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._generate_embedding_sync,
            text
        )
        return embedding
    
    def _generate_embedding_sync(self, text: str) -> list[float]:
        """Synchronous embedding generation."""
        from vertexai.language_models import TextEmbeddingModel
        
        model = TextEmbeddingModel.from_pretrained(self.model_name)
        embeddings = model.get_embeddings([text])
        
        return embeddings[0].values
    
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        More efficient than individual calls.
        """
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._generate_embeddings_batch_sync,
            texts
        )
        return embeddings
    
    def _generate_embeddings_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding generation."""
        from vertexai.language_models import TextEmbeddingModel
        
        model = TextEmbeddingModel.from_pretrained(self.model_name)
        embeddings = model.get_embeddings(texts)
        
        return [emb.values for emb in embeddings]
```

**Performance Requirements:**
- Single embedding: <1s
- Batch embeddings: <2s for up to 5 texts
- Concurrent with Claude API calls

**Integration:**
- Used by AnswerAnalyzer for semantic similarity
- Runs concurrently with Claude evaluation
- Uses Vertex AI free tier (NOT paid Gemini)



## Data Models

### VoiceSessionState (Extended)

**Purpose**: Extended session state for real-time voice interactions.

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

@dataclass
class VoiceSessionState:
    """Extended session state for real-time voice interactions."""
    
    # Base session fields (from existing SessionState)
    session_id: str
    user_id: str
    role: str
    topics: list[str]
    difficulty: str
    mode: str
    started_at: float
    
    # Real-time voice fields
    conversation_state: ConversationState
    current_question: Optional[str] = None
    current_question_topic: Optional[str] = None
    speech_buffer_text: str = ""
    interruption_count: int = 0
    silence_duration: float = 0.0
    presence_check_attempts: int = 0
    
    # Transcript history
    transcript_segments: list[dict] = field(default_factory=list)
    
    # Audio recordings (GridFS file IDs)
    audio_recordings: list[str] = field(default_factory=list)
    
    # Service failure tracking
    stt_failures: int = 0
    tts_failures: int = 0
    claude_failures: int = 0
    vertex_ai_failures: int = 0
    
    # Performance metrics
    total_analysis_time: float = 0.0
    total_interruptions: int = 0
    average_response_latency: float = 0.0
```

### SilenceEvent

```python
@dataclass
class SilenceEvent:
    """Event emitted when silence is detected."""
    duration: float
    timestamp: float
    context: str  # "prolonged" or "answer_complete"
    audio_level_db: float
```

### PresenceCheckResult

```python
@dataclass
class PresenceCheckResult:
    """Result of presence verification."""
    confirmed: bool
    attempts: int
    response_text: Optional[str]
    confidence: float
    timestamp: float
```

### AnalysisResult

```python
@dataclass
class AnalysisResult:
    """Result of answer relevance analysis."""
    is_relevant: bool
    semantic_similarity: float
    should_interrupt: bool
    interruption_message: Optional[str]
    confidence: float
    analysis_duration: float
    claude_response: dict
    embedding_similarity: float
```

### InterruptionContext

```python
@dataclass
class InterruptionContext:
    """Context for generating interruption messages."""
    question_topic: str
    off_topic_content: str
    attempt_number: int
    previous_interruptions: list[str]
    timestamp: float
```

### TranscriptSegment

```python
@dataclass
class TranscriptSegment:
    """A segment of transcribed speech."""
    text: str
    timestamp: float
    is_final: bool
    confidence: float
    speaker: str  # "user" or "agent"
    word_count: int
```

### QuestionContext

```python
@dataclass
class QuestionContext:
    """Context information for a question."""
    full_question: str
    core_topic: str
    keywords: list[str]
    timestamp: float
    expected_answer_length: Optional[int] = None
```



## API Endpoints (FastAPI)

### 1. Start Real-Time Voice Session

**Endpoint:** `POST /session/{session_id}/voice/realtime/start`

**Purpose:** Initialize real-time voice interaction for a session.

**Request Body:**
```json
{
  "enable_interruptions": true,
  "max_interruptions_per_question": 2,
  "silence_threshold_seconds": 10.0,
  "answer_complete_threshold_seconds": 3.0
}
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "websocket_url": "wss://api.roundzero.com/session/sess_abc123/voice/realtime/stream",
  "deepgram_config": {
    "model": "nova-2",
    "language": "en-US",
    "interim_results": true
  },
  "state": "IDLE",
  "rate_limit_remaining": 9
}
```

**Implementation:**
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class StartRealTimeVoiceRequest(BaseModel):
    enable_interruptions: bool = True
    max_interruptions_per_question: int = 2
    silence_threshold_seconds: float = 10.0
    answer_complete_threshold_seconds: float = 3.0

@router.post("/session/{session_id}/voice/realtime/start")
async def start_realtime_voice(
    session_id: str,
    request: StartRealTimeVoiceRequest,
    cache_service: CacheService = Depends(get_cache_service),
    user_id: str = Depends(get_current_user_id)
):
    """Initialize real-time voice interaction."""
    
    # Check rate limit
    is_allowed, remaining = await cache_service.check_rate_limit(
        user_id=user_id,
        limit=10,
        window=86400
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Daily session limit reached. Try again tomorrow."
        )
    
    # Initialize voice flow controller
    voice_controller = await initialize_voice_controller(
        session_id=session_id,
        config=request
    )
    
    # Store in session registry
    await register_voice_session(session_id, voice_controller)
    
    return {
        "session_id": session_id,
        "websocket_url": f"wss://api.roundzero.com/session/{session_id}/voice/realtime/stream",
        "deepgram_config": {
            "model": "nova-2",
            "language": "en-US",
            "interim_results": True
        },
        "state": "IDLE",
        "rate_limit_remaining": remaining
    }
```



### 2. WebSocket Stream Endpoint

**Endpoint:** `WebSocket /session/{session_id}/voice/realtime/stream`

**Purpose:** Real-time bidirectional communication for voice interaction.

**Message Types:**

**Client → Server:**
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "timestamp": 1705315800.123
}
```

```json
{
  "type": "transcript_segment",
  "text": "This is what I said",
  "is_final": true,
  "confidence": 0.95
}
```

```json
{
  "type": "answer_complete",
  "timestamp": 1705315800.123
}
```

**Server → Client:**
```json
{
  "type": "state_change",
  "old_state": "LISTENING",
  "new_state": "ANALYZING",
  "timestamp": 1705315800.123
}
```

```json
{
  "type": "question",
  "text": "What is the value of four plus two?",
  "audio_url": "https://cdn.roundzero.com/audio/q123.mp3",
  "topic": "the mathematical calculation"
}
```

```json
{
  "type": "interruption",
  "message": "Wait, I asked about the mathematical calculation, please focus on that",
  "audio_url": "https://cdn.roundzero.com/audio/int456.mp3",
  "attempt": 1
}
```

```json
{
  "type": "presence_check",
  "message": "Hey, can you hear me?",
  "audio_url": "https://cdn.roundzero.com/audio/presence.mp3",
  "attempt": 1
}
```

```json
{
  "type": "silence_detected",
  "duration": 10.5,
  "context": "prolonged"
}
```

```json
{
  "type": "analysis_result",
  "is_relevant": false,
  "semantic_similarity": 0.25,
  "should_interrupt": true
}
```

**Implementation:**
```python
from fastapi import WebSocket, WebSocketDisconnect
import json

@router.websocket("/session/{session_id}/voice/realtime/stream")
async def realtime_voice_stream(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for real-time voice interaction."""
    
    await websocket.accept()
    
    # Get voice controller for this session
    voice_controller = await get_voice_controller(session_id)
    
    if not voice_controller:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    # Register WebSocket with controller
    voice_controller.set_websocket(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] == "transcript_segment":
                await voice_controller.handle_speech_input(
                    transcript_segment=message["text"],
                    is_final=message["is_final"]
                )
            
            elif message["type"] == "answer_complete":
                await voice_controller.handle_silence_detected(3.0)
            
            elif message["type"] == "audio_chunk":
                # Process audio for silence detection
                audio_level = await calculate_audio_level(message["data"])
                await voice_controller.silence_detector.process_audio_level(
                    audio_level
                )
    
    except WebSocketDisconnect:
        # Cleanup on disconnect
        await cleanup_voice_session(session_id)
    
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        await cleanup_voice_session(session_id)
```



### 3. Manual Interruption Endpoint

**Endpoint:** `POST /session/{session_id}/voice/realtime/interrupt`

**Purpose:** Allow manual interruption trigger (for testing or emergency stop).

**Request Body:**
```json
{
  "reason": "manual_stop",
  "message": "Let me stop you there"
}
```

**Response:**
```json
{
  "success": true,
  "interruption_sent": true,
  "new_state": "INTERRUPTING"
}
```

**Implementation:**
```python
class ManualInterruptRequest(BaseModel):
    reason: str
    message: Optional[str] = None

@router.post("/session/{session_id}/voice/realtime/interrupt")
async def manual_interrupt(
    session_id: str,
    request: ManualInterruptRequest
):
    """Manually trigger interruption."""
    
    voice_controller = await get_voice_controller(session_id)
    
    if not voice_controller:
        raise HTTPException(status_code=404, detail="Session not found")
    
    message = request.message or "Let me stop you there"
    
    await voice_controller.handle_off_topic_detected(message)
    
    return {
        "success": True,
        "interruption_sent": True,
        "new_state": voice_controller.state.conversation_state.value
    }
```

### 4. Session Status Endpoint

**Endpoint:** `GET /session/{session_id}/voice/realtime/status`

**Purpose:** Get current status of real-time voice session.

**Response:**
```json
{
  "session_id": "sess_abc123",
  "state": "LISTENING",
  "current_question": "What is the value of four plus two?",
  "current_question_topic": "the mathematical calculation",
  "speech_buffer_word_count": 15,
  "interruption_count": 0,
  "silence_duration": 0.0,
  "presence_check_attempts": 0,
  "performance_metrics": {
    "total_analysis_time": 1.5,
    "average_response_latency": 0.8,
    "stt_failures": 0,
    "tts_failures": 0,
    "claude_failures": 0
  }
}
```

**Implementation:**
```python
@router.get("/session/{session_id}/voice/realtime/status")
async def get_realtime_status(session_id: str):
    """Get current status of real-time voice session."""
    
    voice_controller = await get_voice_controller(session_id)
    
    if not voice_controller:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": voice_controller.state.conversation_state.value,
        "current_question": voice_controller.state.current_question,
        "current_question_topic": voice_controller.state.current_question_topic,
        "speech_buffer_word_count": voice_controller.speech_buffer.word_count(),
        "interruption_count": voice_controller.state.interruption_count,
        "silence_duration": voice_controller.silence_detector.get_current_silence_duration(),
        "presence_check_attempts": voice_controller.state.presence_check_attempts,
        "performance_metrics": {
            "total_analysis_time": voice_controller.state.total_analysis_time,
            "average_response_latency": voice_controller.state.average_response_latency,
            "stt_failures": voice_controller.state.stt_failures,
            "tts_failures": voice_controller.state.tts_failures,
            "claude_failures": voice_controller.state.claude_failures
        }
    }
```



## Frontend Components (React)

### 1. RealTimeVoicePanel

**Purpose:** Main container component for real-time voice interaction UI.

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface RealTimeVoicePanelProps {
  sessionId: string;
  onComplete: () => void;
}

interface VoiceState {
  conversationState: string;
  currentQuestion: string | null;
  currentQuestionTopic: string | null;
  isRecording: boolean;
  isSpeaking: boolean;
  silenceDuration: number;
  interruptionCount: number;
}

export const RealTimeVoicePanel: React.FC<RealTimeVoicePanelProps> = ({
  sessionId,
  onComplete
}) => {
  const [voiceState, setVoiceState] = useState<VoiceState>({
    conversationState: 'IDLE',
    currentQuestion: null,
    currentQuestionTopic: null,
    isRecording: false,
    isSpeaking: false,
    silenceDuration: 0,
    interruptionCount: 0
  });
  
  const [transcript, setTranscript] = useState<string>('');
  const [showPresenceCheck, setShowPresenceCheck] = useState(false);
  const [showInterruption, setShowInterruption] = useState(false);
  const [interruptionMessage, setInterruptionMessage] = useState('');
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  
  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    `wss://api.roundzero.com/session/${sessionId}/voice/realtime/stream`
  );
  
  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(JSON.parse(lastMessage.data));
    }
  }, [lastMessage]);
  
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'state_change':
        setVoiceState(prev => ({
          ...prev,
          conversationState: message.new_state
        }));
        break;
      
      case 'question':
        setVoiceState(prev => ({
          ...prev,
          currentQuestion: message.text,
          currentQuestionTopic: message.topic,
          isSpeaking: true
        }));
        playAudio(message.audio_url);
        break;
      
      case 'interruption':
        setInterruptionMessage(message.message);
        setShowInterruption(true);
        playAudio(message.audio_url);
        setVoiceState(prev => ({
          ...prev,
          interruptionCount: message.attempt
        }));
        break;
      
      case 'presence_check':
        setShowPresenceCheck(true);
        playAudio(message.audio_url);
        break;
      
      case 'silence_detected':
        setVoiceState(prev => ({
          ...prev,
          silenceDuration: message.duration
        }));
        break;
    }
  };
  
  const playAudio = async (audioUrl: string) => {
    if (audioRef.current) {
      audioRef.current.src = audioUrl;
      await audioRef.current.play();
      audioRef.current.onended = () => {
        setVoiceState(prev => ({ ...prev, isSpeaking: false }));
      };
    }
  };
  
  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    
    mediaRecorder.ondataavailable = (event) => {
      // Send audio chunks via WebSocket
      const reader = new FileReader();
      reader.onloadend = () => {
        sendMessage(JSON.stringify({
          type: 'audio_chunk',
          data: reader.result,
          timestamp: Date.now() / 1000
        }));
      };
      reader.readAsDataURL(event.data);
    };
    
    mediaRecorder.start(100); // 100ms chunks
    setVoiceState(prev => ({ ...prev, isRecording: true }));
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setVoiceState(prev => ({ ...prev, isRecording: false }));
    }
  };
  
  return (
    <div className="real-time-voice-panel">
      <audio ref={audioRef} />
      
      <div className="question-display">
        {voiceState.currentQuestion && (
          <div className="current-question">
            <h3>{voiceState.currentQuestion}</h3>
            {voiceState.currentQuestionTopic && (
              <p className="topic">Topic: {voiceState.currentQuestionTopic}</p>
            )}
          </div>
        )}
      </div>
      
      <TranscriptStream
        transcript={transcript}
        isRecording={voiceState.isRecording}
      />
      
      <SilenceIndicator
        duration={voiceState.silenceDuration}
        threshold={10.0}
      />
      
      {showInterruption && (
        <InterruptionOverlay
          message={interruptionMessage}
          onClose={() => setShowInterruption(false)}
        />
      )}
      
      {showPresenceCheck && (
        <PresenceCheckDialog
          onResponse={() => setShowPresenceCheck(false)}
        />
      )}
      
      <div className="controls">
        <button
          onClick={voiceState.isRecording ? stopRecording : startRecording}
          className={voiceState.isRecording ? 'recording' : ''}
        >
          {voiceState.isRecording ? 'Stop' : 'Start'} Recording
        </button>
        
        <div className="state-indicator">
          State: {voiceState.conversationState}
        </div>
        
        <div className="interruption-counter">
          Interruptions: {voiceState.interruptionCount} / 2
        </div>
      </div>
    </div>
  );
};
```



### 2. SilenceIndicator

```typescript
interface SilenceIndicatorProps {
  duration: number;
  threshold: number;
}

export const SilenceIndicator: React.FC<SilenceIndicatorProps> = ({
  duration,
  threshold
}) => {
  const percentage = Math.min((duration / threshold) * 100, 100);
  
  return (
    <div className="silence-indicator">
      <div className="silence-bar">
        <div
          className="silence-progress"
          style={{
            width: `${percentage}%`,
            backgroundColor: percentage > 80 ? '#ff4444' : '#4CAF50'
          }}
        />
      </div>
      <span className="silence-duration">
        {duration > 0 ? `${duration.toFixed(1)}s silence` : 'Speaking...'}
      </span>
    </div>
  );
};
```

### 3. TranscriptStream

```typescript
interface TranscriptStreamProps {
  transcript: string;
  isRecording: boolean;
}

export const TranscriptStream: React.FC<TranscriptStreamProps> = ({
  transcript,
  isRecording
}) => {
  const transcriptRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    // Auto-scroll to bottom
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcript]);
  
  return (
    <div className="transcript-stream" ref={transcriptRef}>
      <div className="transcript-content">
        {transcript || 'Start speaking to see your transcript...'}
      </div>
      {isRecording && (
        <div className="recording-indicator">
          <span className="pulse-dot" />
          Recording...
        </div>
      )}
    </div>
  );
};
```

### 4. InterruptionOverlay

```typescript
interface InterruptionOverlayProps {
  message: string;
  onClose: () => void;
}

export const InterruptionOverlay: React.FC<InterruptionOverlayProps> = ({
  message,
  onClose
}) => {
  useEffect(() => {
    // Auto-close after 3 seconds
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);
  
  return (
    <div className="interruption-overlay">
      <div className="interruption-content">
        <div className="interruption-icon">⚠️</div>
        <p className="interruption-message">{message}</p>
      </div>
    </div>
  );
};
```

### 5. PresenceCheckDialog

```typescript
interface PresenceCheckDialogProps {
  onResponse: () => void;
}

export const PresenceCheckDialog: React.FC<PresenceCheckDialogProps> = ({
  onResponse
}) => {
  return (
    <div className="presence-check-dialog">
      <div className="presence-check-content">
        <h3>Can you hear me?</h3>
        <p>Please respond verbally if you can hear the interviewer.</p>
        <div className="listening-animation">
          <span className="pulse-ring" />
          Listening...
        </div>
      </div>
    </div>
  );
};
```



## Error Handling

### Graceful Degradation Strategy

The system implements multiple fallback layers to ensure interview continuity:

**Service Failure Handling:**

1. **Deepgram STT Failure**
   - Fallback: Switch to text-only input mode
   - User notification: "Voice recognition unavailable. Please type your answers."
   - Retry: Attempt reconnection every 30 seconds
   - Max retries: 3 attempts

2. **ElevenLabs TTS Failure**
   - Fallback: Display questions as text without audio
   - User notification: "Voice output unavailable. Questions will be shown as text."
   - Retry: Attempt reconnection for next question
   - Max retries: 3 attempts

3. **Claude API Failure**
   - Fallback: Accept answers without real-time analysis
   - Retry: Exponential backoff (1s, 2s, 4s)
   - Max retries: 3 attempts
   - Degraded mode: Store answers for later evaluation

4. **Vertex AI Failure**
   - Fallback: Rely solely on Claude evaluation
   - No interruption based on semantic similarity
   - Continue with Claude-only analysis

5. **Network Connection Loss**
   - Local state persistence in browser localStorage
   - Auto-sync when connection restored
   - Resume from last known state

**Error Recovery Flow:**

```mermaid
graph TD
    A[Service Failure Detected] --> B{Critical Service?}
    B -->|Yes| C[Attempt Retry]
    B -->|No| D[Continue with Degradation]
    C --> E{Retry Successful?}
    E -->|Yes| F[Resume Normal Operation]
    E -->|No| G{Max Retries?}
    G -->|No| C
    G -->|Yes| H[Switch to Fallback Mode]
    H --> I[Notify User]
    D --> I
    I --> J[Continue Interview]
```

### Error Logging

All errors are logged with context for debugging:

```python
@dataclass
class ErrorLog:
    """Error log entry."""
    timestamp: float
    error_type: str
    service: str
    error_message: str
    session_id: str
    conversation_state: str
    retry_attempt: int
    fallback_activated: bool
```



## Testing Strategy

### Dual Testing Approach

The real-time voice interaction feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests:**
- Specific example scenarios (mathematical question, presence verification)
- Edge cases (service failures, max interruptions reached, connection loss)
- Integration points between components
- UI component rendering and interactions
- Error handling paths

**Property-Based Tests:**
- Universal properties that hold for all inputs
- State machine transitions
- Silence detection across various audio levels
- Answer analysis with random question-answer pairs
- Interruption limiting logic
- Buffer accumulation behavior

### Property-Based Testing Configuration

**Library:** `hypothesis` for Python backend, `fast-check` for TypeScript frontend

**Configuration:**
- Minimum 100 iterations per property test
- Each test references its design document property
- Tag format: `Feature: real-time-voice-interaction, Property {number}: {property_text}`

**Example Property Test:**

```python
from hypothesis import given, strategies as st
import pytest

# Feature: real-time-voice-interaction, Property 1: Silence detection reset
@given(st.floats(min_value=-60.0, max_value=0.0))
async def test_silence_detector_resets_on_speech(audio_level_db):
    """
    Property: For any audio level above threshold, silence timer should reset.
    Validates: Requirements 2.3
    """
    detector = SilenceDetector(silence_threshold_db=-40.0)
    await detector.start_monitoring()
    
    # Simulate silence
    await detector.process_audio_level(-50.0)
    await asyncio.sleep(0.2)
    
    # Simulate speech
    await detector.process_audio_level(audio_level_db)
    
    # Property: Timer should be reset
    assert detector.get_current_silence_duration() == 0.0
```

### Test Coverage Goals

- Unit test coverage: >80% for all components
- Property test coverage: All state transitions and core logic
- Integration test coverage: Complete user flows
- E2E test coverage: Critical paths (start → question → answer → evaluation)



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies and consolidations:

**Redundancies Eliminated:**
- Properties about "starting monitoring" and "resetting timer" can be combined into a single state management property
- Multiple properties about "audio generation" and "audio playback" can be consolidated into TTS pipeline properties
- Properties about "storing data" across different entities can be unified into persistence properties
- Properties about "triggering next action" can be combined into state transition properties

**Consolidated Properties:**
- Silence detection behavior (combines reset, restart, threshold checks)
- TTS pipeline (combines generation, caching, playback)
- Interruption lifecycle (combines generation, delivery, cleanup)
- Data persistence (combines logging, storage across different entities)

### Core Properties

### Property 1: Silence Detection State Management

*For any* audio input stream, when audio level exceeds the silence threshold (-40dB), the silence timer SHALL reset to zero, and when audio level falls below threshold, the silence timer SHALL start/restart counting.

**Validates: Requirements 2.2, 2.3, 2.4, 2.6**

### Property 2: Silence Event Emission

*For any* continuous silence period, when the duration reaches 10 seconds, a "silence_detected" event SHALL be emitted, and brief pauses under 2 seconds SHALL NOT trigger silence events.

**Validates: Requirements 2.5, 2.7**

### Property 3: Presence Verification Trigger

*For any* "silence_detected" event with context "prolonged", the Presence Verifier SHALL generate a presence check message and initiate the verification flow.

**Validates: Requirements 2.8, 3.1**

### Property 4: Affirmative Response Recognition

*For any* candidate response to "Can you hear me?", if the response contains affirmative intent (variations of "yes", "I can", "I hear you"), the Presence Verifier SHALL mark presence as confirmed.

**Validates: Requirements 3.6, 3.10**

### Property 5: Presence Confirmation Flow

*For any* confirmed presence check, the AI Interviewer SHALL proceed with delivering or repeating the interview question.

**Validates: Requirements 3.7**

### Property 6: Speech Transcription Pipeline

*For any* candidate speech input, the Deepgram STT SHALL generate transcription segments, interim results SHALL be displayed in real-time, and final results SHALL replace interim text in the transcript display.

**Validates: Requirements 4.1, 4.3, 4.5**

### Property 7: Speech Buffer Accumulation

*For any* final transcription segment, the Speech Buffer SHALL accumulate the text, and all final segments SHALL be available for answer analysis.

**Validates: Requirements 4.6**

### Property 8: Analysis Trigger Threshold

*For any* Speech Buffer state, when the accumulated word count reaches or exceeds 20 words, the Answer Analyzer SHALL begin relevance analysis.

**Validates: Requirements 5.1**

### Property 9: Dual Analysis Execution

*For any* relevance analysis request, the Answer Analyzer SHALL send both the question and accumulated answer to Claude API for evaluation AND calculate semantic similarity using Vertex AI embeddings, executing both operations concurrently.

**Validates: Requirements 5.2, 5.4, 5.5**

### Property 10: Off-Topic Detection

*For any* answer analysis result, if semantic similarity is below 0.3 OR Claude determines the answer is off-topic, the Answer Analyzer SHALL flag the answer as off-topic and trigger the Interruption Engine.

**Validates: Requirements 5.6, 5.7**

### Property 11: Question Context Preservation

*For any* ongoing answer analysis, the original question text and extracted topic SHALL remain accessible throughout all analysis iterations.

**Validates: Requirements 5.9**

### Property 12: Interruption Message Generation

*For any* off-topic detection, if the interruption count is below the maximum (2), the Interruption Engine SHALL generate a context-aware interruption message that explicitly references the question topic.

**Validates: Requirements 6.1, 6.2**

### Property 13: Interruption Delivery Pipeline

*For any* generated interruption message, the system SHALL convert it to audio via TTS, immediately play the audio (overriding ongoing speech), pause STT during playback, and resume STT after completion.

**Validates: Requirements 6.4, 6.5, 6.6, 6.7**

### Property 14: Interruption Cleanup

*For any* completed interruption, the Speech Buffer SHALL be cleared and the Silence Detector SHALL reset to begin monitoring for the redirected response.

**Validates: Requirements 6.8, 6.9**

### Property 15: Interruption Limiting

*For any* question, the Interruption Engine SHALL allow a maximum of 2 interruptions, and subsequent off-topic detections SHALL NOT trigger additional interruptions.

**Validates: Requirements 6.10, 17.1-17.4**

### Property 16: Topic Extraction

*For any* interview question, the Context Tracker SHALL extract a core topic phrase of 3-7 words using Claude API, and store it alongside the full question text.

**Validates: Requirements 7.1, 7.2, 7.5**

### Property 17: Topic Usage in Interruptions

*For any* interruption message generation, the Interruption Engine SHALL include the extracted core topic from the Context Tracker.

**Validates: Requirements 7.6**

### Property 18: Context History Management

*For any* sequence of questions, the Context Tracker SHALL maintain a history of the last 5 questions with their core topics, automatically removing older entries when the limit is exceeded.

**Validates: Requirements 7.9**

### Property 19: TTS Audio Pipeline

*For any* text content (question, interruption, presence check), the ElevenLabs TTS SHALL convert it to audio, and the system SHALL play the audio through the output device.

**Validates: Requirements 3.3, 3.4, 6.4, 8.2, 8.4**

### Property 20: Question Delivery Flow

*For any* question to be asked, the system SHALL fetch it from the database, convert to audio via TTS, display the text on screen, play the audio, and begin silence monitoring when audio completes.

**Validates: Requirements 8.1, 8.2, 8.4, 8.5, 8.6**

### Property 21: TTS Caching

*For any* repeated text content (common questions, presence checks), the system SHALL use cached audio if available, reducing redundant TTS API calls.

**Validates: Requirements 8.9**

### Property 22: Answer Completion Detection

*For any* candidate speech, when silence duration reaches 3 seconds, the Voice Flow Controller SHALL consider the answer potentially complete and trigger final evaluation.

**Validates: Requirements 9.1, 9.2**

### Property 23: Completion Evaluation

*For any* potentially complete answer, the Answer Analyzer SHALL perform a final completeness check using Claude API to determine if the answer sufficiently addresses the question.

**Validates: Requirements 9.3**

### Property 24: Complete Answer Progression

*For any* answer determined to be complete and on-topic, the Voice Flow Controller SHALL proceed to final answer evaluation and scoring.

**Validates: Requirements 9.5**

### Property 25: Incomplete Answer Follow-up

*For any* answer determined to be incomplete, the AI Interviewer SHALL generate and ask a follow-up question for clarification.

**Validates: Requirements 9.6**

### Property 26: Manual Completion Trigger

*For any* "Done Answering" button click, the Voice Flow Controller SHALL immediately proceed to answer evaluation regardless of silence duration.

**Validates: Requirements 9.9**

### Property 27: Brief Pause Tolerance

*For any* pause in candidate speech, if the duration is less than 3 seconds, the completion detection SHALL NOT trigger.

**Validates: Requirements 9.10**

### Property 28: Low Confidence Warning

*For any* transcription segment with confidence score below 0.7, the system SHALL display a confidence warning indicator in the UI.

**Validates: Requirements 4.10**

### Property 29: Session Data Persistence

*For any* interview session event (question asked, answer given, interruption triggered, presence check performed), the system SHALL log the event with timestamp and store it in the session database.

**Validates: Requirements 12.3, 12.4, 12.5, 12.6**

### Property 30: Audio Recording Storage

*For any* candidate answer audio (when consent is given), the system SHALL store the recording in MongoDB GridFS with metadata including session ID, question index, and duration.

**Validates: Requirements 12.8**

### Property 31: Transcript History Maintenance

*For any* speech segment (user or agent), the system SHALL maintain a complete transcript history with speaker labels, timestamps, and confidence scores.

**Validates: Requirements 12.9**

### Property 32: Rate Limiting Enforcement

*For any* user, the system SHALL enforce a maximum of 10 interview sessions per day, tracked via Redis cache, and reject session creation when the limit is exceeded.

**Validates: Requirements 13.1, 13.2, 13.3**

### Property 33: API Call Rate Limiting

*For any* session, the system SHALL limit Claude API calls to 5 per minute and Vertex AI calls to 10 per minute, implementing exponential backoff for retries.

**Validates: Requirements 13.6, 13.7, 13.8**

### Property 34: Relevance Score Logging

*For any* relevance analysis performed, the system SHALL log the semantic similarity score, Claude evaluation result, and timestamp for post-interview analysis.

**Validates: Requirements 5.10**

### Property 35: State Transition Validity

*For any* conversation state transition, the new state SHALL be a valid successor of the current state according to the state machine definition, and all registered state change handlers SHALL be notified.

**Validates: State machine architecture requirements**



## Security Considerations

### API Key Protection

**Backend (FastAPI):**
- All API keys stored in environment variables (`.env` file)
- Never expose keys to frontend
- Use backend proxy for all external API calls
- Rotate keys regularly

**Environment Variables Required:**
```bash
# Deepgram STT
DEEPGRAM_API_KEY=your_key_here

# ElevenLabs TTS
ELEVENLABS_API_KEY=your_key_here

# Anthropic Claude
ANTHROPIC_API_KEY=your_key_here

# Google Cloud (Vertex AI)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your_project_id

# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# NeonDB
NEONDB_URL=postgresql://user:pass@host/database

# Upstash Redis
REDIS_URL=redis://default:pass@host:port
```

### Input Sanitization

**User Input Validation:**
- Sanitize all transcript text before sending to AI services
- Validate audio data format and size
- Limit transcript segment length (max 1000 characters)
- Escape special characters in database queries

**Example Sanitization:**
```python
def sanitize_transcript(text: str) -> str:
    """Sanitize user transcript input."""
    # Remove control characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # Limit length
    max_length = 1000
    if len(text) > max_length:
        text = text[:max_length]
    
    # Escape SQL injection attempts
    text = text.replace("'", "''")
    
    return text.strip()
```

### Authentication and Authorization

**Session Access Control:**
- Verify user authentication before starting real-time session
- Validate session ownership before WebSocket connection
- Implement JWT token validation for API endpoints
- Rate limit per authenticated user

**WebSocket Security:**
```python
@router.websocket("/session/{session_id}/voice/realtime/stream")
async def realtime_voice_stream(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...)
):
    """Secure WebSocket with token validation."""
    
    # Validate JWT token
    user_id = await validate_jwt_token(token)
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Verify session ownership
    session = await get_session(session_id)
    if session.user_id != user_id:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Proceed with connection
    await websocket.accept()
    # ...
```

### Data Encryption

**Audio Storage:**
- Encrypt audio recordings at rest in MongoDB GridFS
- Use AES-256 encryption
- Store encryption keys in secure key management service

**Transcript Storage:**
- Encrypt sensitive transcript data in NeonDB
- Use database-level encryption
- Implement field-level encryption for PII

### GDPR Compliance

**Data Retention:**
- Automatically delete audio recordings after 90 days
- Provide user data export functionality
- Implement right-to-be-forgotten (data deletion)

**User Consent:**
- Explicit consent for audio recording
- Clear privacy policy disclosure
- Opt-in for data retention beyond session



## Performance Optimization

### Latency Budget

Total target: <5s from answer completion to next question

**Breakdown:**
- Answer completion detection: 3s (silence threshold)
- Final evaluation (Claude): <2s
- Embedding generation (Vertex AI): <1s (concurrent with Claude)
- Next question fetch: <100ms (cached or preloaded)
- TTS generation: <1.5s (cached for common questions)
- Audio playback: Variable (depends on question length)

**Optimization Strategies:**

1. **Concurrent Operations:**
   - Run Claude evaluation and Vertex AI embeddings in parallel
   - Preload next question while user is answering current question
   - Generate TTS audio in background while evaluation completes

2. **Caching:**
   - Cache common TTS audio (greetings, presence checks, common questions)
   - Cache question data in Redis (1 hour TTL)
   - Cache evaluation results for identical Q&A pairs (1 hour TTL)

3. **Connection Pooling:**
   - MongoDB: 10-50 connections
   - NeonDB: 5-20 connections
   - Redis: 50 connections
   - Reuse connections across requests

4. **Async Operations:**
   - All I/O operations use async/await
   - Non-blocking database queries
   - Concurrent API calls where possible

### Memory Management

**Speech Buffer:**
- Clear buffer after each question
- Limit accumulated text to 5000 characters
- No audio buffering (stream directly to STT)

**Audio Cache:**
- Limit TTS cache to 50MB
- LRU eviction policy
- Clear cache on session end

**Connection Management:**
- Close idle connections after 5 minutes
- Implement connection health checks
- Graceful shutdown with connection cleanup

### Monitoring and Metrics

**Key Metrics to Track:**
- Average response latency (target: <5s)
- STT transcription latency (target: <500ms)
- TTS generation latency (target: <1.5s)
- Claude API latency (target: <2s)
- Vertex AI latency (target: <1s)
- WebSocket connection stability
- Cache hit rate (target: >60%)
- Service failure rate (target: <1%)

**Monitoring Implementation:**
```python
from dataclasses import dataclass
import time

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    total_response_time: float
    stt_latency: float
    tts_latency: float
    claude_latency: float
    vertex_ai_latency: float
    cache_hit: bool
    timestamp: float

class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
    
    async def record_response_cycle(
        self,
        start_time: float,
        stt_latency: float,
        tts_latency: float,
        claude_latency: float,
        vertex_ai_latency: float,
        cache_hit: bool
    ):
        """Record complete response cycle metrics."""
        total_time = time.time() - start_time
        
        metrics = PerformanceMetrics(
            total_response_time=total_time,
            stt_latency=stt_latency,
            tts_latency=tts_latency,
            claude_latency=claude_latency,
            vertex_ai_latency=vertex_ai_latency,
            cache_hit=cache_hit,
            timestamp=time.time()
        )
        
        self.metrics.append(metrics)
        
        # Alert if exceeding budget
        if total_time > 5.0:
            await self.send_alert(f"Response time exceeded budget: {total_time:.2f}s")
    
    def get_average_latency(self) -> float:
        """Calculate average response latency."""
        if not self.metrics:
            return 0.0
        return sum(m.total_response_time for m in self.metrics) / len(self.metrics)
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if not self.metrics:
            return 0.0
        hits = sum(1 for m in self.metrics if m.cache_hit)
        return hits / len(self.metrics)
```

