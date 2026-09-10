import os
import json
import fcntl

from mcp.server import MCPServer
from starlette.responses import JSONResponse


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


# ==========================
# LATEST TEXT STATE
# ==========================

latest_text = {
    "id": 0,
    "text": ""
}


# ==========================
# PING
# ==========================

@mcp.tool()
def ping() -> str:
    """
    Test the connection to the Miss Minutes Raspberry Pi.
    """

    print(
        "AIPI called ping()",
        flush=True
    )

    return "Hello from the Miss Minutes Raspberry Pi"


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

    text = final_response.strip()


    # ==========================
    # IGNORE EMPTY RESPONSES
    # ==========================

    if not text:

        print(
            "AIPI EMPTY SPEECH IGNORED",
            flush=True
        )

        return "Empty response ignored"


    # ==========================
    # IGNORE EXACT DUPLICATES
    # ==========================

    if text == latest_text["text"]:

        print(
            f"AIPI DUPLICATE IGNORED: {text}",
            flush=True
        )

        return "Duplicate Miss Minutes response ignored"


    # ==========================
    # UPDATE LATEST RESPONSE
    # ==========================

    latest_text["id"] += 1
    latest_text["text"] = text


    print(
        f"MISS MINUTES RESPONSE: {text}",
        flush=True
    )


    # ==========================
    # ADD TO SPEECH QUEUE
    # ==========================

    try:

        with open(
            SPEECH_QUEUE_FILE,
            "a"
        ) as file:

            fcntl.flock(
                file,
                fcntl.LOCK_EX
            )

            file.write(
                json.dumps(text)
                + "\n"
            )

            file.flush()

            fcntl.flock(
                file,
                fcntl.LOCK_UN
            )


        print(
            "Added response to Miss Minutes speech queue",
            flush=True
        )


    except Exception as error:

        print(
            "Speech queue error:",
            error,
            flush=True
        )

        return (
            "Response received but "
            "speech queue failed"
        )


    return (
        "Miss Minutes response queued "
        "for physical face"
    )


# ==========================
# LATEST TEXT ROUTE
# ==========================

@mcp.custom_route(
    "/latest-text",
    methods=["GET"]
)
async def latest_text_route(request):

    return JSONResponse(
        latest_text,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store"
        }
    )


# ==========================
# START SERVER
# ==========================

if __name__ == "__main__":

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )