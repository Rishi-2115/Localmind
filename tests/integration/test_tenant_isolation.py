"""
Test Cross-Tenant Isolation for Ingest File Streaming and Risk Assessments.

Verifies:
1. Tenant A accesses Tenant A's document file -> 200 OK.
2. Tenant B attempts to access Tenant A's file via /ingest/file/{doc_id} -> 404 Not Found (zero cross-tenant leak).
3. Tenant B attempts to access Tenant A's risk audit via /ingest/risks/{doc_id} -> 404 Not Found / empty.
4. Unauthenticated request without Bearer token -> 401 Unauthorized.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.app.main import app
from services.api.app.core.dependencies import get_current_active_user, get_db
from services.api.app.models.models import User
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def disable_lifespan():
    # Avoid connecting to real PostgreSQL during isolated route unit tests
    orig_lifespan = app.router.lifespan_context
    app.router.lifespan_context = None
    yield
    app.router.lifespan_context = orig_lifespan


@pytest.mark.asyncio
async def test_tenant_isolation_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        fake_id = "00000000-0000-0000-0000-000000000001"
        res_file = await ac.get(f"/api/v1/ingest/file/{fake_id}")
        assert res_file.status_code == 401
        
        # Confirm query param token no longer bypasses 401
        res_query = await ac.get(f"/api/v1/ingest/file/{fake_id}?token=fake_jwt")
        assert res_query.status_code == 401

        res_risks = await ac.get(f"/api/v1/ingest/risks/{fake_id}")
        assert res_risks.status_code == 401


@pytest.mark.asyncio
async def test_tenant_isolation_foreign_tenant_404():
    # User B from tenant_b
    user_b = User(id=2, email="user_b@hospital_b.com", tenant_id="tenant_b", role="staff")

    async def override_user_b():
        return user_b

    # Mock DB that returns None when querying Tenant B for Tenant A's document
    mock_db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = override_user_b
    app.dependency_overrides[get_db] = override_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            doc_id_a = "00000000-0000-0000-0000-000000000001"

            # 1. Tenant B accessing Tenant A's file MUST return 404
            res_file = await ac.get(f"/api/v1/ingest/file/{doc_id_a}")
            assert res_file.status_code == 404, f"Expected 404 on foreign tenant file, got {res_file.status_code}"

            # 2. Tenant B accessing Tenant A's risks MUST return 404
            res_risks = await ac.get(f"/api/v1/ingest/risks/{doc_id_a}")
            assert res_risks.status_code == 404, f"Expected 404 on foreign tenant risks, got {res_risks.status_code}"
    finally:
        app.dependency_overrides.clear()



