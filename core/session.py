"""
Session management for ThoughtLens.
Tracks sessions, declared scope, and event history.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import uuid
from events.schema import ThoughtEvent

# Import DeclaredScope from security.scope to keep single definition
from security.scope import DeclaredScope


@dataclass
class ActionContext:
    action_type: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    api_url: Optional[str] = None
    shell_cmd: Optional[str] = None
    raw_args: Optional[Dict[str, Any]] = None


@dataclass
class TLSession:
    session_id: str
    created_at: float
    original_prompt: str
    declared_scope: DeclaredScope
    events: List[ThoughtEvent] = field(default_factory=list)
    status: str = "active"  # active, paused, killed, completed
    threat_payload: Optional[Any] = None
    injection_span: Optional[tuple[int, int]] = None
    injection_vector: Optional[str] = None


# Global session registry
_sessions: Dict[str, TLSession] = {}


def create_session(original_prompt: str, scope: DeclaredScope, session_id: str = None) -> TLSession:
    """Create a new TLSession."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    session = TLSession(
        session_id=session_id,
        created_at=time.time(),
        original_prompt=original_prompt,
        declared_scope=scope,
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[TLSession]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def append_event(session_id: str, event: ThoughtEvent) -> None:
    """Append an event to a session's history."""
    if session_id in _sessions:
        _sessions[session_id].events.append(event)


def update_status(session_id: str, status: str) -> None:
    """Update the status of a session."""
    if session_id in _sessions:
        _sessions[session_id].status = status


def get_all_sessions() -> List[TLSession]:
    """Get all active sessions."""
    return list(_sessions.values())


def clear_session(session_id: str) -> None:
    """Remove a session from the registry."""
    if session_id in _sessions:
        del _sessions[session_id]