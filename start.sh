#!/usr/bin/env bash
# =============================================================================
# ThoughtLens — Universal Startup Script
# Works on: Linux, macOS, Windows (Git Bash / WSL)
# Run from anywhere: bash start.sh  OR  ./start.sh
# =============================================================================

set -euo pipefail

# ── Locate repo root ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ────────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; BOLD=''; NC=''
fi

# ── OS detection ──────────────────────────────────────────────────────────────
OS="linux"
case "$(uname -s 2>/dev/null)" in
    Darwin*)             OS="mac"     ;;
    MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
    *)
        grep -qi microsoft /proc/version 2>/dev/null && OS="wsl" || true
        ;;
esac

# ── Find Lobster Trap binary (check parent directory too) ─────────────────────
LT_BIN=""
for candidate in \
    "./lobstertrap/lobstertrap" \
    "./lobstertrap/lobstertrap.exe" \
    "../lobstertrap/lobstertrap" \
    "../lobstertrap/lobstertrap.exe" \
    "$(command -v lobstertrap 2>/dev/null || true)"
do
    if [ -n "$candidate" ] && [ -f "$candidate" ] && [ -x "$candidate" ]; then
        LT_BIN="$candidate"
        break
    fi
done

# ── Find Python ───────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3.11 python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

# ── Open browser helper ───────────────────────────────────────────────────────
open_browser() {
    case "$OS" in
        mac)             open "$1" 2>/dev/null || true ;;
        windows|wsl)     cmd.exe /c start "$1" 2>/dev/null || true ;;
        *)               xdg-open "$1" 2>/dev/null || true ;;
    esac
}

# ── Read .env value helper ────────────────────────────────────────────────────
env_val() {
    local key="$1" default="${2:-}"
    local val
    val=$(grep -E "^${key}=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
    echo "${val:-$default}"
}

# ── Cleanup on Ctrl+C ─────────────────────────────────────────────────────────
PIDS=()
cleanup() {
    echo ""
    echo -e "${RED}  Shutting down ThoughtLens...${NC}"
    for pid in "${PIDS[@]:-}"; do
        kill "$pid" 2>/dev/null || true
    done
    echo -e "${GREEN}  Done.${NC}"
    exit 0
}
trap cleanup INT TERM

# ─────────────────────────────────────────────────────────────────────────────
clear

echo -e "${CYAN}${BOLD}"
echo "   ######## ##     ## ########  ##     ##  ######   ##     ## ######## "
echo "       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##    "
echo "       ##    ##     ## ##     ## ##     ## ##        ##     ##    ##    "
echo "       ##    ######### ##     ## ##     ## ##   #### #########    ##    "
echo "       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##    "
echo "       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##    "
echo "       ##    ##     ##  #######   #######   ######   ##     ##    ##    "
echo ""
echo "        ##       ######## ##    ##  ######  "
echo "        ##       ##       ###   ## ##    ## "
echo "        ##       ##       ####  ## ##       "
echo "        ##       ######   ## ## ##  ######  "
echo "        ##       ##       ##  ####       ## "
echo "        ##       ##       ##   ### ##    ## "
echo "        ######## ########  ##    ##  ######  "
echo -e "${NC}"
echo -e "  ${CYAN}         L I V E   A G E N T   F O R E N S I C S${NC}"
echo ""
echo -e "  ${YELLOW}v0.1.0  -  Agent Security and AI Governance  -  OS: ${OS}${NC}"
echo ""
echo "  --------------------------------------------------------------------------"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────────────
ERRORS=0

if [ ! -f ".env" ]; then
    echo -e "${RED}  [ERROR] .env not found.${NC}"
    echo -e "          Copy .env.example to .env and add your API keys."
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$PYTHON" ]; then
    echo -e "${RED}  [ERROR] Python 3.11+ not found.${NC}"
    echo -e "          Install from https://python.org"
    ERRORS=$((ERRORS + 1))
fi

if ! command -v npm &>/dev/null; then
    echo -e "${RED}  [ERROR] npm not found.${NC}"
    echo -e "          Install Node.js from https://nodejs.org"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -ne 0 ]; then
    echo ""
    echo -e "${RED}  Fix the above and re-run.${NC}"
    exit 1
fi

# Auto-install UI deps if missing
if [ ! -d "ui/node_modules" ]; then
    echo -e "${YELLOW}  Installing UI dependencies (first run)...${NC}"
    cd ui && npm install --silent && cd ..
    echo -e "${GREEN}  + UI dependencies ready${NC}"
    echo ""
fi

# ── Read config from .env ─────────────────────────────────────────────────────
TL_PORT=$(env_val "TL_PORT" "8000")
LT_PORT=$(env_val "TL_LT_PORT" "8080")
LLM_URL=$(env_val "TL_LLM_URL" "https://api.groq.com/openai/v1")
LT_POLICY=$(env_val "TL_LT_POLICY" "./configs/thoughtlens_policy.yaml")

# ── 1. Lobster Trap ───────────────────────────────────────────────────────────
echo -e "${GREEN}  [1/3] Lobster Trap${NC}"
if [ -n "$LT_BIN" ]; then
    # Change to lobstertrap directory if binary is in parent
    LT_DIR=$(dirname "$LT_BIN")
    if [[ "$LT_BIN" == *"../"* ]]; then
        (cd "$LT_DIR" && ./$(basename "$LT_BIN") serve --listen ":${LT_PORT}" --backend "${LLM_URL}" --policy "${LT_POLICY}") 2>/dev/null &
    else
        "$LT_BIN" serve --listen ":${LT_PORT}" --backend "${LLM_URL}" --policy "${LT_POLICY}" 2>/dev/null &
    fi
    PIDS+=($!)
    sleep 2
    echo -e "${GREEN}        + running on :${LT_PORT}  (${LT_BIN})${NC}"
else
    echo -e "${YELLOW}        + binary not found - DPI layer disabled${NC}"
    echo -e "${YELLOW}          pre-execution scanner + runtime detector still active${NC}"
fi
echo ""

# ── 2. ThoughtLens backend ────────────────────────────────────────────────────
echo -e "${GREEN}  [2/3] ThoughtLens backend${NC}"
"$PYTHON" main.py &
PIDS+=($!)
sleep 3
echo -e "${GREEN}        + running on :${TL_PORT}${NC}"
echo ""

# ── 3. React UI ───────────────────────────────────────────────────────────────
echo -e "${GREEN}  [3/3] React UI${NC}"
cd ui && npm run dev --silent & PIDS+=($!) && cd ..
sleep 4
echo -e "${GREEN}        + running on :3000${NC}"
echo ""

# ── Ready ─────────────────────────────────────────────────────────────────────
echo "  --------------------------------------------------------------------------"
echo ""
echo -e "  ${BOLD}ThoughtLens is ready.${NC}"
echo ""
echo -e "  ${CYAN}  Dashboard ->  http://localhost:3000${NC}"
echo -e "  ${CYAN}  API       ->  http://localhost:${TL_PORT}${NC}"
echo -e "  ${CYAN}  Docs      ->  http://localhost:${TL_PORT}/docs${NC}"
echo ""
echo -e "  ${BOLD}  Run the agent:${NC}"
echo -e "  ${YELLOW}    python demo/interactive_agent.py${NC}"
echo ""
echo "  --------------------------------------------------------------------------"
echo -e "  ${RED}  Ctrl+C to stop all services.${NC}"
echo ""

# Open browser
(sleep 2 && open_browser "http://localhost:3000") &

# Hold until Ctrl+C
wait