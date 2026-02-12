#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-auto}"

case "$MODE" in
  auto|cpu|gpu)
    exec python3 "$ROOT_DIR/scripts/launcher/start.py" --mode docker --docker-mode "$MODE"
    ;;
  cpu-internet)
    exec python3 "$ROOT_DIR/scripts/launcher/start.py" --mode docker --docker-mode cpu --internet
    ;;
  gpu-internet)
    exec python3 "$ROOT_DIR/scripts/launcher/start.py" --mode docker --docker-mode gpu --internet
    ;;
  *)
    echo "Usage: $0 [auto|cpu|gpu|cpu-internet|gpu-internet]"
    exit 2
    ;;
esac
