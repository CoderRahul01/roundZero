"""
Performance Monitor

Tracks and reports performance metrics for real-time voice interaction.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetric:
    """Single latency measurement."""
    service: str
    operation: str
    latency_ms: float
    timestamp: float
    success: bool


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics."""
    timestamp: float
    total_response_time_ms: float
    stt_latency_ms: float
    tts_latency_ms: float
    claude_latency_ms: float
    gemini_latency_ms: float
    analysis_latency_ms: float
    cache_hit_rate: float
    error_count: int


class PerformanceMonitor:
    """
    Tracks response cycle latencies and service performance.
    """
    
    # Performance thresholds (in milliseconds)
    THRESHOLDS = {
        "total_response": 5000,  # 5s total
        "stt": 500,
        "tts": 1500,
        "claude": 2000,
        "gemini": 1000,
        "analysis": 2000
    }
    
    def __init__(self, history_size: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            history_size: Number of recent metrics to keep in memory
        """
        self.history_size = history_size
        
        # Metric storage
        self._latency_history: deque[LatencyMetric] = deque(maxlen=history_size)
        self._response_cycles: deque[float] = deque(maxlen=history_size)
        
        # Service-specific metrics
        self._service_latencies: Dict[str, deque[float]] = {
            "stt": deque(maxlen=history_size),
            "tts": deque(maxlen=history_size),
            "claude": deque(maxlen=history_size),
            "gemini": deque(maxlen=history_size),
            "analysis": deque(maxlen=history_size)
        }
        
        # Error tracking
        self._error_counts: Dict[str, int] = {
            "stt": 0,
            "tts": 0,
            "claude": 0,
            "gemini": 0,
            "network": 0
        }
        
        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Alert tracking
        self._alerts: List[str] = []
    
    def record_latency(
        self,
        service: str,
        operation: str,
        latency_ms: float,
        success: bool = True
    ):
        """
        Record a latency measurement.
        """
        metric = LatencyMetric(
            service=service,
            operation=operation,
            latency_ms=latency_ms,
            timestamp=time.time(),
            success=success
        )
        
        self._latency_history.append(metric)
        
        # Add to service-specific history
        if service in self._service_latencies:
            self._service_latencies[service].append(latency_ms)
        
        # Check threshold and alert if exceeded
        threshold = self.THRESHOLDS.get(service)
        if threshold and latency_ms > threshold:
            self._alert(
                f"{service} latency exceeded threshold: {latency_ms:.0f}ms > {threshold}ms"
            )
        
        logger.debug(f"{service}.{operation}: {latency_ms:.2f}ms")
    
    def record_response_cycle(self, total_time_ms: float):
        """
        Record total response cycle time.
        """
        self._response_cycles.append(total_time_ms)
        
        if total_time_ms > self.THRESHOLDS["total_response"]:
            self._alert(
                f"Total response time exceeded threshold: {total_time_ms:.0f}ms > {self.THRESHOLDS['total_response']}ms"
            )
    
    def record_error(self, service: str):
        """
        Record a service error.
        """
        if service in self._error_counts:
            self._error_counts[service] += 1
            logger.warning(f"{service} error count: {self._error_counts[service]}")
    
    def record_cache_hit(self):
        """Record cache hit."""
        self._cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self._cache_misses += 1
    
    def get_average_latency(self, service: str) -> float:
        """
        Get average latency for a service.
        """
        latencies = self._service_latencies.get(service, [])
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)
    
    def get_p95_latency(self, service: str) -> float:
        """
        Get 95th percentile latency for a service.
        """
        latencies = list(self._service_latencies.get(service, []))
        if not latencies:
            return 0.0
        
        latencies.sort()
        index = int(len(latencies) * 0.95)
        return latencies[index] if index < len(latencies) else latencies[-1]
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total
    
    def get_error_count(self, service: Optional[str] = None) -> int:
        """
        Get error count for a service or total.
        """
        if service:
            return self._error_counts.get(service, 0)
        return sum(self._error_counts.values())
    
    def get_performance_snapshot(self) -> PerformanceSnapshot:
        """
        Get current performance snapshot.
        """
        return PerformanceSnapshot(
            timestamp=time.time(),
            total_response_time_ms=self._get_avg_response_time(),
            stt_latency_ms=self.get_average_latency("stt"),
            tts_latency_ms=self.get_average_latency("tts"),
            claude_latency_ms=self.get_average_latency("claude"),
            gemini_latency_ms=self.get_average_latency("gemini"),
            analysis_latency_ms=self.get_average_latency("analysis"),
            cache_hit_rate=self.get_cache_hit_rate(),
            error_count=self.get_error_count()
        )
    
    def get_detailed_metrics(self) -> dict:
        """
        Get detailed performance metrics.
        """
        return {
            "averages": {
                "total_response_ms": self._get_avg_response_time(),
                "stt_ms": self.get_average_latency("stt"),
                "tts_ms": self.get_average_latency("tts"),
                "claude_ms": self.get_average_latency("claude"),
                "gemini_ms": self.get_average_latency("gemini"),
                "analysis_ms": self.get_average_latency("analysis")
            },
            "p95": {
                "stt_ms": self.get_p95_latency("stt"),
                "tts_ms": self.get_p95_latency("tts"),
                "claude_ms": self.get_p95_latency("claude"),
                "gemini_ms": self.get_p95_latency("gemini"),
                "analysis_ms": self.get_p95_latency("analysis")
            },
            "cache": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": round(self.get_cache_hit_rate(), 3)
            },
            "errors": self._error_counts.copy(),
            "total_errors": self.get_error_count(),
            "alerts": self._alerts[-10:],  # Last 10 alerts
            "sample_size": len(self._latency_history)
        }
    
    def _get_avg_response_time(self) -> float:
        """Get average total response time."""
        if not self._response_cycles:
            return 0.0
        return sum(self._response_cycles) / len(self._response_cycles)
    
    def _alert(self, message: str):
        """
        Record an alert.
        """
        alert = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self._alerts.append(alert)
        logger.warning(f"PERFORMANCE ALERT: {message}")
    
    def reset_metrics(self):
        """
        Reset all metrics.
        """
        self._latency_history.clear()
        self._response_cycles.clear()
        for service in self._service_latencies:
            self._service_latencies[service].clear()
        self._error_counts = {k: 0 for k in self._error_counts}
        self._cache_hits = 0
        self._cache_misses = 0
        self._alerts.clear()
        logger.info("Performance metrics reset")


class LatencyTracker:
    """
    Context manager for tracking operation latency.
    """
    
    def __init__(
        self,
        monitor: PerformanceMonitor,
        service: str,
        operation: str
    ):
        self.monitor = monitor
        self.service = service
        self.operation = operation
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            latency_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            
            self.monitor.record_latency(
                service=self.service,
                operation=self.operation,
                latency_ms=latency_ms,
                success=self.success
            )
            
            if not self.success:
                self.monitor.record_error(self.service)
        
        return False  # Don't suppress exceptions
    
    def mark_failure(self):
        """Mark this operation as failed."""
        self.success = False


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def track_latency(service: str, operation: str) -> LatencyTracker:
    """
    Convenience function to track latency.
    
    Usage:
        with track_latency("claude", "analyze_relevance"):
            result = await claude_api.analyze(...)
    """
    monitor = get_performance_monitor()
    return LatencyTracker(monitor, service, operation)
