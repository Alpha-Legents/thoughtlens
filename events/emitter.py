import asyncio
from typing import AsyncGenerator

try:
    from .schema import ThoughtEvent, EventType, Severity
except ImportError:
    from schema import ThoughtEvent, EventType, Severity


class EventEmitter:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def broadcast(self, session_id: str, event) -> None:
        async with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = asyncio.Queue()

        await self._queues[session_id].put(event)

    async def stream(self, session_id: str) -> AsyncGenerator[str, None]:
        if session_id not in self._queues:
            await self._broadcast_empty_event(session_id)

        while True:
            try:
                event = await self._queues[session_id].get()
                yield f"data: {self._event_to_sse(event)}\n\n"
            except asyncio.CancelledError:
                break

    async def _broadcast_empty_event(self, session_id: str) -> None:
        await self.broadcast(session_id, ThoughtEvent(
            id=f"empty-{session_id}",
            session_id=session_id,
            type=EventType.TEXT_CHUNK,
            severity=Severity.INFO,
            timestamp=0.0,
            message=f"Waiting for session {session_id}..."
        ))

    def _event_to_sse(self, event) -> str:
        try:
            from .schema import event_to_json
        except ImportError:
            from schema import event_to_json
        return event_to_json(event)


emitter = EventEmitter()
