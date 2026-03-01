"""
Adaptive Frame Sampler for rate limit management.

This module provides dynamic frame sampling rate adjustment based on
daily API usage to stay within Gemini API limits.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class AdaptiveFrameSampler:
    """
    Adaptive frame sampler that adjusts sampling rate based on API usage.
    
    Features:
    - Track daily API calls
    - Adjust sampling rate at usage thresholds
    - Reset at midnight UTC
    - Prevent exceeding daily limits
    
    Rate adjustment strategy:
    - 0-700 calls (0-70%): Normal rate (10 frames)
    - 700-900 calls (70-90%): Reduced rate (15 frames)
    - 900-1000 calls (90-100%): Minimal rate (20 frames)
    - 1000+ calls: Disable emotion processing
    """
    
    def __init__(
        self,
        base_sample_rate: int = 10,
        daily_limit: int = 1000,
        threshold_70_percent: int = 700,
        threshold_90_percent: int = 900
    ):
        """
        Initialize adaptive frame sampler.
        
        Args:
            base_sample_rate: Base sampling rate (every Nth frame)
            daily_limit: Maximum API calls per day
            threshold_70_percent: Threshold for first rate reduction
            threshold_90_percent: Threshold for second rate reduction
        """
        self.base_sample_rate = base_sample_rate
        self.daily_limit = daily_limit
        self.threshold_70 = threshold_70_percent
        self.threshold_90 = threshold_90_percent
        
        # State
        self.daily_call_count = 0
        self.current_sample_rate = base_sample_rate
        self.last_reset_date: Optional[datetime] = None
        self.is_disabled = False
        
        logger.info(
            f"Initialized AdaptiveFrameSampler "
            f"(base_rate={base_sample_rate}, limit={daily_limit})"
        )
    
    def should_process_frame(self, frame_number: int) -> bool:
        """
        Determine if frame should be processed based on current sampling rate.
        
        Args:
            frame_number: Current frame number (1-indexed)
        
        Returns:
            True if frame should be processed, False otherwise
        """
        # Check if emotion processing is disabled
        if self.is_disabled:
            return False
        
        # Check daily reset
        self._check_daily_reset()
        
        # Check if we've hit the limit
        if self.daily_call_count >= self.daily_limit:
            self.is_disabled = True
            logger.warning(
                f"Daily API limit reached ({self.daily_limit}). "
                "Emotion processing disabled."
            )
            return False
        
        # Sample based on current rate
        return frame_number % self.current_sample_rate == 0
    
    def record_api_call(self) -> None:
        """
        Record an API call and adjust sampling rate if needed.
        """
        self.daily_call_count += 1
        
        # Adjust sampling rate based on usage
        old_rate = self.current_sample_rate
        
        if self.daily_call_count >= self.threshold_90:
            # 90%+ usage: Minimal sampling (every 20th frame)
            self.current_sample_rate = 20
        elif self.daily_call_count >= self.threshold_70:
            # 70-90% usage: Reduced sampling (every 15th frame)
            self.current_sample_rate = 15
        else:
            # <70% usage: Normal sampling
            self.current_sample_rate = self.base_sample_rate
        
        # Log rate changes
        if old_rate != self.current_sample_rate:
            usage_percent = (self.daily_call_count / self.daily_limit) * 100
            logger.info(
                f"Sampling rate adjusted: {old_rate} -> {self.current_sample_rate} "
                f"(usage: {self.daily_call_count}/{self.daily_limit} = {usage_percent:.1f}%)"
            )
    
    def _check_daily_reset(self) -> None:
        """
        Check if daily reset is needed (midnight UTC).
        """
        now = datetime.now(timezone.utc)
        current_date = now.date()
        
        # Initialize on first call
        if self.last_reset_date is None:
            self.last_reset_date = current_date
            return
        
        # Check if date has changed
        if current_date > self.last_reset_date:
            self._reset_daily_counters()
            self.last_reset_date = current_date
    
    def _reset_daily_counters(self) -> None:
        """
        Reset daily counters at midnight UTC.
        """
        logger.info(
            f"Daily reset: {self.daily_call_count} calls made yesterday. "
            "Resetting counters."
        )
        
        self.daily_call_count = 0
        self.current_sample_rate = self.base_sample_rate
        self.is_disabled = False
    
    def get_usage_stats(self) -> dict:
        """
        Get current usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        usage_percent = (self.daily_call_count / self.daily_limit) * 100
        remaining = self.daily_limit - self.daily_call_count
        
        return {
            "daily_calls": self.daily_call_count,
            "daily_limit": self.daily_limit,
            "usage_percent": round(usage_percent, 1),
            "remaining_calls": remaining,
            "current_sample_rate": self.current_sample_rate,
            "base_sample_rate": self.base_sample_rate,
            "is_disabled": self.is_disabled,
            "last_reset_date": self.last_reset_date.isoformat() if self.last_reset_date else None
        }
    
    def force_reset(self) -> None:
        """
        Force reset counters (for testing or manual intervention).
        """
        logger.warning("Force reset triggered")
        self._reset_daily_counters()
        self.last_reset_date = datetime.now(timezone.utc).date()
    
    def set_daily_call_count(self, count: int) -> None:
        """
        Set daily call count (for testing or recovery).
        
        Args:
            count: New call count
        """
        old_count = self.daily_call_count
        self.daily_call_count = max(0, min(count, self.daily_limit))
        
        # Recalculate sampling rate
        self.record_api_call()
        self.daily_call_count -= 1  # Compensate for the increment in record_api_call
        
        logger.info(f"Daily call count adjusted: {old_count} -> {self.daily_call_count}")
