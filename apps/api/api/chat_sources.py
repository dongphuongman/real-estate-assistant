from __future__ import annotations

import json
from typing import Any, Iterable, List

from api.models import EnhancedCitation


def serialize_enhanced_citations(
    citations: List[EnhancedCitation],
    *,
    max_items: int = 50,
    max_content_chars: int = 500,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Serialize EnhancedCitation objects to source format for ChatResponse.

    Args:
        citations: List of EnhancedCitation objects
        max_items: Maximum number of items to return
        max_content_chars: Maximum characters in content snippet

    Returns:
        Tuple of (sources list, citation_stats dict or None)
    """
    max_items = max(0, int(max_items))
    max_content_chars = max(0, int(max_content_chars))

    sources: list[dict[str, Any]] = []
    total_confidence = 0.0
    by_type: dict[str, int] = {}
    unique_count = 0

    for _i, citation in enumerate(citations[:max_items]):
        # Use content_snippet or empty string
        content = citation.content_snippet or ""
        if max_content_chars and len(content) > max_content_chars:
            content = content[:max_content_chars]

        # Build metadata with enhanced fields
        metadata: dict[str, Any] = {
            "source": citation.source,
            "chunk_index": citation.chunk_index,
            "page_number": citation.page_number,
            "paragraph_number": citation.paragraph_number,
            "source_type": citation.source_type.value,
            "confidence": citation.confidence.value,
            "confidence_score": citation.confidence_score,
            "source_title": citation.source_title,
            "source_url": citation.source_url,
            "is_duplicate": citation.is_duplicate,
            "validated": citation.validated,
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        sources.append({"content": content, "metadata": metadata})

        # Track stats
        total_confidence += citation.confidence_score
        by_type[citation.source_type.value] = by_type.get(citation.source_type.value, 0) + 1
        if not citation.is_duplicate:
            unique_count += 1

    # Build citation stats
    stats = None
    if citations:
        stats = {
            "total": len(citations[:max_items]),
            "unique": unique_count,
            "duplicates": len(citations[:max_items]) - unique_count,
            "by_type": by_type,
            "avg_confidence": round(total_confidence / len(citations[:max_items]), 4)
            if citations
            else 0.0,
        }

    return sources, stats


def serialize_chat_sources(
    docs: Iterable[Any],
    *,
    max_items: int,
    max_content_chars: int,
    max_total_bytes: int,
) -> tuple[list[dict[str, Any]], bool]:
    max_items = max(0, int(max_items))
    max_content_chars = max(0, int(max_content_chars))
    max_total_bytes = max(0, int(max_total_bytes))

    sources: list[dict[str, Any]] = []
    total_bytes = 0
    truncated = False

    iterator = iter(docs)
    for doc in iterator:
        # Check max_items limit
        if max_items and len(sources) >= max_items:
            truncated = True
            break

        if doc is None:
            break

        content = getattr(doc, "page_content", "")
        if not isinstance(content, str):
            content = str(content)
        if max_content_chars and len(content) > max_content_chars:
            content = content[:max_content_chars]
            truncated = True

        metadata = getattr(doc, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {"value": str(metadata)}

        try:
            json.dumps(metadata, ensure_ascii=False)
            safe_metadata = metadata
        except TypeError:
            safe_metadata = {str(k): str(v) for k, v in metadata.items()}

        item = {"content": content, "metadata": safe_metadata}

        if max_total_bytes:
            encoded = json.dumps(item, ensure_ascii=False).encode("utf-8")
            if total_bytes + len(encoded) > max_total_bytes:
                truncated = True
                break
            total_bytes += len(encoded)

        sources.append(item)

    return sources, truncated


def serialize_web_sources(
    web_sources: Iterable[dict[str, Any]],
    *,
    max_items: int,
    max_content_chars: int,
    max_total_bytes: int,
) -> tuple[list[dict[str, Any]], bool]:
    max_items = max(0, int(max_items))
    max_content_chars = max(0, int(max_content_chars))
    max_total_bytes = max(0, int(max_total_bytes))

    sources: list[dict[str, Any]] = []
    total_bytes = 0
    truncated = False

    iterator = iter(web_sources)
    for raw in iterator:
        # Check max_items limit
        if max_items and len(sources) >= max_items:
            truncated = True
            break

        if raw is None:
            break
        if not isinstance(raw, dict):
            raw = {"value": str(raw)}

        content = str(raw.get("snippet") or raw.get("content") or "").strip()
        if max_content_chars and len(content) > max_content_chars:
            content = content[:max_content_chars]
            truncated = True

        metadata = {k: v for k, v in raw.items() if k not in {"snippet", "content"}}
        try:
            json.dumps(metadata, ensure_ascii=False)
            safe_metadata = metadata
        except TypeError:
            safe_metadata = {str(k): str(v) for k, v in metadata.items()}

        item = {"content": content, "metadata": safe_metadata}

        if max_total_bytes:
            encoded = json.dumps(item, ensure_ascii=False).encode("utf-8")
            if total_bytes + len(encoded) > max_total_bytes:
                truncated = True
                break
            total_bytes += len(encoded)

        sources.append(item)

    return sources, truncated
