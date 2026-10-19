import asyncio, os, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main(text):
    headers = {"Authorization": f"Bearer {os.environ['MISSMINUTES_MCP_TOKEN']}"}
    async with streamablehttp_client("http://127.0.0.1:8000/mcp", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("receive_text", {"text": text, "emotion": "happy"})
            print(res.structuredContent)

asyncio.run(main(" ".join(sys.argv[1:])))
