"""
EmotionProcessor for analyzing video frames using Gemini Flash-8B.

This module processes webcam frames to detect emotions, confidence levels,
and body language observations.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from agent.vision.core.emotion_snapshot import EmotionSnapshot

logger = logging.getLogger(__name__)


class EmotionProcessor:
    """
    Processes video frames for emotion detection using Gemini Flash-8B.
    Samples every Nth frame to respect rate limits (1000 RPD).
    
    Features:
    - Adaptive frame sampling based on rate limit usage
    - Real-time emotion detection
    - Confidence scoring (0-100)
    - Engagement level tracking
    - Body language observations
    """
    
    def __init__(
        self,
        gemini_client,
        session_id: str,
        mongo_repository,
        frame_sample_rate: int = 10,
        rate_limit_threshold: int = 900,
        error_handler=None
    ):
        """
        Initialize EmotionProcessor.
        
        Args:
            gemini_client: Google Generative AI client
            session_id: Current session identifier
            mongo_repository: LiveSessionRepository instance
            frame_sample_rate: Sample every Nth frame (default: 10)
            rate_limit_threshold: Threshold to reduce sampling (default: 900)
            error_handler: Optional ErrorHandler instance for centralized error handling
        """
        self.gemini_client = gemini_client
        self.session_id = session_id
        self.mongo_repository = mongo_repository
        self.frame_sample_rate = frame_sample_rate
        self.rate_limit_threshold = rate_limit_threshold
        self.error_handler = error_handler
        
        # State tracking
        self.frame_count = 0
        self.emotion_snapshots: List[EmotionSnapshot] = []
        self.daily_request_count = 0
        self.last_reset_time = time.time()
        
        logger.info(
            f"Initialized EmotionProcessor for session {session_id} "
            f"with sample rate {frame_sample_rate}"
        )

    
    async def process_frame(self, frame: bytes) -> Optional[EmotionSnapshot]:
        """
        Process video frame for emotion detection.
        Samples every Nth frame based on frame_sample_rate.
        
        Args:
            frame: Video frame as bytes (JPEG format)
        
        Returns:
            EmotionSnapshot if frame was processed, None if skipped
        """
        self.frame_count += 1
        
        # Check if we should reset daily counter (midnight UTC)
        self.reset_daily_counter()
        
        # Sample every Nth frame
        if self.frame_count % self.frame_sample_rate != 0:
            return None
        
        # Check rate limit
        if self.daily_request_count >= 1000:
            logger.warning(
                f"Gemini rate limit reached (1000 RPD). "
                f"Emotion processing disabled for session {self.session_id}"
            )
            return None
        
        # Adjust sampling frequency if approaching limit
        if self.daily_request_count >= self.rate_limit_threshold:
            self.frame_sample_rate = 20
            logger.info(
                f"Approaching rate limit ({self.daily_request_count}/1000). "
                f"Reduced sampling to every {self.frame_sample_rate} frames"
            )
        
        try:
            # Analyze frame with Gemini Flash-8B
            analysis = await self._analyze_with_gemini(frame)
            
            # Create emotion snapshot
            snapshot = EmotionSnapshot(
                emotion=analysis.get("emotion", "neutral"),
                confidence_score=analysis.get("confidence_score", 50),
                engagement_level=analysis.get("engagement_level", "medium"),
                body_language_observations=analysis.get("body_language", ""),
                timestamp=time.time()
            )
            
            # Store snapshot
            self.emotion_snapshots.append(snapshot)
            await self._store_snapshot(snapshot)
            
            self.daily_request_count += 1
            
            logger.debug(
                f"Processed frame {self.frame_count}: "
                f"emotion={snapshot.emotion}, confidence={snapshot.confidence_score}"
            )
            
            return snapshot
            
        except Exception as e:
            # Log error but continue processing without throwing
            logger.error(f"Emotion processing error for session {self.session_id}: {e}")
            return None
    
    async def _analyze_with_gemini(self, frame: bytes) -> Dict[str, Any]:
        """
        Send frame to Gemini Flash-8B for emotion analysis.
        
        Args:
            frame: Video frame bytes
        
        Returns:
            Dictionary with emotion, confidence_score, engagement_level, body_language
        """
        prompt = """Analyze this person's emotional state during an interview. Provide:

1. emotion: One of (confident, nervous, confused, neutral, enthusiastic)
2. confidence_score: Integer from 0 to 100
3. engagement_level: One of (high, medium, low)
4. body_language: Brief observations about posture, gestures, facial expressions

Return as JSON format:
{
    "emotion": "confident",
    "confidence_score": 85,
    "engagement_level": "high",
    "body_language": "Maintaining eye contact, upright posture, minimal fidgeting"
}"""
        
        try:
            # Call Gemini Flash-8B API
            response = await self.gemini_client.generate_content(
                model="gemini-1.5-flash-8b",
                contents=[
                    {"mime_type": "image/jpeg", "data": frame},
                    {"text": prompt}
                ]
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.text)
            
            # Validate and sanitize response
            return {
                "emotion": result.get("emotion", "neutral"),
                "confidence_score": min(max(int(result.get("confidence_score", 50)), 0), 100),
                "engagement_level": result.get("engagement_level", "medium"),
                "body_language": result.get("body_language", "")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            
            # Use error handler if available
            if self.error_handler:
                context = {
                    "session_id": self.session_id,
                    "frame_count": self.frame_count,
                    "daily_requests": self.daily_request_count
                }
                neutral_data = await self.error_handler.handle_gemini_error(e, context)
                return neutral_data
            
            return self._get_neutral_emotion()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            
            # Use error handler if available
            if self.error_handler:
                context = {
                    "session_id": self.session_id,
                    "frame_count": self.frame_count,
                    "daily_requests": self.daily_request_count
                }
                neutral_data = await self.error_handler.handle_gemini_error(e, context)
                return neutral_data
            
            return self._get_neutral_emotion()
    
    def _get_neutral_emotion(self) -> Dict[str, Any]:
        """Return neutral emotion data as fallback."""
        return {
            "emotion": "neutral",
            "confidence_score": 50,
            "engagement_level": "medium",
            "body_language": "Unable to analyze"
        }
    
    async def _store_snapshot(self, snapshot: EmotionSnapshot) -> None:
        """
        Store emotion snapshot to MongoDB.
        
        Args:
            snapshot: EmotionSnapshot instance
        """
        try:
            await self.mongo_repository.add_emotion_snapshot(
                session_id=self.session_id,
                snapshot=snapshot.to_dict()
            )
        except Exception as e:
            logger.error(f"Failed to store emotion snapshot: {e}")
    
    def get_latest_emotion(self) -> Optional[EmotionSnapshot]:
        """
        Get most recent emotion snapshot.
        
        Returns:
            Latest EmotionSnapshot or None if no snapshots exist
        """
        return self.emotion_snapshots[-1] if self.emotion_snapshots else None
    
    def get_average_confidence(self) -> float:
        """
        Calculate average confidence score across all snapshots.
        
        Returns:
            Average confidence score (0-100)
        """
        if not self.emotion_snapshots:
            return 0.0
        
        total = sum(s.confidence_score for s in self.emotion_snapshots)
        return total / len(self.emotion_snapshots)
    
    def reset_daily_counter(self) -> None:
        """
        Reset daily request counter at midnight UTC.
        Also resets sampling rate to normal.
        """
        current_time = time.time()
        elapsed = current_time - self.last_reset_time
        
        # Reset if 24 hours have passed
        if elapsed >= 86400:  # 24 hours in seconds
            self.daily_request_count = 0
            self.last_reset_time = current_time
            self.frame_sample_rate = 10  # Reset to normal sampling
            logger.info(f"Reset daily Gemini request counter for session {self.session_id}")
    
    def get_emotion_timeline(self) -> List[Dict[str, Any]]:
        """
        Get complete emotion timeline for session summary.
        
        Returns:
            List of emotion snapshot dictionaries
        """
        return [snapshot.to_dict() for snapshot in self.emotion_snapshots]
