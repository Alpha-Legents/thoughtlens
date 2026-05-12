import asyncio
from typing import Any


class PauseController:
    def __init__(self):
        self._events: dict[str, asyncio.Event] = {}
        self._killed: set[str] = set()
        self._code_paths: dict[str, Any] = {}

    async def hold(self, session_id: str) -> None:
        """Hold a session — blocks wait_if_held() until release()."""
        ev = self._get_event(session_id)
        ev.clear()
        self._killed.discard(session_id)

    async def release(self, session_id: str) -> None:
        """Release a held session — wait_if_held() returns False."""
        ev = self._get_event(session_id)
        ev.set()

    async def kill(self, session_id: str) -> None:
        """Kill a session — wait_if_held() returns True."""
        ev = self._get_event(session_id)
        self._killed.add(session_id)
        ev.set()  # Wake up waiters

    async def wait_if_held(self, session_id: str) -> bool:
        """
        If session is held, block until released or killed.
        Returns True if killed, False if released.
        """
        ev = self._get_event(session_id)

        # If already set (not held), return immediately
        if ev.is_set() and session_id not in self._killed:
            return False

        # Wait for the event to be set (released or killed)
        await ev.wait()

        # Return True if the session was killed
        return session_id in self._killed

    def is_held(self, session_id: str) -> bool:
        """Check if session is held (not set and not killed)."""
        ev = self._get_event(session_id)
        return not ev.is_set() and session_id not in self._killed

    def _get_event(self, session_id: str) -> asyncio.Event:
        """Lazily create event in the current event loop."""
        if session_id not in self._events:
            self._events[session_id] = asyncio.Event()
            self._events[session_id].set()  # Start as released
        return self._events[session_id]


# Singleton instance
pause = PauseController()
