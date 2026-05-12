"""
Lobster Trap HTTP client and header interpreter for ThoughtLens.

Lobster Trap is an external OpenAI-compatible DPI proxy. ThoughtLens treats it
as a dependency: call it when available, interpret its headers, and degrade
without crashing when it is absent during local demos.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx

from config import settings


@dataclass
class LTResult:
    action: str
    risk_score: float = 0.0
    intent_category: str = "unknown"
    rule_triggered: str = ""
    forwarded_body: dict[str, Any] | None = None
    raw_headers: dict[str, str] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.action not in {"DENY", "HUMAN_REVIEW", "QUARANTINE"}


def _header(headers: httpx.Headers | dict[str, str], name: str, default: str = "") -> str:
    lowered = {key.lower(): value for key, value in dict(headers).items()}
    return lowered.get(name.lower(), default)


def _parse_risk_score(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fallback_body(reason: str) -> dict[str, Any]:
    return {
        "id": "thoughtlens-fallback",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"ThoughtLens fallback response: {reason}",
                },
                "finish_reason": "stop",
            }
        ],
    }


async def _forward_direct_to_llm(request_body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    if settings.tl_llm_key == "placeholder_key" or settings.prism_key == "placeholder_key":
        return _fallback_body("Lobster Trap is unavailable and no LLM key is configured.")

    outbound_headers = {
        "content-type": "application/json",
        "authorization": headers.get("authorization") or f"Bearer {settings.tl_llm_key}",
    }
    url = settings.tl_llm_url.rstrip("/") + "/chat/completions"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=request_body, headers=outbound_headers)
        response.raise_for_status()
        return response.json()


async def forward_to_lt(
    request_body: dict[str, Any],
    headers: dict[str, str],
    lt_url: str,
) -> LTResult:
    """
    Forward a request through Lobster Trap.

    If LT is not available, default to UNAVAILABLE and try direct LLM fallback.
    Per DECISIONS.md, LT failures must not crash ThoughtLens.
    """
    outbound_headers = {"content-type": "application/json"}
    if headers.get("authorization"):
        outbound_headers["authorization"] = headers["authorization"]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            base_url = lt_url.rstrip("/")
            response = await client.post(f"{base_url}/v1/messages", json=request_body, headers=outbound_headers)
            if response.status_code == 404:
                response = await client.post(f"{base_url}/v1/chat/completions", json=request_body, headers=outbound_headers)
            response.raise_for_status()

        raw_headers = dict(response.headers)
        action = _header(response.headers, "x-lobstertrap-action", "ALLOW").upper()
        risk_score = _parse_risk_score(_header(response.headers, "x-lobstertrap-risk-score", "0"))
        intent_category = _header(response.headers, "x-lobstertrap-intent-category", "unknown")
        rule_triggered = _header(response.headers, "x-lobstertrap-policy-rule", "")

        try:
            forwarded_body = response.json()
        except ValueError:
            forwarded_body = _fallback_body(response.text)

        return LTResult(
            action=action,
            risk_score=risk_score,
            intent_category=intent_category,
            rule_triggered=rule_triggered,
            forwarded_body=forwarded_body,
            raw_headers=raw_headers,
        )
    except Exception as exc:
        try:
            forwarded_body = await _forward_direct_to_llm(request_body, headers)
        except Exception as llm_exc:
            forwarded_body = _fallback_body(f"Lobster Trap and direct LLM forwarding failed: {llm_exc}")

        return LTResult(
            action="UNAVAILABLE",
            risk_score=0.0,
            intent_category="unknown",
            rule_triggered=str(exc),
            forwarded_body=forwarded_body,
            raw_headers={},
        )