#!/usr/bin/env python3
"""Pre-bundle the default fastembed embedding model with retries.

The smoke-test step in publish-ghcr.yml runs in CI, where the runner
hits HuggingFace's CloudFront with HTTP 429 (rate-limited) when it
tries to download the default model. A bare `TextEmbedding()` call
retries 3x with 3s/9s/27s backoff (~39s), which blows the 40s
smoke-test window. This script retries with longer backoff and more
attempts so the pre-bundle usually succeeds within the build's
slack.

If the pre-bundle still fails after all retries, the build continues
with a warning — the app still boots, but embedding-dependent
features may not work. The runtime will fall back to alternative
embedding providers (e.g., OpenAI) or report embeddings as
unavailable.

Usage (from Dockerfile.backend):
    RUN python deploy/docker/prebundle_fastembed.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

MAX_RETRIES = 8
BASE_DELAY_S = 5
MAX_DELAY_S = 60


def _download_with_retry() -> bool:
    from fastembed import TextEmbedding

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"[pre-bundle] attempt {attempt}/{MAX_RETRIES}: instantiating TextEmbedding...",
                flush=True,
            )
            TextEmbedding()
            print(
                f"[pre-bundle] attempt {attempt}: SUCCESS",
                flush=True,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < MAX_RETRIES:
                delay = min(BASE_DELAY_S * (2 ** (attempt - 1)), MAX_DELAY_S)
                print(
                    f"[pre-bundle] attempt {attempt}: FAILED "
                    f"({type(exc).__name__}: {exc}); "
                    f"sleeping {delay}s before retry",
                    flush=True,
                )
                time.sleep(delay)
    print(
        f"[pre-bundle] FAILED after {MAX_RETRIES} attempts: {last_err}",
        flush=True,
    )
    return False


def main() -> int:
    cache_dir = Path(os.environ.get("FASTEMBED_CACHE_PATH", Path.home() / ".cache" / "fastembed"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"[pre-bundle] cache dir: {cache_dir}", flush=True)

    success = _download_with_retry()

    if success:
        print(
            "[pre-bundle] OK: model cached at "
            f"{cache_dir}. Runtime boot will not need outbound HTTPS "
            "to HuggingFace for the default embedding model.",
            flush=True,
        )
        return 0

    print(
        "[pre-bundle] WARNING: model NOT cached. Runtime boot will "
        "retry the download (and likely fail in environments with "
        "HuggingFace rate-limiting). The app still boots; "
        "embedding-dependent features will be unavailable.",
        flush=True,
    )
    return 0  # do not fail the build


if __name__ == "__main__":
    sys.exit(main())
