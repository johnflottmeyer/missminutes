import asyncio
import os

import httpx2

from mcp import Client
from mcp.client.streamable_http import streamable_http_client


# Point this at your own tunnel/host - never hardcode a live URL here.
MCP_URL = os.environ.get(
    "MISSMINUTES_MCP_URL",
    "http://127.0.0.1:8000/mcp"
)

MCP_TOKEN = os.environ.get(
    "MISSMINUTES_MCP_TOKEN",
    ""
)


async def main():

    if not MCP_TOKEN:

        raise SystemExit(
            "Set MISSMINUTES_MCP_TOKEN to the same shared secret the "
            "server was started with before running this test client."
        )

    http_client = httpx2.AsyncClient(
        headers={
            "Authorization": f"Bearer {MCP_TOKEN}"
        }
    )

    transport = streamable_http_client(
        MCP_URL,
        http_client=http_client
    )

    async with Client(transport) as client:
        text = "Well hey there, sugar."
        emotion = "happy"

        print("\nSending text to Miss Minutes...")
        print(text)

        result = await client.call_tool(
            "receive_text",
            {"text": text, "emotion": emotion}
        )

        print("\nResult:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
