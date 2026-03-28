#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colours ───────────────────────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; C='\033[0;36m'; Y='\033[1;33m'
BOLD='\033[1m'; RESET='\033[0m'

section() { echo -e "\n${BOLD}${C}── $1${RESET}"; }
ok()      { echo -e "  ${G}✓${RESET}  $1"; }
warn()    { echo -e "  ${Y}⚠${RESET}  $1"; }
die()     { echo -e "  ${R}✗${RESET}  $1"; exit 1; }

echo -e "\n${BOLD}${C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${C}  LIPS IDE${RESET}"
echo -e "${BOLD}${C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ── Prerequisite checks ───────────────────────────────────────────────────────
section "Checking prerequisites"

# Python 3.11+
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    ver=$($cmd -c 'import sys; print(1 if sys.version_info >= (3, 11) else 0)' 2>/dev/null || echo 0)
    if [ "$ver" -eq 1 ]; then
      PYTHON="$cmd"
      ok "Python $($cmd --version 2>&1)"
      break
    fi
  fi
done
[ -z "$PYTHON" ] && die "Python 3.11+ required — https://python.org"

# Node 18+
command -v node &>/dev/null || die "Node.js 18+ required — https://nodejs.org"
NODE_MAJOR=$(node -e "process.stdout.write(process.version.slice(1).split('.')[0])")
[ "$NODE_MAJOR" -ge 18 ] || die "Node.js 18+ required (found $(node --version))"
ok "Node.js $(node --version)"

command -v npm &>/dev/null || die "npm required (ships with Node.js)"
ok "npm $(npm --version)"

# LIPS package (vendored at lips-ide/lips/)
if PYTHONPATH="$SCRIPT_DIR" $PYTHON -c "import lips" 2>/dev/null; then
  ok "LIPS package found"
else
  warn "LIPS package not found — pipeline stages will fail."
fi

# Export PYTHONPATH so uvicorn and its child processes inherit it
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# ── Backend ───────────────────────────────────────────────────────────────────
section "Starting backend"
cd "$SCRIPT_DIR/backend"

$PYTHON -m pip install -r requirements.txt -q --disable-pip-version-check
ok "Python dependencies ready"

$PYTHON -m uvicorn main:app --reload --port 8000 --log-level warning &
BACKEND_PID=$!
ok "FastAPI server started (PID $BACKEND_PID)"

# Poll until the API responds (up to 15 s)
echo -n "  Waiting for backend"
READY=0
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/templates > /dev/null 2>&1; then
    READY=1; break
  fi
  printf '.'
  sleep 0.5
done
if [ "$READY" -eq 1 ]; then
  echo -e "\r  ${G}✓${RESET}  Backend ready                                    "
else
  echo -e "\r  ${Y}⚠${RESET}  Backend health-check timed out (may still be starting)"
fi

# ── Frontend ──────────────────────────────────────────────────────────────────
section "Starting frontend"
cd "$SCRIPT_DIR/frontend"

npm install --silent
ok "Node dependencies ready"

npm run dev &
FRONTEND_PID=$!
ok "Vite dev server started (PID $FRONTEND_PID)"

# ── Ready ─────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}${C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${BOLD}Frontend${RESET} → ${C}http://localhost:5173${RESET}  ← open this"
echo -e "  ${BOLD}Backend${RESET}  → ${C}http://localhost:8000${RESET}"
echo -e "${BOLD}${C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop both servers.\n"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo -e "\n${Y}Stopping servers…${RESET}"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo -e "${G}Done.${RESET}"
  exit 0
}
trap cleanup INT TERM

wait
