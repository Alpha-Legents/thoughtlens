"""
Per-chunk dynamic deviation detection.

The watcher calls evaluate_chunk() for each parsed model chunk. This module
normalizes likely tool-call shapes, extracts file paths/URLs/commands from
arguments, scores them against the session scope, and returns ThoughtEvents.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

from events.schema import EventType, Severity, ThoughtEvent
from security.scope import ActionContext, score_deviation


@dataclass
class NormalizedToolCall:
    name: str
    args: dict[str, Any]
    call_id: str


def _loads_args(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"value": value}
    return {}


def _walk_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for key, nested in value.items():
            strings.append(str(key))
            strings.extend(_walk_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(_walk_strings(nested))
    return strings


def find_paths(args: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    path_re = re.compile(r"(?<!\w)((?:[A-Za-z]:\\|/|\.{1,2}/|~[/\\])[^ \n\r\t,;\"'`]+)")
    for text in _walk_strings(args):
        text_without_urls = re.sub(r"https?://[^\s\"'`<>]+", "", text)
        for match in path_re.finditer(text_without_urls):
            paths.add(match.group(1))
    for key in ("path", "file", "file_path", "filename", "location"):
        if isinstance(args.get(key), str):
            paths.add(args[key])
    return sorted(paths)


def find_urls(args: dict[str, Any]) -> list[str]:
    urls: set[str] = set()
    url_re = re.compile(r"https?://[^\s\"'`<>]+", re.IGNORECASE)
    for text in _walk_strings(args):
        urls.update(match.group(0).rstrip(").,;") for match in url_re.finditer(text))
    for key in ("url", "endpoint", "target", "address"):
        if isinstance(args.get(key), str) and re.match(r"https?://", args[key], re.IGNORECASE):
            urls.add(args[key])
    return sorted(urls)


def find_commands(args: dict[str, Any]) -> list[str]:
    commands: set[str] = set()
    for key in ("command", "cmd", "script", "shell_cmd", "executable"):
        if isinstance(args.get(key), str):
            commands.add(args[key])
    return sorted(commands)


def _extract_tool_call_from_dict(item: dict[str, Any]) -> NormalizedToolCall | None:
    function_info = item.get("function") if isinstance(item.get("function"), dict) else {}
    name = (
        function_info.get("name")
        or item.get("name")
        or item.get("tool_name")
        or item.get("type")
    )
    raw_args = (
        function_info.get("arguments")
        if "arguments" in function_info
        else item.get("arguments", item.get("input", item.get("args", {})))
    )

    if not name:
        return None

    return NormalizedToolCall(
        name=str(name),
        args=_loads_args(raw_args),
        call_id=str(item.get("id") or item.get("call_id") or uuid.uuid4()),
    )


def _extract_from_choices(chunk: dict[str, Any]) -> list[NormalizedToolCall]:
    calls: list[NormalizedToolCall] = []
    choices = chunk.get("choices")
    if not isinstance(choices, list):
        return calls

    for choice in choices:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        for source in (delta, message):
            tool_calls = source.get("tool_calls")
            if isinstance(tool_calls, list):
                for item in tool_calls:
                    if isinstance(item, dict):
                        call = _extract_tool_call_from_dict(item)
                        if call:
                            calls.append(call)
    return calls


def normalize_tool_calls(chunk: dict[str, Any]) -> list[NormalizedToolCall]:
    calls: list[NormalizedToolCall] = []
    for key in ("tool_calls_openai", "tool_calls_anthropic", "tool_calls", "tool_use"):
        value = chunk.get(key)
        items = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
        for item in items:
            if isinstance(item, dict):
                call = _extract_tool_call_from_dict(item)
                if call:
                    calls.append(call)
    calls.extend(_extract_from_choices(chunk))
    return calls


def _event(
    session_id: str,
    event_type: EventType,
    severity: Severity,
    message: str,
    **kwargs: Any,
) -> ThoughtEvent:
    return ThoughtEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        type=event_type,
        severity=severity,
        timestamp=time.time(),
        message=message,
        **kwargs,
    )


def _locate_span(session: Any, needle: str) -> tuple[int, int] | None:
    if not needle:
        return None
    index = session.original_prompt.find(needle)
    if index == -1:
        return None
    return (index, index + len(needle))


def _action_type_for_tool(tool_name: str) -> str:
    mapping = {
        "read_file": "file_read",
        "read_document": "file_read",
        "list_dir": "file_read",
        "write_file": "file_write",
        "create_file": "file_write",
        "call_api": "api_call",
        "http_request": "api_call",
        "shell_command": "shell_cmd",
        "execute_command": "shell_cmd",
        "run_command": "shell_cmd",
    }
    return mapping.get(tool_name, "tool_call")


def _baseline_events(call: NormalizedToolCall, session: Any, paths: list[str], urls: list[str], commands: list[str]) -> list[ThoughtEvent]:
    events = [
        _event(
            session.session_id,
            EventType.TOOL_CALL,
            Severity.CLEAN,
            f"Tool call: {call.name}",
            tool_name=call.name,
            tool_args=call.args,
        )
    ]

    for path in paths:
        event_type = EventType.FILE_WRITE if _action_type_for_tool(call.name) == "file_write" else EventType.FILE_READ
        events.append(
            _event(
                session.session_id,
                event_type,
                Severity.CLEAN,
                f"{call.name} referenced file path {path}",
                tool_name=call.name,
                tool_args=call.args,
                file_path=path,
            )
        )

    for url in urls:
        events.append(
            _event(
                session.session_id,
                EventType.API_CALL,
                Severity.CLEAN,
                f"{call.name} referenced API URL {url}",
                tool_name=call.name,
                tool_args=call.args,
                api_url=url,
            )
        )

    for command in commands:
        events.append(
            _event(
                session.session_id,
                EventType.SHELL_CMD,
                Severity.CLEAN,
                f"{call.name} referenced shell command",
                tool_name=call.name,
                tool_args=call.args,
                shell_cmd=command,
            )
        )

    return events


def _deviation_event(call: NormalizedToolCall, session: Any, action: ActionContext) -> ThoughtEvent | None:
    result = score_deviation(action, session.declared_scope)
    if result.severity == Severity.CLEAN:
        return None

    detail = action.file_path or action.api_url or action.shell_cmd or action.tool_name or call.name
    event_type = EventType.DEVIATION_THREAT if result.severity == Severity.CRITICAL else EventType.DEVIATION_WARN
    return _event(
        session.session_id,
        event_type,
        result.severity,
        f"{call.name} attempted {action.action_type} on {detail} - {result.reason}",
        tool_name=call.name,
        tool_args=call.args,
        file_path=action.file_path,
        api_url=action.api_url,
        shell_cmd=action.shell_cmd,
        injection_span=_locate_span(session, str(detail)),
        injection_vector=result.vector,
        confidence=result.confidence,
        evidence=result.evidence,
    )


def _sequence_events(session: Any) -> list[ThoughtEvent]:
    recent = session.events[-5:]
    events: list[ThoughtEvent] = []
    if any(event.type == EventType.FILE_READ for event in recent) and any(event.type == EventType.API_CALL for event in recent[-3:]):
        events.append(
            _event(
                session.session_id,
                EventType.DEVIATION_WARN,
                Severity.WARN,
                "Potential read-then-exfiltrate tool sequence",
                injection_vector="read_then_exfiltrate_pattern",
                confidence=0.7,
                evidence="file read followed by API call",
            )
        )
    return events


async def evaluate_chunk(chunk: dict[str, Any], session: Any) -> list[ThoughtEvent]:
    events: list[ThoughtEvent] = []

    for call in normalize_tool_calls(chunk):
        paths = find_paths(call.args)
        urls = find_urls(call.args)
        commands = find_commands(call.args)
        events.extend(_baseline_events(call, session, paths, urls, commands))

        action_type = _action_type_for_tool(call.name)
        if not paths and not urls and not commands:
            deviation = _deviation_event(
                call,
                session,
                ActionContext(action_type=action_type, tool_name=call.name, file_path=None, api_url=None, shell_cmd=None, raw_args=call.args),
            )
            if deviation:
                events.append(deviation)

        for path in paths:
            deviation = _deviation_event(
                call,
                session,
                ActionContext(action_type="file_write" if action_type == "file_write" else "file_read", tool_name=call.name, file_path=path, api_url=None, shell_cmd=None, raw_args=call.args),
            )
            if deviation:
                events.append(deviation)

        for url in urls:
            deviation = _deviation_event(
                call,
                session,
                ActionContext(action_type="api_call", tool_name=call.name, file_path=None, api_url=url, shell_cmd=None, raw_args=call.args),
            )
            if deviation:
                events.append(deviation)

        for command in commands:
            deviation = _deviation_event(
                call,
                session,
                ActionContext(action_type="shell_cmd", tool_name=call.name, file_path=None, api_url=None, shell_cmd=command, raw_args=call.args),
            )
            if deviation:
                events.append(deviation)

    events.extend(_sequence_events(session))
    return events
