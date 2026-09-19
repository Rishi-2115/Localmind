import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from services.api.app.main import app
from services.api.app.core.security import get_password_hash
from services.api.app.models.models import User
from services.api.app.core.database import get_db

@pytest.fixture
def mock_db_with_user():
    user = User(
        id=1,
        tenant_id="test_tenant",
        email="fresh_admin@localmind.in",
        hashed_password=get_password_hash("TemporaryPass123!"),
        role="admin",
        must_change_password=True,
    )
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    return mock_session, user

@pytest.mark.asyncio
async def test_fresh_account_password_change_required(mock_db_with_user):
    mock_session, user = mock_db_with_user

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Attempt login with initial credentials -> must return 403 PASSWORD_CHANGE_REQUIRED
        login_res = await ac.post(
            "/api/v1/auth/login",
            data={"username": "fresh_admin@localmind.in", "password": "TemporaryPass123!"},
        )
        assert login_res.status_code == 403
        data = login_res.json()
        assert data["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"
        assert "access_token" not in data

        # 2. Attempt changing password to weak password (<12 chars) -> must be rejected
        weak_res = await ac.patch(
            "/api/v1/auth/change-password",
            json={
                "email": "fresh_admin@localmind.in",
                "current_password": "TemporaryPass123!",
                "new_password": "short",
            },
        )
        assert weak_res.status_code == 400
        assert "at least 12 characters" in weak_res.json()["detail"]

        # 3. Attempt changing password to blocklisted password -> must be rejected
        blocklist_res = await ac.patch(
            "/api/v1/auth/change-password",
            json={
                "email": "fresh_admin@localmind.in",
                "current_password": "TemporaryPass123!",
                "new_password": "localmind_admin_2027",
            },
        )
        assert blocklist_res.status_code == 400
        assert "too common" in blocklist_res.json()["detail"]

        # 4. Supply compliant strong password (>= 12 chars)
        strong_res = await ac.patch(
            "/api/v1/auth/change-password",
            json={
                "email": "fresh_admin@localmind.in",
                "current_password": "TemporaryPass123!",
                "new_password": "NewCompliantLegalPassword2027#",
            },
        )
        assert strong_res.status_code == 200
        strong_data = strong_res.json()
        assert "access_token" in strong_data
        assert user.must_change_password is False

    app.dependency_overrides.clear()
