import asyncio
from security.lobster import forward_to_lt

async def test():
    result = await forward_to_lt(
        {"model": "test", "messages": [{"role": "user", "content": "hi"}]},
        {},
        "http://localhost:8080"
    )
    print(f"Result: {result.action}")

asyncio.run(test())