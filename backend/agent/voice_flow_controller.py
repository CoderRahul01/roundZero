"""
Voice Flow Controller

Orchestrates the entire real-time voice interaction flow, managing state
transitions and coordinating all components.
"""

import asyncio
import time
from typing import Optional, Callable
from anthropic import AsyncAnthropic

from agent.realtime_models import (
    ConversationState,
    VoiceFlowState,
    SilenceEvent,
    PresenceCheckResult,
    AnalysisResult,
    InterruptionContext
)
from agent.silence_detector import SilenceDetector
from agent.presence_verifier import PresenceVerifier
from agent.answer_analyzer import AnswerAnalyzer
from agent.interruption_engine import InterruptionEngine
from agent.context_tracker import ContextTracker
from agent.speech_buffer import SpeechBuffer


class VoiceFlowController:
    """
    Orchestrates real-time voice interaction flow.
    Manages state machine and coordinates all components.
    """
    
    def __init__(
        self,
        session_id: str,
        silence_detector: SilenceDetector,
        presence_verifier: PresenceVerifier,
        answer_analyzer: AnswerAnalyzer,
        interruption_engine: InterruptionEngine,
        context_tracker: ContextTracker,
        speech_buffer: SpeechBuffer,
        tts_service,
        stt_service
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
        
        # WebSocket connection
        self._websocket = None
    
    def set_websocket(self, websocket):
        """Set WebSocket connection for sending messages to client."""
        self._websocket = websocket
    
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
        
        # Send question to client
        if self._websocket:
            await self._websocket.send_json({
                "type": "question",
                "text": first_question,
                "topic": self.state.current_question_topic
            })
        
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
            if self.speech_buffer.should_trigger_analysis():
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
        
        # Send interruption to client
        if self._websocket:
            await self._websocket.send_json({
                "type": "interruption",
                "message": interruption_message,
                "attempt": self.state.interruption_count + 1
            })
        
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
        self.interruption_engine.reset_for_new_question()
        
        # Move to next question or complete
        # ... (integration with existing interview flow)
    
    async def _transition_to(self, new_state: ConversationState):
        """Handle state transition with event notification."""
        old_state = self.state.conversation_state
        self.state.conversation_state = new_state
        
        # Send state change to client
        if self._websocket:
            await self._websocket.send_json({
                "type": "state_change",
                "old_state": old_state.value,
                "new_state": new_state.value,
                "timestamp": time.time()
            })
        
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
