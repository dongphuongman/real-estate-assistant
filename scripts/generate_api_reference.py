from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from api.openapi_markdown import export_api_reference_markdown

    parser = argparse.ArgumentParser(
        description="Generate a Markdown API reference from the committed OpenAPI schema snapshot."
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
        default=Path("docs") / "API_REFERENCE.generated.md",
        help="Output Markdown file path (default: docs/API_REFERENCE.generated.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if output differs from the committed generated Markdown.",
    )
    args = parser.parse_args()

    export_api_reference_markdown(
        schema_path=args.schema, output_path=args.output, check=args.check
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
