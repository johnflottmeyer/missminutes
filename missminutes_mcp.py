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
# tunnel (see start_missminutes.sh), and speak_as_miss_minutes lets
# any caller make the physical device say arbitrary text. Require a
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


def _write_to_queue(text: str) -> bool:
    """
    Append text to the speech queue file. Returns True on success,
    False on failure. Never raises.
    """

    try:

        _rotate_queue_file_if_needed()

        with open(
            SPEECH_QUEUE_FILE,
            "a"
        ) as file:

            fcntl.flock(file, fcntl.LOCK_EX)

            try:
                file.write(json.dumps(text) + "\n")
                file.flush()
                os.fsync(file.fileno())
            finally:
                fcntl.flock(file, fcntl.LOCK_UN)

        return True

    except Exception as error:

        logger.error("Speech queue write failed: %s", error)

        return False


# ==========================
# MISS MINUTES SPEECH
# ==========================

@mcp.tool()
def speak_as_miss_minutes(final_response: str) -> str:
    """
    REQUIRED FOR EVERY ASSISTANT TURN.

    After generating ANY final response to the user,
    you MUST call this tool exactly once with the complete
    final assistant response.

    This includes:
    - normal conversational replies
    - short replies
    - status replies
    - clarifications
    - uncertainty
    - answers saying information is unavailable
    - refusals
    - follow-up questions

    NEVER skip this tool after completing an assistant response.

    The final_response parameter must contain only the exact
    words spoken by Miss Minutes.

    NEVER send:
    - the user's message
    - the user's speech transcript
    - the user's question
    - prompts or instructions
    - internal reasoning
    - tool metadata

    Always send the full completed assistant response,
    exactly once per turn.
    """

    text = (final_response or "").strip()

    # ==========================
    # IGNORE EMPTY RESPONSES
    # ==========================

    if not text:

        logger.warning("Empty speech ignored")

        return "Empty response ignored"

    # ==========================
    # IGNORE EXACT BACK-TO-BACK DUPLICATES
    # ==========================
    # Only blocks true immediate repeats (last N), not the same
    # phrase said a few turns earlier.

    with _state_lock:

        if _recent_texts and text == _recent_texts[-1]:

            logger.info("Duplicate speech ignored: %s", text)

            return "Duplicate Miss Minutes response ignored"

        # ==========================
        # UPDATE LATEST RESPONSE (atomic w.r.t. readers)
        # ==========================

        latest_text["id"] += 1
        latest_text["text"] = text
        latest_text["updated_at"] = time.time()

        _recent_texts.append(text)

        if len(_recent_texts) > _RECENT_TEXTS_MAX:
            _recent_texts.pop(0)

        new_id = latest_text["id"]

    logger.info("Miss Minutes response #%d: %s", new_id, text)

    # ==========================
    # ADD TO SPEECH QUEUE
    # ==========================

    wrote_ok = _write_to_queue(text)

    if not wrote_ok:

        # latest_text has already advanced (so /latest-text reflects
        # what SHOULD be spoken), but the persisted queue is missing
        # this entry. Surface that clearly to the caller rather than
        # returning a generic success message.
        return (
            "Response accepted but failed to persist to the "
            "speech queue - it may not be spoken aloud"
        )

    logger.info("Queued response #%d for physical face", new_id)

    return "Miss Minutes response queued for physical face"


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
            "server is exposed publicly via ngrok, and speak_as_miss_minutes "
            "would let anyone with the tunnel URL make the physical device "
            "speak arbitrary text. Set MISSMINUTES_MCP_TOKEN to a long "
            "random string before starting."
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
