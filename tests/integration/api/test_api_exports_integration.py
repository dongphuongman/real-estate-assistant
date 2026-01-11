from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_export_properties_endpoint_auth_enforcement():
    response = client.post(
        "/api/v1/export/properties", json={"format": "csv", "property_ids": ["p1"]}
    )
    assert response.status_code in [401, 403]

    response = client.post(
        "/api/v1/export/properties",
        json={"format": "csv", "property_ids": ["p1"]},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_export_properties_endpoint_validation_error():
    headers = {"X-API-Key": "dev-secret-key"}
    response = client.post(
        "/api/v1/export/properties", json={"format": "csv"}, headers=headers
    )
    assert response.status_code == 422
