from api.main import app
from fastapi.testclient import TestClient

def test_cors_dev_environment_allows_all_origin_header():
    client = TestClient(app)
    r = client.get("/health", headers={"Origin": "http://example.com"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"
