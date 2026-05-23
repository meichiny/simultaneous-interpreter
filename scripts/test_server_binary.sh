#!/bin/bash
# Test: PyInstaller binary should serve HTTP successfully
# RED phase: should fail (server crashes due to allow_unsafe_werkzeug=debug)
# GREEN phase: should pass (HTTP 200)

set -e

BINARY="electron/resources/server/server"
PORT=5004
TIMEOUT=15

echo "=== Test: PyInstaller binary HTTP server ==="
echo "Binary: $BINARY"

if [ ! -f "$BINARY" ]; then
    echo "FAIL: Binary not found at $BINARY"
    exit 1
fi

# Clear any stale server process and wait for port release
pkill -f "$BINARY" 2>/dev/null || true
for i in $(seq 1 15); do
    if ! lsof -i :"$PORT" > /dev/null 2>&1; then
        break
    fi
    echo "Waiting for port $PORT (TIME_WAIT) ... ${i}s"
    sleep 1
done

"$BINARY" &
PID=$!
echo "PID: $PID"

# Poll for HTTP 200 with timeout
for i in $(seq 1 "$TIMEOUT"); do
    sleep 1
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" 2>&1 || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "HTTP 200 after ${i}s"
        break
    fi
    echo "t=${i}s: HTTP $HTTP_CODE"
done

echo "Final HTTP response code: $HTTP_CODE"

kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

if [ "$HTTP_CODE" = "200" ]; then
    echo "PASS: Server responded with HTTP $HTTP_CODE"
    exit 0
else
    echo "FAIL: Server did not respond (HTTP $HTTP_CODE)"
    exit 1
fi
