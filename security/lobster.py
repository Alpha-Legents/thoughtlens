"""
Lobster Trap HTTP client and header interpreter for ThoughtLens.

Lobster Trap is an external OpenAI-compatible DPI proxy. ThoughtLens treats it
as a dependency: call it when available, interpret its headers, and degrade
without crashing when it is absent during local demos.
"""

from dataclasses import dataclass, field
import json
from typing import Any
from urllib import response

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
    print(f"DEBUG: TL_LLM_KEY = {settings.tl_llm_key[:20]}...", flush=True)
    if settings.tl_llm_key == "placeholder_key" or settings.prism_key == "placeholder_key":
        return _fallback_body("Lobster Trap is unavailable and no LLM key is configured.")

    # For direct LLM call, disable streaming
    request_body = {**request_body, "stream": False}
    
    # Clean messages for Groq compatibility (remove null tool_calls)
    messages = request_body.get("messages", [])
    cleaned_messages = []
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls") is None:
            # Remove the tool_calls key entirely
            msg = {k: v for k, v in msg.items() if k != "tool_calls"}
        cleaned_messages.append(msg)
    request_body["messages"] = cleaned_messages
    
    outbound_headers = {
        "content-type": "application/json",
        "authorization": headers.get("authorization") or f"Bearer {settings.tl_llm_key}",
    }
    url = settings.tl_llm_url.rstrip("/") + "/chat/completions"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=request_body, headers=outbound_headers)
        print(f"DEBUG: Response status: {response.status_code}", flush=True)
        print(f"DEBUG: Response text: {response.text[:200]}", flush=True)
        response.raise_for_status()
        return response.json()
    
    
async def forward_to_lt(
    request_body: dict[str, Any],
    headers: dict[str, str],
    lt_url: str,
) -> LTResult:
    """
    Forward a request through Lobster Trap.
    """
    outbound_headers = {"content-type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            base_url = lt_url.rstrip("/")
            full_url = f"{base_url}/v1/chat/completions"
            
            # Create body for LobsterTrap - preserve tool definitions
            lt_body = {
                "model": request_body.get("model", "test"),
                "messages": []
            }

            for msg in request_body.get("messages", []):
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Extract text from content array (for multimodal)
                    text_parts = []
                    for block in content:
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    content = " ".join(text_parts)
                lt_body["messages"].append({
                    "role": msg.get("role", "user"),
                    "content": content
                })

            # ✅ CRITICAL FIX: Preserve tool definitions and other fields
            if "tools" in request_body:
                lt_body["tools"] = request_body["tools"]
                print(f">>> Preserved {len(request_body['tools'])} tool(s) to Lobster Trap", flush=True)

            if "tool_choice" in request_body:
                lt_body["tool_choice"] = request_body["tool_choice"]

            if "temperature" in request_body:
                lt_body["temperature"] = request_body["temperature"]

            if "max_tokens" in request_body:
                lt_body["max_tokens"] = request_body["max_tokens"]

            print(f">>> LT request body keys: {list(lt_body.keys())}", flush=True)
            
            
            # ONLY ONE POST CALL - use lt_body
            response = await client.post(full_url, json=lt_body, headers=outbound_headers)
            print(f">>> LT RESPONSE STATUS: {response.status_code}", flush=True)
            response.raise_for_status()

        raw_headers = dict(response.headers)
        print(f">>> ALL HEADERS: {raw_headers}", flush=True)

        try:
            forwarded_body = response.json()
            verdict = forwarded_body.get("_lobstertrap", {}).get("verdict", "ALLOW")
            action = verdict.upper()
            print(f">>> ACTION FROM BODY VERDICT: '{action}'", flush=True)
        except Exception as e:
            print(f">>> Could not get verdict from body: {e}", flush=True)
            action_raw = _header(response.headers, "x-lobstertrap-action", "ALLOW")
            print(f">>> ACTION RAW FROM HEADER: '{action_raw}'", flush=True)
            action = action_raw.upper()
            forwarded_body = _fallback_body(response.text)

        risk_score = _parse_risk_score(_header(response.headers, "x-lobstertrap-risk-score", "0"))
        intent_category = _header(response.headers, "x-lobstertrap-intent-category", "unknown")
        rule_triggered = _header(response.headers, "x-lobstertrap-policy-rule", "")

        print(f">>> FINAL ACTION: '{action}'", flush=True)
        
        return LTResult(
            action=action,
            risk_score=risk_score,
            intent_category=intent_category,
            rule_triggered=rule_triggered,
            forwarded_body=forwarded_body,
            raw_headers=raw_headers,
        )
        
    except Exception as exc:
        print(f"!!! LOBSTER TRAP CALL FAILED: {type(exc).__name__}: {exc}", flush=True)
        import traceback
        traceback.print_exc()
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