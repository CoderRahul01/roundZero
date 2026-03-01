"""
RoundZeroAgent - Main orchestrator for live interview sessions.

This module coordinates all processors and services to conduct
intelligent, multimodal AI interviews.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from agent.vision.processors.emotion_processor import EmotionProcessor
from agent.vision.processors.speech_processor import SpeechProcessor
from agent.vision.core.decision_engine import DecisionEngine
from agent.vision.core.question_manager import QuestionManager

logger = logging.getLogger(__name__)


class InterviewAction:
    """Enum for interview actions."""
    CONTINUE = "CONTINUE"
    INTERRUPT = "INTERRUPT"
    ENCOURAGE = "ENCOURAGE"
    NEXT = "NEXT"
    HINT = "HINT"


class RoundZeroAgent:
    """
    Main orchestrator for live interview sessions.
    Coordinates EmotionProcessor, SpeechProcessor, and DecisionEngine.
    
    Features:
    - Multimodal context analysis
    - Intelligent decision-making
    - Question progression
    - Session summary generation
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
        decision_engine: DecisionEngine,
        question_manager: QuestionManager,
        tts_service,
        mongo_repository,
        supermemory_client=None
    ):
        """
        Initialize RoundZeroAgent.
        
        Args:
            session_id: Session identifier
            candidate_id: Candidate identifier
            role: Interview role
            topics: Interview topics
            difficulty: Question difficulty
            mode: Interview mode
            emotion_processor: EmotionProcessor instance
            speech_processor: SpeechProcessor instance
            decision_engine: DecisionEngine instance
            question_manager: QuestionManager instance
            tts_service: TTS service for AI speech
            mongo_repository: MongoDB repository
            supermemory_client: Optional Supermemory client
        """
        self.session_id = session_id
        self.candidate_id = candidate_id
        self.role = role
        self.topics = topics
        self.difficulty = difficulty
        self.mode = mode
        
        # Processors and services
        self.emotion_processor = emotion_processor
        self.speech_processor = speech_processor
        self.decision_engine = decision_engine
        self.question_manager = question_manager
        self.tts_service = tts_service
        self.mongo_repository = mongo_repository
        self.supermemory_client = supermemory_client
        
        # State
        self.questions: List[Dict[str, Any]] = []
        self.current_question_index = 0
        self.transcript_buffer = ""
        self.word_count = 0
        self.candidate_memory: Optional[Dict] = None
        self.ai_state = "idle"  # idle, listening, thinking, speaking
        
        logger.info(
            f"Initialized RoundZeroAgent for session {session_id} "
            f"(role={role}, difficulty={difficulty})"
        )

    
    async def initialize(self) -> None:
        """
        Initialize agent: fetch questions and candidate memory.
        """
        try:
            # Fetch questions from Pinecone
            query_text = f"{self.role} {' '.join(self.topics)}"
            self.questions = await self.question_manager.fetch_questions(
                query_text=query_text,
                difficulty=self.difficulty,
                limit=10
            )
            
            if not self.questions:
                logger.warning("No questions retrieved, using empty list")
                self.questions = []
            
            # Fetch candidate memory from Supermemory (if available)
            if self.supermemory_client:
                try:
                    self.candidate_memory = await self._fetch_candidate_memory()
                except Exception as e:
                    logger.warning(f"Failed to fetch candidate memory: {e}")
                    self.candidate_memory = None
            
            logger.info(
                f"Agent initialized with {len(self.questions)} questions "
                f"(memory: {'yes' if self.candidate_memory else 'no'})"
            )
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise
    
    async def start_interview(self) -> None:
        """
        Start interview with greeting and first question.
        """
        try:
            self.ai_state = "speaking"
            
            # Generate and speak greeting
            greeting = await self._generate_greeting()
            await self._speak(greeting)
            
            # Ask first question
            if self.questions:
                await self._ask_question(0)
            else:
                logger.error("No questions available to start interview")
                await self._speak("I apologize, but I'm unable to load questions at this time.")
            
            self.ai_state = "listening"
            
        except Exception as e:
            logger.error(f"Failed to start interview: {e}")
            raise
    
    async def handle_transcript_segment(
        self,
        text: str,
        is_final: bool,
        timestamp: float
    ) -> None:
        """
        Handle incoming transcript segment from Deepgram.
        
        Args:
            text: Transcript text
            is_final: Whether this is a final transcript
            timestamp: Unix timestamp
        """
        if is_final:
            self.transcript_buffer += " " + text
            self.word_count += len(text.split())
            
            # Process with SpeechProcessor
            await self.speech_processor.process_transcript_segment(
                text=text,
                is_final=is_final,
                timestamp=timestamp
            )
            
            # Store transcript to MongoDB
            await self.mongo_repository.add_transcript_segment(
                session_id=self.session_id,
                text=text,
                timestamp=timestamp,
                speaker="user",
                is_final=is_final
            )
            
            # Check if we have enough content for decision (20+ words)
            if self.word_count >= 20:
                await self._request_decision()
    
    async def _request_decision(self) -> None:
        """
        Request decision from DecisionEngine based on current context.
        """
        try:
            self.ai_state = "thinking"
            
            # Get latest emotion data
            emotion_data = self.emotion_processor.get_latest_emotion()
            
            # Get current speech metrics
            speech_metrics = self.speech_processor.get_current_metrics()
            
            # Get current question
            if self.current_question_index < len(self.questions):
                current_question = self.questions[self.current_question_index]
            else:
                logger.warning("No current question available")
                return
            
            # Build context
            context = {
                "question_text": current_question.get("text", ""),
                "transcript_so_far": self.transcript_buffer,
                "emotion": emotion_data.emotion if emotion_data else "neutral",
                "confidence_score": emotion_data.confidence_score if emotion_data else 50,
                "engagement_level": emotion_data.engagement_level if emotion_data else "medium",
                "filler_word_count": speech_metrics.get("filler_word_count", 0),
                "speech_pace": speech_metrics.get("speech_pace", 0),
                "long_pause_count": speech_metrics.get("long_pause_count", 0)
            }
            
            # Request decision from Claude
            decision = await self.decision_engine.make_decision(context)
            
            # Log decision to MongoDB
            await self.mongo_repository.add_decision_record(
                session_id=self.session_id,
                decision={
                    "timestamp": time.time(),
                    "action": decision["action"],
                    "context": context,
                    "message": decision.get("message", ""),
                    "reasoning": decision.get("reasoning", "")
                }
            )
            
            # Execute action
            await self._execute_action(decision)
            
        except Exception as e:
            logger.error(f"Decision request failed: {e}")
            self.ai_state = "listening"
    
    async def _execute_action(self, decision: Dict[str, Any]) -> None:
        """
        Execute action based on decision from DecisionEngine.
        
        Args:
            decision: Decision dictionary with action and optional message
        """
        action = decision.get("action", InterviewAction.CONTINUE)
        message = decision.get("message", "")
        
        if action == InterviewAction.CONTINUE:
            # Continue listening, no interruption
            self.ai_state = "listening"
            logger.debug("Action: CONTINUE - no interruption")
        
        elif action == InterviewAction.INTERRUPT:
            # Speak interruption message
            self.ai_state = "speaking"
            await self._speak(message)
            # Clear transcript buffer for fresh start
            self.transcript_buffer = ""
            self.word_count = 0
            self.ai_state = "listening"
            logger.info(f"Action: INTERRUPT - {message}")
        
        elif action == InterviewAction.ENCOURAGE:
            # Speak encouragement
            self.ai_state = "speaking"
            await self._speak(message)
            self.ai_state = "listening"
            logger.info(f"Action: ENCOURAGE - {message}")
        
        elif action == InterviewAction.HINT:
            # Speak hint
            self.ai_state = "speaking"
            await self._speak(message)
            self.ai_state = "listening"
            logger.info(f"Action: HINT - {message}")
        
        elif action == InterviewAction.NEXT:
            # Evaluate current answer and move to next question
            await self._evaluate_and_next()
    
    async def _evaluate_and_next(self) -> None:
        """
        Evaluate current answer and move to next question.
        Uses concurrent operations for improved performance.
        """
        import asyncio
        
        try:
            if self.current_question_index >= len(self.questions):
                logger.warning("No current question to evaluate")
                return
            
            current_question = self.questions[self.current_question_index]
            
            # Run evaluation, storage, and next question prep concurrently
            try:
                # Concurrent operations
                evaluation_task = self.decision_engine.evaluate_answer(
                    question=current_question.get("text", ""),
                    answer=self.transcript_buffer
                )
                
                # Wait for evaluation first (needed for storage)
                evaluation = await evaluation_task
                
                # Now run storage and reset concurrently
                storage_task = self.mongo_repository.store_question_result(
                    session_id=self.session_id,
                    question_id=current_question.get("id", "unknown"),
                    question_text=current_question.get("text", ""),
                    answer=self.transcript_buffer,
                    evaluation=evaluation
                )
                
                next_question_id = f"question_{self.current_question_index + 1}"
                reset_task = self.speech_processor.reset_for_new_question(next_question_id)
                
                # Wait for both to complete
                await asyncio.gather(storage_task, reset_task, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"Concurrent operations failed: {e}")
                # Continue despite errors
            
            # Reset for next question
            self.transcript_buffer = ""
            self.word_count = 0
            
            # Move to next question
            self.current_question_index += 1
            
            if self.current_question_index < len(self.questions):
                await self._ask_question(self.current_question_index)
            else:
                await self._complete_interview()
            
        except Exception as e:
            logger.error(f"Evaluate and next failed: {e}")
    
    async def _ask_question(self, index: int) -> None:
        """
        Ask question at given index.
        
        Args:
            index: Question index
        """
        if index >= len(self.questions):
            logger.warning(f"Question index {index} out of range")
            return
        
        question = self.questions[index]
        self.ai_state = "speaking"
        await self._speak(question.get("text", ""))
        self.ai_state = "listening"
        
        logger.info(f"Asked question {index + 1}/{len(self.questions)}")
    
    async def _speak(self, text: str) -> None:
        """
        Generate speech and play audio.
        
        Args:
            text: Text to speak
        """
        try:
            # Store agent transcript
            await self.mongo_repository.add_transcript_segment(
                session_id=self.session_id,
                text=text,
                timestamp=time.time(),
                speaker="agent",
                is_final=True
            )
            
            # Generate audio with TTS
            audio = await self.tts_service.synthesize_speech(text)
            
            # TODO: Play audio through Stream.io
            # This will be implemented in Stream.io integration
            
            logger.debug(f"Spoke: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
    
    async def _generate_greeting(self) -> str:
        """
        Generate personalized greeting.
        
        Returns:
            Greeting text
        """
        greeting = f"Hello! Welcome to your {self.role} interview. "
        
        if self.candidate_memory:
            greeting += "I see you've practiced with us before. Let's build on that experience. "
        
        greeting += f"I'll be asking you {len(self.questions)} questions today. Let's begin!"
        
        return greeting
    
    async def _complete_interview(self) -> None:
        """
        Complete interview: generate summary and store to Supermemory.
        """
        try:
            self.ai_state = "thinking"
            
            # Generate session summary with Claude
            summary = await self._generate_session_summary()
            
            # Write to Supermemory (if available)
            if self.supermemory_client:
                try:
                    await self.supermemory_client.write_memory(
                        key=f"candidate_{self.candidate_id}",
                        content=summary
                    )
                    logger.info("Session summary written to Supermemory")
                except Exception as e:
                    logger.warning(f"Failed to write to Supermemory: {e}")
            
            # Finalize session in MongoDB
            await self.mongo_repository.finalize_session(
                session_id=self.session_id,
                summary=summary
            )
            
            # Thank candidate
            self.ai_state = "speaking"
            closing = "Great job! Your interview is complete. You'll receive detailed feedback shortly."
            await self._speak(closing)
            
            self.ai_state = "idle"
            logger.info(f"Interview completed for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Interview completion failed: {e}")
    
    async def _generate_session_summary(self) -> str:
        """
        Generate comprehensive session summary using Claude.
        
        Returns:
            Session summary text
        """
        # Gather all data
        emotion_timeline = self.emotion_processor.get_emotion_timeline()
        avg_confidence = self.emotion_processor.get_average_confidence()
        
        # Build summary prompt
        prompt = f"""Generate a comprehensive interview session summary:

Role: {self.role}
Topics: {', '.join(self.topics)}
Difficulty: {self.difficulty}
Questions Completed: {self.current_question_index}/{len(self.questions)}

Average Confidence: {avg_confidence:.1f}/100
Emotion Snapshots: {len(emotion_timeline)}

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
    
    async def _fetch_candidate_memory(self) -> Optional[Dict]:
        """
        Fetch candidate memory from Supermemory.
        
        Returns:
            Candidate memory dictionary or None
        """
        try:
            memory = await self.supermemory_client.get_memory(
                key=f"candidate_{self.candidate_id}",
                limit=5  # Last 5 sessions
            )
            return memory
        except Exception as e:
            logger.error(f"Failed to fetch candidate memory: {e}")
            return None
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current agent state for real-time updates.
        
        Returns:
            Dictionary with current state
        """
        emotion_data = self.emotion_processor.get_latest_emotion()
        speech_metrics = self.speech_processor.get_current_metrics()
        
        return {
            "ai_state": self.ai_state,
            "current_question": self.current_question_index + 1,
            "total_questions": len(self.questions),
            "emotion": {
                "emotion": emotion_data.emotion if emotion_data else "neutral",
                "confidence_score": emotion_data.confidence_score if emotion_data else 50,
                "engagement_level": emotion_data.engagement_level if emotion_data else "medium"
            },
            "speech_metrics": speech_metrics
        }
