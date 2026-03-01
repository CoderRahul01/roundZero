"""
Error Handlers for Real-Time Voice Interaction

Implements graceful degradation and error recovery for all external services.
"""

import asyncio
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Types of external services."""
    STT = "stt"
    TTS = "tts"
    CLAUDE = "claude"
    GEMINI = "gemini"
    NETWORK = "network"


@dataclass
class ServiceFailure:
    """Record of a service failure."""
    service_type: ServiceType
    error_message: str
    timestamp: float
    retry_count: int


class ErrorRecoveryManager:
    """
    Manages error recovery and graceful degradation for all services.
    """
    
    def __init__(self):
        self._failure_counts = {
            ServiceType.STT: 0,
            ServiceType.TTS: 0,
            ServiceType.CLAUDE: 0,
            ServiceType.GEMINI: 0,
            ServiceType.NETWORK: 0
        }
        self._failure_history: list[ServiceFailure] = []
        self._fallback_mode = {
            ServiceType.STT: False,
            ServiceType.TTS: False,
            ServiceType.CLAUDE: False,
            ServiceType.GEMINI: False
        }
    
    def record_failure(self, service_type: ServiceType, error: Exception):
        """Record a service failure."""
        import time
        
        self._failure_counts[service_type] += 1
        failure = ServiceFailure(
            service_type=service_type,
            error_message=str(error),
            timestamp=time.time(),
            retry_count=self._failure_counts[service_type]
        )
        self._failure_history.append(failure)
        
        logger.error(
            f"{service_type.value} failure #{self._failure_counts[service_type]}: {error}"
        )
    
    def should_retry(self, service_type: ServiceType, max_retries: int = 3) -> bool:
        """Check if service should be retried."""
        return self._failure_counts[service_type] < max_retries
    
    def enable_fallback_mode(self, service_type: ServiceType):
        """Enable fallback mode for a service."""
        self._fallback_mode[service_type] = True
        logger.warning(f"Fallback mode enabled for {service_type.value}")
    
    def is_fallback_mode(self, service_type: ServiceType) -> bool:
        """Check if service is in fallback mode."""
        return self._fallback_mode.get(service_type, False)
    
    def reset_failures(self, service_type: ServiceType):
        """Reset failure count for a service."""
        self._failure_counts[service_type] = 0
        self._fallback_mode[service_type] = False
    
    def get_failure_count(self, service_type: ServiceType) -> int:
        """Get current failure count for a service."""
        return self._failure_counts[service_type]


class STTErrorHandler:
    """
    Handles STT (Deepgram) failures with retry logic and fallback to text input.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
        self.max_retries = 3
        self.retry_interval = 30  # seconds
    
    async def handle_connection_failure(self, error: Exception) -> dict:
        """
        Handle STT connection failure.
        Returns fallback instructions.
        """
        self.recovery_manager.record_failure(ServiceType.STT, error)
        
        if self.recovery_manager.should_retry(ServiceType.STT, self.max_retries):
            # Schedule retry
            retry_count = self.recovery_manager.get_failure_count(ServiceType.STT)
            await asyncio.sleep(self.retry_interval)
            
            return {
                "action": "retry",
                "retry_count": retry_count,
                "message": f"STT connection failed. Retrying... (Attempt {retry_count}/{self.max_retries})"
            }
        else:
            # Switch to text-only mode
            self.recovery_manager.enable_fallback_mode(ServiceType.STT)
            
            return {
                "action": "fallback_text_input",
                "message": "Voice input unavailable. Please use text input instead.",
                "user_message": "We're having trouble with voice recognition. You can type your answers instead."
            }
    
    async def handle_transcription_error(self, error: Exception) -> dict:
        """Handle transcription quality issues."""
        logger.warning(f"Transcription error: {error}")
        
        return {
            "action": "continue",
            "message": "Transcription quality degraded, continuing with available data",
            "show_confidence_warning": True
        }


class TTSErrorHandler:
    """
    Handles TTS (ElevenLabs) failures with fallback to text display.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
        self.max_retries = 3
    
    async def handle_synthesis_failure(self, text: str, error: Exception) -> dict:
        """
        Handle TTS synthesis failure.
        Returns fallback to text display.
        """
        self.recovery_manager.record_failure(ServiceType.TTS, error)
        
        if self.recovery_manager.should_retry(ServiceType.TTS, self.max_retries):
            # Try again for next question
            return {
                "action": "display_text_only",
                "text": text,
                "message": "Audio unavailable for this question. Displaying text instead.",
                "retry_next": True
            }
        else:
            # Permanent fallback to text
            self.recovery_manager.enable_fallback_mode(ServiceType.TTS)
            
            return {
                "action": "display_text_only",
                "text": text,
                "message": "Audio unavailable. All questions will be displayed as text.",
                "retry_next": False
            }


class ClaudeErrorHandler:
    """
    Handles Claude API failures with exponential backoff and graceful degradation.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
        self.max_retries = 3
        self.backoff_delays = [1, 2, 4]  # seconds
    
    async def handle_api_failure(
        self,
        operation: str,
        error: Exception,
        fallback_fn: Optional[Callable] = None
    ) -> dict:
        """
        Handle Claude API failure with exponential backoff.
        """
        self.recovery_manager.record_failure(ServiceType.CLAUDE, error)
        retry_count = self.recovery_manager.get_failure_count(ServiceType.CLAUDE)
        
        if retry_count <= self.max_retries:
            # Exponential backoff
            delay = self.backoff_delays[min(retry_count - 1, len(self.backoff_delays) - 1)]
            await asyncio.sleep(delay)
            
            return {
                "action": "retry",
                "retry_count": retry_count,
                "delay": delay,
                "message": f"Claude API error. Retrying in {delay}s..."
            }
        else:
            # Use fallback or accept without analysis
            if fallback_fn:
                result = await fallback_fn()
                return {
                    "action": "fallback",
                    "result": result,
                    "message": "Using fallback analysis method"
                }
            else:
                return {
                    "action": "accept_without_analysis",
                    "message": "Analysis unavailable. Accepting answer as-is.",
                    "store_for_later": True
                }


class GeminiErrorHandler:
    """
    Handles Gemini embedding failures with fallback to Claude-only evaluation.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
    
    async def handle_embedding_failure(self, error: Exception) -> dict:
        """
        Handle Gemini embedding failure.
        Falls back to Claude-only evaluation.
        """
        self.recovery_manager.record_failure(ServiceType.GEMINI, error)
        self.recovery_manager.enable_fallback_mode(ServiceType.GEMINI)
        
        logger.warning("Gemini embeddings unavailable. Using Claude-only evaluation.")
        
        return {
            "action": "fallback_claude_only",
            "message": "Semantic similarity unavailable. Using text-based evaluation only.",
            "disable_similarity_scoring": True
        }


class NetworkErrorHandler:
    """
    Handles network connection loss with state persistence and auto-sync.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
        self._local_state_backup: Optional[dict] = None
    
    async def handle_connection_loss(self, current_state: dict) -> dict:
        """
        Handle network connection loss.
        Persists state locally.
        """
        self.recovery_manager.record_failure(ServiceType.NETWORK, Exception("Connection lost"))
        
        # Backup state to localStorage (will be handled by frontend)
        self._local_state_backup = current_state
        
        return {
            "action": "persist_local",
            "state": current_state,
            "message": "Connection lost. Your progress is saved locally.",
            "enable_offline_mode": True
        }
    
    async def handle_connection_restored(self) -> dict:
        """
        Handle network connection restoration.
        Syncs local state to server.
        """
        self.recovery_manager.reset_failures(ServiceType.NETWORK)
        
        if self._local_state_backup:
            return {
                "action": "sync_to_server",
                "state": self._local_state_backup,
                "message": "Connection restored. Syncing your progress...",
                "clear_local_backup": True
            }
        
        return {
            "action": "resume_normal",
            "message": "Connection restored."
        }


class CompositeErrorHandler:
    """
    Composite error handler that coordinates all service-specific handlers.
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.stt_handler = STTErrorHandler(self.recovery_manager)
        self.tts_handler = TTSErrorHandler(self.recovery_manager)
        self.claude_handler = ClaudeErrorHandler(self.recovery_manager)
        self.gemini_handler = GeminiErrorHandler(self.recovery_manager)
        self.network_handler = NetworkErrorHandler(self.recovery_manager)
    
    async def handle_error(
        self,
        service_type: ServiceType,
        error: Exception,
        context: Optional[dict] = None
    ) -> dict:
        """
        Route error to appropriate handler.
        """
        handlers = {
            ServiceType.STT: self.stt_handler.handle_connection_failure,
            ServiceType.TTS: lambda e: self.tts_handler.handle_synthesis_failure(
                context.get("text", "") if context else "", e
            ),
            ServiceType.CLAUDE: lambda e: self.claude_handler.handle_api_failure(
                context.get("operation", "unknown") if context else "unknown",
                e,
                context.get("fallback_fn") if context else None
            ),
            ServiceType.GEMINI: self.gemini_handler.handle_embedding_failure,
            ServiceType.NETWORK: lambda e: self.network_handler.handle_connection_loss(
                context.get("state", {}) if context else {}
            )
        }
        
        handler = handlers.get(service_type)
        if handler:
            return await handler(error)
        
        return {
            "action": "log_and_continue",
            "message": f"Unhandled error in {service_type.value}: {error}"
        }
    
    def get_system_health(self) -> dict:
        """Get overall system health status."""
        return {
            "stt_failures": self.recovery_manager.get_failure_count(ServiceType.STT),
            "tts_failures": self.recovery_manager.get_failure_count(ServiceType.TTS),
            "claude_failures": self.recovery_manager.get_failure_count(ServiceType.CLAUDE),
            "gemini_failures": self.recovery_manager.get_failure_count(ServiceType.GEMINI),
            "network_failures": self.recovery_manager.get_failure_count(ServiceType.NETWORK),
            "fallback_modes": {
                "stt": self.recovery_manager.is_fallback_mode(ServiceType.STT),
                "tts": self.recovery_manager.is_fallback_mode(ServiceType.TTS),
                "claude": self.recovery_manager.is_fallback_mode(ServiceType.CLAUDE),
                "gemini": self.recovery_manager.is_fallback_mode(ServiceType.GEMINI)
            }
        }
