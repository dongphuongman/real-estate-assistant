from __future__ import annotations

import json
from typing import Any, Iterable


def serialize_chat_sources(
    docs: Iterable[Any],
    *,
    max_items: int,
    max_content_chars: int,
    max_total_bytes: int,
) -> list[dict[str, Any]]:
    max_items = max(0, int(max_items))
    max_content_chars = max(0, int(max_content_chars))
    max_total_bytes = max(0, int(max_total_bytes))

    sources: list[dict[str, Any]] = []
    total_bytes = 0

    for doc in docs:
        if max_items and len(sources) >= max_items:
            break

        content = getattr(doc, "page_content", "")
        if not isinstance(content, str):
            content = str(content)
        if max_content_chars and len(content) > max_content_chars:
            content = content[:max_content_chars]

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
                break
            total_bytes += len(encoded)

        sources.append(item)

    return sources

