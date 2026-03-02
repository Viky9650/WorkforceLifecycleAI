#!/usr/bin/env bash
set -euo pipefail

PORTS="3000 9000 9001"

echo "Stopping dev processes..."
echo "--------------------------------"

kill_port() {
  port="$1"

  # Get PIDs listening on this port
  pids=$(lsof -nP -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)

  if [ -z "$pids" ]; then
    echo "Port $port: nothing running"
    return 0
  fi

  echo "Port $port: found PIDs $pids"

  # Graceful kill
  kill $pids 2>/dev/null || true

  # Wait briefly
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.3
    still=$(lsof -nP -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)
    if [ -z "$still" ]; then
      echo "Port $port: stopped cleanly"
      return 0
    fi
  done

  # Force kill if still alive
  echo "Port $port: force killing"
  kill -9 $pids 2>/dev/null || true
}

# Kill by ports
for p in $PORTS; do
  kill_port "$p"
done

echo "--------------------------------"
echo "Cleaning up stray dev processes..."

pkill -f "uvicorn .*--port 9000" 2>/dev/null || true
pkill -f "uvicorn .*--port 9001" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "--------------------------------"
echo "Verifying ports..."

verify_failed=0

for p in $PORTS; do
  if lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
    echo "❌ Port $p is STILL in use"
    lsof -nP -iTCP:$p -sTCP:LISTEN
    verify_failed=1
  else
    echo "✅ Port $p is free"
  fi
done

echo "--------------------------------"

if [ "$verify_failed" -eq 0 ]; then
  echo "All dev ports are clean."
else
  echo "Some ports are still occupied."
fi

echo "Done."
