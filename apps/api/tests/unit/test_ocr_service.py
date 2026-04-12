"""Unit tests for OCRService."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ocr_service import OCRService


class TestIsAvailable:
    """Tests for is_available method."""

    def test_available_when_tesseract_installed(self):
        """Returns True when pytesseract is available."""
        with patch("services.ocr_service.TESSERACT_AVAILABLE", True):
            with patch("services.ocr_service.DOCX_AVAILABLE", False):
                # Suppress _check_dependencies subprocess call
                with patch.object(OCRService, "_check_dependencies"):
                    service = OCRService()
                    assert service.is_available() is True

    def test_available_when_docx_installed(self):
        """Returns True when python-docx is available (even without pytesseract)."""
        with patch("services.ocr_service.TESSERACT_AVAILABLE", False):
            with patch("services.ocr_service.DOCX_AVAILABLE", True):
                service = OCRService()
                assert service.is_available() is True

    def test_not_available_when_nothing_installed(self):
        """Returns False when neither pytesseract nor python-docx is installed."""
        with patch("services.ocr_service.TESSERACT_AVAILABLE", False):
            with patch("services.ocr_service.DOCX_AVAILABLE", False):
                service = OCRService()
                assert service.is_available() is False


class TestExtractText:
    """Tests for extract_text method."""

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_file(self):
        """Returns error tuple when file does not exist."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        result = await service.extract_text("/nonexistent/file.pdf", "application/pdf")
        assert result == (None, "File not found: /nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_returns_error_for_unsupported_file_type(self):
        """Returns error tuple for unsupported MIME types."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with patch.object(Path, "exists", return_value=True):
            result = await service.extract_text("/some/file.zip", "application/zip")

        assert result[0] is None
        assert "Unsupported file type" in result[1]

    @pytest.mark.asyncio
    async def test_extracts_from_pdf(self):
        """Delegates to _extract_from_pdf for PDF files."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        expected = ("PDF text content", None)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                OCRService, "_extract_from_pdf", new_callable=AsyncMock, return_value=expected
            ),
        ):
            result = await service.extract_text("/doc/test.pdf", "application/pdf")

        assert result == expected

    @pytest.mark.asyncio
    async def test_extracts_from_jpeg_image(self):
        """Delegates to _extract_from_image for JPEG files."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        expected = ("Image text", None)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                OCRService, "_extract_from_image", new_callable=AsyncMock, return_value=expected
            ),
        ):
            result = await service.extract_text("/img/photo.jpg", "image/jpeg")

        assert result == expected

    @pytest.mark.asyncio
    async def test_extracts_from_png_image(self):
        """Delegates to _extract_from_image for PNG files."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        expected = ("PNG text", None)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                OCRService, "_extract_from_image", new_callable=AsyncMock, return_value=expected
            ),
        ):
            result = await service.extract_text("/img/screenshot.png", "image/png")

        assert result == expected

    @pytest.mark.asyncio
    async def test_extracts_from_docx(self):
        """Delegates to _extract_from_docx for DOCX MIME type."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        expected = ("DOCX content", None)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                OCRService, "_extract_from_docx", new_callable=AsyncMock, return_value=expected
            ),
        ):
            result = await service.extract_text("/doc/report.docx", docx_mime)

        assert result == expected

    @pytest.mark.asyncio
    async def test_extracts_from_legacy_doc(self):
        """Returns limited support message for .doc files."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with patch.object(Path, "exists", return_value=True):
            result = await service.extract_text("/doc/old.doc", "application/msword")

        assert result[0] is None
        assert "limited support" in result[1].lower()

    @pytest.mark.asyncio
    async def test_handles_extraction_exception(self):
        """Returns error message when extraction raises an exception."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                OCRService,
                "_extract_from_pdf",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Corrupt PDF"),
            ),
        ):
            result = await service.extract_text("/doc/bad.pdf", "application/pdf")

        assert result[0] is None
        assert "Corrupt PDF" in result[1]


class TestExtractFromPdf:
    """Tests for _extract_from_pdf internal method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_dependencies_missing(self):
        """Returns error when pdf2image or pytesseract is not available."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with (
            patch("services.ocr_service.PDF2IMAGE_AVAILABLE", False),
            patch("services.ocr_service.TESSERACT_AVAILABLE", False),
        ):
            result = await service._extract_from_pdf("/file.pdf")

        assert result == (None, "PDF OCR requires pdf2image and pytesseract packages")

    @pytest.mark.asyncio
    async def test_extracts_text_from_pdf(self):
        """Extracts text by converting PDF pages to images and OCR-ing."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with patch.object(service, "_pdf_to_text_sync", return_value="Page text"):
            with (
                patch("services.ocr_service.PDF2IMAGE_AVAILABLE", True),
                patch("services.ocr_service.TESSERACT_AVAILABLE", True),
            ):
                result = await service._extract_from_pdf("/doc/test.pdf", max_pages=5)

        assert result[0] == "Page text"
        assert result[1] is None


class TestExtractFromImage:
    """Tests for _extract_from_image internal method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_dependencies_missing(self):
        """Returns error when pytesseract or Pillow is not available."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with (
            patch("services.ocr_service.TESSERACT_AVAILABLE", False),
            patch("services.ocr_service.PIL_AVAILABLE", False),
        ):
            result = await service._extract_from_image("/image.png")

        assert result == (None, "Image OCR requires pytesseract and Pillow packages")

    @pytest.mark.asyncio
    async def test_extracts_text_from_image(self):
        """Extracts text from image using pytesseract."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with patch.object(service, "_image_to_text_sync", return_value="Extracted"):
            with (
                patch("services.ocr_service.TESSERACT_AVAILABLE", True),
                patch("services.ocr_service.PIL_AVAILABLE", True),
            ):
                result = await service._extract_from_image("/photo.jpg")

        assert result == ("Extracted", None)


class TestExtractFromDocx:
    """Tests for _extract_from_docx internal method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_docx_not_available(self):
        """Returns error when python-docx is not installed."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        with patch("services.ocr_service.DOCX_AVAILABLE", False):
            result = await service._extract_from_docx("/doc/report.docx")

        assert result == (None, "DOCX extraction requires python-docx package")

    @pytest.mark.asyncio
    async def test_extracts_text_from_docx(self):
        """Extracts text paragraphs and table cells from DOCX."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        mock_doc = MagicMock()
        para1 = MagicMock()
        para1.text = "Title"
        para2 = MagicMock()
        para2.text = "  "  # Should be skipped (whitespace)
        mock_doc.paragraphs = [para1, para2]
        mock_doc.tables = []

        with (
            patch("services.ocr_service.DOCX_AVAILABLE", True),
            patch("services.ocr_service.Document", return_value=mock_doc),
        ):
            result = await service._extract_from_docx("/doc/report.docx")

        assert result[0] == "Title"
        assert result[1] is None


class TestCheckDependencies:
    """Tests for _check_dependencies method."""

    def test_logs_warning_when_tesseract_missing(self):
        """Logs a warning when pytesseract is not installed."""
        with (
            patch("services.ocr_service.TESSERACT_AVAILABLE", False),
            patch("services.ocr_service.PDF2IMAGE_AVAILABLE", False),
        ):
            OCRService()
            # No exception raised; just logs

    def test_handles_tesseract_binary_not_found(self):
        """Handles FileNotFoundError when tesseract binary is not in PATH."""
        with (
            patch("services.ocr_service.TESSERACT_AVAILABLE", True),
            patch("services.ocr_service.subprocess.run", side_effect=FileNotFoundError),
        ):
            OCRService()
            # No exception raised; just logs warning


class TestCustomLanguage:
    """Tests for language parameter."""

    def test_default_language_is_eng(self):
        """Default language is 'eng'."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()

        assert service.language == "eng"

    def test_custom_language_stored(self):
        """Custom language is stored on the instance."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService(language="pol")

        assert service.language == "pol"
