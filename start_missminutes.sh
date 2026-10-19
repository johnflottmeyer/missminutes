#!/bin/bash

# ============================================================
# Miss Minutes Startup
# ============================================================

PROJECT_DIR="/home/mminutes/missminutes"

# The MCP server runs in its own venv (.venv-mcp) built from
# requirements-mcp.txt. On Raspberry Pi OS Lite 64-bit the system
# Python is new enough (>= 3.10), so the venv is created directly:
#   python3 -m venv .venv-mcp
#   .venv-mcp/bin/pip install -r requirements-mcp.txt
VENV_MCP="$PROJECT_DIR/.venv-mcp"

# The display process (main.py) needs pygame, which is installed
# for the system Python (apt: python3-pygame). Pin this to the
# system interpreter explicitly so an active .venv-mcp in the
# calling shell can never make "python3" resolve to the venv,
# which has no pygame.
SYSTEM_PYTHON="/usr/bin/python3"

# Force Python's UTF-8 mode (PEP 540) for every process this
# script launches. AIPI-generated text routinely contains
# characters outside latin-1 (curly quotes, em dashes), which
# breaks printing, log writes and subprocess arguments if the
# locale's default encoding isn't UTF-8.
export PYTHONUTF8=1
export SDL_AUDIODRIVER=dummy

LOG_DIR="$PROJECT_DIR/logs"

MCP_PORT=8000

mkdir -p "$LOG_DIR"

# ============================================================
# LOAD SECRETS (MISSMINUTES_MCP_TOKEN, etc.)
# ============================================================
# Keeps the shared auth token for the MCP server out of this
# script (and out of git). Create "$PROJECT_DIR/.env" on the Pi
# with a line like: export MISSMINUTES_MCP_TOKEN="<long random string>"

if [ -f "$PROJECT_DIR/.env" ]
then
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
fi

echo ""
echo "======================================"
echo " Starting Miss Minutes"
echo "======================================"
echo ""


# ============================================================
# 1. START MCP SERVER
# ============================================================

if pgrep -f "missminutes_mcp.py" > /dev/null
then

    echo "[OK] MCP server already running"

else

    echo "[START] MCP server on port $MCP_PORT"

    cd "$PROJECT_DIR" || exit 1

    if [ ! -x "$VENV_MCP/bin/python" ]
    then
        echo "[ERROR] $VENV_MCP not found - see requirements-mcp.txt" \
            "for the one-time venv setup"
    else
        nohup "$VENV_MCP/bin/python" \
            missminutes_mcp.py \
            > "$LOG_DIR/mcp.log" 2>&1 &

        sleep 2
    fi

fi


# ============================================================
# 2. START NGROK
# ============================================================

if pgrep -f "ngrok.*$MCP_PORT" > /dev/null
then

    echo "[OK] ngrok already running"

else

    echo "[START] ngrok for MCP port $MCP_PORT"

    nohup ngrok http "$MCP_PORT" \
        > "$LOG_DIR/ngrok.log" 2>&1 &

    sleep 2

fi


# ============================================================
# 3. START PYGAME MISS MINUTES
# ============================================================
# Raspberry Pi OS Lite has no desktop, so xinit starts a bare X
# server on :0 that runs only main.py (no window manager, no
# cursor). Direct kmsdrm and cage/Wayland both hung on this Pi 3B;
# plain X works. Needs /etc/X11/Xwrapper.config with:
#   allowed_users=anybody
#   needs_root_rights=yes
# so X can start without sudo.

if pgrep -f "python3.*main.py" > /dev/null
then

    echo "[OK] Miss Minutes display already running"

else

    echo "[START] Miss Minutes Pygame on display :0"

    cd "$PROJECT_DIR" || exit 1

    nohup xinit "$SYSTEM_PYTHON" "$PROJECT_DIR/main.py" \
        -- :0 -nocursor \
        > "$LOG_DIR/pygame.log" 2>&1 &

    sleep 2

fi


# ============================================================
# STATUS
# ============================================================

echo ""
echo "======================================"
echo " Miss Minutes started"
echo "======================================"
echo ""

echo "Pygame display : :0 (xinit)"
echo "MCP port       : $MCP_PORT"

echo ""
echo "Logs:"
echo "  $LOG_DIR"
echo ""
echo "  pygame.log"
echo "  mcp.log"
echo "  ngrok.log"
echo ""