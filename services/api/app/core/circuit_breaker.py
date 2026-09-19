import time
import httpx
from .config import settings
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                logger.warning("Circuit breaker is OPEN. Returning fallback.")
                return self._fallback()

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            logger.error(f"Call failed. Failures: {self.failures}. Error: {e}")
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            return self._fallback()

    def _fallback(self):
        return {
            "error": "Service temporarily unavailable due to high load or failure. Graceful degradation active.",
            "status": "degraded"
        }

ollama_circuit_breaker = CircuitBreaker()
