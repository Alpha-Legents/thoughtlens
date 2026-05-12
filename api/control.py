from fastapi import APIRouter, HTTPException
from events.pause import pause
from core import session as session_registry
from events.schema import ThoughtEvent, EventType, Severity
from events.emitter import emitter
import uuid
import time

router = APIRouter()


def _build_control_event(session_id: str, event_type: EventType, message: str) -> ThoughtEvent:
    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        type=event_type,
        severity=Severity.INFO,
        timestamp=time.time(),
        message=message,
    )


@router.post("/resume/{session_id}")
async def resume_session(session_id: str):
    session = session_registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await pause.release(session_id)
    session_registry.update_status(session_id, "resumed")

    event = _build_control_event(session_id, EventType.RESUMED, "Session resumed by operator")
    await emitter.broadcast(session_id, event)
    session_registry.append_event(session_id, event)

    return {"status": "resumed"}


@router.post("/kill/{session_id}")
async def kill_session(session_id: str):
    session = session_registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await pause.kill(session_id)
    session_registry.update_status(session_id, "killed")

    event = _build_control_event(session_id, EventType.KILLED, "Session killed by operator")
    await emitter.broadcast(session_id, event)
    session_registry.append_event(session_id, event)

    return {"status": "killed"}


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    session = session_registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "status": session.status,
        "created_at": session.created_at,
        "original_prompt": session.original_prompt,
        "declared_scope": {
            "allowed_file_paths": session.declared_scope.allowed_file_paths,
            "allowed_domains": session.declared_scope.allowed_domains,
            "allowed_tools": session.declared_scope.allowed_tools,
            "declared_task": session.declared_scope.declared_task,
            "sensitive_keywords": session.declared_scope.sensitive_keywords,
        },
        "events_count": len(session.events),
        "threat_payload": session.threat_payload,
        "injection_span": session.injection_span,
        "injection_vector": session.injection_vector,
    }


@router.get("/audit/{session_id}")
async def get_audit_log(session_id: str):
    session = session_registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "events": [event.__dict__ for event in session.events],
    }


@router.get("/sessions")
async def get_all_sessions():
    sessions = session_registry.get_all_sessions()
    return {
        "sessions": [
            {
                "id": s.session_id,
                "session_id": s.session_id,
                "status": s.status,
                "created_at": s.created_at,
                "eventCount": len(s.events),
                "events_count": len(s.events),
                "criticalCount": sum(1 for event in s.events if event.severity.value == "critical"),
                "warnCount": sum(1 for event in s.events if event.severity.value == "warn"),
                "paused": s.status == "paused",
            }
            for s in sessions
        ]
    }
