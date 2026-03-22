"""Tests for CitationService - Enhanced citation processing.

Task #65: Citation Quality Enhancement
"""

import pytest
from langchain_core.documents import Document

from api.models import (
    CitationConfidence,
    EnhancedCitation,
    SourceType,
)
from services.citation_service import CitationService


@pytest.fixture
def citation_service():
    """Create a CitationService instance."""
    return CitationService()


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document(
        page_content="Berlin apartment under 500k is great for families.",
        metadata={
            "source": "document.pdf",
            "chunk_index": 0,
            "page_number": 1,
            "paragraph_number": 3,
        },
    )


class TestSourceTypeDetection:
    """Test source type detection."""

    def test_extract_source_type_pdf(self, citation_service):
        """Test PDF source type detection."""
        result = citation_service.extract_source_type("document.pdf")
        assert result == SourceType.PDF

    def test_extract_source_type_docx(self, citation_service):
        """Test DOCX source type detection."""
        result = citation_service.extract_source_type("document.docx")
        assert result == SourceType.DOCX

    def test_extract_source_type_web(self, citation_service):
        """Test web source type detection."""
        result = citation_service.extract_source_type("https://example.com")
        assert result == SourceType.WEB

    def test_extract_source_type_web_www(self, citation_service):
        """Test web source type detection with www."""
        result = citation_service.extract_source_type("www.example.com")
        assert result == SourceType.WEB

    def test_extract_source_type_database(self, citation_service):
        """Test database source type detection."""
        result = citation_service.extract_source_type("db:properties")
        assert result == SourceType.DATABASE

    def test_extract_source_type_api(self, citation_service):
        """Test API source type detection."""
        result = citation_service.extract_source_type("api:endpoint")
        assert result == SourceType.API

    def test_extract_source_type_xlsx(self, citation_service):
        """Test Excel source type detection."""
        result = citation_service.extract_source_type("data.xlsx")
        assert result == SourceType.DATABASE

    def test_extract_source_type_json(self, citation_service):
        """Test JSON source type detection."""
        result = citation_service.extract_source_type("data.json")
        assert result == SourceType.API

    def test_extract_source_type_unknown(self, citation_service):
        """Test unknown source type detection."""
        result = citation_service.extract_source_type("unknown")
        assert result == SourceType.UNKNOWN

    def test_extract_source_type_none(self, citation_service):
        """Test None source type detection."""
        result = citation_service.extract_source_type(None)
        assert result == SourceType.UNKNOWN

    def test_extract_source_type_empty(self, citation_service):
        """Test empty string source type detection."""
        result = citation_service.extract_source_type("")
        assert result == SourceType.UNKNOWN


class TestConfidenceCalculation:
    """Test confidence calculation."""

    def test_calculate_confidence_high(self, citation_service, sample_document):
        """Test high confidence calculation."""
        confidence, score = citation_service.calculate_confidence(
            doc=sample_document,
            query="Berlin apartment families",
            similarity_score=0.9,
        )
        assert confidence == CitationConfidence.HIGH
        assert score >= 0.8

    def test_calculate_confidence_medium(self, citation_service, sample_document):
        """Test medium confidence calculation."""
        # Use a query with some keyword overlap for medium confidence
        confidence, score = citation_service.calculate_confidence(
            doc=sample_document,
            query="Berlin apartment test",
            similarity_score=0.6,
        )
        assert confidence in [CitationConfidence.MEDIUM, CitationConfidence.LOW]
        assert score < 0.8

    def test_calculate_confidence_low(self, citation_service):
        """Test low confidence calculation."""
        doc = Document(
            page_content="Completely unrelated content about cooking.",
            metadata={"source": "other.pdf"},
        )
        confidence, score = citation_service.calculate_confidence(
            doc=doc,
            query="Berlin apartment families",
            similarity_score=0.3,
        )
        assert confidence == CitationConfidence.LOW
        assert score < 0.5

    def test_calculate_confidence_with_keyword_overlap(self, citation_service, sample_document):
        """Test confidence with keyword overlap."""
        confidence, score = citation_service.calculate_confidence(
            doc=sample_document,
            query="Berlin apartment 500k families",
            similarity_score=0.7,
        )
        # Should have higher confidence due to keyword overlap
        assert score >= 0.5


class TestCitationHash:
    """Test citation hash generation."""

    def test_generate_citation_hash_consistent(self, citation_service):
        """Test that hash is deterministic."""
        citation = EnhancedCitation(
            source="document.pdf",
            chunk_index=0,
            page_number=1,
        )
        hash1 = citation_service.generate_citation_hash(citation)
        hash2 = citation_service.generate_citation_hash(citation)
        assert hash1 == hash2

    def test_generate_citation_hash_different_sources(self, citation_service):
        """Test that different sources produce different hashes."""
        citation1 = EnhancedCitation(source="doc1.pdf", chunk_index=0)
        citation2 = EnhancedCitation(source="doc2.pdf", chunk_index=0)
        hash1 = citation_service.generate_citation_hash(citation1)
        hash2 = citation_service.generate_citation_hash(citation2)
        assert hash1 != hash2

    def test_generate_citation_hash_different_chunks(self, citation_service):
        """Test that different chunks produce different hashes."""
        citation1 = EnhancedCitation(source="document.pdf", chunk_index=0)
        citation2 = EnhancedCitation(source="document.pdf", chunk_index=1)
        hash1 = citation_service.generate_citation_hash(citation1)
        hash2 = citation_service.generate_citation_hash(citation2)
        assert hash1 != hash2


class TestDeduplication:
    """Test citation deduplication."""

    def test_deduplicate_citations_no_duplicates(self, citation_service):
        """Test deduplication with no duplicates."""
        citations = [
            EnhancedCitation(source="doc1.pdf", chunk_index=0),
            EnhancedCitation(source="doc2.pdf", chunk_index=0),
        ]
        result = citation_service.deduplicate_citations(citations)
        assert len(result) == 2
        assert all(not c.is_duplicate for c in result)

    def test_deduplicate_citations_with_duplicates(self, citation_service):
        """Test deduplication with duplicates."""
        citations = [
            EnhancedCitation(
                source="document.pdf",
                chunk_index=0,
                confidence_score=0.8,
            ),
            EnhancedCitation(
                source="document.pdf",
                chunk_index=0,
                confidence_score=0.9,  # Higher confidence
            ),
        ]
        result = citation_service.deduplicate_citations(citations)
        assert len(result) == 1
        assert result[0].confidence_score == 0.9  # Kept higher confidence

    def test_deduplicate_citations_empty_list(self, citation_service):
        """Test deduplication with empty list."""
        result = citation_service.deduplicate_citations([])
        assert result == []


class TestCitationFormatting:
    """Test citation formatting."""

    def test_format_citation_inline(self, citation_service):
        """Test inline citation formatting."""
        citation = EnhancedCitation(
            source_title="Example Document",
            page_number=5,
        )
        result = citation_service.format_citation(citation, style="inline")
        assert "Example Document" in result
        assert "p.5" in result

    def test_format_citation_footnote(self, citation_service):
        """Test footnote citation formatting."""
        citation = EnhancedCitation(
            source_title="Example Document",
            chunk_index=2,
            confidence=CitationConfidence.HIGH,
        )
        result = citation_service.format_citation(citation, style="footnote")
        assert "Example Document" in result
        assert "chunk 2" in result
        assert "high" in result

    def test_format_citation_endnote(self, citation_service):
        """Test endnote citation formatting."""
        citation = EnhancedCitation(
            source_title="Example Document",
            page_number=10,
            chunk_index=5,
            source_type=SourceType.PDF,
        )
        result = citation_service.format_citation(citation, style="endnote")
        assert "Example Document" in result
        assert "p.10" in result

    def test_format_citation_unknown_style_defaults_inline(self, citation_service):
        """Test unknown style defaults to inline."""
        citation = EnhancedCitation(source_title="Test")
        result = citation_service.format_citation(citation, style="unknown")
        assert "Test" in result


class TestContentSnippet:
    """Test content snippet extraction."""

    def test_extract_content_snippet_basic(self, citation_service):
        """Test basic snippet extraction."""
        content = "Berlin apartment under 500k is great for families and has good schools."
        result = citation_service.extract_content_snippet(
            content, "Berlin apartment", max_length=100
        )
        assert len(result) <= 103  # max_length + "..."
        assert "Berlin" in result.lower() or "apartment" in result.lower()

    def test_extract_content_snippet_truncation(self, citation_service):
        """Test snippet truncation."""
        content = "A" * 500
        result = citation_service.extract_content_snippet(content, "test", max_length=50)
        assert len(result) <= 53  # max_length + "..."

    def test_extract_content_snippet_empty_content(self, citation_service):
        """Test snippet extraction with empty content."""
        result = citation_service.extract_content_snippet("", "query")
        assert result == ""


class TestCitationValidation:
    """Test citation validation."""

    def test_validate_citation_match(self, citation_service):
        """Test validation with matching content."""
        citation = EnhancedCitation(content_snippet="Berlin apartment")
        original = "The Berlin apartment market is growing."
        result = citation_service.validate_citation(citation, original)
        assert result is True

    def test_validate_citation_no_match(self, citation_service):
        """Test validation with non-matching content."""
        citation = EnhancedCitation(content_snippet="Paris apartment")
        original = "The Berlin apartment market is growing."
        result = citation_service.validate_citation(citation, original)
        assert result is False

    def test_validate_citation_none_content(self, citation_service):
        """Test validation with None content."""
        citation = EnhancedCitation(content_snippet="test")
        result = citation_service.validate_citation(citation, None)
        assert result is False

    def test_validate_citation_none_snippet(self, citation_service):
        """Test validation with None snippet."""
        citation = EnhancedCitation(content_snippet=None)
        result = citation_service.validate_citation(citation, "some content")
        assert result is False


class TestProcessCitations:
    """Test full citation processing."""

    def test_process_citations_basic(self, citation_service):
        """Test basic citation processing."""
        docs = [
            Document(
                page_content="Berlin apartment under 500k is great for families.",
                metadata={"source": "document.pdf", "chunk_index": 0},
            ),
        ]
        scores = [0.8]

        result = citation_service.process_citations(
            documents=docs,
            scores=scores,
            query="Berlin apartment",
        )

        assert len(result) == 1
        assert result[0].source_type == SourceType.PDF
        assert result[0].confidence in [CitationConfidence.HIGH, CitationConfidence.MEDIUM]

    def test_process_citations_multiple_docs(self, citation_service):
        """Test processing multiple documents."""
        docs = [
            Document(
                page_content="Content 1",
                metadata={"source": "doc1.pdf", "chunk_index": 0},
            ),
            Document(
                page_content="Content 2",
                metadata={"source": "doc2.pdf", "chunk_index": 0},
            ),
        ]
        scores = [0.8, 0.7]

        result = citation_service.process_citations(
            documents=docs,
            scores=scores,
            query="test query",
        )

        assert len(result) == 2

    def test_process_citations_empty(self, citation_service):
        """Test processing empty document list."""
        result = citation_service.process_citations(
            documents=[],
            scores=[],
            query="test",
        )
        assert result == []


class TestCitationStats:
    """Test citation statistics calculation."""

    def test_calculate_citation_stats_basic(self, citation_service):
        """Test basic stats calculation."""
        citations = [
            EnhancedCitation(
                source="doc1.pdf",
                source_type=SourceType.PDF,
                confidence=CitationConfidence.HIGH,
                confidence_score=0.9,
                is_duplicate=False,
            ),
            EnhancedCitation(
                source="doc2.docx",
                source_type=SourceType.DOCX,
                confidence=CitationConfidence.MEDIUM,
                confidence_score=0.6,
                is_duplicate=False,
            ),
        ]

        result = citation_service.calculate_citation_stats(citations)

        assert result.total == 2
        assert result.unique == 2
        assert result.duplicates == 0
        assert "pdf" in result.by_type
        assert "docx" in result.by_type
        assert 0.7 <= result.avg_confidence <= 0.8

    def test_calculate_citation_stats_empty(self, citation_service):
        """Test stats with empty list."""
        result = citation_service.calculate_citation_stats([])

        assert result.total == 0
        assert result.unique == 0
        assert result.duplicates == 0
        assert result.avg_confidence == 0.0

    def test_calculate_citation_stats_with_duplicates(self, citation_service):
        """Test stats with duplicates."""
        citations = [
            EnhancedCitation(
                source="doc.pdf",
                source_type=SourceType.PDF,
                confidence=CitationConfidence.HIGH,
                confidence_score=0.9,
                is_duplicate=False,
            ),
            EnhancedCitation(
                source="doc.pdf",
                source_type=SourceType.PDF,
                confidence=CitationConfidence.MEDIUM,
                confidence_score=0.6,
                is_duplicate=True,
            ),
        ]

        result = citation_service.calculate_citation_stats(citations)

        assert result.total == 2
        assert result.unique == 1
        assert result.duplicates == 1
