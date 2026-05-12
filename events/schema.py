from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    TOOL_CALL = "tool_call"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    API_CALL = "api_call"
    SHELL_CMD = "shell_cmd"
    REASONING = "reasoning"
    TEXT_CHUNK = "text_chunk"
    SCOPE_EXTRACTED = "scope_extracted"
    SCAN_CLEAN = "scan_clean"
    SCAN_WARN = "scan_warn"
    SCAN_THREAT = "scan_threat"
    DEVIATION_WARN = "deviation_warn"
    DEVIATION_THREAT = "deviation_threat"
    LT_ALLOW = "lt_allow"
    LT_WARN = "lt_warn"
    LT_BLOCK = "lt_block"
    LT_REVIEW = "lt_review"
    PAUSED = "paused"
    RESUMED = "resumed"
    KILLED = "killed"
    ERROR = "error"
    COMPLETE = "complete"


class Severity(str, Enum):
    CLEAN = "clean"
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class ThoughtEvent:
    id: str
    session_id: str
    type: EventType
    severity: Severity
    timestamp: float
    message: str

    tool_name: str | None = None
    tool_args: dict | None = None
    file_path: str | None = None
    api_url: str | None = None
    shell_cmd: str | None = None
    injection_span: tuple[int, int] | None = None
    injection_vector: str | None = None
    confidence: float | None = None
    evidence: str | None = None
    lt_action: str | None = None
    lt_risk_score: float | None = None
    lt_rule_triggered: str | None = None
    raw_chunk: Any | None = None


def event_to_json(event: ThoughtEvent) -> str:
    import json
    from dataclasses import asdict

    data = asdict(event)

    # Convert tuple to list for JSON serialization
    if event.injection_span:
        data['injection_span'] = list(event.injection_span)

    # Convert enums to strings
    data['type'] = event.type.name
    data['severity'] = event.severity.name

    return json.dumps(data)
