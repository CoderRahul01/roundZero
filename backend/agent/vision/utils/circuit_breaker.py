"""
Circuit Breaker Pattern implementation for service resilience.

This module provides a circuit breaker to prevent cascading failures
when external services are unavailable or degraded.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failing, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Features:
    - Automatic state transitions
    - Configurable failure threshold
    - Configurable timeout for recovery attempts
    - Failure tracking and statistics
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
        logger.info(
            f"CircuitBreaker '{name}' initialized "
            f"(threshold: {failure_threshold}, timeout: {recovery_timeout}s)"
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception if circuit is closed
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # After 3 successful calls in HALF_OPEN, close circuit
            if self.success_count >= 3:
                self._transition_to_closed()
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        logger.warning(
            f"CircuitBreaker '{self.name}' failure "
            f"({self.failure_count}/{self.failure_threshold})"
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN immediately opens circuit
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.
        
        Returns:
            True if recovery should be attempted
        """
        if not self.last_failure_time:
            return False
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        logger.info(f"CircuitBreaker '{self.name}' -> CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        logger.warning(f"CircuitBreaker '{self.name}' -> OPEN")
        self.state = CircuitState.OPEN
        self.success_count = 0
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        logger.info(f"CircuitBreaker '{self.name}' -> HALF_OPEN (testing recovery)")
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
    
    def get_state(self) -> str:
        """
        Get current circuit state.
        
        Returns:
            State name
        """
        return self.state.value
    
    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"CircuitBreaker '{self.name}' manually reset")
        self._transition_to_closed()


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator for applying circuit breaker to async functions.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type to catch
    
    Example:
        @circuit_breaker("gemini_api", failure_threshold=5, recovery_timeout=60)
        async def call_gemini_api():
            # API call here
            pass
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        # Attach breaker to function for access to stats
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Features:
    - Centralized circuit breaker management
    - Statistics aggregation
    - Bulk reset capability
    """
    
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}
    
    def register(self, breaker: CircuitBreaker):
        """
        Register a circuit breaker.
        
        Args:
            breaker: CircuitBreaker instance
        """
        self.breakers[breaker.name] = breaker
        logger.info(f"Registered circuit breaker: {breaker.name}")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get circuit breaker by name.
        
        Args:
            name: Circuit breaker name
        
        Returns:
            CircuitBreaker instance or None
        """
        return self.breakers.get(name)
    
    def get_all_stats(self) -> dict:
        """
        Get statistics for all circuit breakers.
        
        Returns:
            Dictionary with all breaker stats
        """
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")
    
    def get_open_breakers(self) -> list[str]:
        """
        Get list of open circuit breakers.
        
        Returns:
            List of breaker names in OPEN state
        """
        return [
            name for name, breaker in self.breakers.items()
            if breaker.state == CircuitState.OPEN
        ]


# Global registry
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """
    Get global circuit breaker registry.
    
    Returns:
        CircuitBreakerRegistry instance
    """
    return _registry
