"""
Citation Service for enhanced citation processing.

Task #65: Citation Quality Enhancement
Provides extraction, scoring, deduplication, and formatting for citations.
"""

import hashlib
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

from api.models import (
    CitationConfidence,
    CitationStats,
    EnhancedCitation,
    SourceType,
)


class CitationService:
    """Service for processing and enhancing citations from retrieved documents."""

    # File extension to source type mapping
    EXTENSION_MAP = {
        ".pdf": SourceType.PDF,
        ".docx": SourceType.DOCX,
        ".doc": SourceType.DOCX,
        ".xlsx": SourceType.DATABASE,
        ".xls": SourceType.DATABASE,
        ".csv": SourceType.DATABASE,
        ".json": SourceType.API,
        ".xml": SourceType.API,
    }

    # URL patterns for web source detection
    WEB_PATTERNS = [
        r"^https?://",
        r"^www\.",
        r"\.com$",
        r"\.org$",
        r"\.net$",
        r"\.edu$",
        r"\.gov$",
    ]

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    LOW_CONFIDENCE_THRESHOLD = 0.5

    def extract_source_type(self, source: Optional[str]) -> SourceType:
        """
        Detect the type of source from its identifier.

        Args:
            source: Source identifier (filename, URL, etc.)

        Returns:
            SourceType enum value
        """
        if not source:
            return SourceType.UNKNOWN

        source_lower = source.lower().strip()

        # Check for web URLs
        for pattern in self.WEB_PATTERNS:
            if re.search(pattern, source_lower):
                return SourceType.WEB

        # Check for file extensions
        for ext, source_type in self.EXTENSION_MAP.items():
            if source_lower.endswith(ext):
                return source_type

        # Check for database-like identifiers
        if source_lower.startswith(("db:", "database:", "sql:")):
            return SourceType.DATABASE

        # Check for API-like identifiers
        if source_lower.startswith(("api:", "endpoint:")):
            return SourceType.API

        return SourceType.UNKNOWN

    def calculate_confidence(
        self,
        doc: Document,
        query: str,
        similarity_score: float,
    ) -> Tuple[CitationConfidence, float]:
        """
        Calculate confidence level for a citation.

        Confidence is based on:
        - Similarity score from vector search (primary)
        - Keyword overlap between query and document content
        - Chunk position relevance

        Args:
            doc: Retrieved document
            query: Original query string
            similarity_score: Vector similarity score (0.0-1.0)

        Returns:
            Tuple of (CitationConfidence, float score)
        """
        # Normalize similarity score (assuming it's a distance, convert to similarity)
        # ChromaDB returns distance, lower is better
        if similarity_score > 1.0:
            # Likely a distance score, invert
            base_score = max(0.0, 1.0 - (similarity_score / 10.0))
        else:
            base_score = similarity_score

        # Calculate keyword overlap
        query_words = set(query.lower().split())
        content_words = set(doc.page_content.lower().split())

        # Remove common stop words for better matching
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        query_words -= stop_words
        content_words -= stop_words

        if query_words:
            overlap_ratio = len(query_words & content_words) / len(query_words)
        else:
            overlap_ratio = 0.0

        # Weighted combination
        # 70% similarity score, 30% keyword overlap
        confidence_score = (base_score * 0.7) + (overlap_ratio * 0.3)

        # Clamp to valid range
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Determine confidence level
        if confidence_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence = CitationConfidence.HIGH
        elif confidence_score >= self.LOW_CONFIDENCE_THRESHOLD:
            confidence = CitationConfidence.MEDIUM
        else:
            confidence = CitationConfidence.LOW

        return confidence, round(confidence_score, 4)

    def generate_citation_hash(self, citation: EnhancedCitation) -> str:
        """
        Generate a deterministic hash for citation deduplication.

        Args:
            citation: EnhancedCitation object

        Returns:
            SHA256 hash string
        """
        # Create a canonical string from citation fields
        hash_components = [
            citation.source or "",
            str(citation.chunk_index or ""),
            str(citation.page_number or ""),
            str(citation.paragraph_number or ""),
        ]

        canonical = "|".join(hash_components).lower()
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def deduplicate_citations(
        self,
        citations: List[EnhancedCitation],
    ) -> List[EnhancedCitation]:
        """
        Deduplicate citations based on source and location.

        Keeps the highest confidence version when duplicates are found.

        Args:
            citations: List of EnhancedCitation objects

        Returns:
            Deduplicated list with is_duplicate flags set
        """
        if not citations:
            return []

        # Group by hash
        hash_groups: Dict[str, List[Tuple[int, EnhancedCitation]]] = defaultdict(list)

        for idx, citation in enumerate(citations):
            citation.citation_hash = self.generate_citation_hash(citation)
            hash_groups[citation.citation_hash].append((idx, citation))

        # Process each group
        result: List[EnhancedCitation] = []

        for _hash_key, group in hash_groups.items():
            if len(group) == 1:
                # No duplicate
                citation = group[0][1]
                citation.is_duplicate = False
                result.append(citation)
            else:
                # Multiple duplicates - keep highest confidence
                sorted_group = sorted(
                    group,
                    key=lambda x: x[1].confidence_score,
                    reverse=True,
                )

                # Mark first as primary
                primary = sorted_group[0][1]
                primary.is_duplicate = False
                result.append(primary)

                # Mark others as duplicates (but don't include in result)
                # They're tracked via is_duplicate flag if needed

        return result

    def validate_citation(
        self,
        citation: EnhancedCitation,
        original_content: Optional[str],
    ) -> bool:
        """
        Validate that citation content exists in original source.

        Args:
            citation: EnhancedCitation to validate
            original_content: Original source content to check against

        Returns:
            True if citation is valid, False otherwise
        """
        if not original_content or not citation.content_snippet:
            return False

        # Normalize both for comparison
        snippet_normalized = citation.content_snippet.lower().strip()
        content_normalized = original_content.lower()

        # Check if snippet exists in content (with some fuzziness)
        # Allow for minor whitespace differences
        snippet_words = snippet_normalized.split()
        if len(snippet_words) < 3:
            # Very short snippet - require exact match
            return snippet_normalized in content_normalized

        # For longer snippets, check if most words appear in sequence
        # This handles cases where text might have minor formatting differences
        content_normalized.split()

        # Create a simple pattern to search for
        search_pattern = " ".join(snippet_words[:10])  # First 10 words
        return search_pattern.lower() in content_normalized

    def format_citation(
        self,
        citation: EnhancedCitation,
        style: str = "inline",
    ) -> str:
        """
        Format citation for display.

        Args:
            citation: EnhancedCitation to format
            style: Format style - "inline", "footnote", or "endnote"

        Returns:
            Formatted citation string
        """
        title = citation.source_title or citation.source or "Unknown Source"

        if style == "inline":
            # Inline format: [Source, p.X]
            parts = [f"[{title}"]
            if citation.page_number:
                parts.append(f", p.{citation.page_number}")
            parts.append("]")
            return "".join(parts)

        elif style == "footnote":
            # Footnote format: ¹ Source (chunk X, confidence: high)
            confidence_str = citation.confidence.value
            parts = [f"{title}"]
            if citation.chunk_index is not None:
                parts.append(f" (chunk {citation.chunk_index}")
                parts.append(f", confidence: {confidence_str})")
            else:
                parts.append(f" (confidence: {confidence_str})")
            return "".join(parts)

        elif style == "endnote":
            # Endnote format: [1] Full Source Details
            parts = [f"{title}"]
            details = []
            if citation.page_number:
                details.append(f"p.{citation.page_number}")
            if citation.chunk_index is not None:
                details.append(f"chunk {citation.chunk_index}")
            if citation.source_type != SourceType.UNKNOWN:
                details.append(f"type: {citation.source_type.value}")
            if details:
                parts.append(f" ({', '.join(details)})")
            return "".join(parts)

        else:
            # Default to inline
            return self.format_citation(citation, style="inline")

    def extract_content_snippet(
        self,
        content: str,
        query: str,
        max_length: int = 200,
    ) -> str:
        """
        Extract a relevant snippet from content based on query.

        Args:
            content: Full document content
            query: Query to find relevant section
            max_length: Maximum snippet length

        Returns:
            Extracted snippet string
        """
        if not content:
            return ""

        # Find query terms in content
        query_terms = query.lower().split()
        content_lower = content.lower()

        # Find best starting position
        best_pos = -1
        best_score = 0

        for term in query_terms:
            if len(term) < 3:  # Skip short terms
                continue
            pos = content_lower.find(term)
            if pos != -1:
                # Score based on how many other terms are nearby
                window = content_lower[max(0, pos - 100) : pos + 100]
                score = sum(1 for t in query_terms if t in window)
                if score > best_score:
                    best_score = score
                    best_pos = pos

        if best_pos == -1:
            # No match found, return start of content
            snippet = content[:max_length]
        else:
            # Start snippet a bit before the match for context
            start = max(0, best_pos - 30)
            snippet = content[start : start + max_length]

        # Clean up snippet
        snippet = snippet.strip()

        # Add ellipsis if truncated
        if len(content) > max_length:
            if not snippet.endswith((".", "!", "?")):
                snippet += "..."

        return snippet

    def process_citations(
        self,
        documents: List[Document],
        scores: List[float],
        query: str,
        format_style: str = "inline",
        original_contents: Optional[Dict[str, str]] = None,
    ) -> List[EnhancedCitation]:
        """
        Process a list of documents into enhanced citations.

        Args:
            documents: List of retrieved LangChain Documents
            scores: Corresponding similarity scores
            query: Original query string
            format_style: Citation format style
            original_contents: Optional dict mapping source to original content

        Returns:
            List of EnhancedCitation objects
        """
        citations: List[EnhancedCitation] = []

        for doc, score in zip(documents, scores, strict=False):
            metadata = doc.metadata or {}
            source = metadata.get("source")

            # Calculate confidence
            confidence, confidence_score = self.calculate_confidence(doc, query, score)

            # Extract content snippet
            snippet = self.extract_content_snippet(doc.page_content, query)

            # Create enhanced citation
            citation = EnhancedCitation(
                source=source,
                chunk_index=metadata.get("chunk_index"),
                page_number=metadata.get("page_number"),
                paragraph_number=metadata.get("paragraph_number"),
                source_type=self.extract_source_type(source),
                confidence=confidence,
                confidence_score=confidence_score,
                content_snippet=snippet,
                source_url=metadata.get("url")
                if self.extract_source_type(source) == SourceType.WEB
                else None,
                source_title=metadata.get("title") or metadata.get("source_name") or source,
                validated=False,
            )

            # Validate if original content available
            if original_contents and source:
                citation.validated = self.validate_citation(
                    citation,
                    original_contents.get(source),
                )

            citations.append(citation)

        # Deduplicate
        citations = self.deduplicate_citations(citations)

        return citations

    def calculate_citation_stats(
        self,
        citations: List[EnhancedCitation],
    ) -> CitationStats:
        """
        Calculate statistics for a list of citations.

        Args:
            citations: List of EnhancedCitation objects

        Returns:
            CitationStats object
        """
        if not citations:
            return CitationStats(
                total=0,
                unique=0,
                duplicates=0,
                by_type={},
                avg_confidence=0.0,
            )

        # Count by type
        by_type: Dict[str, int] = defaultdict(int)
        for citation in citations:
            by_type[citation.source_type.value] += 1

        # Count duplicates
        duplicates = sum(1 for c in citations if c.is_duplicate)

        # Calculate average confidence
        avg_confidence = sum(c.confidence_score for c in citations) / len(citations)

        return CitationStats(
            total=len(citations),
            unique=len(citations) - duplicates,
            duplicates=duplicates,
            by_type=dict(by_type),
            avg_confidence=round(avg_confidence, 4),
        )
