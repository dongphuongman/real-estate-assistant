#!/usr/bin/env bash
#
# Smoke Test Script for Deployment Validation (Task #69)
#
# Validates a running instance by checking health, search, chat,
# security headers, and CORS configuration.
#
# Usage:
#   ./scripts/smoke_test.sh [BASE_URL] [API_KEY]
#
# Examples:
#   ./scripts/smoke_test.sh                              # defaults: http://localhost:8000
#   ./scripts/smoke_test.sh https://api.example.com my-key
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
API_KEY="${2:-${API_ACCESS_KEY:-dev-secret-key}}"

PASS=0
FAIL=0
CHECKS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

check() {
  local name="$1"
  local result="$2"
  if [ "$result" = "pass" ]; then
    CHECKS="${CHECKS}\n  ${GREEN}PASS${NC}  ${name}"
    PASS=$((PASS + 1))
  else
    CHECKS="${CHECKS}\n  ${RED}FAIL${NC}  ${name}"
    FAIL=$((FAIL + 1))
  fi
}

echo "============================================"
echo " Smoke Test — ${BASE_URL}"
echo "============================================"
echo ""

# --- 1. Health Check ---
echo -n "  Health endpoint (/health)... "
HTTP_CODE=$(curl -s -o /tmp/smoke_health.json -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  STATUS=$(python3 -c "import json; print(json.load(open('/tmp/smoke_health.json')).get('status','unknown'))" 2>/dev/null || echo "parse_error")
  if [ "$STATUS" = "healthy" ]; then
    check "Health endpoint returns 200 + healthy" "pass"
  else
    check "Health endpoint returns 200 but status=${STATUS}" "fail"
  fi
else
  check "Health endpoint returns HTTP ${HTTP_CODE} (expected 200)" "fail"
fi

# --- 2. Health Ready ---
echo -n "  Readiness (/health/ready)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health/ready" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  check "Readiness probe returns 200" "pass"
else
  check "Readiness probe returns HTTP ${HTTP_CODE}" "fail"
fi

# --- 3. Search Endpoint ---
echo -n "  Search (/api/v1/properties/search)... "
HTTP_CODE=$(curl -s -o /tmp/smoke_search.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/properties/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"query":"apartments","limit":5}' 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  check "Search endpoint returns 200" "pass"
elif [ "$HTTP_CODE" = "000" ]; then
  check "Search endpoint unreachable" "fail"
else
  check "Search endpoint returns HTTP ${HTTP_CODE}" "fail"
fi

# --- 4. Chat Endpoint ---
echo -n "  Chat (/api/v1/chat)... "
HTTP_CODE=$(curl -s -o /tmp/smoke_chat.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"message":"Hello","session_id":"smoke"}' 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  check "Chat endpoint returns 200" "pass"
elif [ "$HTTP_CODE" = "000" ]; then
  check "Chat endpoint unreachable" "fail"
else
  check "Chat endpoint returns HTTP ${HTTP_CODE}" "fail"
fi

# --- 5. Auth Required (no API key) ---
echo -n "  Auth rejection (no API key)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/properties/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}' 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  check "Unauthenticated request rejected (${HTTP_CODE})" "pass"
else
  check "Unauthenticated request returned HTTP ${HTTP_CODE} (expected 401/403)" "fail"
fi

# --- 6. Security Headers ---
echo -n "  Security headers... "
HEADERS=$(curl -s -I "${BASE_URL}/health" 2>/dev/null || echo "")
SEC_PASS="true"

if echo "$HEADERS" | grep -qi "x-content-type-options"; then
  : # OK
else
  SEC_PASS="false"
fi

if echo "$HEADERS" | grep -qi "strict-transport-security\|x-frame-options"; then
  : # OK
else
  # One of these should be present
  if echo "$HEADERS" | grep -qi "content-security-policy"; then
    : # OK
  else
    SEC_PASS="false"
  fi
fi

if [ "$SEC_PASS" = "true" ]; then
  check "Security headers present" "pass"
else
  check "Security headers missing or incomplete" "fail"
fi

# --- 7. CORS Headers ---
echo -n "  CORS headers... "
CORS_HEADERS=$(curl -s -I -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  "${BASE_URL}/api/v1/properties/search" 2>/dev/null || echo "")
if echo "$CORS_HEADERS" | grep -qi "access-control-allow-origin"; then
  check "CORS headers present" "pass"
else
  check "CORS headers missing (may be OK if same-origin)" "fail"
fi

# --- 8. API Docs ---
echo -n "  OpenAPI docs (/docs)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/docs" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  check "API docs accessible" "pass"
else
  check "API docs returned HTTP ${HTTP_CODE}" "fail"
fi

# --- Summary ---
echo ""
echo "============================================"
echo -e " Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo -e "${CHECKS}"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
