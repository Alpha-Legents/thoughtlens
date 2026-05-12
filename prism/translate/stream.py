"""
SSE stream translator for ThoughtLens.
Converts any provider's SSE stream to Anthropic format expected by clients.
"""

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger("thoughtlens.prism.stream")


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def translate_stream(
    chunks: AsyncIterator[str],
    client_format: str,
    model: str,
    msg_id: str = "msg_thoughtlens",
) -> AsyncIterator[str]:
    """
    Translate SSE stream to client-expected format.
    
    Args:
        chunks: Raw SSE chunks from provider
        client_format: 'anthropic' or 'openai-compat'
        model: Model name
        msg_id: Message ID for response
    
    Yields:
        SSE-formatted strings ready to send to client
    """
    if client_format != "anthropic":
        # For non-Anthropic clients, pass through raw
        async for chunk in chunks:
            yield chunk
        return
    
    # State for streaming translation
    text_buf = ""
    tool_bufs: dict[int, dict] = {}
    has_text = False
    has_thinking = False
    content_block_idx = 0
    input_tokens = 0
    output_tokens = 0
    finish_reason = "end_turn"
    started = False
    
    async for raw_chunk in chunks:
        line = raw_chunk.strip()
        
        if not line or line == "data: [DONE]":
            continue
        
        if not line.startswith("data:"):
            continue
        
        try:
            chunk = json.loads(line[5:].strip())
        except Exception:
            continue
        
        choice = (chunk.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        fin_reason = choice.get("finish_reason")
        
        # Track token usage
        usage = chunk.get("usage") or {}
        if usage.get("prompt_tokens"):
            input_tokens = usage["prompt_tokens"]
        if usage.get("completion_tokens"):
            output_tokens = usage["completion_tokens"]
        
        # Emit message_start on first real chunk
        if not started:
            started = True
            yield _sse("message_start", {
                "type": "message_start",
                "message": {
                    "id": msg_id,
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": input_tokens, "output_tokens": 0},
                },
            })
        
        # Handle text delta
        delta_content = delta.get("content")
        if isinstance(delta_content, str) and delta_content:
            if not has_text:
                if has_thinking:
                    yield _sse("content_block_stop", {"type": "content_block_stop", "index": content_block_idx})
                    content_block_idx += 1
                has_text = True
                yield _sse("content_block_start", {
                    "type": "content_block_start",
                    "index": content_block_idx,
                    "content_block": {"type": "text", "text": ""},
                })
            text_buf += delta_content
            yield _sse("content_block_delta", {
                "type": "content_block_delta",
                "index": content_block_idx,
                "delta": {"type": "text_delta", "text": delta_content},
            })
        
        # Handle tool calls - buffer them
        tool_calls = delta.get("tool_calls") or []
        for tc in tool_calls:
            idx = tc.get("index", 0)
            if idx not in tool_bufs:
                tool_bufs[idx] = {
                    "id": tc.get("id", f"toolu_{idx}"),
                    "name": (tc.get("function") or {}).get("name", ""),
                    "args_buf": "",
                }
            fn = tc.get("function") or {}
            if fn.get("arguments"):
                tool_bufs[idx]["args_buf"] += fn["arguments"]
        
        # Handle finish reason
        if fin_reason:
            finish_reason = {
                "tool_calls": "tool_use",
                "stop": "end_turn",
                "length": "max_tokens",
            }.get(fin_reason, "end_turn")
    
    # Emit buffered tool calls
    if tool_bufs:
        finish_reason = "tool_use"
        
        # Close open text/thinking block
        if has_text or has_thinking:
            yield _sse("content_block_stop", {"type": "content_block_stop", "index": content_block_idx})
            content_block_idx += 1
        
        for idx in sorted(tool_bufs.keys()):
            tc = tool_bufs[idx]
            try:
                args = json.loads(tc["args_buf"] or "{}")
            except Exception:
                args = {"_raw": tc["args_buf"]}
            
            yield _sse("content_block_start", {
                "type": "content_block_start",
                "index": content_block_idx,
                "content_block": {
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": {},
                },
            })
            if tc["args_buf"]:
                yield _sse("content_block_delta", {
                    "type": "content_block_delta",
                    "index": content_block_idx,
                    "delta": {"type": "input_json_delta", "partial_json": tc["args_buf"]},
                })
            yield _sse("content_block_stop", {"type": "content_block_stop", "index": content_block_idx})
            content_block_idx += 1
    
    elif has_text or has_thinking:
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": content_block_idx})
    
    # Handle empty response
    if not started:
        yield _sse("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id, "type": "message", "role": "assistant",
                "model": model, "content": [], "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })
    
    # Final events
    yield _sse("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": finish_reason, "stop_sequence": None},
        "usage": {"output_tokens": output_tokens},
    })
    yield _sse("message_stop", {"type": "message_stop"})