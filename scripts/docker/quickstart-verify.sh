#!/usr/bin/env bash
# Quickstart verification script — checks that the Docker stack is healthy.
# Usage: bash scripts/docker/quickstart-verify.sh
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8082}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3082}"
API_KEY="${API_ACCESS_KEY:-dev-secret-key}"
TIMEOUT=5

pass=0
fail=0

check_url() {
    local label="$1" url="$2" expected="${3:-200}" headers="${4:-}"
    if command -v curl &>/dev/null; then
        if [ -n "$headers" ]; then
            code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -H "$headers" "$url" 2>/dev/null || echo "000")
        else
            code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
        fi
    elif command -v wget &>/dev/null; then
        code=$(wget --server-response --spider --timeout="$TIMEOUT" -q "$url" 2>&1 | grep "HTTP/" | tail -1 | awk '{print $2}' || echo "000")
        [ -z "$code" ] && code="000"
    else
        echo "  $label: SKIP (no curl/wget)"
        return
    fi

    if [ "$code" = "$expected" ] || { [ "$expected" = "200" ] && [ "$code" -ge 200 ] 2>/dev/null && [ "$code" -lt 300 ] 2>/dev/null; }; then
        echo "  $label: PASS ($code)"
        ((pass++))
    else
        echo "  $label: FAIL (got $code, expected $expected)"
        ((fail++))
    fi
}

echo "Verifying AI Real Estate Assistant stack..."
echo ""

check_url "Backend health"  "$BACKEND_URL/health"
check_url "Frontend"        "$FRONTEND_URL/"
check_url "API auth"        "$BACKEND_URL/api/v1/verify-auth" "200" "X-API-Key: $API_KEY"

echo ""
if [ "$fail" -eq 0 ]; then
    echo "All checks passed. Open $FRONTEND_URL to start chatting."
    exit 0
else
    echo "$fail check(s) failed. See logs: docker compose -f deploy/compose/docker-compose.yml logs"
    exit 1
fi
