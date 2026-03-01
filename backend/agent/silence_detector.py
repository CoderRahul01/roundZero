"""
Silence Detector Component

Monitors audio stream for silence detection, distinguishing between brief pauses
and prolonged silence for real-time voice interaction.
"""

import asyncio
import time
from typing import Optional, Callable
from dataclasses import dataclass

from agent.realtime_models import SilenceEvent


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
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
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
                        context="answer_complete",
                        audio_level_db=self.silence_threshold_db
                    )
                    await self._emit_silence_event(event)
                    self._silence_start_time = None  # Reset after emitting
                
                # Check for prolonged silence (10s)
                elif silence_duration >= self.prolonged_silence_threshold:
                    event = SilenceEvent(
                        duration=silence_duration,
                        timestamp=time.time(),
                        context="prolonged",
                        audio_level_db=self.silence_threshold_db
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
