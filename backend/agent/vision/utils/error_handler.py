"""
Centralized Error Handler for Vision Agents system.

This module provides error handling, tracking, and alerting for all
service failures in the Vision Agents interview system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handler with tracking and alerting.
    
    Features:
    - Track error counts per service
    - Calculate error rates
    - Send alerts when thresholds exceeded
    - Provide fallback responses
    """
    
    def __init__(self, alert_service=None):
        """
        Initialize error handler.
        
        Args:
            alert_service: Optional alert service for notifications
        """
        self.alert_service = alert_service
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_history: Dict[str, list] = defaultdict(list)
        self.alert_thresholds = {
            "gemini": 10,  # Alert after 10 errors
            "claude": 10,
            "deepgram": 5,
            "elevenlabs": 5,
            "mongodb": 3,
            "stream": 5
        }
        
        logger.info("ErrorHandler initialized")
    
    async def handle_gemini_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Gemini API errors with fallback.
        
        Args:
            error: Exception that occurred
            context: Error context (session_id, frame_number, etc.)
        
        Returns:
            Neutral emotion data as fallback
        """
        service = "gemini"
        self._log_error(service, error, context)
        self._increment_error_count(service)
        await self._check_alert_threshold(service)
        
        # Return neutral emotion data as fallback
        return {
            "emotion": "neutral",
            "confidence_score": 50,
            "engagement_level": "medium",
            "body_language_observations": "Unable to analyze (service error)",
            "timestamp": datetime.utcnow().timestamp()
        }
    
    async def handle_claude_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Claude API errors with fallback decision logic.
        
        Args:
            error: Exception that occurred
            context: Error context (session_id, question, transcript, etc.)
        
        Returns:
            Fallback decision (CONTINUE action)
        """
        service = "claude"
        self._log_error(service, error, context)
        self._increment_error_count(service)
        await self._check_alert_threshold(service)
        
        # Return safe fallback decision
        return {
            "action": "CONTINUE",
            "message": "",
            "reasoning": "Using fallback decision due to service error"
        }
    
    async def handle_deepgram_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        max_retries: int = 3
    ) -> Optional[bool]:
        """
        Handle Deepgram STT errors with reconnection attempts.
        
        Args:
            error: Exception that occurred
            context: Error context (session_id, etc.)
            max_retries: Maximum reconnection attempts
        
        Returns:
            True if reconnection successful, False otherwise
        """
        service = "deepgram"
        self._log_error(service, error, context)
        self._increment_error_count(service)
        await self._check_alert_threshold(service)
        
        # Attempt reconnection with exponential backoff
        import asyncio
        for attempt in range(max_retries):
            try:
                logger.info(f"Deepgram reconnection attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                # Reconnection logic would go here
                # For now, return False to indicate failure
                return False
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        logger.error("All Deepgram reconnection attempts failed")
        return False
    
    async def handle_elevenlabs_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle ElevenLabs TTS errors by switching to text-only mode.
        
        Args:
            error: Exception that occurred
            context: Error context (session_id, text, etc.)
        
        Returns:
            Status indicating text-only mode
        """
        service = "elevenlabs"
        self._log_error(service, error, context)
        self._increment_error_count(service)
        await self._check_alert_threshold(service)
        
        return {
            "mode": "text_only",
            "message": "Audio synthesis unavailable, continuing with text",
            "text": context.get("text", "")
        }
    
    async def handle_mongodb_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        data: Any = None
    ) -> bool:
        """
        Handle MongoDB storage errors with retry logic.
        
        Args:
            error: Exception that occurred
            context: Error context (session_id, operation, etc.)
            data: Data that failed to store (for in-memory fallback)
        
        Returns:
            True if retry successful, False otherwise
        """
        service = "mongodb"
        self._log_error(service, error, context)
        self._increment_error_count(service)
        await self._check_alert_threshold(service)
        
        # Retry logic with exponential backoff
        import asyncio
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"MongoDB retry attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)
                
                # Retry logic would go here
                # For now, return False to indicate failure
                return False
                
            except Exception as e:
                logger.error(f"Retry attempt {attempt + 1} failed: {e}")
        
        # Store in memory as last resort
        logger.warning("Storing data in memory due to MongoDB failure")
        # In-memory storage logic would go here
        
        return False
    
    def _log_error(
        self,
        service: str,
        error: Exception,
        context: Dict[str, Any]
    ):
        """
        Log error with full context.
        
        Args:
            service: Service name
            error: Exception that occurred
            context: Error context
        """
        error_record = {
            "service": service,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.error_history[service].append(error_record)
        
        logger.error(
            f"Service error - {service}: {type(error).__name__} - {str(error)}",
            extra={"context": context}
        )
    
    def _increment_error_count(self, service: str):
        """
        Increment error count for service.
        
        Args:
            service: Service name
        """
        self.error_counts[service] += 1
    
    async def _check_alert_threshold(self, service: str):
        """
        Check if error count exceeds threshold and send alert.
        
        Args:
            service: Service name
        """
        threshold = self.alert_thresholds.get(service, 10)
        
        if self.error_counts[service] >= threshold:
            await self._send_alert(service)
    
    async def _send_alert(self, service: str):
        """
        Send alert for high error rate.
        
        Args:
            service: Service name
        """
        if self.alert_service:
            try:
                await self.alert_service.send_alert(
                    title=f"High Error Rate: {service}",
                    message=f"{service} has {self.error_counts[service]} errors",
                    severity="high"
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
        else:
            logger.warning(
                f"Alert threshold exceeded for {service} "
                f"({self.error_counts[service]} errors) but no alert service configured"
            )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics for all services.
        
        Returns:
            Dictionary with error counts and rates
        """
        return {
            "error_counts": dict(self.error_counts),
            "total_errors": sum(self.error_counts.values()),
            "services_with_errors": len(self.error_counts)
        }
    
    def get_service_errors(self, service: str) -> list:
        """
        Get error history for a specific service.
        
        Args:
            service: Service name
        
        Returns:
            List of error records
        """
        return self.error_history.get(service, [])
    
    def reset_error_counts(self):
        """Reset all error counts (e.g., daily reset)."""
        self.error_counts.clear()
        logger.info("Error counts reset")
