import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.dependencies.auth import get_current_user

# Mock user data
MOCK_TENANT = {"id": 1, "role": "Tenant"}
MOCK_OWNER = {"id": 2, "role": "Owner"}

async def override_get_current_user_tenant():
    return MOCK_TENANT

async def override_get_current_user_unauthorized():
    raise HTTPException(status_code=401, detail="Invalid token")

@pytest_asyncio.fixture
def client():
    app.dependency_overrides[get_current_user] = override_get_current_user_tenant
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides = {}
