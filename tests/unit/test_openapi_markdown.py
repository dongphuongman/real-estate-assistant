from __future__ import annotations

from pathlib import Path

import pytest

from api.openapi_markdown import (
    export_api_reference_markdown,
    iter_openapi_operations,
    render_operation_block,
    render_parameters_table,
    render_request_body,
    render_responses,
    schema_type,
    serialize_api_reference_markdown,
)


def test_schema_type_handles_refs_arrays_and_unions() -> None:
    assert schema_type({"$ref": "#/components/schemas/SearchRequest"}) == "SearchRequest"
    assert schema_type({"type": "string"}) == "string"
    assert schema_type({"type": "array", "items": {"type": "integer"}}) == "array[integer]"
    assert (
        schema_type({"oneOf": [{"type": "string"}, {"$ref": "#/components/schemas/X"}]})
        == "string | X"
    )
    assert (
        schema_type({"anyOf": [{"type": "string"}, {"type": "integer"}]})
        == "string | integer"
    )
    assert schema_type({"type": "array", "items": "not-a-dict"}) == "array"
    assert schema_type({"enum": list(range(20))}).endswith("…)")
    assert schema_type({}) == "object"


def test_serialize_api_reference_markdown_includes_operations() -> None:
    schema = {
        "info": {"title": "Test API", "version": "1.2.3"},
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/search": {
                "post": {
                    "summary": "Search",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchRequest"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SearchResponse"}
                                }
                            },
                        }
                    },
                }
            },
        },
    }

    md = serialize_api_reference_markdown(schema)
    assert md.startswith("# API Reference (Generated)\n")
    assert "## GET /health" in md
    assert "## POST /api/v1/search" in md
    assert "application/json: SearchRequest" in md
    assert "| 200 | OK | SearchResponse |" in md


def test_serialize_api_reference_markdown_handles_unknown_version_and_method_sorting() -> None:
    schema = {
        "info": {"title": "Test API"},
        "paths": {
            "/x": {
                "foo": {"responses": {"200": {"description": "OK"}}},
                "get": {"responses": {"200": {"description": "OK"}}},
            }
        },
    }
    md = serialize_api_reference_markdown(schema)
    assert "- Source version: (unknown)" in md
    assert md.index("## GET /x") < md.index("## FOO /x")


def test_iter_openapi_operations_skips_invalid_shapes() -> None:
    assert list(iter_openapi_operations({"paths": []})) == []
    assert (
        list(iter_openapi_operations({"paths": {"/x": "not-a-dict"}}))
        == []
    )


def test_render_operation_block_renders_tags_description_and_parameters() -> None:
    operation = {
        "summary": " Hello\nworld ",
        "description": " Detailed\ndescription ",
        "tags": ["A", "B"],
        "parameters": [
            {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
        ],
        "responses": {"200": {"description": "OK"}},
    }
    text = render_operation_block(path="/x", method="get", operation=operation)
    assert "**Tags**: A, B" in text
    assert "Hello world" in text
    assert "Detailed description" in text
    assert "| q | query | string | yes |  |" in text


def test_render_parameters_table_escapes_pipes_and_skips_invalid_entries() -> None:
    table = render_parameters_table(
        [
            "not-a-dict",
            {"name": "", "in": "query"},
            {
                "name": "x|y",
                "in": "header",
                "required": False,
                "schema": {"enum": ["a", "b"]},
                "description": "line1\nline2",
            },
        ]
    )
    assert "x\\|y" in table
    assert "line1 line2" in table


def test_render_request_body_returns_empty_when_no_content() -> None:
    assert render_request_body({"required": True, "content": {}}) == ""


def test_render_request_body_skips_non_dict_media_but_keeps_required_line() -> None:
    text = render_request_body({"required": False, "content": {"application/json": "nope"}})
    assert text.strip() == "- Required: no"


def test_render_responses_handles_non_dict_entries_and_empty_rows() -> None:
    assert render_responses({"default": "nope"}) == ""
    assert (
        render_responses({"200": {"description": "OK", "content": {"text/plain": {}}}})
        != ""
    )


def test_export_api_reference_markdown_writes_file(tmp_path: Path) -> None:
    schema_path = tmp_path / "openapi.json"
    schema_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"X"},"paths":{"/ping":{"get":{"responses":{"200":{"description":"OK"}}}}}}\n',
        encoding="utf-8",
    )
    out = tmp_path / "API_REFERENCE.generated.md"
    export_api_reference_markdown(schema_path=schema_path, output_path=out, check=False)
    assert out.read_text(encoding="utf-8").endswith("\n")
    assert "## GET /ping" in out.read_text(encoding="utf-8")


def test_export_api_reference_markdown_check_missing_file(tmp_path: Path) -> None:
    schema_path = tmp_path / "openapi.json"
    schema_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"X"},"paths":{}}\n', encoding="utf-8"
    )
    out = tmp_path / "API_REFERENCE.generated.md"
    with pytest.raises(SystemExit):
        export_api_reference_markdown(schema_path=schema_path, output_path=out, check=True)


def test_export_api_reference_markdown_check_detects_drift(tmp_path: Path) -> None:
    schema_path = tmp_path / "openapi.json"
    schema_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"X"},"paths":{"/ping":{"get":{"responses":{"200":{"description":"OK"}}}}}}\n',
        encoding="utf-8",
    )
    out = tmp_path / "API_REFERENCE.generated.md"
    out.write_text("# not generated\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        export_api_reference_markdown(schema_path=schema_path, output_path=out, check=True)


def test_export_api_reference_markdown_check_passes_when_in_sync(tmp_path: Path) -> None:
    schema_path = tmp_path / "openapi.json"
    schema_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"X"},"paths":{"/ping":{"get":{"responses":{"200":{"description":"OK"}}}}}}\n',
        encoding="utf-8",
    )
    out = tmp_path / "API_REFERENCE.generated.md"
    export_api_reference_markdown(schema_path=schema_path, output_path=out, check=False)
    export_api_reference_markdown(schema_path=schema_path, output_path=out, check=True)
