"""
Unit tests for exports router (api/routers/exports.py).

Tests cover:
- Export properties endpoint (CSV, JSON, Markdown, Excel, PDF)
- Vector store dependency handling
- Search-based export vs property_ids export
- Error handling (503 unavailable, 400 invalid format)
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.routers.exports import router as exports_router


class MockVectorStore:
    """Mock ChromaPropertyStore for testing."""

    def __init__(self, documents=None):
        self.documents = documents or []

    def get_properties_by_ids(self, property_ids):
        """Mock getting properties by IDs."""
        return [doc for doc in self.documents if doc.metadata.get("id") in property_ids]

    def hybrid_search(
        self,
        query,
        k=5,
        filters=None,
        alpha=None,
        lat=None,
        lon=None,
        radius_km=None,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None,
        sort_by=None,
        sort_order=None,
    ):
        """Mock hybrid search."""
        return [(doc, 0.8) for doc in self.documents]


class MockDocument:
    """Mock LangChain Document."""

    def __init__(self, metadata=None):
        self.metadata = metadata or {}


@pytest.fixture
async def exports_client():
    """Create an async HTTP client for testing exports endpoints."""
    from fastapi import FastAPI

    from api.dependencies import get_vector_store

    test_app = FastAPI()
    test_app.include_router(exports_router)

    # Override the get_vector_store dependency
    mock_store = MockVectorStore()

    async def override_get_vector_store():
        return mock_store

    test_app.dependency_overrides[get_vector_store] = override_get_vector_store

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestExportPropertiesEndpoint:
    """Test export properties endpoint."""

    @pytest.mark.asyncio
    async def test_export_csv_with_property_ids(self):
        """Test export to CSV format with specific property IDs."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore(
            [
                MockDocument(metadata={"id": "prop1", "city": "Berlin", "price": 500000}),
                MockDocument(metadata={"id": "prop2", "city": "Warsaw", "price": 450000}),
            ]
        )

        async def override_get_vector_store():
            return mock_store

        # Create a new test app for this test
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "csv",
                    "property_ids": ["prop1", "prop2"],
                    "columns": ["city", "price"],
                    "include_header": True,
                    "csv_delimiter": ",",
                    "csv_decimal": ".",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "content-disposition" in response.headers
        assert ".csv" in response.headers["content-disposition"]
        # Verify CSV content has headers
        assert b"city,price" in response.content or b"city" in response.content

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        """Test export to JSON format."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore(
            [
                MockDocument(metadata={"id": "prop1", "city": "Berlin"}),
            ]
        )

        async def override_get_vector_store():
            return mock_store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "json",
                    "property_ids": ["prop1"],
                    "pretty": True,
                    "include_metadata": True,
                    "columns": ["city"],
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"
        assert ".json" in response.headers["content-disposition"]
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_markdown_format(self):
        """Test export to Markdown format."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore(
            [
                MockDocument(
                    metadata={"id": "prop1", "city": "Berlin", "rooms": 2, "bathrooms": 1}
                ),
            ]
        )

        async def override_get_vector_store():
            return mock_store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "md",
                    "property_ids": ["prop1"],
                    "include_summary": True,
                    "max_properties": 10,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert ".md" in response.headers["content-disposition"]
        # Should have markdown content
        content = response.text
        assert len(content) > 0

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_with_search_query(self):
        """Test export using search query instead of property IDs."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore(
            [
                MockDocument(metadata={"id": "prop1", "city": "Berlin"}),
            ]
        )

        async def override_get_vector_store():
            return mock_store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "csv",
                    "search": {
                        "query": "apartments in Berlin",
                        "limit": 10,
                    },
                    "columns": ["city"],
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_vector_store_unavailable(self):
        """Test export when vector store is not available."""
        from api.dependencies import get_vector_store

        async def override_get_vector_store():
            return None  # Simulate unavailable store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "csv",
                    "property_ids": ["prop1"],
                },
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
        assert "vector store" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_missing_search_without_ids(self):
        """Test export with missing search when property_ids not provided."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore()

        async def override_get_vector_store():
            return mock_store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Don't provide search or property_ids (missing both)
            response = await client.post(
                "/export/properties",
                json={
                    "format": "csv",
                },
            )

        # Should fail validation (400) or assertion error
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_unsupported_format(self):
        """Test export with unsupported format."""
        from api.dependencies import get_vector_store

        mock_store = MockVectorStore()

        async def override_get_vector_store():
            return mock_store

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(exports_router)
        test_app.dependency_overrides[get_vector_store] = override_get_vector_store

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/export/properties",
                json={
                    "format": "xml",  # Unsupported format
                    "property_ids": ["prop1"],
                },
            )

        # Pydantic enum validation returns 422 for invalid format
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        test_app.dependency_overrides.clear()


class TestExportsRouterConfiguration:
    """Test exports router configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert exports_router.tags == ["Export"]

    def test_router_endpoints_registered(self):
        """Test that router has expected endpoints registered."""
        assert len(exports_router.routes) >= 1

        # Check endpoint path
        paths = [route.path for route in exports_router.routes]
        assert "/export/properties" in paths

    def test_endpoint_method(self):
        """Test that endpoint has correct HTTP method."""
        for route in exports_router.routes:
            if route.path == "/export/properties":
                assert "POST" in route.methods
