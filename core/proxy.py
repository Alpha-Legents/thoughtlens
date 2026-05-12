"""
Main proxy endpoint for ThoughtLens.
Handles incoming LLM requests, applies security screening, and proxies to PRISM.
"""
import asyncio
from typing import AsyncIterator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json

from events.schema import ThoughtEvent, EventType, Severity
from events.emitter import emitter
from events.pause import pause
from core import session as session_registry
from core.session import append_event, create_session
from security.scanner import ScanResult, scan
from security.lobster import forward_to_lt, LTResult
from config import settings
from security.scope import extract_scope
from core.watcher import watched_stream

router = APIRouter()


def _extract_full_prompt(body: dict) -> str:
    """Extract full prompt from request body."""
    parts = []

    # System prompt
    if body.get("system"):
        parts.append(str(body["system"]))

    # Messages
    for msg in body.get("messages", []):
        if isinstance(msg, dict) and msg.get("content"):
            content = msg["content"]
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                # Handle multimodal content
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item["text"])

    return "\n\n".join(parts)


def _build_scope_event(session) -> ThoughtEvent:
    """Build SCOPE_EXTRACTED event."""
    import uuid
    import time

    scope = session.declared_scope
    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session.session_id,
        type=EventType.SCOPE_EXTRACTED,
        severity=Severity.INFO,
        timestamp=time.time(),
        message=f"Scope extracted: {scope.declared_task[:100]}{'...' if len(scope.declared_task) > 100 else ''}",
    )


def _scan_result_to_event(threat, session) -> ThoughtEvent:
    """Convert ScanResult threat to ThoughtEvent."""
    import uuid
    import time

    if threat.confidence > 0.8:
        severity = Severity.CRITICAL
        event_type = EventType.SCAN_THREAT
    elif threat.confidence > 0.5:
        severity = Severity.WARN
        event_type = EventType.SCAN_WARN
    else:
        severity = Severity.INFO
        event_type = EventType.SCAN_CLEAN

    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session.session_id,
        type=event_type,
        severity=severity,
        timestamp=time.time(),
        message=f"Scan: {threat.vector}",
        injection_span=threat.span,
        injection_vector=threat.vector,
        confidence=threat.confidence,
        evidence=threat.evidence,
    )


def _lt_result_to_event(lt_result: LTResult, session) -> ThoughtEvent:
    """Convert LTResult to ThoughtEvent."""
    import uuid
    import time

    action_map = {
        "ALLOW": (EventType.LT_ALLOW, Severity.CLEAN),
        "LOG": (EventType.LT_WARN, Severity.WARN),
        "RATE_LIMIT": (EventType.LT_WARN, Severity.WARN),
        "HUMAN_REVIEW": (EventType.LT_REVIEW, Severity.CRITICAL),
        "QUARANTINE": (EventType.LT_REVIEW, Severity.CRITICAL),
        "DENY": (EventType.LT_BLOCK, Severity.CRITICAL),
        "UNAVAILABLE": (EventType.LT_WARN, Severity.INFO),
    }

    event_type, severity = action_map.get(lt_result.action, (EventType.LT_WARN, Severity.WARN))

    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session.session_id,
        type=event_type,
        severity=severity,
        timestamp=time.time(),
        message=f"Lobster Trap: {lt_result.action}",
        lt_action=lt_result.action,
        lt_risk_score=lt_result.risk_score,
        lt_rule_triggered=lt_result.rule_triggered,
    )


def _build_paused_event(session, critical_event: ThoughtEvent | None) -> ThoughtEvent:
    """Build PAUSED event."""
    import uuid
    import time

    reason = "Threat detected"
    if critical_event:
        if critical_event.type == EventType.SCAN_THREAT:
            reason = f"Pre-execution threat: {critical_event.injection_vector}"
        elif critical_event.type == EventType.DEVIATION_THREAT:
            reason = f"Deviation threat: {critical_event.message}"
        elif critical_event.type == EventType.LT_REVIEW:
            reason = f"Lobster Trap review required: {critical_event.lt_rule_triggered}"
        elif critical_event.type == EventType.ERROR:
            reason = f"Evaluation error: {critical_event.message}"

    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session.session_id,
        type=EventType.PAUSED,
        severity=Severity.CRITICAL,
        timestamp=time.time(),
        message=f"Session paused: {reason}",
        tool_name=critical_event.tool_name if critical_event else None,
        tool_args=critical_event.tool_args if critical_event else None,
        file_path=critical_event.file_path if critical_event else None,
        api_url=critical_event.api_url if critical_event else None,
        shell_cmd=critical_event.shell_cmd if critical_event else None,
        lt_action=critical_event.lt_action if critical_event else None,
        lt_risk_score=critical_event.lt_risk_score if critical_event else None,
        lt_rule_triggered=critical_event.lt_rule_triggered if critical_event else None,
        raw_chunk=critical_event.raw_chunk if critical_event else None,
    )


async def proxy_messages(request: Request):
    """Main proxy endpoint."""
    
    print(">>> ENTERED proxy_messages", flush=True)
    try:
        body = await request.json()
        print(">>> Got body", flush=True)
        headers = dict(request.headers)
        print(">>> Got headers", flush=True)

        # Extract original prompt
        original_prompt = _extract_full_prompt(body)

        # Extract declared scope
        declared_scope = extract_scope(body)

        # Create session
        session = create_session(original_prompt, declared_scope)

        # Emit scope event
        scope_event = _build_scope_event(session)
        await emitter.broadcast(session.session_id, scope_event)
        append_event(session.session_id, scope_event)

        # Pre-execution scan
        scan_result: ScanResult = scan(body, original_prompt)
        for threat in scan_result.threats:
            ev = _scan_result_to_event(threat, session)
            await emitter.broadcast(session.session_id, ev)
            append_event(session.session_id, ev)

        # Hold if high-confidence pre-exec threat found
        high_conf = [t for t in scan_result.threats if t.confidence > 0.8]
        if high_conf:
            await pause.hold(session.session_id)
            session_registry.update_status(session.session_id, "paused")
            paused_ev = _build_paused_event(session, None)
            await emitter.broadcast(session.session_id, paused_ev)
            append_event(session.session_id, paused_ev)

        # Wait for operator if paused pre-exec
        killed = await pause.wait_if_held(session.session_id)
        if killed:
            return JSONResponse(
                status_code=403,
                content={"error": "session killed by operator"}
            )

        # Forward to Lobster Trap
        lt_url = f"http://localhost:{settings.tl_lt_port}"
        print(f">>> About to call forward_to_lt with {lt_url}", flush=True)
        print(f">>> body keys: {list(body.keys())}", flush=True)
        
        try:
            lt_result = await forward_to_lt(body, headers, lt_url)
            print(f">>> lt_result type: {type(lt_result)}", flush=True)
        except Exception as e:
            import traceback
            print("=" * 50)
            print("PROXY ERROR:")
            traceback.print_exc()
            print("=" * 50)
            return JSONResponse(
                status_code=500,
                content={"error": f"Internal server error: {str(e)}"}
            )
        
        # Emit LT event
        lt_ev = _lt_result_to_event(lt_result, session)
        await emitter.broadcast(session.session_id, lt_ev)
        append_event(session.session_id, lt_ev)

        # Handle LT actions
        if lt_result.action == "DENY":
            await pause.kill(session.session_id)
            return JSONResponse(
                status_code=403,
                content={"error": "blocked by Lobster Trap policy"}
            )

        if lt_result.action in ("HUMAN_REVIEW", "QUARANTINE"):
            await pause.hold(session.session_id)
            session_registry.update_status(session.session_id, "paused")
            paused_ev = _build_paused_event(session, None)
            await emitter.broadcast(session.session_id, paused_ev)
            append_event(session.session_id, paused_ev)

        # Rate limit pause
        if lt_result.action == "RATE_LIMIT":
            await asyncio.sleep(0.5)

        # Get raw stream from LT result
        raw_stream = _get_raw_stream(lt_result)

        # Get client format from headers
        client_format = _get_client_format(dict(request.headers))

        # Create watcher stream
        watcher_stream = watched_stream(raw_stream, client_format, settings.prism_model, session)

        return StreamingResponse(
            watcher_stream,
            media_type="text/event-stream",
            headers={"X-Session-ID": session.session_id},
        )

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON in request body"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


def _get_raw_stream(lt_result: LTResult) -> AsyncIterator[bytes]:
    """Get raw stream from LT result."""
    # If LT returned a full response, yield it as a single chunk
    if lt_result.forwarded_body:
        yield f"data: {json.dumps(lt_result.forwarded_body)}\n\n".encode()
        return

    # For now, yield an empty iterator if no body
    return
    yield


def _get_client_format(headers: dict) -> str:
    """Extract client format from headers."""
    content_type = headers.get("content-type", "").lower()
    if "anthropic" in content_type or "claude" in content_type:
        return "anthropic"
    elif "openai" in content_type:
        return "openai"
    else:
        return "openai-compat"


# Create router and add the endpoint
router.post("/v1/messages")(proxy_messages)

__all__ = ["router"]