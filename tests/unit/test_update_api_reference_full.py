from __future__ import annotations

from pathlib import Path

from api.openapi_markdown import serialize_endpoints_markdown
from scripts.docs.update_api_reference_full import main as update_main


def test_serialize_endpoints_markdown_outputs_operations_only() -> None:
    schema = {
        "info": {"title": "Test"},
        "paths": {
            "/ping": {"get": {"summary": "Ping", "responses": {"200": {"description": "OK"}}}}
        },
    }
    text = serialize_endpoints_markdown(schema)
    assert text.startswith("## GET /ping")
    assert "# API Reference" not in text


def test_update_api_reference_full_replaces_endpoints_section(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    schema_path = docs_dir / "openapi.json"
    schema_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"X"},"paths":{"\/ping":{"get":{"responses":{"200":{"description":"OK"}}}}}}\n',
        encoding="utf-8",
    )
    api_ref = docs_dir / "API_REFERENCE.md"
    api_ref.write_text("# Title\n\n### Endpoints\n\nold\n", encoding="utf-8")

    # Run update (via imported main) using cwd-relative defaults
    cwd = Path.cwd()
    try:
        # Temporarily chdir to tmp project so defaults point to our files
        import os

        os.chdir(tmp_path)
        assert update_main([]) == 0
    finally:
        import os

        os.chdir(cwd)

    updated = api_ref.read_text(encoding="utf-8")
    assert "## GET /ping" in updated
    assert "old" not in updated
