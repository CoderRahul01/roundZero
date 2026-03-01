"""
Presence Verifier Component

Verifies candidate presence when prolonged silence is detected by generating
and analyzing responses to "Can you hear me?" prompts.
"""

import asyncio
import time
from typing import Optional
from anthropic import AsyncAnthropic

from backend.agent.realtime_models import PresenceCheckResult


class PresenceVerifier:
    """
    Handles presence verification flow.
    Generates presence check prompts and analyzes responses.
    """
    
    def __init__(
        self,
        tts_service,
        stt_service,
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
                    confidence=0.9,
                    timestamp=time.time()
                )
        
        # No response or negative response
        if self._current_attempt >= self.max_attempts:
            return PresenceCheckResult(
                confirmed=False,
                attempts=self._current_attempt,
                response_text=response_text,
                confidence=0.0,
                timestamp=time.time()
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
        # This will be implemented when integrating with the frontend
        pass
    
    def reset(self):
        """Reset attempt counter for new presence check sequence."""
        self._current_attempt = 0
