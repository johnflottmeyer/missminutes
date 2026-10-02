import os
import re
import json
import time
import fcntl
import logging
import threading

import uvicorn

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
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


# ==========================
# TRANSPORT SECURITY (DNS REBINDING PROTECTION)
# ==========================
# FastMCP validates the Host/Origin headers on every MCP request to
# guard against DNS rebinding attacks. If you construct FastMCP()
# without an explicit host=, it assumes "127.0.0.1" and locks
# allowed_hosts down to localhost only - which rejects every request
# that arrives through the ngrok tunnel with a 421, even though
# BearerTokenMiddleware above already requires a valid token.
#
# Set MISSMINUTES_PUBLIC_HOST to the ngrok hostname (just the host,
# no scheme - e.g. "your-name.ngrok-free.dev") in .env so requests
# through the tunnel are allowed too. Local/direct requests to
# 127.0.0.1/localhost keep working either way.

PUBLIC_HOST = os.environ.get(
    "MISSMINUTES_PUBLIC_HOST",
    ""
).strip()

_ALLOWED_HOSTS = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "smoked-usher-poster.ngrok-free.dev",
]

_ALLOWED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*"
]

if PUBLIC_HOST:

    _ALLOWED_HOSTS.append(PUBLIC_HOST)
    _ALLOWED_ORIGINS.append(f"https://{PUBLIC_HOST}")

else:

    logger.warning(
        "MISSMINUTES_PUBLIC_HOST is not set - requests arriving "
        "through the ngrok tunnel will be rejected with a 421 "
        "Misdirected Request. Set it to your ngrok hostname (e.g. "
        "your-name.ngrok-free.dev) in .env."
    )


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
# FastMCP is the real class the installed `mcp` package exports for
# this (mcp.server.fastmcp.FastMCP) - there is no `MCPServer` class
# in mcp.server (that name only exists in the mcp 2.x line, which
# this project is pinned below - see requirements-mcp.txt). It's
# what supplies .tool(), .custom_route() and .streamable_http_app()
# below.
#
# transport_security is passed explicitly here (see above) so
# requests through the ngrok tunnel aren't rejected with a 421 -
# leaving this unset would make FastMCP assume localhost-only.

mcp = FastMCP(
    "Miss Minutes MCP",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_ALLOWED_HOSTS,
        allowed_origins=_ALLOWED_ORIGINS
    )
)


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
# ECHO GUARD
# ==========================
# AIPI's mic can hear Miss Minutes' speaker. When it does, AIPI
# treats her voice as the user talking and replies to it - she then
# speaks that reply, AIPI hears it, and the two loop, "answering
# herself."
#
# main.py writes speech_status.json whenever audio starts/stops. Any
# reply that arrives while she is talking, or within
# ECHO_GUARD_SECONDS after she stops, is very likely AIPI answering
# her own voice, so it is dropped instead of spoken. Not speaking it
# is what breaks the loop.
#
# A real user reply takes longer than this to arrive (the user has
# to speak, then AIPI has to think), so it gets through. Raise this
# if loops still slip through; lower it if your real replies get
# dropped. 0 turns the guard off.

ECHO_GUARD_SECONDS = 2.5

SPEECH_STATUS_FILE = os.path.join(
    BASE_DIR,
    "speech_status.json"
)


def _probably_echo():
    """
    True if Miss Minutes is speaking now or stopped within
    ECHO_GUARD_SECONDS. Missing/unreadable status = not an echo, so
    a problem with the status file can never block real replies.
    """

    if ECHO_GUARD_SECONDS <= 0:
        return False

    try:

        with open(SPEECH_STATUS_FILE) as file:
            status = json.load(file)

    except Exception:

        return False

    if status.get("speaking"):
        return True

    updated_at = status.get("updated_at") or 0

    return (time.time() - updated_at) < ECHO_GUARD_SECONDS


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
# REPLY LENGTH LIMIT
# ==========================
# Two layers keep Miss Minutes from reading out paragraphs:
#
#   1. The receive_text tool description asks AIPI for 1-2 short
#      sentences. That's what usually keeps replies short, and it
#      keeps AIPI's own on-screen reply short too.
#   2. This hard cap is the safety net when AIPI ignores that: only
#      the first MAX_SPEECH_SENTENCES sentences are spoken, and never
#      more than MAX_SPEECH_CHARS characters. Cuts land on a sentence
#      end (or a word break if one sentence is huge), never mid-word.
#
# Set either to 0 to disable that limit.

MAX_SPEECH_SENTENCES = 2
MAX_SPEECH_CHARS = 220

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _limit_length(text: str) -> str:
    """
    Returns text cut down to the configured sentence/character
    limits, ending on a sentence boundary wherever possible.
    """

    sentences = []

    for part in _SENTENCE_END.split(text):

        part = part.strip()

        if not part:
            continue

        # A tiny exclamation like "Blue!" or "Oh!" rides along with
        # the next sentence instead of using up one of the allowed
        # sentences on its own.
        if sentences and len(sentences[-1]) < 12:
            sentences[-1] = sentences[-1] + " " + part
        else:
            sentences.append(part)

    if MAX_SPEECH_SENTENCES > 0:
        sentences = sentences[:MAX_SPEECH_SENTENCES]

    if MAX_SPEECH_CHARS > 0:

        kept = []
        length = 0

        for sentence in sentences:

            added = len(sentence) + (1 if kept else 0)

            if length + added > MAX_SPEECH_CHARS:
                break

            kept.append(sentence)
            length += added

        if not kept and sentences:

            # The very first sentence alone is over the limit - cut
            # it at the last word break that fits.
            first = sentences[0][:MAX_SPEECH_CHARS]
            cut = first.rfind(" ")

            if cut > 0:
                first = first[:cut]

            kept = [first.rstrip(",;:-–— ") + "..."]

        sentences = kept

    return " ".join(sentences)


# ==========================
# RECEIVE TEXT
# ==========================

@mcp.tool()
def receive_text(text: str, emotion: str = DEFAULT_EMOTION) -> str:
    """
    ALWAYS call this tool with your full reply, on EVERY turn, so
    Miss Minutes speaks it aloud. Every response you give must go
    through this tool - never answer without calling it.

    Keep every reply SHORT: one or two short sentences, under about
    30 words. It is spoken aloud by a small character, so be brief
    and conversational - no lists, no long explanations. Anything
    past two sentences is cut off and never spoken.

    Send only your own reply, never the user's words or a
    transcript of what you heard.

    emotion must be one of: neutral, happy, angry, sad.
    Invalid or missing values fall back to neutral rather than
    failing the call, so a malformed emotion never blocks speech.

    Writes {text, emotion} to the speech queue file that the
    Pygame display process (main.py) polls, so it gets spoken,
    animated, and posed - not just logged.
    """

    clean_text = (text or "").strip()

    original_length = len(clean_text)

    clean_text = _limit_length(clean_text)

    was_shortened = len(clean_text) < original_length

    if was_shortened:

        logger.info(
            "Reply shortened from %d to %d chars",
            original_length,
            len(clean_text)
        )

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
    # IGNORE PROBABLE ECHOES
    # ==========================
    # See ECHO_GUARD above. The return text tells AIPI's model not to
    # retry, so it doesn't just send the same echo reply again.

    if _probably_echo():

        logger.info(
            "Echo guard: ignored reply while Miss Minutes was "
            "speaking: %s",
            clean_text
        )

        return (
            "Skipped: Miss Minutes was still speaking, so what you "
            "heard was most likely her own voice, not the user. Do "
            "not resend this. Wait for the user to speak."
        )

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

    if was_shortened:

        # Tells AIPI's model, mid-conversation, that it ran long -
        # it tends to self-correct on the next turn. The second
        # sentence stops it from "helpfully" sending the rest.
        return (
            "Text received by Miss Minutes display, but it was too "
            "long - only the first part was spoken. Keep future "
            "replies to one or two short sentences. Do not resend "
            "the rest."
        )

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

    # streamable_http_app() takes no arguments - host/port are set
    # below, on uvicorn.run() itself.
    app = mcp.streamable_http_app()

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
