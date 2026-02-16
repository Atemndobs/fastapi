import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_rfps():
    response = client.get("/rfps?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "id" in data[0]
        assert "title" in data[0]
        assert "location" in data[0]

def test_search_rfps():
    response = client.get("/rfps/search?query=website")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert any("website" in rfp["title"].lower() or 
                  "website" in rfp["description"].lower() 
                  for rfp in data)

@pytest.mark.asyncio
async def test_get_rfp_by_id():
    # First get a list of RFPs to get a valid ID
    list_response = client.get("/rfps?limit=1")
    if list_response.status_code == 200 and list_response.json():
        rfp_id = list_response.json()[0]["id"]
        response = client.get(f"/rfps/{rfp_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rfp_id
    else:
        # Skip if no RFPs found
        pytest.skip("No RFPs found to test with")

def test_invalid_rfp_id():
    response = client.get("/rfps/invalid-id-123")
    assert response.status_code == 404

def test_invalid_category():
    response = client.get("/rfps?category=invalid-category")
    assert response.status_code == 422  # Validation error
