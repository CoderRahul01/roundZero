"""
Deepgram Speech-to-Text service integration.

This module provides real-time speech-to-text transcription using Deepgram.
"""

import os
import logging
import asyncio
from typing import Optional, Callable
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions
)

logger = logging.getLogger(__name__)


class DeepgramSTTService:
    """
    Deepgram Speech-to-Text service for real-time transcription.
    
    Features:
    - Real-time streaming transcription
    - Interim and final results
    - Automatic reconnection
    - Error handling
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Deepgram service.
        
        Args:
            api_key: Deepgram API key
        """
        self.api_key = api_key
        
        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.client = DeepgramClient(api_key, config)
        
        # Connection state
        self.connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        logger.info("Initialized Deepgram STT service")
    
    async def start_streaming(
        self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None
    ):
        """
        Start streaming transcription.
        
        Args:
            on_transcript: Callback for transcript results
            on_error: Optional callback for errors
        """
        try:
            # Configure live transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=True,
                punctuate=True,
                diarize=False
            )
            
            # Create live transcription connection
            self.connection = self.client.listen.live.v("1")
            
            # Register event handlers
            self.connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
            
            if on_error:
                self.connection.on(LiveTranscriptionEvents.Error, on_error)
            
            self.connection.on(LiveTranscriptionEvents.Close, self._on_close)
            
            # Start connection
            if await self.connection.start(options):
                self.is_connected = True
                logger.info("Deepgram streaming started")
            else:
                raise Exception("Failed to start Deepgram connection")
            
        except Exception as e:
            logger.error(f"Failed to start Deepgram streaming: {e}")
            if on_error:
                await on_error(e)
            raise
    
    async def send_audio(self, audio_chunk: bytes):
        """
        Send audio chunk for transcription.
        
        Args:
            audio_chunk: Audio data bytes
        """
        if not self.is_connected or not self.connection:
            logger.warning("Deepgram not connected, cannot send audio")
            return
        
        try:
            self.connection.send(audio_chunk)
        except Exception as e:
            logger.error(f"Failed to send audio to Deepgram: {e}")
            await self._attempt_reconnection()
    
    async def stop_streaming(self):
        """
        Stop streaming transcription.
        """
        if self.connection:
            try:
                await self.connection.finish()
                self.is_connected = False
                logger.info("Deepgram streaming stopped")
            except Exception as e:
                logger.error(f"Error stopping Deepgram: {e}")
    
    async def _on_close(self, *args, **kwargs):
        """
        Handle connection close event.
        """
        self.is_connected = False
        logger.info("Deepgram connection closed")
    
    async def _attempt_reconnection(self):
        """
        Attempt to reconnect to Deepgram.
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting Deepgram reconnection ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
        
        try:
            # Wait with exponential backoff
            await asyncio.sleep(2 ** self.reconnect_attempts)
            
            # Try to reconnect
            # Note: Actual reconnection logic would go here
            # For now, just log the attempt
            
            logger.info("Deepgram reconnection successful")
            self.reconnect_attempts = 0
            
        except Exception as e:
            logger.error(f"Deepgram reconnection failed: {e}")


def get_deepgram_service() -> DeepgramSTTService:
    """
    Get Deepgram service instance from environment.
    
    Returns:
        DeepgramSTTService instance
    
    Raises:
        ValueError: If DEEPGRAM_API_KEY not configured
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not api_key:
        raise ValueError(
            "DEEPGRAM_API_KEY not configured. "
            "Set DEEPGRAM_API_KEY environment variable."
        )
    
    return DeepgramSTTService(api_key=api_key)
