"""Tests for the document storage service.

Uses tmp_path fixture for filesystem operations — no real uploads directory.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.document_storage import (
    ALLOWED_EXTENSIONS,
    DocumentStorageError,
    DocumentStorageService,
)


@pytest.fixture
def storage(tmp_path):
    """Create a DocumentStorageService with a temporary directory."""
    return DocumentStorageService(storage_path=str(tmp_path / "docs"))


class TestValidateFile:
    """Tests for file validation."""

    def test_valid_pdf(self, storage):
        mock_file = MagicMock()
        mock_file.filename = "report.pdf"
        mock_file.content_type = "application/pdf"
        valid, error = storage.validate_file(mock_file)
        assert valid is True
        assert error is None

    def test_valid_image(self, storage):
        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"
        mock_file.content_type = "image/jpeg"
        valid, error = storage.validate_file(mock_file)
        assert valid is True

    def test_invalid_extension(self, storage):
        mock_file = MagicMock()
        mock_file.filename = "malware.exe"
        mock_file.content_type = "application/octet-stream"
        valid, error = storage.validate_file(mock_file)
        assert valid is False
        assert "Invalid file type" in error

    def test_no_filename(self, storage):
        mock_file = MagicMock()
        mock_file.filename = None
        valid, error = storage.validate_file(mock_file)
        assert valid is False
        assert "No filename" in error

    def test_allowed_extensions(self):
        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".doc" in ALLOWED_EXTENSIONS
        assert ".docx" in ALLOWED_EXTENSIONS
        assert ".jpg" in ALLOWED_EXTENSIONS
        assert ".jpeg" in ALLOWED_EXTENSIONS
        assert ".png" in ALLOWED_EXTENSIONS
        assert ".exe" not in ALLOWED_EXTENSIONS


class TestGenerateFilename:
    """Tests for unique filename generation."""

    def test_generates_unique_names(self, storage):
        name1 = storage._generate_filename("report.pdf")
        name2 = storage._generate_filename("report.pdf")
        assert name1 != name2
        assert name1.endswith(".pdf")
        assert name2.endswith(".pdf")

    def test_sanitizes_special_chars(self, storage):
        name = storage._generate_filename("my file (1) @home.pdf")
        assert " " not in name
        assert "(" not in name
        assert name.endswith(".pdf")

    def test_preserves_extension(self, storage):
        name = storage._generate_filename("document.docx")
        assert name.endswith(".docx")


class TestSaveFile:
    """Tests for file saving."""

    @pytest.mark.asyncio
    async def test_save_file(self, storage, tmp_path):
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        content = b"PDF content here"
        mock_file.read = AsyncMock(side_effect=[content, b""])

        path, filename, size = await storage.save_file("user-1", mock_file)
        assert size == len(content)
        assert filename.endswith(".pdf")
        assert "user-1" in path

    @pytest.mark.asyncio
    async def test_save_rejects_oversized(self, storage):
        mock_file = MagicMock()
        mock_file.filename = "huge.pdf"
        # Simulate a file larger than 100 bytes
        big_chunk = b"x" * 200
        mock_file.read = AsyncMock(side_effect=[big_chunk, b""])

        with pytest.raises(DocumentStorageError):
            await storage.save_file("user-1", mock_file, max_size_bytes=100)


class TestReadDeleteFile:
    """Tests for file read and delete operations."""

    @pytest.mark.asyncio
    async def test_read_file(self, storage, tmp_path):
        # Write a file manually
        user_dir = storage._get_user_dir("user-1")
        test_file = user_dir / "test.pdf"
        test_file.write_bytes(b"test content")

        content = await storage.read_file(str(test_file))
        assert content == b"test content"

    @pytest.mark.asyncio
    async def test_read_missing_file(self, storage):
        with pytest.raises(DocumentStorageError, match="not found"):
            await storage.read_file("/nonexistent/path/file.pdf")

    @pytest.mark.asyncio
    async def test_delete_file(self, storage, tmp_path):
        user_dir = storage._get_user_dir("user-1")
        test_file = user_dir / "to_delete.pdf"
        test_file.write_bytes(b"delete me")
        assert test_file.exists()

        await storage.delete_file(str(test_file))
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_missing_file_no_error(self, storage):
        # Should not raise, just log warning
        await storage.delete_file("/nonexistent/file.pdf")


class TestStorageStats:
    """Tests for storage statistics."""

    def test_empty_user_stats(self, storage):
        stats = storage.get_storage_stats("new-user")
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_with_files(self, storage):
        user_dir = storage._get_user_dir("user-1")
        (user_dir / "a.pdf").write_bytes(b"x" * 100)
        (user_dir / "b.pdf").write_bytes(b"x" * 200)

        stats = storage.get_storage_stats("user-1")
        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 300


class TestGetFileType:
    """Tests for MIME type detection."""

    def test_pdf(self, storage):
        assert storage.get_file_type("doc.pdf") == "application/pdf"

    def test_jpg(self, storage):
        assert storage.get_file_type("photo.jpg") == "image/jpeg"

    def test_unknown(self, storage):
        assert storage.get_file_type("file.xyz") == "application/octet-stream"
