#!/usr/bin/env python3
"""
ThoughtLens - Live mid-execution agent forensics proxy
"""
import sys
import os
import uvicorn
import asyncio
from typing import Optional

# Add project root to Python path for proper imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

# Import our modules
from config import settings as app_settings
from events.schema import ThoughtEvent, EventType, Severity
from events.emitter import emitter
from events.pause import pause
from core.session import create_session, get_session, DeclaredScope, get_all_sessions
from security.lobster import forward_to_lt, LTResult
from api.sse import router as sse_router
from api.control import router as control_router

# Windows-specific event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize the FastAPI app
app = FastAPI(
    title="ThoughtLens",
    description="Live mid-execution agent forensics proxy",
    version="0.1.0"
)

# Register documented routes and UI-compatible aliases.
app.include_router(sse_router)
app.include_router(control_router)
app.include_router(sse_router, prefix="/api/control")
app.include_router(control_router, prefix="/api/control")

# Import and register proxy router after app creation to avoid circular imports
from core.proxy import router as proxy_router
app.include_router(proxy_router)

class SimpleSettings:
    """Simplified settings that never fail"""
    def __init__(self):
        self.tl_port = int(os.environ.get('TL_PORT', 8000))
        self.tl_llm_url = os.environ.get('TL_LLM_URL', 'https://api.groq.com/openai/v1')
        self.tl_llm_key = os.environ.get('TL_LLM_KEY', 'placeholder_key')
        self.tl_lt_port = int(os.environ.get('TL_LT_PORT', 8080))
        self.tl_lt_binary = os.environ.get('TL_LT_BINARY', './lobstertrap/lobstertrap')
        self.tl_lt_policy = os.environ.get('TL_LT_POLICY', './configs/thoughtlens_policy.yaml')
        self.tl_log_level = os.environ.get('TL_LOG_LEVEL', 'info')
        self.prism_provider = os.environ.get('PRISM_PROVIDER', 'https://api.groq.com/openai/v1')
        self.prism_key = os.environ.get('PRISM_KEY', 'placeholder_key')
        self.prism_model = os.environ.get('PRISM_MODEL', 'llama-3.3-70b-versatile')

settings = SimpleSettings()

@app.get("/")
async def root():
    return {"message": "ThoughtLens v0.1.0 is running", "port": settings.tl_port}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "time": str(asyncio.get_event_loop().time()),
        "running_sessions": len(get_all_sessions())
    }

@app.get("/docs")
async def docs():
    return {"message": "FastAPI server is running. Access /docs for automatic API documentation"}

if __name__ == "__main__":
    print(f"Starting ThoughtLens v0.1.0 on port {settings.tl_port}")
    print(f"Logging level: {settings.tl_log_level}")
    print(f"LLM Provider: {settings.prism_provider}")
    print("Server starting...")

    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.tl_port,
            log_level=settings.tl_log_level,
            reload=False,
            use_colors=True
        )
    except KeyboardInterrupt:
        print("\nServer shutdown requested")
    except Exception as e:
        print(f"Server error: {e}")
        raise
