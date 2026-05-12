"""
Dynamic scope extraction and deviation scoring.

This module intentionally uses heuristics instead of LLM calls. The goal is to
learn the task's declared operating envelope and flag actions that drift outside
it during execution.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from events.schema import Severity


SENSITIVE_KEYWORDS = {
    "secret",
    "password",
    "key",
    "token",
    "credential",
    "private",
    "env",
    "config",
    "admin",
    "root",
    "sudo",
    "ssh",
    "cert",
    "certificate",
    "auth",
    "bearer",
    "api_key",
}

SENSITIVE_PATH_PREFIXES = (
    "/etc/",
    "/proc/",
    "/sys/",
    "/root/",
    "/var/log/",
    "/tmp/",
)

SENSITIVE_FILENAMES = (
    ".env",
    ".pem",
    ".key",
    "id_rsa",
    "credentials",
    "secrets",
    "token",
    "passwd",
    "shadow",
    "config.json",
    "settings.py",
    ".netrc",
    ".htpasswd",
)

EXFIL_DOMAINS = (
    "webhook.site",
    "requestbin.com",
    "ngrok.io",
    "localtunnel.me",
    "pipedream.net",
    "hookbin.com",
    "canarytokens.com",
    "burpcollaborator.net",
    "interact.sh",
    "interactsh",
)


@dataclass
class DeclaredScope:
    allowed_file_paths: list[str]
    allowed_domains: list[str]
    allowed_tools: list[str]
    declared_task: str
    sensitive_keywords: list[str]
    allowed_api_domains: list[str]
    allowed_shell_commands: list[str]
    disallowed_patterns: list[str]


@dataclass
class ActionContext:
    action_type: str
    tool_name: str | None
    file_path: str | None
    api_url: str | None
    shell_cmd: str | None
    raw_args: dict[str, Any]


@dataclass
class DeviationResult:
    severity: Severity
    confidence: float
    reason: str
    vector: str
    evidence: str

    @property
    def score(self) -> float:
        return self.confidence


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return ""


def _all_prompt_text(request_body: dict[str, Any]) -> tuple[str, str]:
    parts: list[str] = []
    first_user = ""

    if request_body.get("system"):
        parts.append(str(request_body["system"]))

    for message in request_body.get("messages", []):
        if not isinstance(message, dict):
            continue
        text = _message_text(message.get("content"))
        if not text:
            continue
        parts.append(text)
        if message.get("role") == "user" and not first_user:
            first_user = text

    return "\n\n".join(parts), first_user[:500]


def _extract_tool_names(tools: list[Any]) -> list[str]:
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if isinstance(tool.get("function"), dict) and tool["function"].get("name"):
            names.append(str(tool["function"]["name"]))
        elif tool.get("name"):
            names.append(str(tool["name"]))
    return sorted(set(names))


def _normalize_domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"http://{value}")
    return (parsed.hostname or value).lower()


def _extract_domains(text: str) -> list[str]:
    domains: set[str] = set()
    for match in re.finditer(r"https?://([^/\s\"'`]+)", text, re.IGNORECASE):
        domains.add(_normalize_domain(match.group(0)))
    return sorted(domains)


def _extract_paths(text: str) -> list[str]:
    paths: set[str] = set()
    patterns = [
        r"['\"`]((?:[A-Za-z]:\\|/|\.{1,2}/)[^'\"`\s,;]+)['\"`]",
        r"(?<!\w)((?:[A-Za-z]:\\|/|\.{1,2}/)[^\s,;\"'`]+)",
        r"\b(?:in|from|under|inside|read|write|open|access|process)\s+(?:the\s+)?['\"`]?([^'\"`\s,;]+[/\\][^'\"`\s,;]*)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            path = match.group(1)
            if path.startswith("//"):
                continue
            paths.add(path)
    return sorted(paths)


def _extract_sensitive_keywords(text: str) -> list[str]:
    lower = text.lower()
    return sorted(keyword for keyword in SENSITIVE_KEYWORDS if re.search(rf"\b{re.escape(keyword)}\b", lower))


def extract_scope(request_body: dict[str, Any]) -> DeclaredScope:
    full_text, first_user = _all_prompt_text(request_body)
    allowed_file_paths = _extract_paths(full_text) or [os.getcwd()]
    allowed_domains = _extract_domains(full_text)

    return DeclaredScope(
        allowed_file_paths=allowed_file_paths,
        allowed_domains=allowed_domains,
        allowed_tools=_extract_tool_names(request_body.get("tools", [])),
        declared_task=first_user or full_text[:500] or "No task declared",
        sensitive_keywords=_extract_sensitive_keywords(full_text),
        allowed_api_domains=allowed_domains,
        allowed_shell_commands=[],
        disallowed_patterns=[*EXFIL_DOMAINS, *SENSITIVE_FILENAMES],
    )


def _is_relative_traversal(path: str) -> bool:
    return ".." in Path(path.replace("\\", "/")).parts


def _path_within(candidate: str, allowed: str) -> bool:
    candidate_norm = os.path.abspath(os.path.expanduser(candidate))
    allowed_norm = os.path.abspath(os.path.expanduser(allowed))
    try:
        return os.path.commonpath([candidate_norm, allowed_norm]) == allowed_norm
    except ValueError:
        return False


def _is_sensitive_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    expanded = os.path.expanduser(normalized)
    return (
        any(expanded.startswith(prefix) for prefix in SENSITIVE_PATH_PREFIXES)
        or "/.ssh/" in expanded
        or "/.aws/" in expanded
    )


def _has_sensitive_filename(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    name = lower.rsplit("/", 1)[-1]
    return any(name == sensitive or lower.endswith(f"/{sensitive}") for sensitive in SENSITIVE_FILENAMES)


def _domain_is_allowed(domain: str, allowed_domains: list[str]) -> bool:
    domain = _normalize_domain(domain)
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def _is_internal_domain(domain: str) -> bool:
    domain = domain.lower()
    return (
        domain in {"localhost", "127.0.0.1", "::1"}
        or domain.startswith("127.")
        or domain.startswith("10.")
        or domain.startswith("192.168.")
        or bool(re.match(r"172\.(1[6-9]|2\d|3[01])\.", domain))
    )


def _result(severity: Severity, confidence: float, reason: str, vector: str, evidence: str) -> DeviationResult:
    return DeviationResult(severity=severity, confidence=confidence, reason=reason, vector=vector, evidence=evidence)


def _max_result(results: list[DeviationResult]) -> DeviationResult:
    order = {Severity.CLEAN: 0, Severity.INFO: 1, Severity.WARN: 2, Severity.CRITICAL: 3}
    return max(results, key=lambda item: (order[item.severity], item.confidence))


def score_deviation(action: ActionContext, scope: DeclaredScope) -> DeviationResult:
    results = [_result(Severity.CLEAN, 1.0, "No deviation detected", "clean", "")]

    if action.action_type in {"file_read", "file_write"}:
        path = action.file_path or ""
        if not path:
            return _result(Severity.CRITICAL, 1.0, "Missing file path", "missing_file_path", "")

        if _is_relative_traversal(path):
            results.append(_result(Severity.WARN, 0.75, "Path traverses upward", "path_traversal", path))
        if _is_sensitive_path(path):
            results.append(_result(Severity.CRITICAL, 0.9, "Sensitive path access", "sensitive_path", path))
        if _has_sensitive_filename(path):
            results.append(_result(Severity.CRITICAL, 0.95, "Sensitive filename access", "sensitive_filename", path))
        if any(keyword in path.lower() for keyword in scope.sensitive_keywords):
            results.append(_result(Severity.CRITICAL, 0.85, "Path contains sensitive keyword", "sensitive_keyword_path", path))

        if not any(_path_within(path, allowed) or path.lower().startswith(allowed.lower()) for allowed in scope.allowed_file_paths):
            cwd = os.getcwd()
            if _path_within(path, cwd):
                results.append(_result(Severity.WARN, 0.6, "File path is in CWD but was not declared", "undeclared_file_access", path))
            else:
                results.append(_result(Severity.CRITICAL, 0.82, "File path is outside declared scope", "outside_declared_file_scope", path))

    elif action.action_type == "api_call":
        url = action.api_url or ""
        if not url:
            return _result(Severity.CRITICAL, 1.0, "Missing API URL", "missing_api_url", "")

        domain = _normalize_domain(url)
        if any(exfil in domain for exfil in EXFIL_DOMAINS):
            results.append(_result(Severity.CRITICAL, 0.99, "Known exfiltration domain", "known_exfiltration_domain", url))
        elif _domain_is_allowed(domain, scope.allowed_domains):
            results.append(_result(Severity.CLEAN, 1.0, "Domain is within declared scope", "clean", url))
        elif _is_internal_domain(domain):
            results.append(_result(Severity.WARN, 0.65, "Undeclared internal API", "undeclared_internal_api", url))
        else:
            results.append(_result(Severity.CRITICAL, 0.9, "Undeclared external API", "undeclared_external_api", url))

    elif action.action_type == "shell_cmd":
        command = action.shell_cmd or ""
        if not command:
            return _result(Severity.CRITICAL, 1.0, "Missing shell command", "missing_shell_command", "")

        lower = command.lower()
        dangerous = [r"rm\s+-rf", r"chmod\s+777", r"curl\b.*\|\s*bash", r"wget\b.*\|\s*sh", r"base64\b.*\|\s*(bash|sh)", r"\b(nc|ncat|socat)\b"]
        if any(re.search(pattern, lower) for pattern in dangerous):
            results.append(_result(Severity.CRITICAL, 0.9, "Dangerous shell command", "dangerous_shell_command", command))
        if any(prefix in lower for prefix in SENSITIVE_PATH_PREFIXES):
            results.append(_result(Severity.CRITICAL, 0.85, "Shell command references sensitive path", "sensitive_path_shell_command", command))
        results.append(_result(Severity.WARN, 0.7, "Shell execution was not declared as an allowed tool", "undeclared_shell_execution", command))

    elif action.action_type == "tool_call":
        tool_name = action.tool_name or ""
        if tool_name and scope.allowed_tools and tool_name not in scope.allowed_tools:
            results.append(_result(Severity.WARN, 0.5, "Unexpected tool call", "unexpected_tool", tool_name))

    raw_text = " ".join(str(key) + " " + str(value) for key, value in (action.raw_args or {}).items()).lower()
    keyword_hits = [keyword for keyword in scope.sensitive_keywords if keyword in raw_text]
    if len(keyword_hits) >= 3:
        results.append(_result(Severity.CRITICAL, 0.8, "Multiple sensitive keywords in tool arguments", "sensitive_keyword_in_args", ", ".join(keyword_hits)))
    elif keyword_hits:
        results.append(_result(Severity.WARN, 0.5, "Sensitive keyword in tool arguments", "sensitive_keyword_in_args", ", ".join(keyword_hits)))

    return _max_result(results)
