"""
Onboarding Manager

Handles the personalized onboarding flow for interview candidates, including
greeting generation, introduction, and readiness confirmation.
"""

import logging
from datetime import datetime
from typing import Optional
from anthropic import AsyncAnthropic
from elevenlabs.types import VoiceSettings

logger = logging.getLogger(__name__)


class OnboardingManager:
    """
    Manages the onboarding flow for interview candidates.
    
    Features:
    - Time-based personalized greetings
    - Natural introduction to interview process
    - Readiness confirmation with Claude interpretation
    - Audio generation for all onboarding messages
    """
    
    def __init__(
        self,
        tts_service,
        claude_client: AsyncAnthropic,
        user_repository=None
    ):
        """
        Initialize OnboardingManager.
        
        Args:
            tts_service: Text-to-speech service for audio generation
            claude_client: Anthropic Claude client for response interpretation
            user_repository: Optional repository for user data access
        """
        self.tts_service = tts_service
        self.claude_client = claude_client
        self.user_repository = user_repository
        
        # Voice settings for warm, welcoming tone
        self.greeting_voice_settings = VoiceSettings(
            stability=0.6,
            similarity_boost=0.8,
            style=0.0,
            use_speaker_boost=True
        )
        
        logger.info("OnboardingManager initialized")
    
    async def start_onboarding(
        self,
        session_id: str,
        first_name: Optional[str] = None,
        question_count: int = 5
    ) -> dict:
        """
        Orchestrate the complete onboarding flow.
        
        Args:
            session_id: Interview session identifier
            first_name: Candidate's first name (optional)
            question_count: Number of questions in the interview
        
        Returns:
            Dictionary with onboarding results including audio URLs and readiness status
        """
        logger.info(f"Starting onboarding for session {session_id}")
        
        # Step 1: Generate and play greeting
        greeting_text = self.generate_greeting(first_name)
        greeting_audio = await self.tts_service.synthesize_speech(
            greeting_text,
            voice_settings=self.greeting_voice_settings
        )
        
        # Step 2: Generate and play introduction
        introduction_text = self.generate_introduction(question_count)
        introduction_audio = await self.tts_service.synthesize_speech(
            introduction_text,
            voice_settings=self.greeting_voice_settings
        )
        
        # Step 3: Ask readiness question
        # (This will be handled by the caller with voice input)
        
        return {
            "greeting_text": greeting_text,
            "greeting_audio": greeting_audio,
            "introduction_text": introduction_text,
            "introduction_audio": introduction_audio,
            "session_id": session_id
        }
    
    def generate_greeting(self, first_name: Optional[str] = None) -> str:
        """
        Generate personalized greeting with time-of-day awareness.
        
        Args:
            first_name: Candidate's first name (optional)
        
        Returns:
            Greeting message string
        """
        # Get time-based greeting
        time_greeting = self.get_time_of_day()
        
        # Format with name or fallback to "there"
        name = first_name if first_name else "there"
        
        greeting = f"Hey {name}, nice to meet you. {time_greeting}."
        
        logger.debug(f"Generated greeting: {greeting}")
        return greeting
    
    def get_time_of_day(self) -> str:
        """
        Get appropriate greeting based on current time.
        
        Returns:
            Time-based greeting string
        """
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            return "Good morning"
        elif 12 <= current_hour < 17:
            return "Good afternoon"
        elif 17 <= current_hour < 21:
            return "Good evening"
        else:
            return "Hello"
    
    def generate_introduction(self, question_count: int) -> str:
        """
        Generate introduction explaining the interview process.
        
        Args:
            question_count: Number of questions in the interview
        
        Returns:
            Introduction message string
        """
        introduction = (
            f"We have an interview with {question_count} questions lined up for you today. "
            f"I'll ask you each question, and you can take your time to answer. "
            f"I might ask follow-up questions if I need clarification or want to dive deeper. "
            f"Just speak naturally, and I'll be listening."
        )
        
        logger.debug(f"Generated introduction for {question_count} questions")
        return introduction
    
    async def confirm_readiness(
        self,
        candidate_response: str,
        attempt: int = 1,
        max_attempts: int = 3
    ) -> dict:
        """
        Interpret candidate's readiness response using Claude.
        
        Args:
            candidate_response: Transcribed response from candidate
            attempt: Current attempt number (for timeout handling)
            max_attempts: Maximum number of attempts before proceeding
        
        Returns:
            Dictionary with readiness status and response message
        """
        logger.info(f"Confirming readiness (attempt {attempt}/{max_attempts})")
        
        # Use Claude to interpret the response
        prompt = f"""Analyze this candidate's response to the question "Are you ready to start the interview?":

Response: "{candidate_response}"

Classify the response as one of:
1. AFFIRMATIVE - Ready to proceed (e.g., "yes", "let's go", "I'm ready", "sure")
2. NEGATIVE - Not ready or needs time (e.g., "no", "wait", "not yet", "give me a minute")
3. UNCLEAR - Ambiguous or off-topic response

Respond with only one word: AFFIRMATIVE, NEGATIVE, or UNCLEAR"""
        
        try:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )
            
            classification = response.content[0].text.strip().upper()
            
            if classification == "AFFIRMATIVE":
                return {
                    "ready": True,
                    "message": "Great! Let's begin.",
                    "classification": "affirmative"
                }
            elif classification == "NEGATIVE":
                return {
                    "ready": False,
                    "message": "No problem. Take your time. Let me know when you're ready.",
                    "classification": "negative"
                }
            else:
                # UNCLEAR or unexpected response
                if attempt >= max_attempts:
                    # Proceed anyway after max attempts
                    return {
                        "ready": True,
                        "message": "Alright, let's get started.",
                        "classification": "timeout"
                    }
                else:
                    return {
                        "ready": False,
                        "message": "I didn't quite catch that. Are you ready to start?",
                        "classification": "unclear",
                        "retry": True
                    }
        
        except Exception as e:
            logger.error(f"Error in confirm_readiness: {e}")
            # Fallback: proceed if we can't interpret
            return {
                "ready": True,
                "message": "Let's begin.",
                "classification": "error",
                "error": str(e)
            }
