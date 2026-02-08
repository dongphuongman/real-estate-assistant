#!/usr/bin/env bash
# =============================================================================
# AI Real Estate Assistant - Docker Development Launcher (Linux/Mac)
# =============================================================================
#
# Usage:
#   ./run-docker.sh              # Auto-detect GPU if available
#   ./run-docker.sh cpu          # Force CPU mode
#   ./run-docker.sh gpu          # Force GPU mode
#   ./run-docker.sh internet     # Enable internet access
#
# =============================================================================

set -eu

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT_DIR"

# Default Docker mode (auto-detect GPU)
DOCKER_MODE="${1:-auto}"

# Map simple arguments to docker modes
case "$DOCKER_MODE" in
    cpu|gpu|auto|internet)
        # Valid modes
        ;;
    *)
        echo "Error: Unknown mode '$DOCKER_MODE'"
        echo "Usage: $0 [auto|cpu|gpu|internet]"
        exit 1
        ;;
esac

# Run the Python start script with Docker mode
exec python3 "$SCRIPT_DIR/start.py" --mode docker --docker-mode "$DOCKER_MODE"
