import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import AsyncMock, patch
from app.dependencies.auth import get_current_user
from fastapi import status, HTTPException

# Mock user for authentication
MOCK_TENANT = {"id": 1, "role": "Tenant"}
MOCK_LANDLORD = {"id": 2, "role": "Landlord"}

async def override_get_current_user_tenant():
    return MOCK_TENANT

async def override_get_current_user_landlord():
    return MOCK_LANDLORD

async def override_get_current_user_unauthenticated():
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

# Helper to temporarily set and restore dependency overrides
@pytest.fixture
def tenant_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user_tenant
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def landlord_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user_landlord
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def unauthenticated_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user_unauthenticated
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
@patch('app.services.search.search_properties', new_callable=AsyncMock)
@patch('app.services.gebeta.geocode', new_callable=AsyncMock)
async def test_search_properties_endpoint_success(mock_geocode, mock_search_properties, client, tenant_auth_override):
    mock_geocode.return_value = {"lat": 9.0, "lon": 38.7}
    mock_search_properties.return_value = [
        {
            "id": 1, "title": "Apartment in Bole", "description": "Nice place", "location": "Bole",
            "price": 3000.00, "house_type": "apartment", "amenities": ["wifi"], "bedrooms": 2,
            "lat": 9.0, "lon": 38.7, "distance_km": 0.5, "map_url": "http://example.com/map"
        }
    ]
    
    response = await client.get(
        "/api/v1/search?location=Bole&min_price=1000&max_price=5000&house_type=apartment&max_distance_km=5&sort_by=distance",
    )
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert isinstance(json_response, list)
    assert len(json_response) == 1
    assert json_response[0]["title"] == "Apartment in Bole"
    assert "distance_km" in json_response[0]
    mock_search_properties.assert_called_once()
    mock_geocode.assert_called_once_with("Bole")

@pytest.mark.asyncio
async def test_search_properties_endpoint_unauthenticated(client, unauthenticated_auth_override):
    response = await client.get("/api/v1/search")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_search_properties_endpoint_forbidden_role(client, landlord_auth_override):
    response = await client.get("/api/v1/search")
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
@patch('app.services.search.save_search', new_callable=AsyncMock)
async def test_save_search_endpoint_success(mock_save_search, client, tenant_auth_override):
    mock_save_search.return_value = 123

    response = await client.post(
        "/api/v1/saved-searches",
        json={"location": "Bole", "min_price": 1000, "max_price": 5000, "house_type": "apartment", "max_distance_km": 5.0},
    )
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["message"] == "Search saved"
    assert json_response["id"] == 123
    mock_save_search.assert_called_once()

@pytest.mark.asyncio
async def test_save_search_endpoint_forbidden_role(client, landlord_auth_override):
    response = await client.post(
        "/api/v1/saved-searches",
        json={"location": "Bole"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
@patch('app.services.gebeta.geocode', new_callable=AsyncMock)
async def test_geocode_endpoint_success(mock_geocode, client):
    mock_geocode.return_value = {"lat": 9.02, "lon": 38.76}
    response = await client.get("/api/v1/geocode/Bole")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"lat": 9.02, "lon": 38.76}
    mock_geocode.assert_called_once_with("Bole")

@pytest.mark.asyncio
@patch('app.services.gebeta.geocode', new_callable=AsyncMock)
async def test_geocode_endpoint_fallback(mock_geocode, client):
    mock_geocode.side_effect = Exception("Gebeta API error") # Simulate failure
    response = await client.get("/api/v1/geocode/InvalidLocation")
    assert response.status_code == status.HTTP_200_OK # Fallback returns 200
    assert response.json() == {"lat": 9.03, "lon": 38.75} # Expected fallback coordinates

@pytest.mark.asyncio
@patch('app.services.gebeta.get_map_tile', new_callable=AsyncMock)
async def test_map_tile_proxy_success(mock_get_map_tile, client):
    mock_get_map_tile.return_value = b"someimagedata"

    response = await client.get("/api/v1/map/tile/1/2/3")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"someimagedata"
    assert response.headers["content-type"] == "image/png"
    mock_get_map_tile.assert_called_once_with(1, 2, 3)

@pytest.mark.asyncio
@patch('app.services.gebeta.get_map_tile', new_callable=AsyncMock)
async def test_map_tile_proxy_failure(mock_get_map_tile, client):
    mock_get_map_tile.side_effect = ValueError("Map tile service error")

    response = await client.get("/api/v1/map/tile/1/2/3")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to fetch map tile" in response.json()["detail"]

@pytest.mark.asyncio
@patch('app.services.search.search_properties', new_callable=AsyncMock)
async def test_search_properties_invalid_price_range(mock_search_properties, client, tenant_auth_override):
    response = await client.get("/api/v1/search?min_price=5000&max_price=1000")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "min_price cannot be greater than max_price" in response.json()["detail"]
    mock_search_properties.assert_not_called()

@pytest.mark.asyncio
@patch('app.services.search.search_properties', new_callable=AsyncMock)
@patch('app.services.gebeta.geocode', new_callable=AsyncMock)
async def test_search_properties_sort_by_price(mock_geocode, mock_search_properties, client, tenant_auth_override):
    mock_geocode.return_value = {"lat": 9.0, "lon": 38.7}
    mock_search_properties.return_value = [
        {
            "id": 1, "title": "Apartment A", "description": "Desc A", "location": "Loc A",
            "price": 1000.00, "house_type": "apartment", "amenities": ["wifi"], "bedrooms": 1,
            "lat": 9.0, "lon": 38.7, "distance_km": 1.0, "map_url": "http://example.com/map"
        },
        {
            "id": 2, "title": "Apartment B", "description": "Desc B", "location": "Loc B",
            "price": 2000.00, "house_type": "apartment", "amenities": ["parking"], "bedrooms": 2,
            "lat": 9.0, "lon": 38.7, "distance_km": 2.0, "map_url": "http://example.com/map"
        }
    ]
    response = await client.get("/api/v1/search?location=Bole&sort_by=price")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response[0]["price"] == 1000.00
    assert json_response[1]["price"] == 2000.00
    mock_search_properties.assert_called_once_with(
        location='Bole', min_price=None, max_price=None, house_type=None, amenities=None, bedrooms=None, max_distance_km=None, sort_by='price'
    )
