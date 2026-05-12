"""
Semantic slot extraction - the Rosetta Stone for LLM APIs.
Extracts tool calls, text, and metadata from any provider's response format.
"""

import json
from typing import Any

# Response slots (what providers return)
RESPONSE_SLOTS: dict[str, list[str]] = {
    "response_text": [
        "choices[0].message.content",
        "content[0].text",
        "output[0].text",
    ],
    "stop_reason": [
        "choices[0].finish_reason",
        "stop_reason",
    ],
    "input_tokens": [
        "usage.prompt_tokens",
        "usage.input_tokens",
    ],
    "output_tokens": [
        "usage.completion_tokens",
        "usage.output_tokens",
    ],
    "model": ["model"],
    "tool_calls_openai": ["choices[0].message.tool_calls"],
    "tool_calls_anthropic": ["content[?type=='tool_use']"],
}


def extract(data: dict, slot: str) -> Any:
    """
    Extract a semantic slot from provider response using JMESPath-style paths.
    Simplified version without full JMESPath dependency.
    """
    paths = RESPONSE_SLOTS.get(slot, [])
    
    for path in paths:
        val = _simple_path_get(data, path)
        if val is not None:
            return val
    return None


def _simple_path_get(data: dict, path: str) -> Any:
    """Simple dotted-notation path getter (no complex JMESPath)."""
    parts = path.split('.')
    current = data
    
    for part in parts:
        # Handle array access like choices[0]
        if '[' in part and ']' in part:
            base = part[:part.index('[')]
            idx = int(part[part.index('[')+1:part.index(']')])
            if isinstance(current, dict) and base in current:
                current = current[base]
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
    
    return current


def detect_format(data: dict) -> str:
    """Identify response format: 'anthropic' or 'openai-compat'."""
    if "choices" in data:
        return "openai-compat"
    if "stop_reason" in data and "content" in data:
        return "anthropic"
    return "unknown"