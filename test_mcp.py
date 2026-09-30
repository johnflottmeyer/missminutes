import asyncio
import os

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MISSMINUTES_MCP_URL", "http://127.0.0.1:8000/mcp")
MCP_TOKEN = os.environ.get("MISSMINUTES_MCP_TOKEN", "")


async def main():

    if not MCP_TOKEN:
        raise SystemExit(
            "MISSMINUTES_MCP_TOKEN is not set. Set it to the same value "
            "the server is running with before running this test."
        )

    headers = {"Authorization": f"Bearer {MCP_TOKEN}"}

    # streamablehttp_client is an async context manager that yields a
    # (read_stream, write_stream, get_session_id_callback) tuple - it
    # is not a plain object you hand to a "Client" constructor (there
    # is no mcp.Client class). The headers go straight to the
    # transport itself rather than a separate httpx.AsyncClient.
    async with streamablehttp_client(
        MCP_URL,
        headers=headers,
    ) as (read_stream, write_stream, get_session_id):

        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()

            text = "Well hey there, sugar."
            emotion = "happy"

            result = await session.call_tool(
                "receive_text",
                {"text": text, "emotion": emotion},
            )

            print(result)


if __name__ == "__main__":
    asyncio.run(main())
