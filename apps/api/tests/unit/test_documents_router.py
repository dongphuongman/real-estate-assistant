"""
Unit tests for documents router (api/routers/documents.py).

Tests cover:
- Router configuration
- Helper functions (_parse_tags, _read_upload_file_limited, _document_to_response)
- POST /documents  (upload: success, validation errors, too large, storage failure)
- GET  /documents  (list: empty, with data, filters, pagination, invalid sort)
- GET  /documents/expiring  (empty, with results)
- GET  /documents/{id}  (download: success, not found, storage error)
- PATCH /documents/{id}  (update: success, not found, empty update)
- DELETE /documents/{id}  (delete: success, not found, storage error)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.routers.documents import (
    _document_to_response,
    _parse_tags,
    _read_upload_file_limited,
)
from api.routers.documents import (
    router as documents_router,
)
from db.database import get_db

# ---------------------------------------------------------------------------
# Mock user
# ---------------------------------------------------------------------------


class _MockUser:
    """Mock authenticated user for dependency override."""

    def __init__(self) -> None:
        self.id = "test-user-123"
        self.email = "test@example.com"
        self.is_active = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def documents_client(db_session):
    """Create an async HTTP client wired to an isolated app with the documents router."""
    from api.deps.auth import get_current_active_user

    test_app = FastAPI()
    test_app.include_router(documents_router)

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return _MockUser()

    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


def _make_mock_document(
    doc_id: str = "doc-001",
    user_id: str = "test-user-123",
    filename: str = "abc_test.pdf",
    original_filename: str = "test.pdf",
    file_type: str = "application/pdf",
    file_size: int = 1024,
    storage_path: str = "/tmp/test.pdf",
    property_id: str | None = None,
    category: str | None = None,
    tags: str | None = None,
    description: str | None = None,
    ocr_status: str = "pending",
    expiry_date: datetime | None = None,
) -> MagicMock:
    """Create a mock DocumentDB object."""
    doc = MagicMock()
    doc.id = doc_id
    doc.user_id = user_id
    doc.property_id = property_id
    doc.filename = filename
    doc.original_filename = original_filename
    doc.file_type = file_type
    doc.file_size = file_size
    doc.storage_path = storage_path
    doc.category = category
    doc.tags = tags
    doc.description = description
    doc.ocr_status = ocr_status
    doc.expiry_date = expiry_date
    doc.created_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
    return doc


# ---------------------------------------------------------------------------
# Router configuration
# ---------------------------------------------------------------------------


class TestDocumentsRouterConfiguration:
    """Test router metadata and route registration."""

    def test_router_prefix(self):
        assert documents_router.prefix == "/documents"

    def test_router_tag(self):
        assert "Documents" in documents_router.tags

    def test_routes_registered(self):
        paths = {route.path for route in documents_router.routes}
        assert "/documents" in paths
        assert "/documents/expiring" in paths
        assert "/documents/{document_id}" in paths


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestParseTags:
    """Tests for _parse_tags helper."""

    def test_parse_json_array(self):
        assert _parse_tags('["tag1", "tag2"]') == ["tag1", "tag2"]

    def test_parse_comma_separated(self):
        assert _parse_tags("tag1, tag2, tag3") == ["tag1", "tag2", "tag3"]

    def test_parse_empty_string(self):
        assert _parse_tags("") is None

    def test_parse_none(self):
        assert _parse_tags(None) is None

    def test_parse_json_object_returns_none(self):
        assert _parse_tags('{"key": "value"}') is None

    def test_parse_comma_with_empty_parts(self):
        result = _parse_tags("a,,b,")
        assert result == ["a", "b"]

    def test_parse_single_tag_json(self):
        assert _parse_tags('["single"]') == ["single"]

    def test_parse_single_comma_tag(self):
        assert _parse_tags("single") == ["single"]


class TestDocumentToResponse:
    """Tests for _document_to_response helper."""

    def test_basic_conversion(self):
        doc = _make_mock_document()
        result = _document_to_response(doc)
        assert result["id"] == "doc-001"
        assert result["filename"] == "abc_test.pdf"
        assert result["original_filename"] == "test.pdf"
        assert result["file_type"] == "application/pdf"
        assert result["file_size"] == 1024

    def test_tags_parsed_from_json(self):
        doc = _make_mock_document(tags='["contract", "legal"]')
        result = _document_to_response(doc)
        assert result["tags"] == ["contract", "legal"]

    def test_tags_none_when_not_set(self):
        doc = _make_mock_document(tags=None)
        result = _document_to_response(doc)
        assert result["tags"] is None

    def test_tags_none_on_invalid_json(self):
        doc = _make_mock_document(tags="not valid json")
        result = _document_to_response(doc)
        assert result["tags"] is None

    def test_all_fields_present(self):
        doc = _make_mock_document(
            property_id="prop-1",
            category="contract",
            description="A test document",
            expiry_date=datetime(2026, 12, 31, tzinfo=UTC),
        )
        result = _document_to_response(doc)
        assert result["property_id"] == "prop-1"
        assert result["category"] == "contract"
        assert result["description"] == "A test document"
        assert result["expiry_date"] == datetime(2026, 12, 31, tzinfo=UTC)
        assert "created_at" in result
        assert "updated_at" in result


class TestReadUploadFileLimited:
    """Tests for _read_upload_file_limited helper."""

    @pytest.mark.asyncio
    async def test_small_file(self):
        file_mock = AsyncMock()
        file_mock.read.side_effect = [b"hello", b""]
        data, too_large = await _read_upload_file_limited(file_mock, 1024)
        assert data == b"hello"
        assert too_large is False

    @pytest.mark.asyncio
    async def test_file_exceeds_limit(self):
        file_mock = AsyncMock()
        file_mock.read.side_effect = [b"a" * 100, b""]
        data, too_large = await _read_upload_file_limited(file_mock, 50)
        assert too_large is True

    @pytest.mark.asyncio
    async def test_empty_file(self):
        file_mock = AsyncMock()
        file_mock.read.side_effect = [b""]
        data, too_large = await _read_upload_file_limited(file_mock, 1024)
        assert data == b""
        assert too_large is False

    @pytest.mark.asyncio
    async def test_multi_chunk_within_limit(self):
        file_mock = AsyncMock()
        file_mock.read.side_effect = [b"chunk1", b"chunk2", b""]
        data, too_large = await _read_upload_file_limited(file_mock, 1024)
        assert data == b"chunk1chunk2"
        assert too_large is False


# ---------------------------------------------------------------------------
# POST /documents  —  upload_document
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """Tests for POST /documents."""

    @pytest.mark.asyncio
    async def test_upload_success(self, documents_client):
        """Should upload a valid PDF and return 201."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service") as mock_ocr_factory,
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_ocr_svc = MagicMock()
            mock_ocr_svc.is_available.return_value = False
            mock_ocr_factory.return_value = mock_ocr_svc
            mock_audit_factory.return_value = MagicMock()

            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["filename"] == "abc_test.pdf"
        assert data["original_filename"] == "test.pdf"
        assert data["message"] == "Document uploaded successfully"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, documents_client):
        """Should upload with optional metadata fields."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/doc.docx", "abc_report.docx", 500))
        mock_storage.get_file_type = MagicMock(
            return_value="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        mock_doc = _make_mock_document(
            filename="abc_report.docx",
            original_filename="report.docx",
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=500,
        )
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service") as mock_ocr_factory,
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_ocr_svc = MagicMock()
            mock_ocr_svc.is_available.return_value = False
            mock_ocr_factory.return_value = mock_ocr_svc
            mock_audit_factory.return_value = MagicMock()

            response = await documents_client.post(
                "/documents",
                files={"file": ("report.docx", b"DOCX content", "application/octet-stream")},
                data={
                    "property_id": "prop-1",
                    "category": "contract",
                    "tags": '["legal", "2026"]',
                    "description": "Sales contract",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_upload_no_filename(self, documents_client):
        """Should reject upload when filename is empty (422 from FastAPI validation)."""
        mock_audit = MagicMock()
        with patch("api.routers.documents.get_audit_logger", return_value=mock_audit):
            # FastAPI rejects empty filename at the multipart level (422)
            # because file is required with File(...)
            response = await documents_client.post(
                "/documents",
                files={"file": ("", b"content", "application/pdf")},
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_upload_invalid_extension(self, documents_client):
        """Should return 400 for unsupported file type."""
        mock_audit = MagicMock()
        with patch("api.routers.documents.get_audit_logger", return_value=mock_audit):
            response = await documents_client.post(
                "/documents",
                files={"file": ("malware.exe", b"content", "application/octet-stream")},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, documents_client):
        """Should return 413 when file exceeds size limit."""
        # Patch the limit constant to make a small file trigger it
        mock_audit = MagicMock()
        mock_audit.log = MagicMock()

        large_content = b"x" * 200  # Will exceed our patched limit

        with (
            patch("api.routers.documents.get_audit_logger", return_value=mock_audit),
            patch("api.routers.documents._MAX_UPLOAD_FILE_BYTES", 100),
        ):
            response = await documents_client.post(
                "/documents",
                files={"file": ("big.pdf", large_content, "application/pdf")},
            )
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "too large" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_storage_failure(self, documents_client):
        """Should return 500 when storage fails."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(side_effect=RuntimeError("disk full"))

        mock_audit = MagicMock()

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_audit_logger", return_value=mock_audit),
        ):
            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"content", "application/pdf")},
            )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_upload_with_ocr_success(self, documents_client):
        """Should run OCR and update document on successful extraction."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=mock_doc)

        mock_ocr_svc = MagicMock()
        mock_ocr_svc.is_available.return_value = True
        mock_ocr_svc.extract_text = AsyncMock(return_value=("Extracted text content", None))

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service", return_value=mock_ocr_svc),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_repo.update.assert_called_once_with(
            mock_doc, ocr_status="completed", extracted_text="Extracted text content"
        )

    @pytest.mark.asyncio
    async def test_upload_with_ocr_failure(self, documents_client):
        """Should handle OCR failure gracefully and still return 201."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=mock_doc)

        mock_ocr_svc = MagicMock()
        mock_ocr_svc.is_available.return_value = True
        mock_ocr_svc.extract_text = AsyncMock(return_value=(None, "OCR engine error"))

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service", return_value=mock_ocr_svc),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_repo.update.assert_called_once_with(mock_doc, ocr_status="failed")

    @pytest.mark.asyncio
    async def test_upload_with_ocr_exception(self, documents_client):
        """Should handle OCR throwing an exception and still return 201."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=mock_doc)

        mock_ocr_svc = MagicMock()
        mock_ocr_svc.is_available.return_value = True
        mock_ocr_svc.extract_text = AsyncMock(side_effect=RuntimeError("crash"))

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service", return_value=mock_ocr_svc),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_repo.update.assert_called_once_with(mock_doc, ocr_status="failed")

    @pytest.mark.asyncio
    async def test_upload_with_ocr_no_text_no_error(self, documents_client):
        """Should mark OCR completed when OCR returns no text and no error."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=mock_doc)

        mock_ocr_svc = MagicMock()
        mock_ocr_svc.is_available.return_value = True
        mock_ocr_svc.extract_text = AsyncMock(return_value=(None, None))

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service", return_value=mock_ocr_svc),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_repo.update.assert_called_once_with(mock_doc, ocr_status="completed")

    @pytest.mark.asyncio
    async def test_upload_with_expiry_date(self, documents_client):
        """Should parse and pass expiry date."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/test.pdf", "abc_test.pdf", 100))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")

        mock_doc = _make_mock_document(file_size=100)
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service") as mock_ocr_factory,
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_ocr_svc = MagicMock()
            mock_ocr_svc.is_available.return_value = False
            mock_ocr_factory.return_value = mock_ocr_svc
            mock_audit_factory.return_value = MagicMock()

            response = await documents_client.post(
                "/documents",
                files={"file": ("test.pdf", b"content", "application/pdf")},
                data={"expiry_date": "2026-12-31T23:59:59Z"},
            )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_upload_jpeg_file(self, documents_client):
        """Should accept .jpeg files."""
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/photo.jpeg", "abc_photo.jpeg", 5000))
        mock_storage.get_file_type = MagicMock(return_value="image/jpeg")

        mock_doc = _make_mock_document(
            filename="abc_photo.jpeg",
            original_filename="photo.jpeg",
            file_type="image/jpeg",
            file_size=5000,
        )
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service") as mock_ocr_factory,
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_ocr_svc = MagicMock()
            mock_ocr_svc.is_available.return_value = False
            mock_ocr_factory.return_value = mock_ocr_svc
            mock_audit_factory.return_value = MagicMock()

            response = await documents_client.post(
                "/documents",
                files={"file": ("photo.jpeg", b"\xff\xd8\xff\xe0", "image/jpeg")},
            )

        assert response.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# GET /documents  —  list_documents
# ---------------------------------------------------------------------------


class TestListDocuments:
    """Tests for GET /documents."""

    @pytest.mark.asyncio
    async def test_list_empty(self, documents_client):
        """Should return empty list when no documents exist."""
        mock_repo = MagicMock()
        mock_repo.get_by_user = AsyncMock(return_value=[])
        mock_repo.count_by_user = AsyncMock(return_value=0)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_list_with_documents(self, documents_client):
        """Should return documents with correct pagination."""
        mock_doc1 = _make_mock_document(doc_id="doc-1", original_filename="a.pdf")
        mock_doc2 = _make_mock_document(doc_id="doc-2", original_filename="b.pdf")

        mock_repo = MagicMock()
        mock_repo.get_by_user = AsyncMock(return_value=[mock_doc1, mock_doc2])
        mock_repo.count_by_user = AsyncMock(return_value=2)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_list_with_filters(self, documents_client):
        """Should pass filter params to repository."""
        mock_repo = MagicMock()
        mock_repo.get_by_user = AsyncMock(return_value=[])
        mock_repo.count_by_user = AsyncMock(return_value=0)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get(
                "/documents?property_id=prop-1&category=contract&ocr_status=completed&search_query=lease"
            )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_repo.get_by_user.call_args
        assert call_kwargs.kwargs["property_id"] == "prop-1"
        assert call_kwargs.kwargs["category"] == "contract"
        assert call_kwargs.kwargs["ocr_status"] == "completed"
        assert call_kwargs.kwargs["search_query"] == "lease"

    @pytest.mark.asyncio
    async def test_list_pagination(self, documents_client):
        """Should apply pagination parameters."""
        mock_repo = MagicMock()
        mock_repo.get_by_user = AsyncMock(return_value=[])
        mock_repo.count_by_user = AsyncMock(return_value=50)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents?page=2&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_pages"] == 5
        call_kwargs = mock_repo.get_by_user.call_args.kwargs
        assert call_kwargs["offset"] == 10
        assert call_kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_invalid_sort_field(self, documents_client):
        """Should return 400 for an invalid sort field."""
        response = await documents_client.get("/documents?sort_by=invalid_field")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid sort field" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_valid_sort_fields(self, documents_client):
        """Should accept all valid sort fields."""
        valid_fields = ["created_at", "updated_at", "filename", "file_size", "category"]
        for field in valid_fields:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)

            with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
                response = await documents_client.get(f"/documents?sort_by={field}")
                assert response.status_code == status.HTTP_200_OK, f"Failed for sort_by={field}"

    @pytest.mark.asyncio
    async def test_list_with_sort_order(self, documents_client):
        """Should pass sort_order to repository."""
        mock_repo = MagicMock()
        mock_repo.get_by_user = AsyncMock(return_value=[])
        mock_repo.count_by_user = AsyncMock(return_value=0)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents?sort_order=asc")

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_repo.get_by_user.call_args.kwargs
        assert call_kwargs["sort_order"] == "asc"


# ---------------------------------------------------------------------------
# GET /documents/expiring  —  get_expiring_documents
# ---------------------------------------------------------------------------


class TestGetExpiringDocuments:
    """Tests for GET /documents/expiring."""

    @pytest.mark.asyncio
    async def test_expiring_empty(self, documents_client):
        """Should return empty list when no expiring documents."""
        mock_repo = MagicMock()
        mock_repo.get_expiring_soon = AsyncMock(return_value=[])

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents/expiring")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["days_ahead"] == 30

    @pytest.mark.asyncio
    async def test_expiring_with_documents(self, documents_client):
        """Should return documents expiring within the specified days."""
        future_date = datetime.now(UTC) + timedelta(days=10)
        mock_doc = _make_mock_document(
            doc_id="exp-1",
            original_filename="expiring_contract.pdf",
            expiry_date=future_date,
        )
        mock_repo = MagicMock()
        mock_repo.get_expiring_soon = AsyncMock(return_value=[mock_doc])

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents/expiring?days_ahead=60")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["days_ahead"] == 60
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_expiring_custom_days(self, documents_client):
        """Should pass custom days_ahead and limit to repository."""
        mock_repo = MagicMock()
        mock_repo.get_expiring_soon = AsyncMock(return_value=[])

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.get("/documents/expiring?days_ahead=7&limit=10")

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_repo.get_expiring_soon.call_args.kwargs
        assert call_kwargs["days_ahead"] == 7
        assert call_kwargs["limit"] == 10


# ---------------------------------------------------------------------------
# GET /documents/{document_id}  —  download_document
# ---------------------------------------------------------------------------


class TestDownloadDocument:
    """Tests for GET /documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_download_success(self, documents_client):
        """Should return file content as streaming response."""
        mock_doc = _make_mock_document(
            storage_path="/tmp/test.pdf",
            file_type="application/pdf",
            original_filename="test.pdf",
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)

        mock_storage = MagicMock()
        mock_storage.read_file = AsyncMock(return_value=b"PDF binary content")

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.get("/documents/doc-001")

        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"PDF binary content"
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_not_found(self, documents_client):
        """Should return 404 when document does not exist."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.get("/documents/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_storage_error(self, documents_client):
        """Should return 500 when storage read fails."""
        mock_doc = _make_mock_document(storage_path="/tmp/missing.pdf")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)

        mock_storage = MagicMock()
        mock_storage.read_file = AsyncMock(side_effect=RuntimeError("disk error"))

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.get("/documents/doc-001")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "failed to read" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PATCH /documents/{document_id}  —  update_document
# ---------------------------------------------------------------------------


class TestUpdateDocument:
    """Tests for PATCH /documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_update_success(self, documents_client):
        """Should update document metadata and return updated document."""
        mock_doc = _make_mock_document(category="other")
        updated_doc = _make_mock_document(category="contract")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=updated_doc)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.patch(
                "/documents/doc-001",
                json={"category": "contract"},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, documents_client):
        """Should return 404 when document does not exist."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.patch(
                "/documents/nonexistent",
                json={"category": "contract"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_empty_body(self, documents_client):
        """Should return current document when no fields are set in body."""
        mock_doc = _make_mock_document(category="contract")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.patch(
                "/documents/doc-001",
                json={},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "doc-001"
        mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, documents_client):
        """Should update multiple fields at once."""
        mock_doc = _make_mock_document()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
        mock_repo.update = AsyncMock(return_value=mock_doc)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            response = await documents_client.patch(
                "/documents/doc-001",
                json={
                    "category": "inspection",
                    "description": "Updated description",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        update_kwargs = mock_repo.update.call_args.kwargs
        assert update_kwargs["category"] == "inspection"
        assert update_kwargs["description"] == "Updated description"


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}  —  delete_document
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    """Tests for DELETE /documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_delete_success(self, documents_client):
        """Should delete document and return 204."""
        mock_doc = _make_mock_document(storage_path="/tmp/test.pdf")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
        mock_repo.delete = AsyncMock()

        mock_storage = MagicMock()
        mock_storage.delete_file = AsyncMock()

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.delete("/documents/doc-001")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_storage.delete_file.assert_called_once_with("/tmp/test.pdf")
        mock_repo.delete.assert_called_once_with(mock_doc)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, documents_client):
        """Should return 404 when document does not exist."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.delete("/documents/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_storage_error(self, documents_client):
        """Should return 500 when storage deletion fails."""
        mock_doc = _make_mock_document(storage_path="/tmp/test.pdf")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)

        mock_storage = MagicMock()
        mock_storage.delete_file = AsyncMock(side_effect=RuntimeError("disk error"))

        with (
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
        ):
            mock_audit_factory.return_value = MagicMock()
            response = await documents_client.delete("/documents/doc-001")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "failed to delete" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Integration-style: full workflow
# ---------------------------------------------------------------------------


class TestDocumentsWorkflow:
    """End-to-end workflow tests across multiple endpoints."""

    @pytest.mark.asyncio
    async def test_upload_list_update_delete_workflow(self, documents_client):
        """Full lifecycle: upload -> list -> update -> download -> delete."""
        # --- Upload ---
        mock_storage = MagicMock()
        mock_storage.save_file = AsyncMock(return_value=("/tmp/wf.pdf", "wf_test.pdf", 200))
        mock_storage.get_file_type = MagicMock(return_value="application/pdf")
        mock_storage.read_file = AsyncMock(return_value=b"workflow content")
        mock_storage.delete_file = AsyncMock()

        mock_doc = _make_mock_document(
            doc_id="wf-1",
            filename="wf_test.pdf",
            original_filename="workflow.pdf",
            file_size=200,
            category="contract",
        )
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_doc)
        mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
        mock_repo.get_by_user = AsyncMock(return_value=[mock_doc])
        mock_repo.count_by_user = AsyncMock(return_value=1)
        mock_repo.update = AsyncMock(return_value=mock_doc)
        mock_repo.delete = AsyncMock()

        with (
            patch("api.routers.documents.get_document_storage", return_value=mock_storage),
            patch("api.routers.documents.get_ocr_service") as mock_ocr_factory,
            patch("api.routers.documents.get_audit_logger") as mock_audit_factory,
            patch("api.routers.documents.DocumentRepository", return_value=mock_repo),
        ):
            mock_ocr_svc = MagicMock()
            mock_ocr_svc.is_available.return_value = False
            mock_ocr_factory.return_value = mock_ocr_svc
            mock_audit_factory.return_value = MagicMock()

            # Upload
            upload_resp = await documents_client.post(
                "/documents",
                files={"file": ("workflow.pdf", b"workflow content", "application/pdf")},
                data={"category": "contract"},
            )
            assert upload_resp.status_code == status.HTTP_201_CREATED

            # List
            list_resp = await documents_client.get("/documents")
            assert list_resp.status_code == status.HTTP_200_OK
            assert list_resp.json()["total"] == 1

            # Update
            update_resp = await documents_client.patch(
                "/documents/wf-1",
                json={"description": "Workflow test doc"},
            )
            assert update_resp.status_code == status.HTTP_200_OK

            # Download
            download_resp = await documents_client.get("/documents/wf-1")
            assert download_resp.status_code == status.HTTP_200_OK

            # Delete
            delete_resp = await documents_client.delete("/documents/wf-1")
            assert delete_resp.status_code == status.HTTP_204_NO_CONTENT
