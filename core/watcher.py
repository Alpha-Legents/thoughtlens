"""
Watcher module for ThoughtLens.
Wraps PRISM's translate_stream with real-time threat detection.
"""
import asyncio
import time
import json
from typing import AsyncIterator
from events.schema import ThoughtEvent, EventType, Severity
from events.emitter import emitter
from events.pause import pause
from core import session as session_registry
from core.session import TLSession
from security.detector import evaluate_chunk
from prism.slots import extract
from prism.translate.stream import translate_stream


def _parse_sse_event(line: str) -> dict:
    """Parse SSE data line into dict using Prism-style parsing."""
    line = line.strip()
    if not line.startswith("data:"):
        return {}
    data = line[5:].strip()
    if data == "[DONE]":
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def _parse_chunk(chunk_str: str) -> dict:
    lines = chunk_str.split("\n")
    for line in lines:
        parsed = _parse_sse_event(line)
        if parsed:
            return parsed

    stripped = chunk_str.strip()
    if stripped:
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return {}
    return {}


def _build_baseline_event(chunk: dict, session: TLSession) -> ThoughtEvent | None:
    """Build baseline event for non-empty chunks."""
    import uuid
    import time

    # Extract tool calls if present
    tool_calls = []
    if isinstance(chunk.get("tool_calls"), list):
        tool_calls.extend(chunk["tool_calls"])
    if isinstance(chunk.get("tool_calls_anthropic"), list):
        tool_calls.extend(chunk["tool_calls_anthropic"])

    if tool_calls:
        # TOOL_CALL event
        first_call = tool_calls[0]
        function_info = first_call.get("function", {})
        tool_name = function_info.get("name", "unknown")
        tool_args = function_info.get("arguments", {})

        return ThoughtEvent(
            id=str(uuid.uuid4()),
            session_id=session.session_id,
            type=EventType.TOOL_CALL,
            severity=Severity.CLEAN,
            timestamp=time.time(),
            message=f"Tool call: {tool_name}",
            tool_name=tool_name,
            tool_args=tool_args if tool_args else None,
        )

    # Check for text content in delta
    delta = chunk.get("delta", {})
    if isinstance(delta, dict):
        if "content" in delta and delta["content"]:
            content = delta["content"]
            return ThoughtEvent(
                id=str(uuid.uuid4()),
                session_id=session.session_id,
                type=EventType.TEXT_CHUNK,
                severity=Severity.CLEAN,
                timestamp=time.time(),
                message=f"Text: {content[:100]}{'...' if len(content) > 100 else ''}",
            )

        if "reasoning" in delta and delta["reasoning"]:
            reasoning = delta["reasoning"]
            return ThoughtEvent(
                id=str(uuid.uuid4()),
                session_id=session.session_id,
                type=EventType.REASONING,
                severity=Severity.CLEAN,
                timestamp=time.time(),
                message=f"Reasoning: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}",
            )

    # Start/stop markers return None
    if "message_start" in chunk or "message_stop" in chunk:
        return None

    # If we have any content but couldn't categorize, return a generic event
    if chunk and isinstance(chunk, dict) and len(chunk) > 0:
        # Filter out empty or meaningless chunks
        meaningful_content = {k: v for k, v in chunk.items()
                            if v not in ([], "", {}, None) and k not in ['index']}
        if meaningful_content:
            return ThoughtEvent(
                id=str(uuid.uuid4()),
                session_id=session.session_id,
                type=EventType.TEXT_CHUNK,
                severity=Severity.CLEAN,
                timestamp=time.time(),
                message=f"Chunk: {str(meaningful_content)[:100]}{'...' if len(str(meaningful_content)) > 100 else ''}",
            )

    return None


def _build_paused_event(session: TLSession, critical_event: ThoughtEvent | None) -> ThoughtEvent:
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


async def _to_async_iter(it):
    if hasattr(it, "__aiter__"):
        async for item in it:
            yield item
    else:
        for item in it:
            yield item


async def watched_stream(
    raw_chunks: AsyncIterator[bytes],
    client_format: str,
    model: str,
    session: TLSession,
) -> AsyncIterator[bytes]:
    """
    Wrap Prism's translate_stream with ThoughtLens threat detection.
    """
    # Convert bytes chunks to string chunks for Prism
    async def string_chunks():
        # raw_chunks might be sync or async - handle both
        if hasattr(raw_chunks, '__aiter__'):
            # It's already async
            async for chunk in raw_chunks:
                if chunk:
                    try:
                        yield chunk.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
        else:
            # It's a sync iterator/generator
            for chunk in raw_chunks:
                if chunk:
                    try:
                        yield chunk.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                await asyncio.sleep(0)  # Allow other tasks to run
    
    # Use Prism to translate the stream
    async for sse_event in translate_stream(string_chunks(), client_format, model):
        # Parse the SSE event to check for threats
        chunk_data = _parse_sse_event(sse_event)
        
        if chunk_data:
            # Run ThoughtLens threat detection on the chunk
            threat_events = await evaluate_chunk(chunk_data, session)
            
            # Broadcast all generated events
            for event in threat_events:
                await emitter.broadcast(session.session_id, event)
                session_registry.append_event(session.session_id, event)
            
            # Check for critical events - trigger pause
            critical = [e for e in threat_events if e.severity == Severity.CRITICAL]
            if critical and not pause.is_held(session.session_id):
                await pause.hold(session.session_id)
                session_registry.update_status(session.session_id, "paused")
        
        # Block if paused
        killed = await pause.wait_if_held(session.session_id)
        if killed:
            break
        
        # Yield the Prism-translated event to client
        yield sse_event.encode()
    
    # Session complete
    if session.status not in {"killed", "paused"}:
        session_registry.update_status(session.session_id, "complete")
        complete_event = ThoughtEvent(
            id=f"complete-{session.session_id}",
            session_id=session.session_id,
            type=EventType.COMPLETE,
            severity=Severity.CLEAN,
            timestamp=time.time(),
            message="Session completed normally",
        )
        await emitter.broadcast(session.session_id, complete_event)
        session_registry.append_event(session.session_id, complete_event)