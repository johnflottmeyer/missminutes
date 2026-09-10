# missminutes_mcp.py

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Miss Minutes MCP")


@mcp.tool()
def ping() -> str:
    """Simple connection test."""
    print("AIPI called ping()")
    return "Hello from the Miss Minutes Raspberry Pi"


@mcp.tool()
def receive_text(text: str) -> str:
    """Receive text from AIPI for Miss Minutes animation."""
    print(f"AIPI TEXT: {text}")

    # Later this will pass the text into the Miss Minutes
    # animation system running on the Pi.

    return "Text received by Miss Minutes display"


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )