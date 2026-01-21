from __future__ import annotations

import io


class DocumentTextExtractionError(Exception):
    pass


class UnsupportedDocumentTypeError(DocumentTextExtractionError):
    pass


class OptionalDependencyMissingError(DocumentTextExtractionError):
    def __init__(self, message: str, dependency: str):
        super().__init__(message)
        self.dependency = dependency


def extract_text_from_upload(*, filename: str, content_type: str, data: bytes) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    if ctype in {"text/plain", "text/markdown"} or name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore")

    if ctype == "application/pdf" or name.endswith(".pdf"):
        return _extract_pdf_text(data)

    if (
        ctype
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or name.endswith(".docx")
    ):
        return _extract_docx_text(data)

    raise UnsupportedDocumentTypeError(
        f"Unsupported file type: {filename} ({content_type}). Allowed: .txt, .md, .pdf, .docx"
    )


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise OptionalDependencyMissingError(
            "PDF parsing requires optional dependency 'pypdf'. Install with: pip install pypdf",
            dependency="pypdf",
        ) from e

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise OptionalDependencyMissingError(
            "DOCX parsing requires optional dependency 'python-docx'. Install with: pip install python-docx",
            dependency="python-docx",
        ) from e

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(parts).strip()

