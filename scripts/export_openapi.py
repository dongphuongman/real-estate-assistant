from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from api.main import app as fastapi_app
    from api.openapi_export import export_openapi_schema

    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI schema to JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs") / "openapi.json",
        help="Output JSON file path (default: docs/openapi.json).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if output differs from the committed schema.",
    )
    args = parser.parse_args()

    export_openapi_schema(app=fastapi_app, output_path=args.output, check=args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
