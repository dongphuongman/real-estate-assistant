from __future__ import annotations

from pathlib import Path

from api.openapi_markdown import load_openapi_schema, serialize_endpoints_markdown


def _extract_endpoints_section(text: str) -> str:
    text = text.replace("\r\n", "\n")
    anchor = "### Endpoints"
    idx = text.find(anchor)
    assert idx != -1, "### Endpoints anchor missing in docs/API_REFERENCE.md"
    return text[idx + len(anchor) :].strip()


def test_api_reference_md_endpoints_in_sync_with_openapi_snapshot() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    schema = load_openapi_schema(repo_root / "docs" / "openapi.json")
    generated = serialize_endpoints_markdown(schema).strip()

    committed = (repo_root / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8")
    committed_section = _extract_endpoints_section(committed)
    assert committed_section.startswith(generated[:100])
    assert generated in committed_section

