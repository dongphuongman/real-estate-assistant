"""
Convenience wrapper for running local security scans.

This script provides an easy way to run security checks from the project root.
It delegates to scripts/ci/security_local.py.

Usage:
    python security-scan.py              # Run all security scans
    python security-scan.py --scan-only=secrets
    python security-scan.py --quick      # Skip slower checks
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run the security scanner
if __name__ == "__main__":
    # Import here to avoid circular import
    from scripts.ci.security_local import main

    # Pass through command line arguments
    raise SystemExit(main(sys.argv[1:]))
