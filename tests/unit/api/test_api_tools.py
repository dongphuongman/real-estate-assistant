import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from api.dependencies import get_vector_store
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
        "loan_years": 30,
    }
    response = client.post(
        "/api/v1/tools/mortgage-calculator", json=payload, headers=valid_headers
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
        "loan_years": 30,
    }
    response = client.post(
        "/api/v1/tools/mortgage-calculator", json=payload, headers=valid_headers
    )
    assert response.status_code == 400
    assert "positive" in response.json()["detail"]


def test_tools_unauthorized():
    response = client.get("/api/v1/tools")
    assert response.status_code == 401


class _FakeVectorStore:
    def __init__(self) -> None:
        self._docs_by_id: dict[str, Document] = {}

    def add_doc(self, doc: Document) -> None:
        doc_id = doc.metadata.get("id")
        if doc_id is None:
            raise ValueError("Document metadata must include id")
        self._docs_by_id[str(doc_id)] = doc

    def get_properties_by_ids(self, property_ids: list[str]) -> list[Document]:
        docs: list[Document] = []
        for pid in property_ids:
            if str(pid) in self._docs_by_id:
                docs.append(self._docs_by_id[str(pid)])
        return docs

    def search(self, query: str, k: int = 20):
        docs = list(self._docs_by_id.values())[:k]
        return [(d, 0.5) for d in docs]


def test_compare_properties_success(valid_headers):
    store = _FakeVectorStore()
    store.add_doc(
        Document(page_content="a", metadata={"id": "p1", "price": 100000, "city": "X"})
    )
    store.add_doc(
        Document(page_content="b", metadata={"id": "p2", "price": 150000, "city": "X"})
    )
    app.dependency_overrides[get_vector_store] = lambda: store

    response = client.post(
        "/api/v1/tools/compare-properties",
        json={"property_ids": ["p1", "p2"]},
        headers=valid_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["count"] == 2
    assert data["summary"]["min_price"] == 100000
    assert data["summary"]["max_price"] == 150000
    assert data["summary"]["price_difference"] == 50000

    app.dependency_overrides = {}


def test_compare_properties_store_unavailable(valid_headers):
    app.dependency_overrides[get_vector_store] = lambda: None

    response = client.post(
        "/api/v1/tools/compare-properties",
        json={"property_ids": ["p1"]},
        headers=valid_headers,
    )

    assert response.status_code == 503
    app.dependency_overrides = {}


def test_price_analysis_success(valid_headers):
    store = _FakeVectorStore()
    store.add_doc(
        Document(
            page_content="a",
            metadata={
                "id": "p1",
                "price": 100000,
                "price_per_sqm": 2000,
                "property_type": "Apartment",
            },
        )
    )
    store.add_doc(
        Document(
            page_content="b",
            metadata={
                "id": "p2",
                "price": 200000,
                "price_per_sqm": 2500,
                "property_type": "House",
            },
        )
    )
    store.add_doc(
        Document(
            page_content="c",
            metadata={
                "id": "p3",
                "price": 150000,
                "price_per_sqm": 2200,
                "property_type": "Apartment",
            },
        )
    )
    app.dependency_overrides[get_vector_store] = lambda: store

    response = client.post(
        "/api/v1/tools/price-analysis",
        json={"query": "apartments"},
        headers=valid_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["average_price"] == 150000
    assert data["median_price"] == 150000
    assert data["min_price"] == 100000
    assert data["max_price"] == 200000
    assert data["distribution_by_type"]["Apartment"] == 2
    assert data["distribution_by_type"]["House"] == 1

    app.dependency_overrides = {}


def test_location_analysis_success(valid_headers):
    store = _FakeVectorStore()
    store.add_doc(
        Document(
            page_content="a", metadata={"id": "p1", "city": "X", "lat": 1.0, "lon": 2.0}
        )
    )
    app.dependency_overrides[get_vector_store] = lambda: store

    response = client.post(
        "/api/v1/tools/location-analysis",
        json={"property_id": "p1"},
        headers=valid_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["city"] == "X"
    assert data["lat"] == 1.0
    assert data["lon"] == 2.0

    app.dependency_overrides = {}
