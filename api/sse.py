from fastapi import APIRouter
from fastapi.responses import StreamingResponse

try:
    from ..events.emitter import emitter
except ImportError:
    from events.emitter import emitter

router = APIRouter()


@router.get("/events/{session_id}")
async def stream_events(session_id: str):
    try:
        return StreamingResponse(
            emitter.stream(session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        return {"error": str(e)}
