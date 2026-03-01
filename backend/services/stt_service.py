"""
Speech-to-Text Service using Deepgram API.

Provides async transcription capabilities for real-time and prerecorded audio.
"""

import logging
from typing import AsyncIterator, Optional
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    LiveOptions,
    LiveTranscriptionEvents
)

logger = logging.getLogger(__name__)


class DeepgramSTTService:
    """
    Async speech-to-text service using Deepgram API.
    
    Features:
    - Real-time streaming transcription
    - Prerecorded audio transcription
    - Confidence scoring
    - Smart formatting and punctuation
    - Error handling and retry logic
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Deepgram client.
        
        Args:
            api_key: Deepgram API key
        """
        self.api_key = api_key
        self.client = DeepgramClient(api_key)
        logger.info("DeepgramSTTService initialized")
    
    async def transcribe_stream(
        self, 
        audio_stream: AsyncIterator[bytes],
        language: str = "en-US",
        model: str = "nova-2"
    ) -> AsyncIterator[str]:
        """
        Real-time transcription of audio stream.
        Uses Deepgram's live transcription API.
        
        Args:
            audio_stream: Async iterator of audio chunks (bytes)
            language: Language code (default: en-US)
            model: Deepgram model to use (default: nova-2)
        
        Yields:
            Transcribed text chunks as they become available
        """
        options = LiveOptions(
            model=model,
            language=language,
            smart_format=True,
            interim_results=True,
            punctuate=True,
            diarize=False,
            encoding="linear16",
            sample_rate=16000
        )
        
        try:
            connection = self.client.listen.live.v("1")
            
            # Store transcripts
            transcripts = []
            
            def on_message(self, result, **kwargs):
                """Handle transcription results."""
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    if result.is_final:
                        transcripts.append(sentence)
                        logger.debug(f"Final transcript: {sentence}")
            
            def on_error(self, error, **kwargs):
                """Handle errors."""
                logger.error(f"Deepgram error: {error}")
            
            # Register event handlers
            connection.on(LiveTranscriptionEvents.Transcript, on_message)
            connection.on(LiveTranscriptionEvents.Error, on_error)
            
            # Start connection
            if not await connection.start(options):
                logger.error("Failed to start Deepgram connection")
                return
            
            # Stream audio data
            async for audio_chunk in audio_stream:
                await connection.send(audio_chunk)
                
                # Yield any new transcripts
                while transcripts:
                    yield transcripts.pop(0)
            
            # Close connection
            await connection.finish()
            
        except Exception as e:
            logger.error(f"Error in transcribe_stream: {e}")
            raise
    
    async def transcribe_audio(
        self, 
        audio_data: bytes,
        language: str = "en-US",
        model: str = "nova-2"
    ) -> str:
        """
        Transcribe complete audio buffer.
        Uses Deepgram's prerecorded API for better accuracy.
        
        Args:
            audio_data: Audio file bytes
            language: Language code (default: en-US)
            model: Deepgram model to use (default: nova-2)
        
        Returns:
            Transcribed text
        """
        options = PrerecordedOptions(
            model=model,
            language=language,
            smart_format=True,
            punctuate=True,
            diarize=False
        )
        
        try:
            response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(
                {"buffer": audio_data},
                options
            )
            
            transcript = response.results.channels[0].alternatives[0].transcript
            logger.info(f"Transcribed audio: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            logger.error(f"Error in transcribe_audio: {e}")
            raise
    
    async def transcribe_with_confidence(
        self, 
        audio_data: bytes,
        language: str = "en-US",
        model: str = "nova-2"
    ) -> tuple[str, float]:
        """
        Transcribe audio and return confidence score.
        Useful for quality assessment.
        
        Args:
            audio_data: Audio file bytes
            language: Language code (default: en-US)
            model: Deepgram model to use (default: nova-2)
        
        Returns:
            Tuple of (transcript, confidence_score)
        """
        options = PrerecordedOptions(
            model=model,
            language=language,
            smart_format=True,
            punctuate=True,
            diarize=False
        )
        
        try:
            response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(
                {"buffer": audio_data},
                options
            )
            
            alternative = response.results.channels[0].alternatives[0]
            transcript = alternative.transcript
            confidence = alternative.confidence
            
            logger.info(
                f"Transcribed audio with confidence {confidence:.2f}: "
                f"{len(transcript)} characters"
            )
            return transcript, confidence
            
        except Exception as e:
            logger.error(f"Error in transcribe_with_confidence: {e}")
            raise
    
    async def transcribe_with_retry(
        self,
        audio_data: bytes,
        max_retries: int = 3,
        language: str = "en-US",
        model: str = "nova-2"
    ) -> Optional[str]:
        """
        Transcribe audio with retry logic for error handling.
        
        Args:
            audio_data: Audio file bytes
            max_retries: Maximum number of retry attempts
            language: Language code (default: en-US)
            model: Deepgram model to use (default: nova-2)
        
        Returns:
            Transcribed text or None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                transcript = await self.transcribe_audio(audio_data, language, model)
                return transcript
            except Exception as e:
                logger.warning(
                    f"Transcription attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error("All transcription attempts failed")
                    return None
        
        return None
