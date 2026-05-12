import asyncio
from security.lobster import forward_to_lt

async def main():
    body = {"model": "test", "messages": [{"role": "user", "content": "hi"}]}
    result = await forward_to_lt(body, {}, "http://localhost:8080")
    print(f"Result: {result}")

asyncio.run(main())