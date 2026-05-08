"""
Unit tests for db.document_repos — 4 repository classes.

Covers DocumentRepository, DocumentTemplateRepository,
SignatureRequestRepository, and SignedDocumentRepository.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.document_repos import (
    DocumentRepository,
    DocumentTemplateRepository,
    SignatureRequestRepository,
    SignedDocumentRepository,
)
from db.models import (
    DocumentDB,
    DocumentTemplateDB,
    SignatureRequestDB,
    SignedDocumentDB,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """AsyncMock session matching the SQLAlchemy AsyncSession interface."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def doc_repo(mock_session):
    return DocumentRepository(mock_session)


@pytest.fixture
def template_repo(mock_session):
    return DocumentTemplateRepository(mock_session)


@pytest.fixture
def sig_repo(mock_session):
    return SignatureRequestRepository(mock_session)


@pytest.fixture
def signed_repo(mock_session):
    return SignedDocumentRepository(mock_session)


def _make_mock_result(scalar_val=None, scalars_list=None, rowcount=0):
    """Build a mock SQLAlchemy result object."""
    mock_result = MagicMock()
    if scalar_val is not None:
        mock_result.scalar.return_value = scalar_val
        mock_result.scalar_one_or_none.return_value = scalar_val
        mock_result.scalar_one.return_value = scalar_val
    else:
        mock_result.scalar.return_value = None
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar_one.return_value = None
    if scalars_list is not None:
        mock_result.scalars.return_value.all.return_value = scalars_list
    else:
        mock_result.scalars.return_value.all.return_value = []
    mock_result.rowcount = rowcount
    return mock_result


def _make_document(**overrides):
    """Create a mock DocumentDB-like object."""
    doc = MagicMock(spec=DocumentDB)
    doc.id = overrides.get("id", "doc-001")
    doc.user_id = overrides.get("user_id", "user-001")
    doc.filename = overrides.get("filename", "stored.pdf")
    doc.original_filename = overrides.get("original_filename", "contract.pdf")
    doc.storage_path = overrides.get("storage_path", "/uploads/contract.pdf")
    doc.file_type = overrides.get("file_type", "application/pdf")
    doc.file_size = overrides.get("file_size", 1024)
    doc.property_id = overrides.get("property_id")
    doc.category = overrides.get("category")
    doc.tags = overrides.get("tags")
    doc.description = overrides.get("description")
    doc.ocr_status = overrides.get("ocr_status", "pending")
    doc.extracted_text = overrides.get("extracted_text")
    doc.expiry_date = overrides.get("expiry_date")
    doc.expiry_notified = overrides.get("expiry_notified", False)
    doc.created_at = overrides.get("created_at", datetime.now(UTC))
    return doc


def _make_template(**overrides):
    """Create a mock DocumentTemplateDB-like object."""
    tpl = MagicMock(spec=DocumentTemplateDB)
    tpl.id = overrides.get("id", "tpl-001")
    tpl.user_id = overrides.get("user_id", "user-001")
    tpl.name = overrides.get("name", "Rental Agreement")
    tpl.template_type = overrides.get("template_type", "rental_agreement")
    tpl.content = overrides.get("content", "<html>{{tenant}}</html>")
    tpl.description = overrides.get("description")
    tpl.variables = overrides.get("variables")
    tpl.is_default = overrides.get("is_default", False)
    tpl.created_at = overrides.get("created_at", datetime.now(UTC))
    return tpl


def _make_sig_request(**overrides):
    """Create a mock SignatureRequestDB-like object."""
    req = MagicMock(spec=SignatureRequestDB)
    req.id = overrides.get("id", "sig-001")
    req.user_id = overrides.get("user_id", "user-001")
    req.title = overrides.get("title", "Sign Contract")
    req.provider = overrides.get("provider", "hellosign")
    req.provider_envelope_id = overrides.get("provider_envelope_id")
    req.document_id = overrides.get("document_id")
    req.template_id = overrides.get("template_id")
    req.subject = overrides.get("subject")
    req.message = overrides.get("message")
    req.property_id = overrides.get("property_id")
    req.document_content_hash = overrides.get("document_content_hash")
    req.signers = overrides.get("signers", [])
    req.variables = overrides.get("variables")
    req.status = overrides.get("status", "draft")
    req.error_message = overrides.get("error_message")
    req.sent_at = overrides.get("sent_at")
    req.viewed_at = overrides.get("viewed_at")
    req.completed_at = overrides.get("completed_at")
    req.cancelled_at = overrides.get("cancelled_at")
    req.expires_at = overrides.get("expires_at")
    req.reminder_sent_at = overrides.get("reminder_sent_at")
    req.reminder_count = overrides.get("reminder_count", 0)
    req.created_at = overrides.get("created_at", datetime.now(UTC))
    return req


def _make_signed_doc(**overrides):
    """Create a mock SignedDocumentDB-like object."""
    sd = MagicMock(spec=SignedDocumentDB)
    sd.id = overrides.get("id", "sd-001")
    sd.signature_request_id = overrides.get("signature_request_id", "sig-001")
    sd.document_id = overrides.get("document_id")
    sd.storage_path = overrides.get("storage_path", "/signed/doc.pdf")
    sd.file_size = overrides.get("file_size", 2048)
    sd.provider_document_id = overrides.get("provider_document_id")
    sd.certificate_url = overrides.get("certificate_url")
    sd.signature_hash = overrides.get("signature_hash")
    sd.created_at = overrides.get("created_at", datetime.now(UTC))
    return sd


# ===========================================================================
# DocumentRepository tests
# ===========================================================================


class TestDocumentRepositoryCreate:
    """Tests for DocumentRepository.create."""

    @pytest.mark.asyncio
    async def test_create_minimal(self, doc_repo, mock_session):
        doc = await doc_repo.create(
            user_id="user-1",
            filename="f.pdf",
            original_filename="original.pdf",
            storage_path="/up/f.pdf",
            file_type="application/pdf",
            file_size=100,
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(doc, DocumentDB)
        assert doc.user_id == "user-1"
        assert doc.filename == "f.pdf"
        assert doc.original_filename == "original.pdf"
        assert doc.ocr_status == "pending"
        assert doc.tags is None

    @pytest.mark.asyncio
    async def test_create_with_all_optional_fields(self, doc_repo, mock_session):
        expiry = datetime(2026, 12, 31, tzinfo=UTC)
        doc = await doc_repo.create(
            user_id="user-1",
            filename="f.pdf",
            original_filename="original.pdf",
            storage_path="/up/f.pdf",
            file_type="application/pdf",
            file_size=100,
            property_id="prop-1",
            category="contract",
            tags=["tag1", "tag2"],
            description="A contract",
            expiry_date=expiry,
        )
        mock_session.add.assert_called_once()
        assert doc.property_id == "prop-1"
        assert doc.category == "contract"
        assert doc.tags == json.dumps(["tag1", "tag2"])
        assert doc.description == "A contract"
        assert doc.expiry_date == expiry

    @pytest.mark.asyncio
    async def test_create_tags_none(self, doc_repo, mock_session):
        doc = await doc_repo.create(
            user_id="user-1",
            filename="f.pdf",
            original_filename="original.pdf",
            storage_path="/up/f.pdf",
            file_type="application/pdf",
            file_size=50,
            tags=None,
        )
        assert doc.tags is None

    @pytest.mark.asyncio
    async def test_create_generates_uuid(self, doc_repo, mock_session):
        doc = await doc_repo.create(
            user_id="u",
            filename="a",
            original_filename="b",
            storage_path="/c",
            file_type="text/plain",
            file_size=0,
        )
        assert len(doc.id) == 36  # UUID4 length


class TestDocumentRepositoryGetById:
    """Tests for DocumentRepository.get_by_id and get_by_id_unscoped."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, doc_repo, mock_session):
        mock_doc = _make_document()
        mock_session.execute.return_value = _make_mock_result(scalar_val=mock_doc)
        result = await doc_repo.get_by_id("doc-1", "user-1")
        assert result is mock_doc
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await doc_repo.get_by_id("missing", "user-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_unscoped_found(self, doc_repo, mock_session):
        mock_doc = _make_document()
        mock_session.execute.return_value = _make_mock_result(scalar_val=mock_doc)
        result = await doc_repo.get_by_id_unscoped("doc-1")
        assert result is mock_doc

    @pytest.mark.asyncio
    async def test_get_by_id_unscoped_not_found(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await doc_repo.get_by_id_unscoped("missing")
        assert result is None


class TestDocumentRepositoryGetByUser:
    """Tests for DocumentRepository.get_by_user with various filters."""

    @pytest.mark.asyncio
    async def test_get_by_user_no_filters(self, doc_repo, mock_session):
        docs = [_make_document(), _make_document(id="doc-2")]
        mock_session.execute.return_value = _make_mock_result(scalars_list=docs)
        result = await doc_repo.get_by_user("user-1")
        assert result == docs
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_property_filter(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", property_id="prop-1")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_category_filter(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", category="contract")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_ocr_status_filter(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", ocr_status="completed")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_search_query(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", search_query="contract")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_sort_asc(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", sort_by="file_size", sort_order="asc")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_offset_and_limit(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", offset=10, limit=5)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_invalid_sort_by_falls_back(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_user("user-1", sort_by="nonexistent_column")
        mock_session.execute.assert_awaited_once()


class TestDocumentRepositoryCount:
    """Tests for DocumentRepository.count_by_user and count_by_user_simple."""

    @pytest.mark.asyncio
    async def test_count_by_user_returns_count(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=42)
        result = await doc_repo.count_by_user("user-1")
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_by_user_returns_zero_on_none(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await doc_repo.count_by_user("user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_by_user_with_filters(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=5)
        result = await doc_repo.count_by_user(
            "user-1",
            property_id="p-1",
            category="contract",
            ocr_status="completed",
            search_query="lease",
        )
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_user_simple(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=10)
        result = await doc_repo.count_by_user_simple("user-1")
        assert result == 10

    @pytest.mark.asyncio
    async def test_count_by_user_simple_zero(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await doc_repo.count_by_user_simple("user-1")
        assert result == 0


class TestDocumentRepositoryGetByProperty:
    """Tests for DocumentRepository.get_by_property."""

    @pytest.mark.asyncio
    async def test_get_by_property_found(self, doc_repo, mock_session):
        docs = [_make_document(property_id="prop-1")]
        mock_session.execute.return_value = _make_mock_result(scalars_list=docs)
        result = await doc_repo.get_by_property("user-1", "prop-1")
        assert result == docs

    @pytest.mark.asyncio
    async def test_get_by_property_empty(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        result = await doc_repo.get_by_property("user-1", "prop-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_property_with_limit(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_by_property("user-1", "prop-1", limit=10)
        mock_session.execute.assert_awaited_once()


class TestDocumentRepositoryGetExpiringSoon:
    """Tests for DocumentRepository.get_expiring_soon."""

    @pytest.mark.asyncio
    async def test_get_expiring_soon_found(self, doc_repo, mock_session):
        expiry = datetime.now(UTC) + timedelta(days=5)
        docs = [_make_document(expiry_date=expiry)]
        mock_session.execute.return_value = _make_mock_result(scalars_list=docs)
        result = await doc_repo.get_expiring_soon("user-1", days_ahead=30)
        assert result == docs

    @pytest.mark.asyncio
    async def test_get_expiring_soon_empty(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        result = await doc_repo.get_expiring_soon("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_expiring_soon_custom_days(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_expiring_soon("user-1", days_ahead=7, limit=10)
        mock_session.execute.assert_awaited_once()


class TestDocumentRepositoryUpdate:
    """Tests for DocumentRepository.update."""

    @pytest.mark.asyncio
    async def test_update_no_fields(self, doc_repo, mock_session):
        doc = _make_document()
        result = await doc_repo.update(doc)
        mock_session.flush.assert_awaited_once()
        assert result is doc

    @pytest.mark.asyncio
    async def test_update_property_id(self, doc_repo, mock_session):
        doc = _make_document()
        result = await doc_repo.update(doc, property_id="new-prop")
        assert doc.property_id == "new-prop"
        assert result is doc

    @pytest.mark.asyncio
    async def test_update_category(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(doc, category="inspection")
        assert doc.category == "inspection"

    @pytest.mark.asyncio
    async def test_update_tags_serializes_json(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(doc, tags=["a", "b"])
        assert doc.tags == json.dumps(["a", "b"])

    @pytest.mark.asyncio
    async def test_update_description(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(doc, description="Updated desc")
        assert doc.description == "Updated desc"

    @pytest.mark.asyncio
    async def test_update_expiry_date(self, doc_repo, mock_session):
        doc = _make_document()
        new_expiry = datetime(2027, 1, 1, tzinfo=UTC)
        await doc_repo.update(doc, expiry_date=new_expiry)
        assert doc.expiry_date == new_expiry

    @pytest.mark.asyncio
    async def test_update_ocr_status(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(doc, ocr_status="completed")
        assert doc.ocr_status == "completed"

    @pytest.mark.asyncio
    async def test_update_extracted_text(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(doc, extracted_text="OCR text here")
        assert doc.extracted_text == "OCR text here"

    @pytest.mark.asyncio
    async def test_update_multiple_fields_at_once(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.update(
            doc,
            category="financial",
            description="Financial doc",
            ocr_status="processing",
        )
        assert doc.category == "financial"
        assert doc.description == "Financial doc"
        assert doc.ocr_status == "processing"


class TestDocumentRepositoryMarkExpiryNotified:
    """Tests for DocumentRepository.mark_expiry_notified."""

    @pytest.mark.asyncio
    async def test_mark_expiry_notified(self, doc_repo, mock_session):
        doc = _make_document(expiry_notified=False)
        await doc_repo.mark_expiry_notified(doc)
        assert doc.expiry_notified is True
        mock_session.flush.assert_awaited_once()


class TestDocumentRepositoryDelete:
    """Tests for DocumentRepository.delete and delete_by_user."""

    @pytest.mark.asyncio
    async def test_delete_single(self, doc_repo, mock_session):
        doc = _make_document()
        await doc_repo.delete(doc)
        mock_session.delete.assert_awaited_once_with(doc)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_user_with_documents(self, doc_repo, mock_session):
        docs = [_make_document(id=f"doc-{i}") for i in range(3)]
        mock_session.execute.return_value = _make_mock_result(scalars_list=docs)
        count = await doc_repo.delete_by_user("user-1")
        assert count == 3
        assert mock_session.delete.await_count == 3
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_user_no_documents(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        count = await doc_repo.delete_by_user("user-1")
        assert count == 0
        mock_session.delete.assert_not_awaited()


class TestDocumentRepositoryOcr:
    """Tests for DocumentRepository.get_pending_ocr and bulk_update_ocr_status."""

    @pytest.mark.asyncio
    async def test_get_pending_ocr(self, doc_repo, mock_session):
        docs = [_make_document(ocr_status="pending")]
        mock_session.execute.return_value = _make_mock_result(scalars_list=docs)
        result = await doc_repo.get_pending_ocr()
        assert result == docs

    @pytest.mark.asyncio
    async def test_get_pending_ocr_with_limit(self, doc_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await doc_repo.get_pending_ocr(limit=50)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_update_ocr_status(self, doc_repo, mock_session):
        mock_result = _make_mock_result(rowcount=5)
        mock_session.execute.return_value = mock_result
        count = await doc_repo.bulk_update_ocr_status(["d1", "d2", "d3", "d4", "d5"], "completed")
        assert count == 5
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_update_ocr_status_zero_affected(self, doc_repo, mock_session):
        mock_result = _make_mock_result(rowcount=0)
        mock_session.execute.return_value = mock_result
        count = await doc_repo.bulk_update_ocr_status([], "failed")
        assert count == 0


# ===========================================================================
# DocumentTemplateRepository tests
# ===========================================================================


class TestDocumentTemplateRepositoryCreate:
    """Tests for DocumentTemplateRepository.create."""

    @pytest.mark.asyncio
    async def test_create_minimal(self, template_repo, mock_session):
        tpl = await template_repo.create(
            user_id="user-1",
            name="Template A",
            template_type="rental_agreement",
            content="<html>{{x}}</html>",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(tpl, DocumentTemplateDB)
        assert tpl.user_id == "user-1"
        assert tpl.name == "Template A"
        assert tpl.is_default is False
        assert tpl.variables is None
        assert tpl.description is None

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, template_repo, mock_session):
        tpl = await template_repo.create(
            user_id="user-1",
            name="Full Template",
            template_type="purchase_offer",
            content="<html>{{y}}</html>",
            description="A full template",
            variables={"tenant": {"type": "string"}},
            is_default=True,
        )
        assert tpl.description == "A full template"
        assert tpl.variables == {"tenant": {"type": "string"}}
        assert tpl.is_default is True

    @pytest.mark.asyncio
    async def test_create_generates_uuid(self, template_repo, mock_session):
        tpl = await template_repo.create(
            user_id="u",
            name="N",
            template_type="custom",
            content="C",
        )
        assert len(tpl.id) == 36


class TestDocumentTemplateRepositoryGetById:
    """Tests for DocumentTemplateRepository.get_by_id."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, template_repo, mock_session):
        tpl = _make_template()
        mock_session.execute.return_value = _make_mock_result(scalar_val=tpl)
        result = await template_repo.get_by_id("tpl-1")
        assert result is tpl

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await template_repo.get_by_id("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_scoping(self, template_repo, mock_session):
        tpl = _make_template()
        mock_session.execute.return_value = _make_mock_result(scalar_val=tpl)
        result = await template_repo.get_by_id("tpl-1", user_id="user-1")
        assert result is tpl

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_scoping_not_found(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await template_repo.get_by_id("tpl-1", user_id="other-user")
        assert result is None


class TestDocumentTemplateRepositoryGetByUser:
    """Tests for DocumentTemplateRepository.get_by_user."""

    @pytest.mark.asyncio
    async def test_get_by_user_no_filters(self, template_repo, mock_session):
        tpls = [_make_template(), _make_template(id="tpl-2")]
        mock_session.execute.return_value = _make_mock_result(scalars_list=tpls)
        result = await template_repo.get_by_user("user-1")
        assert result == tpls

    @pytest.mark.asyncio
    async def test_get_by_user_with_type_filter(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await template_repo.get_by_user("user-1", template_type="rental_agreement")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_pagination(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await template_repo.get_by_user("user-1", page=2, page_size=10)
        mock_session.execute.assert_awaited_once()


class TestDocumentTemplateRepositoryCount:
    """Tests for DocumentTemplateRepository.count_by_user."""

    @pytest.mark.asyncio
    async def test_count_by_user(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=3)
        result = await template_repo.count_by_user("user-1")
        assert result == 3

    @pytest.mark.asyncio
    async def test_count_by_user_with_type(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=1)
        result = await template_repo.count_by_user("user-1", template_type="rental_agreement")
        assert result == 1

    @pytest.mark.asyncio
    async def test_count_by_user_zero(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await template_repo.count_by_user("user-1")
        assert result == 0


class TestDocumentTemplateRepositoryGetDefault:
    """Tests for DocumentTemplateRepository.get_default_template."""

    @pytest.mark.asyncio
    async def test_get_default_template_found(self, template_repo, mock_session):
        tpl = _make_template(is_default=True)
        mock_session.execute.return_value = _make_mock_result(scalar_val=tpl)
        result = await template_repo.get_default_template("rental_agreement", user_id="user-1")
        assert result is tpl

    @pytest.mark.asyncio
    async def test_get_default_template_not_found(self, template_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await template_repo.get_default_template("rental_agreement")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_default_template_without_user(self, template_repo, mock_session):
        tpl = _make_template(is_default=True)
        mock_session.execute.return_value = _make_mock_result(scalar_val=tpl)
        result = await template_repo.get_default_template("purchase_offer")
        assert result is tpl


class TestDocumentTemplateRepositoryUpdate:
    """Tests for DocumentTemplateRepository.update."""

    @pytest.mark.asyncio
    async def test_update_no_fields(self, template_repo, mock_session):
        tpl = _make_template()
        result = await template_repo.update(tpl)
        mock_session.flush.assert_awaited_once()
        assert result is tpl

    @pytest.mark.asyncio
    async def test_update_name(self, template_repo, mock_session):
        tpl = _make_template()
        await template_repo.update(tpl, name="New Name")
        assert tpl.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_description(self, template_repo, mock_session):
        tpl = _make_template()
        await template_repo.update(tpl, description="New description")
        assert tpl.description == "New description"

    @pytest.mark.asyncio
    async def test_update_content(self, template_repo, mock_session):
        tpl = _make_template()
        await template_repo.update(tpl, content="<html>new</html>")
        assert tpl.content == "<html>new</html>"

    @pytest.mark.asyncio
    async def test_update_variables(self, template_repo, mock_session):
        tpl = _make_template()
        new_vars = {"landlord": {"type": "string"}}
        await template_repo.update(tpl, variables=new_vars)
        assert tpl.variables == new_vars

    @pytest.mark.asyncio
    async def test_update_is_default(self, template_repo, mock_session):
        tpl = _make_template(is_default=False)
        await template_repo.update(tpl, is_default=True)
        assert tpl.is_default is True

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, template_repo, mock_session):
        tpl = _make_template()
        await template_repo.update(tpl, name="X", content="Y", is_default=True)
        assert tpl.name == "X"
        assert tpl.content == "Y"
        assert tpl.is_default is True


class TestDocumentTemplateRepositoryDelete:
    """Tests for DocumentTemplateRepository.delete."""

    @pytest.mark.asyncio
    async def test_delete(self, template_repo, mock_session):
        tpl = _make_template()
        await template_repo.delete(tpl)
        mock_session.delete.assert_awaited_once_with(tpl)
        mock_session.flush.assert_awaited_once()


# ===========================================================================
# SignatureRequestRepository tests
# ===========================================================================


class TestSignatureRequestRepositoryCreate:
    """Tests for SignatureRequestRepository.create."""

    @pytest.mark.asyncio
    async def test_create_minimal(self, sig_repo, mock_session):
        signers = [{"email": "a@b.com", "name": "Alice"}]
        req = await sig_repo.create(
            user_id="user-1",
            title="Sign Lease",
            provider="hellosign",
            signers=signers,
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(req, SignatureRequestDB)
        assert req.user_id == "user-1"
        assert req.title == "Sign Lease"
        assert req.provider == "hellosign"
        assert req.signers == signers
        assert req.status == "draft"

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, sig_repo, mock_session):
        signers = [{"email": "a@b.com", "name": "Alice"}]
        now = datetime.now(UTC)
        expiry = now + timedelta(days=7)
        req = await sig_repo.create(
            user_id="user-1",
            title="Full Request",
            provider="docusign",
            signers=signers,
            document_id="doc-1",
            template_id="tpl-1",
            subject="Please sign",
            message="This is important",
            property_id="prop-1",
            variables={"key": "val"},
            document_content_hash="abc123",
            provider_envelope_id="env-1",
            status="sent",
            expires_at=expiry,
        )
        assert req.document_id == "doc-1"
        assert req.template_id == "tpl-1"
        assert req.subject == "Please sign"
        assert req.message == "This is important"
        assert req.property_id == "prop-1"
        assert req.variables == {"key": "val"}
        assert req.document_content_hash == "abc123"
        assert req.provider_envelope_id == "env-1"
        assert req.status == "sent"
        assert req.expires_at == expiry

    @pytest.mark.asyncio
    async def test_create_generates_uuid(self, sig_repo, mock_session):
        req = await sig_repo.create(
            user_id="u",
            title="T",
            provider="p",
            signers=[],
        )
        assert len(req.id) == 36


class TestSignatureRequestRepositoryGetById:
    """Tests for SignatureRequestRepository.get_by_id."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, sig_repo, mock_session):
        req = _make_sig_request()
        mock_session.execute.return_value = _make_mock_result(scalar_val=req)
        result = await sig_repo.get_by_id("sig-1")
        assert result is req

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await sig_repo.get_by_id("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_scoping(self, sig_repo, mock_session):
        req = _make_sig_request()
        mock_session.execute.return_value = _make_mock_result(scalar_val=req)
        result = await sig_repo.get_by_id("sig-1", user_id="user-1")
        assert result is req

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_scoping_mismatch(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await sig_repo.get_by_id("sig-1", user_id="other-user")
        assert result is None


class TestSignatureRequestRepositoryGetByProviderEnvelope:
    """Tests for SignatureRequestRepository.get_by_provider_envelope_id."""

    @pytest.mark.asyncio
    async def test_get_by_provider_envelope_id_found(self, sig_repo, mock_session):
        req = _make_sig_request(provider="hellosign", provider_envelope_id="env-1")
        mock_session.execute.return_value = _make_mock_result(scalar_val=req)
        result = await sig_repo.get_by_provider_envelope_id("hellosign", "env-1")
        assert result is req

    @pytest.mark.asyncio
    async def test_get_by_provider_envelope_id_not_found(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await sig_repo.get_by_provider_envelope_id("docusign", "nonexistent")
        assert result is None


class TestSignatureRequestRepositoryGetByUser:
    """Tests for SignatureRequestRepository.get_by_user."""

    @pytest.mark.asyncio
    async def test_get_by_user_no_filters(self, sig_repo, mock_session):
        reqs = [_make_sig_request()]
        mock_session.execute.return_value = _make_mock_result(scalars_list=reqs)
        result = await sig_repo.get_by_user("user-1")
        assert result == reqs

    @pytest.mark.asyncio
    async def test_get_by_user_with_status(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await sig_repo.get_by_user("user-1", status="sent")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_with_property(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await sig_repo.get_by_user("user-1", property_id="prop-1")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_user_pagination(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await sig_repo.get_by_user("user-1", page=3, page_size=5)
        mock_session.execute.assert_awaited_once()


class TestSignatureRequestRepositoryCount:
    """Tests for SignatureRequestRepository.count_by_user."""

    @pytest.mark.asyncio
    async def test_count_by_user(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=7)
        result = await sig_repo.count_by_user("user-1")
        assert result == 7

    @pytest.mark.asyncio
    async def test_count_by_user_with_status(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=2)
        result = await sig_repo.count_by_user("user-1", status="completed")
        assert result == 2

    @pytest.mark.asyncio
    async def test_count_by_user_zero(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await sig_repo.count_by_user("user-1")
        assert result == 0


class TestSignatureRequestRepositoryUpdateStatus:
    """Tests for SignatureRequestRepository.update_status."""

    @pytest.mark.asyncio
    async def test_update_status_only(self, sig_repo, mock_session):
        req = _make_sig_request(status="draft")
        result = await sig_repo.update_status(req, "sent")
        assert req.status == "sent"
        assert result is req
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_with_error_message(self, sig_repo, mock_session):
        req = _make_sig_request()
        await sig_repo.update_status(req, "failed", error_message="API error")
        assert req.status == "failed"
        assert req.error_message == "API error"

    @pytest.mark.asyncio
    async def test_update_status_with_sent_at(self, sig_repo, mock_session):
        req = _make_sig_request()
        now = datetime.now(UTC)
        await sig_repo.update_status(req, "sent", sent_at=now)
        assert req.sent_at == now

    @pytest.mark.asyncio
    async def test_update_status_with_viewed_at(self, sig_repo, mock_session):
        req = _make_sig_request()
        now = datetime.now(UTC)
        await sig_repo.update_status(req, "viewed", viewed_at=now)
        assert req.viewed_at == now

    @pytest.mark.asyncio
    async def test_update_status_with_completed_at(self, sig_repo, mock_session):
        req = _make_sig_request()
        now = datetime.now(UTC)
        await sig_repo.update_status(req, "completed", completed_at=now)
        assert req.completed_at == now

    @pytest.mark.asyncio
    async def test_update_status_with_cancelled_at(self, sig_repo, mock_session):
        req = _make_sig_request()
        now = datetime.now(UTC)
        await sig_repo.update_status(req, "cancelled", cancelled_at=now)
        assert req.cancelled_at == now

    @pytest.mark.asyncio
    async def test_update_status_all_timestamps(self, sig_repo, mock_session):
        req = _make_sig_request()
        now = datetime.now(UTC)
        await sig_repo.update_status(
            req,
            "completed",
            error_message=None,
            sent_at=now,
            viewed_at=now,
            completed_at=now,
            cancelled_at=None,
        )
        assert req.sent_at == now
        assert req.viewed_at == now
        assert req.completed_at == now


class TestSignatureRequestRepositoryUpdateSigners:
    """Tests for SignatureRequestRepository.update_signers."""

    @pytest.mark.asyncio
    async def test_update_signers(self, sig_repo, mock_session):
        req = _make_sig_request(signers=[])
        new_signers = [{"email": "x@y.com", "name": "Bob", "status": "signed"}]
        result = await sig_repo.update_signers(req, new_signers)
        assert req.signers == new_signers
        assert result is req
        mock_session.flush.assert_awaited_once()


class TestSignatureRequestRepositoryUpdateEnvelopeId:
    """Tests for SignatureRequestRepository.update_provider_envelope_id."""

    @pytest.mark.asyncio
    async def test_update_provider_envelope_id(self, sig_repo, mock_session):
        req = _make_sig_request(provider_envelope_id=None)
        result = await sig_repo.update_provider_envelope_id(req, "env-xyz")
        assert req.provider_envelope_id == "env-xyz"
        assert result is req
        mock_session.flush.assert_awaited_once()


class TestSignatureRequestRepositoryMarkReminder:
    """Tests for SignatureRequestRepository.mark_reminder_sent."""

    @pytest.mark.asyncio
    async def test_mark_reminder_sent(self, sig_repo, mock_session):
        req = _make_sig_request(reminder_count=0)
        result = await sig_repo.mark_reminder_sent(req)
        assert req.reminder_count == 1
        assert req.reminder_sent_at is not None
        assert result is req
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_reminder_sent_increments_count(self, sig_repo, mock_session):
        req = _make_sig_request(reminder_count=2)
        await sig_repo.mark_reminder_sent(req)
        assert req.reminder_count == 3


class TestSignatureRequestRepositoryGetExpiring:
    """Tests for SignatureRequestRepository.get_expiring_requests."""

    @pytest.mark.asyncio
    async def test_get_expiring_requests_found(self, sig_repo, mock_session):
        reqs = [_make_sig_request(status="sent")]
        mock_session.execute.return_value = _make_mock_result(scalars_list=reqs)
        result = await sig_repo.get_expiring_requests(within_hours=24)
        assert result == reqs

    @pytest.mark.asyncio
    async def test_get_expiring_requests_empty(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        result = await sig_repo.get_expiring_requests()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_expiring_requests_custom_hours(self, sig_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalars_list=[])
        await sig_repo.get_expiring_requests(within_hours=48)
        mock_session.execute.assert_awaited_once()


class TestSignatureRequestRepositoryCancel:
    """Tests for SignatureRequestRepository.cancel."""

    @pytest.mark.asyncio
    async def test_cancel(self, sig_repo, mock_session):
        req = _make_sig_request(status="sent")
        result = await sig_repo.cancel(req)
        assert req.status == "cancelled"
        assert req.cancelled_at is not None
        assert result is req
        mock_session.flush.assert_awaited_once()


class TestSignatureRequestRepositoryDelete:
    """Tests for SignatureRequestRepository.delete."""

    @pytest.mark.asyncio
    async def test_delete(self, sig_repo, mock_session):
        req = _make_sig_request()
        await sig_repo.delete(req)
        mock_session.delete.assert_awaited_once_with(req)
        mock_session.flush.assert_awaited_once()


# ===========================================================================
# SignedDocumentRepository tests
# ===========================================================================


class TestSignedDocumentRepositoryCreate:
    """Tests for SignedDocumentRepository.create."""

    @pytest.mark.asyncio
    async def test_create_minimal(self, signed_repo, mock_session):
        sd = await signed_repo.create(
            signature_request_id="sig-1",
            storage_path="/signed/doc.pdf",
            file_size=2048,
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(sd, SignedDocumentDB)
        assert sd.signature_request_id == "sig-1"
        assert sd.storage_path == "/signed/doc.pdf"
        assert sd.file_size == 2048
        assert sd.document_id is None
        assert sd.provider_document_id is None
        assert sd.certificate_url is None
        assert sd.signature_hash is None

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, signed_repo, mock_session):
        sd = await signed_repo.create(
            signature_request_id="sig-1",
            storage_path="/signed/doc.pdf",
            file_size=2048,
            document_id="doc-1",
            provider_document_id="prov-doc-1",
            certificate_url="https://cert.example.com/123",
            signature_hash="sha256hash",
        )
        assert sd.document_id == "doc-1"
        assert sd.provider_document_id == "prov-doc-1"
        assert sd.certificate_url == "https://cert.example.com/123"
        assert sd.signature_hash == "sha256hash"

    @pytest.mark.asyncio
    async def test_create_generates_uuid(self, signed_repo, mock_session):
        sd = await signed_repo.create(
            signature_request_id="sig-1",
            storage_path="/p",
            file_size=0,
        )
        assert len(sd.id) == 36


class TestSignedDocumentRepositoryGetById:
    """Tests for SignedDocumentRepository.get_by_id."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, signed_repo, mock_session):
        sd = _make_signed_doc()
        mock_session.execute.return_value = _make_mock_result(scalar_val=sd)
        result = await signed_repo.get_by_id("sd-1")
        assert result is sd

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, signed_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await signed_repo.get_by_id("missing")
        assert result is None


class TestSignedDocumentRepositoryGetBySignatureRequest:
    """Tests for SignedDocumentRepository.get_by_signature_request."""

    @pytest.mark.asyncio
    async def test_get_by_signature_request_found(self, signed_repo, mock_session):
        sd = _make_signed_doc(signature_request_id="sig-1")
        mock_session.execute.return_value = _make_mock_result(scalar_val=sd)
        result = await signed_repo.get_by_signature_request("sig-1")
        assert result is sd

    @pytest.mark.asyncio
    async def test_get_by_signature_request_not_found(self, signed_repo, mock_session):
        mock_session.execute.return_value = _make_mock_result(scalar_val=None)
        result = await signed_repo.get_by_signature_request("missing")
        assert result is None


class TestSignedDocumentRepositoryDelete:
    """Tests for SignedDocumentRepository.delete."""

    @pytest.mark.asyncio
    async def test_delete(self, signed_repo, mock_session):
        sd = _make_signed_doc()
        await signed_repo.delete(sd)
        mock_session.delete.assert_awaited_once_with(sd)
        mock_session.flush.assert_awaited_once()
