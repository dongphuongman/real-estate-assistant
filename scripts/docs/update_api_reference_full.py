from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from api.openapi_markdown import load_openapi_schema, serialize_endpoints_markdown

    parser = argparse.ArgumentParser(
        description="Update docs\\API_REFERENCE.md Endpoints section from committed OpenAPI schema snapshot."
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("docs") / "openapi.json",
        help="Input OpenAPI JSON schema path (default: docs/openapi.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs") / "API_REFERENCE.md",
        help="API reference Markdown file to update (default: docs/API_REFERENCE.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated Endpoints section differs from the committed file.",
    )
    args = parser.parse_args(argv)

    schema = load_openapi_schema(args.schema)
    endpoints_text = serialize_endpoints_markdown(schema)

    output_path = args.output
    existing = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    anchor = "### Endpoints"
    idx = existing.find(anchor)
    if idx == -1:
        raise SystemExit(f"Anchor not found in {output_path}: {anchor}")

    before = existing[: idx + len(anchor)]
    after = "\n\n" + endpoints_text
    updated = (before + after).rstrip() + "\n"

    if args.check:
        if existing != updated:
            raise SystemExit(
                "API_REFERENCE.md endpoints drift detected. Regenerate with: "
                "python scripts\\docs\\export_openapi.py && python scripts\\docs\\update_api_reference_full.py"
            )
        return 0

    output_path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
