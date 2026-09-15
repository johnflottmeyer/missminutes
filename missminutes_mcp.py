import os
import json
import time
import fcntl
import logging
import threading

import uvicorn

from mcp.server import MCPServer
from starlette.responses import JSONResponse


# ==========================
# LOGGING
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("miss_minutes")


# ==========================
# AUTH
# ==========================
# This server is reachable from the public internet via an ngrok
# tunnel (see start_missminutes.sh), and receive_text lets any
# caller make the physical device say arbitrary text. Require a
# shared-secret bearer token on every request so a leaked/guessed
# tunnel URL alone isn't enough to use it.
#
# Set this on the Pi before starting the server, e.g. in the shell
# profile or a .env file loaded by start_missminutes.sh:
#   export MISSMINUTES_MCP_TOKEN="<a long random string>"

MCP_AUTH_TOKEN = os.environ.get(
    "MISSMINUTES_MCP_TOKEN",
    ""
)

# Routes that stay reachable without the token - status only,
# nothing that reveals speech content or accepts input.
PUBLIC_PATHS = {
    "/health"
}


class BearerTokenMiddleware:
    """
    Minimal ASGI middleware requiring "Authorization: Bearer <token>"
    on every HTTP request except PUBLIC_PATHS.
    """

    def __init__(self, app, token):

        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):

        if (
            scope["type"] != "http"
            or scope["path"] in PUBLIC_PATHS
        ):

            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])

        auth_header = headers.get(
            b"authorization",
            b""
        ).decode()

        if auth_header != f"Bearer {self.token}":

            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401
            )

            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ==========================
# MCP SERVER
# ==========================

mcp = MCPServer("Miss Minutes MCP")


# ==========================
# PATHS
# ==========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SPEECH_QUEUE_FILE = os.path.join(
    BASE_DIR,
    "speech_queue.txt"
)

# Rotate the queue file if it grows past this size (bytes).
# Protects against unbounded growth if the consumer falls behind
# or stops draining the file.
SPEECH_QUEUE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


# ==========================
# LATEST TEXT STATE
# ==========================
# Protected by _state_lock. Two fields must always be updated
# together so a concurrent reader (the /latest-text route) never
# sees a new "text" paired with an old "id" or vice versa.

_state_lock = threading.Lock()

latest_text = {
    "id": 0,
    "text": "",
    "emotion": "neutral",
    "updated_at": None
}

# Track the last N responses (not just the last one) so exact-duplicate
# suppression only blocks true back-to-back repeats, not "said this
# a few turns ago."
_recent_texts = []
_RECENT_TEXTS_MAX = 3


# ==========================
# PING
# ==========================

@mcp.tool()
def ping() -> str:
    """
    Test the connection to the Miss Minutes Raspberry Pi.
    """

    logger.info("ping() called")

    return "Hello from the Miss Minutes Raspberry Pi"


# ==========================
# QUEUE FILE HELPERS
# ==========================

def _rotate_queue_file_if_needed() -> None:
    """
    If the speech queue file has grown past SPEECH_QUEUE_MAX_BYTES,
    archive it and start fresh. Prevents unbounded disk growth if
    nothing is draining the file.
    """

    try:

        if not os.path.exists(SPEECH_QUEUE_FILE):
            return

        size = os.path.getsize(SPEECH_QUEUE_FILE)

        if size < SPEECH_QUEUE_MAX_BYTES:
            return

        archive_path = SPEECH_QUEUE_FILE + f".{int(time.time())}.bak"

        os.replace(SPEECH_QUEUE_FILE, archive_path)

        logger.warning(
            "Speech queue exceeded %d bytes, rotated to %s",
            SPEECH_QUEUE_MAX_BYTES,
            archive_path
        )

    except Exception as error:

        logger.error("Queue rotation check failed: %s", error)


def _write_to_queue(text: str, emotion: str) -> bool:
    """
    Append a {text, emotion} entry to the speech queue file.
    Returns True on success, False on failure. Never raises.

    Written as a JSON object (not a bare string) so main.py can
    read both the words to speak and the pose to switch to from
    a single queue entry - no separate channel needed.
    """

    try:

        _rotate_queue_file_if_needed()

        entry = {
            "text": text,
            "emotion": emotion
        }

        with open(
            SPEECH_QUEUE_FILE,
            "a"
        ) as file:

            fcntl.flock(file, fcntl.LOCK_EX)

            try:
                file.write(json.dumps(entry) + "\n")
                file.flush()
                os.fsync(file.fileno())
            finally:
                fcntl.flock(file, fcntl.LOCK_UN)

        return True

    except Exception as error:

        logger.error("Speech queue write failed: %s", error)

        return False


# ==========================
# VALID EMOTIONS
# ==========================
# Must match the poses main.py knows how to switch to
# (see set_pose calls / K_1-K_4 handlers in main.py).

VALID_EMOTIONS = {
    "neutral",
    "happy",
    "angry",
    "sad"
}

DEFAULT_EMOTION = "neutral"


# ==========================
# RECEIVE TEXT
# ==========================

@mcp.tool()
def receive_text(text: str, emotion: str = DEFAULT_EMOTION) -> str:
    """
    Receive text and an emotional tone from AIPI for Miss Minutes
    to speak and display.

    emotion must be one of: neutral, happy, angry, sad.
    Invalid or missing values fall back to neutral rather than
    failing the call, so a malformed emotion never blocks speech.

    Writes {text, emotion} to the speech queue file that the
    Pygame display process (main.py) polls, so it gets spoken,
    animated, and posed - not just logged.
    """

    clean_text = (text or "").strip()

    clean_emotion = (emotion or "").strip().lower()

    if clean_emotion not in VALID_EMOTIONS:

        if clean_emotion:

            logger.warning(
                "Unknown emotion '%s', defaulting to '%s'",
                clean_emotion,
                DEFAULT_EMOTION
            )

        clean_emotion = DEFAULT_EMOTION

    # ==========================
    # IGNORE EMPTY RESPONSES
    # ==========================

    if not clean_text:

        logger.warning("Empty text ignored")

        return "Empty text ignored"

    # ==========================
    # IGNORE EXACT BACK-TO-BACK DUPLICATES
    # ==========================
    # Only blocks true immediate repeats (last N), not the same
    # phrase said a few turns earlier. Compares text only - the
    # same line said with a different emotion is not a duplicate.

    with _state_lock:

        if _recent_texts and clean_text == _recent_texts[-1]:

            logger.info("Duplicate text ignored: %s", clean_text)

            return "Duplicate text ignored"

        # ==========================
        # UPDATE LATEST TEXT (atomic w.r.t. readers)
        # ==========================

        latest_text["id"] += 1
        latest_text["text"] = clean_text
        latest_text["emotion"] = clean_emotion
        latest_text["updated_at"] = time.time()

        _recent_texts.append(clean_text)

        if len(_recent_texts) > _RECENT_TEXTS_MAX:
            _recent_texts.pop(0)

        new_id = latest_text["id"]

    logger.info(
        "AIPI TEXT #%d [%s]: %s",
        new_id,
        clean_emotion,
        clean_text
    )

    # ==========================
    # ADD TO SPEECH QUEUE
    # ==========================

    wrote_ok = _write_to_queue(clean_text, clean_emotion)

    if not wrote_ok:

        # latest_text has already advanced (so /latest-text reflects
        # what SHOULD be spoken), but the persisted queue is missing
        # this entry. Surface that clearly to the caller rather than
        # returning a generic success message.
        return (
            "Text received but failed to queue for display - "
            "it may not be spoken aloud"
        )

    logger.info("Queued text #%d for Miss Minutes display", new_id)

    return "Text received by Miss Minutes display"


# ==========================
# LATEST TEXT ROUTE
# ==========================

@mcp.custom_route(
    "/latest-text",
    methods=["GET"]
)
async def latest_text_route(request):

    with _state_lock:
        snapshot = dict(latest_text)

    return JSONResponse(
        snapshot,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store"
        }
    )


# ==========================
# HEALTH CHECK ROUTE
# ==========================

@mcp.custom_route(
    "/health",
    methods=["GET"]
)
async def health_route(request):

    queue_exists = os.path.exists(SPEECH_QUEUE_FILE)
    queue_size = (
        os.path.getsize(SPEECH_QUEUE_FILE) if queue_exists else 0
    )

    return JSONResponse(
        {
            "status": "ok",
            "queue_file_exists": queue_exists,
            "queue_file_bytes": queue_size
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store"
        }
    )


# ==========================
# START SERVER
# ==========================

if __name__ == "__main__":

    if not MCP_AUTH_TOKEN:

        raise SystemExit(
            "MISSMINUTES_MCP_TOKEN is not set. Refusing to start: this "
            "server is exposed publicly via ngrok, and receive_text would "
            "let anyone with the tunnel URL make the physical device speak "
            "arbitrary text. Set MISSMINUTES_MCP_TOKEN to a long random "
            "string before starting."
        )

    app = mcp.streamable_http_app(
        host="0.0.0.0"
    )

    app = BearerTokenMiddleware(
        app,
        MCP_AUTH_TOKEN
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
