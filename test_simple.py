from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import sys

# Add current directory to path
sys.path.insert(0, '.')

from security.lobster import forward_to_lt, LTResult

app = FastAPI()

@app.post("/test")
async def test_endpoint(request: Request):
    print(">>> TEST ENDPOINT HIT", flush=True)
    try:
        body = await request.json()
        print(f"Body: {body}", flush=True)
        
        # Call lobster
        result = await forward_to_lt(body, {}, "http://localhost:8080")
        print(f"Result: {result}", flush=True)
        
        return JSONResponse({"status": "ok", "result": result.action})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print("Starting test server on port 8001", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")