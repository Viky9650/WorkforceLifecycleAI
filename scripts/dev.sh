#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_PORT="${API_PORT:-9000}"
MCP_PORT="${MCP_PORT:-9001}"
FE_PORT="${FE_PORT:-3000}"

mkdir -p "$ROOT_DIR/store/logs"

# Clean before starting (so ports are always free)
if [[ -x "$ROOT_DIR/scripts/kill.sh" ]]; then
  echo "🧹 Pre-clean: freeing dev ports..."
  bash "$ROOT_DIR/scripts/kill.sh" >/dev/null 2>&1 || true
fi

# Activate venv
if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
else
  echo "ERROR: .venv not found at $ROOT_DIR/.venv"
  exit 1
fi

MCP_PID=""
API_PID=""
FE_PID=""

kill_tree() {
  # Best-effort: kill process group if possible, else kill pid
  pid="$1"
  [[ -z "${pid:-}" ]] && return 0

  # Kill the whole group (works well when the process is its own group leader)
  kill -TERM "-$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
  echo ""
  echo "Stopping..."

  kill_tree "$MCP_PID"
  kill_tree "$API_PID"
  kill_tree "$FE_PID"

  # Give them a moment
  sleep 0.5

  # Safety net: ensure ports are free + stragglers removed
  if [[ -x "$ROOT_DIR/scripts/kill.sh" ]]; then
    bash "$ROOT_DIR/scripts/kill.sh" || true
  fi

  exit 0
}

trap cleanup INT TERM

# Start MCP server
echo "[1/3] Starting MCP server on :$MCP_PORT"
PYTHONPATH=. python -m uvicorn mcp_server.main:app --reload --port "$MCP_PORT" \
  > "$ROOT_DIR/store/logs/mcp.log" 2>&1 &
MCP_PID=$!

# Start API server
echo "[2/3] Starting API server on :$API_PORT"
PYTHONPATH=. python -m uvicorn api.main:app --reload --port "$API_PORT" \
  > "$ROOT_DIR/store/logs/api.log" 2>&1 &
API_PID=$!

# Start Frontend
echo "[3/3] Starting Frontend on :$FE_PORT"
( cd "$ROOT_DIR/frontend" && npm run dev ) \
  > "$ROOT_DIR/store/logs/frontend.log" 2>&1 &
FE_PID=$!

echo ""
echo "✅ Running:"
echo "  MCP      http://127.0.0.1:$MCP_PORT/docs"
echo "  API      http://127.0.0.1:$API_PORT/docs"
echo "  Frontend http://127.0.0.1:$FE_PORT"
echo ""
echo "Logs:"
echo "  store/logs/mcp.log"
echo "  store/logs/api.log"
echo "  store/logs/frontend.log"
echo ""
echo "Press Ctrl+C to stop."

# Wait until one exits; then cleanup the rest
# macOS bash 3.2 doesn't support `wait -n`, so just wait on all:
wait