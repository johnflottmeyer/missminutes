import asyncio
from mcp import Client


async def main():
    url = "https://smoked-usher-poster.ngrok-free.dev/mcp"

    async with Client(url) as client:
        text = "Well hey there, sugar."

        print("\nSending text to Miss Minutes...")
        print(text)

        result = await client.call_tool(
            "receive_text",
            {"text": text}
        )

        print("\nResult:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
