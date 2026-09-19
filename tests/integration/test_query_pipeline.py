import pytest
from httpx import AsyncClient
from services.api.app.main import app
from services.api.app.core.dependencies import get_current_active_user
from services.api.app.models.models import User

@pytest.mark.asyncio
async def test_query_pipeline_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/query", json={"query": "test"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_query_pipeline_authorized_mock():
    # To fully test integration, we'd mock the DB and Semantic Cache
    # Here is a basic skeleton for how it would look
    async def override_get_current_user():
        return User(id=1, tenant_id="t1", role="staff")
        
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    
    # Ideally mock db session as well here
    
    # async with AsyncClient(app=app, base_url="http://test") as ac:
    #     response = await ac.post("/api/v1/query", json={"query": "test"})
    # assert response.status_code == 200 # with properly mocked dependencies
    
    app.dependency_overrides.clear()
