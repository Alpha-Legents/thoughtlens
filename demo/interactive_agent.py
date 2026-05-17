#!/usr/bin/env python3
"""
DUMB CLIENT - Simplified to work with ThoughtLens
"""

import os
import sys
import json
import base64
import argparse
import uuid
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

BANNER = """
+-------------------------------------------------------------------+
|                                                                   |
|     ██████╗ ██╗   ██╗███╗   ███╗██████╗     ██████╗██╗     ██╗    |
|     ██╔══██╗██║   ██║████╗ ████║██╔══██╗    ██╔════╝██║     ██║    |
|     ██║  ██║██║   ██║██╔████╔██║██████╔╝    ██║     ██║     ██║    |
|     ██║  ██║██║   ██║██║╚██╔╝██║██╔══██╗    ██║     ██║     ██║    |
|     ██████╔╝╚██████╔╝██║ ╚═╝ ██║██████╔╝    ╚██████╗███████╗██║    |
|     ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝      ╚═════╝╚══════╝╚═╝    |
|                                                                   |
|                    DUMB CLI CLIENT v1.0                           |
|                                                                   |
+-------------------------------------------------------------------+
"""


def execute_tool(name: str, args: dict) -> str:
    print(f"  [EXECUTE] {name}({json.dumps(args)})")
    
    if name == "read_file":
        try:
            with open(args["path"], "r", errors="replace") as f:
                return f"[FILE: {args['path']}]\n{f.read(2000)}"
        except Exception as e:
            return f"Error: {e}"
    
    if name == "call_api":
        try:
            resp = requests.request(args.get("method", "GET"), args["url"], timeout=15)
            return f"HTTP {resp.status_code}\n{resp.text[:800]}"
        except Exception as e:
            return f"Error: {e}"
        
    if name == "analyze_image":
        try:
            # For demo, just read the file (scanner will detect EXIF)
            with open(args["image_path"], "rb") as f:
                content = f.read()
            return f"[IMAGE] Successfully read {len(content)} bytes from {args['image_path']}"
        except Exception as e:
            return f"Error reading image: {e}"
    
    return f"Unknown tool: {name}"


class SimpleClient:
    def __init__(self, api_url: str, model: str):
        self.api_url = api_url
        self.model = model
        self.history = []
        self.session_id = str(uuid.uuid4())
    
    def send(self, user_text: str):
        # NEW: Check if user typed a direct image path (no "analyze" or anything)
        if Path(user_text).exists() and user_text.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            print(f"  [IMAGE] Sending image for analysis: {user_text}")
            img_data_url = self.encode_image_to_base64(user_text)
            if img_data_url:
                # Send as multimodal message directly
                payload = {
                    "session_id": self.session_id,
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Analyze this image and describe what you see"},
                                {"type": "image_url", "image_url": {"url": img_data_url}}
                            ]
                        }
                    ]
                }
                try:
                    resp = requests.post(self.api_url, json=payload, timeout=60)
                    if resp.status_code == 202:
                        print("\n  [PAUSED] Malicious content detected in image!")
                        print("  Check the ThoughtLens dashboard for details\n")
                    elif resp.status_code == 200:
                        # Parse response
                        result = resp.json()
                        if result.get("choices"):
                            content = result["choices"][0].get("message", {}).get("content", "")
                            print(f"\n  [ASSISTANT] {content}\n")
                    elif resp.status_code == 403:
                        print("\n  [BLOCKED] Image contains prohibited content\n")
                    else:
                        print(f"\n  [RESPONSE] {resp.text[:200]}\n")
                except Exception as e:
                    print(f"\n  [ERROR] {e}\n")
                return
        # Add system prompt if not already in history
        if not any(msg.get("role") == "system" for msg in self.history):
                        self.history.insert(0, {"role": "system", "content": """You are a helpful assistant. 

Stay conversational by default. Only invoke the read_file or analyze_image tools when there is a clear, functional need to process external data to answer the user's specific request. 

If the user is just talking about files, images, or technical concepts in general, simply reply with text. Use your tools as a last resort for practical data extraction, not as a reaction to keywords."""})
    
        # 1. Add user message to history (handle image detection)
        if user_text != "Continue with the tool result":
            # Check if user typed an image file path
            if user_text.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) and Path(user_text).exists():
                print(f"  [IMAGE] Loading image: {user_text}")
                img_data_url = self.encode_image_to_base64(user_text)
                if img_data_url:
                    #Create multimodal message with image
                    self.history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Analyze this image from {user_text}"},
                            {"type": "image_url", "image_url": {"url": img_data_url}}
                        ]
                    })
                else:
                    self.history.append({"role": "user", "content": user_text})
            else:
                self.history.append({"role": "user", "content": user_text})
        
        payload = {
            "session_id": self.session_id,
            "model": self.model,
            "messages": self.history,
                        "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read contents of a file from disk",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"}
                            },
                            "required": ["path"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_image",
                        "description": "Analyze an image and extract metadata",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "image_path": {"type": "string"}
                            },
                            "required": ["image_path"]
                        }
                    }
                }
            ]
        }
        
        
        try:
            resp = requests.post(self.api_url, json=payload, timeout=30)
        except Exception as e:
            print(f"\n  [ERROR] {e}\n")
            return
        
        # Handle HTTP 202 (Paused/Pending Review)
        if resp.status_code == 202:
            print("\n  [PAUSED] The request is being held for review or is currently processing.")
            return

        # Handle HTTP 403 (Blocked)
        if resp.status_code == 403:
            print("\n  [BLOCKED] Request was blocked by ThoughtLens security policy")
            try:
                print(f"  Reason: {resp.json().get('reason', 'unknown')}")
            except:
                pass
            return

        if resp.status_code == 200:
            raw_text = resp.text.strip()
            
            # 2. Check for SSE "data: " prefix and strip it
            if raw_text.startswith("data: "):
                try:
                    # Strip "data: " and parse the JSON
                    result = json.loads(raw_text[6:])
                except json.JSONDecodeError:
                    print(f"\n  [ERROR] Failed to parse streaming JSON: {raw_text[:100]}")
                    return
            else:
                # 3. Handle standard non-streaming JSON
                try:
                    result = resp.json()
                except:
                    print(f"\n  [ERROR] Unexpected response format: {raw_text[:100]}")
                    return

            # Process the parsed result
            choices = result.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
                
                if content:
                    print(f"\n  [ASSISTANT] {content}\n")
                    self.history.append({"role": "assistant", "content": content})
                
                # Handle tool calling loop
                
                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        try:
                            args = json.loads(fn.get("arguments", "{}"))
                        except:
                            args = {}
                        
                        tool_result = execute_tool(name, args)
                        print(f"  [RESULT] {tool_result[:200]}\n")
                        
                        self.history.append({"role": "tool", "content": tool_result})
                    
                    # Recursively call send to provide tool output back to the model
                    self.send("Continue with the tool result")
                    return  # Exit after scheduling the recursive call
            
    @staticmethod
    def encode_image_to_base64(image_path: str) -> str | None:
        """Read image file and return base64 data URL."""
        try:
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            # Detect image type
            ext = Path(image_path).suffix.lower()
            mime = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')
            return f"data:{mime};base64,{img_data}"
        except Exception as e:
            print(f"  [ERROR] Failed to encode image: {e}")
        return None
            

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/v1/messages")
    parser.add_argument("--model", default="meta/llama-3.1-8b-instruct")
    args = parser.parse_args()
    
    print(BANNER)
    print(f"  Endpoint: {args.url}")
    print(f"  Model: {args.model}")
    print("\n  Commands: exit | clear")
    print()
    
    client = SimpleClient(args.url, args.model)
    
    while True:
        try:
            user = input("  you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  [EXIT]\n")
            break
        
        if not user:
            continue
        if user.lower() == "exit":
            print("\n  [EXIT]\n")
            break
        if user.lower() == "clear":
            client.history = []
            print("  [CLEARED]\n")
            continue
        
        client.send(user)


if __name__ == "__main__":
    main()