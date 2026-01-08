import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

@pytest.fixture
def valid_headers():
    return {"X-API-Key": "dev-secret-key"}

def test_list_tools(valid_headers):
    response = client.get("/api/v1/tools", headers=valid_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [tool["name"] for tool in data]
    assert "mortgage_calculator" in names

def test_mortgage_calculator_success(valid_headers):
    payload = {
        "property_price": 500000,
        "down_payment_percent": 20,
        "interest_rate": 5.0,
        "loan_years": 30
    }
    response = client.post(
        "/api/v1/tools/mortgage-calculator",
        json=payload,
        headers=valid_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_payment"] > 0
    assert data["loan_amount"] == 400000
    assert data["down_payment"] == 100000

def test_mortgage_calculator_invalid_input(valid_headers):
    payload = {
        "property_price": -100,  # Invalid
        "down_payment_percent": 20,
        "interest_rate": 5.0,
        "loan_years": 30
    }
    response = client.post(
        "/api/v1/tools/mortgage-calculator",
        json=payload,
        headers=valid_headers
    )
    assert response.status_code == 400
    assert "positive" in response.json()["detail"]

def test_tools_unauthorized():
    response = client.get("/api/v1/tools")
    assert response.status_code == 401
