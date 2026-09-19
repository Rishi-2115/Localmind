import pytest
import asyncio
from services.api.app.core.circuit_breaker import CircuitBreaker

@pytest.mark.asyncio
async def test_circuit_breaker_success():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    async def dummy_success():
        return "success"
        
    res = await cb.call(dummy_success)
    assert res == "success"
    assert cb.state == "CLOSED"

@pytest.mark.asyncio
async def test_circuit_breaker_failure():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    async def dummy_fail():
        raise ValueError("error")
        
    # First failure
    res1 = await cb.call(dummy_fail)
    assert res1.get("status") == "degraded"
    assert cb.state == "CLOSED"
    assert cb.failures == 1
    
    # Second failure opens breaker
    res2 = await cb.call(dummy_fail)
    assert res2.get("status") == "degraded"
    assert cb.state == "OPEN"
    
    # Wait for recovery timeout
    await asyncio.sleep(1.1)
    
    # Next call should be HALF_OPEN
    async def dummy_success():
        return "success"
        
    res3 = await cb.call(dummy_success)
    assert res3 == "success"
    assert cb.state == "CLOSED"
