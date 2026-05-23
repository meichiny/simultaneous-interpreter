#!/bin/bash
# Test: Flask server CORS headers for data: URI cross-origin requests
# RED:  should fail (no CORS headers → browser blocks fetch)
# GREEN: should pass (Access-Control-Allow-Origin: *)

set -e

SERVER_URL="http://127.0.0.1:5004"
TIMEOUT=10

start_server() {
    "$1" &
    PID=$!
    for i in $(seq 1 "$TIMEOUT"); do
        sleep 1
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/" 2>&1 || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then return 0; fi
    done
    echo "FAIL: Server did not start"
    kill "$PID" 2>/dev/null || true
    exit 1
}

PYTHON=".venv/bin/python3"
BINARY="electron/resources/server/server"

echo "=== CORS Test ==="

# Start server (prefer binary, fallback to venv python)
if [ -f "$BINARY" ]; then
    start_server "$BINARY"
    echo "Using binary"
else
    start_server "$PYTHON" "wsgi.py"
    echo "Using python"
fi

echo "PID: $PID"

# Test 1: OPTIONS preflight with Origin: null
echo ""
echo "--- Test 1: OPTIONS preflight from Origin: null ---"
OPTIONS_HEADERS=$(curl -s -D - -o /dev/null \
  -X OPTIONS \
  -H "Origin: null" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  "$SERVER_URL/api/save_env" 2>&1)
echo "$OPTIONS_HEADERS"

# Check for CORS headers
if echo "$OPTIONS_HEADERS" | grep -qi "access-control-allow-origin"; then
    echo "PASS: Access-Control-Allow-Origin header found"
    CORS_OK=1
else
    echo "FAIL: Access-Control-Allow-Origin header missing"
    CORS_OK=0
fi

# Test 2: Actual POST from Origin: null
echo ""
echo "--- Test 2: POST from Origin: null ---"
POST_RESULT=$(curl -s -D - \
  -X POST \
  -H "Origin: null" \
  -H "Content-Type: application/json" \
  -d '{"app_key":"test_key","access_key":"test_secret"}' \
  "$SERVER_URL/api/save_env" 2>&1)
echo "$POST_RESULT"

# Check for CORS headers in POST response
if echo "$POST_RESULT" | grep -qi "access-control-allow-origin"; then
    echo "PASS: CORS headers present in POST response"
    POST_CORS_OK=1
else
    echo "FAIL: CORS headers missing in POST response"
    POST_CORS_OK=0
fi

# Check POST success
if echo "$POST_RESULT" | grep -q '"success":true'; then
    echo "PASS: POST returned success"
    POST_OK=1
else
    echo "FAIL: POST did not return success"
    POST_OK=0
fi

# Cleanup
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

# Summary
echo ""
echo "=== Results ==="
echo "CORS preflight: $([ $CORS_OK -eq 1 ] && echo 'PASS' || echo 'FAIL')"
echo "CORS on POST:   $([ $POST_CORS_OK -eq 1 ] && echo 'PASS' || echo 'FAIL')"
echo "POST success:   $([ $POST_OK -eq 1 ] && echo 'PASS' || echo 'FAIL')"

if [ "$CORS_OK" -eq 1 ] && [ "$POST_CORS_OK" -eq 1 ] && [ "$POST_OK" -eq 1 ]; then
    echo ""
    echo "=== ALL TESTS PASSED ==="
    exit 0
else
    echo ""
    echo "=== SOME TESTS FAILED ==="
    exit 1
fi
