#!/bin/bash

# ============================================================
# Miss Minutes Startup
# ============================================================

PROJECT_DIR="/home/mminutes/missminutes"
VENV="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"

MCP_PORT=8000

VNC_DISPLAY=":1"
VNC_GEOMETRY="1920x1080"

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
# 1. START VNC
# ============================================================

if pgrep -f "Xvnc.*:1" > /dev/null
then

    echo "[OK] VNC :1 already running"

else

    echo "[START] VNC virtual desktop :1"

    vncserver-virtual "$VNC_DISPLAY" \
        -geometry "$VNC_GEOMETRY" \
        > "$LOG_DIR/vnc.log" 2>&1 &

    sleep 3

fi


# ============================================================
# 2. START MCP SERVER
# ============================================================

if pgrep -f "missminutes_mcp.py" > /dev/null
then

    echo "[OK] MCP server already running"

else

    echo "[START] MCP server on port $MCP_PORT"

    cd "$PROJECT_DIR" || exit 1

    nohup "$VENV/bin/python" \
        missminutes_mcp.py \
        > "$LOG_DIR/mcp.log" 2>&1 &

    sleep 2

fi


# ============================================================
# 3. START NGROK
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
# 4. START PYGAME MISS MINUTES
# ============================================================

if pgrep -f "python3.*main.py" > /dev/null
then

    echo "[OK] Miss Minutes display already running"

else

    echo "[START] Miss Minutes Pygame on display :0"

    cd "$PROJECT_DIR" || exit 1

    DISPLAY=:0 nohup python3 main.py \
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

echo "Pygame display : :0"
echo "MCP port       : $MCP_PORT"
echo "VNC desktop    : $VNC_DISPLAY $VNC_GEOMETRY"

echo ""
echo "Logs:"
echo "  $LOG_DIR"
echo ""
echo "  pygame.log"
echo "  mcp.log"
echo "  ngrok.log"
echo "  vnc.log"
echo ""