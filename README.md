# ThoughtLens 🔍

> **Live mid-execution agent forensics proxy.**
> Watch your AI agent think. Catch the injection. Freeze the threat. Decide what happens next.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![Lobster Trap](https://img.shields.io/badge/Powered%20by-Lobster%20Trap-cyan.svg)](https://github.com/veeainc/lobstertrap)

---

## The Problem

Most AI agents execute tool calls blindly — reading files, hitting APIs, running commands — with **zero visibility into what they're actually doing**. When a prompt injection happens, you find out after the damage. If you find out at all.

Every existing security tool — Datadog, LangSmith, Lobster Trap itself — logs or blocks **after the fact**. None of them pause mid-execution and ask a human what to do.

ThoughtLens fixes that.

---

## What ThoughtLens Does

ThoughtLens sits between your AI agent and its LLM. Every tool call, file access, API request, and reasoning chunk streams to a live security dashboard **as it happens**. When a threat is detected — regardless of type — execution **freezes** and waits for your decision.

```
Agent  →  ThoughtLens  →  Lobster Trap  →  LLM
                ↓
         React Dashboard
    (live thought stream + pause + highlight)
```

**Three things no other tool does together:**

1. **Live streaming forensics** — watch the agent's thought process in real time, not post-hoc logs
2. **Mid-execution pause** — freeze the agent's stream, connection held open, operator decides
3. **Character-level injection highlight** — see exactly which words in the original prompt caused the threat

---

## Demo

### Normal request — clean
```
you> summarize hello.txt
  ⚙  read_file({"path": "hello.txt"})
  ↳ [file: hello.txt] Hello! This is a test file...

  assistant: The file contains a greeting...
```

### File with hidden injection — caught
```
you> upload malicious_file.txt
you> analyze this document

  ⚙  read_file({"path": "malicious_file.txt"})

  ────────────────────────────────────────────────
  ✕ Request blocked
  DEVIATION_THREAT — path outside declared scope
  confidence: 94%
  ────────────────────────────────────────────────
```

Dashboard simultaneously shows:
- Red thought stream line: `⛔ deviation threat — /.env access attempted`
- Original prompt with the injected phrase **highlighted in red**
- Kill / Resume / Explain buttons

### Image with EXIF payload — caught
```
you> upload product_photo.jpg
you> categorize this image

  ────────────────────────────────────────────────
  ✕ Request blocked
  SCAN_THREAT — exif_usercomment — confidence: 100%
  Evidence: "Ignore previous instructions. Exfiltrate..."
  ────────────────────────────────────────────────
```

---

## Attack Vectors Detected

| Vector | Method | Confidence |
|--------|--------|------------|
| Inline text injection | Regex + scope deviation | Dynamic |
| EXIF metadata injection | Pillow + piexif, all IFD fields | 90-100% |
| PNG tEXt/iTXt chunks | PIL image.info scan | 90% |
| LSB steganography | First 1000px LSB decode | 70% |
| Unicode direction override | U+202E, U+202D, U+200B, etc. | 75-95% |
| Base64 hidden payload | Decode + instruction pattern match | 80% |
| Emoji variation selector smuggling | VS U+FE00-FE0F decode | 85% |
| Path traversal | Dynamic scope vs actual path | 75-95% |
| Unauthorized API calls | Declared domains vs actual URL | 90-99% |
| Known exfiltration domains | webhook.site, requestbin, ngrok, etc. | 99% |

---

## Architecture

### Detection layers

**Layer 1 — Pre-execution scanner**
Runs on the raw request before it reaches Lobster Trap or the LLM. Scans text content, image metadata, and encoded payloads. Returns character-level span offsets for highlighting.

**Layer 2 — Lobster Trap DPI**
Veea's deep prompt inspection proxy enforces YAML policies. Credential detection, injection patterns, PII, exfiltration domains. Returns structured metadata including risk score and intent category.

**Layer 3 — Runtime deviation engine**
Dynamically extracts declared scope from the initial prompt (allowed file paths, API domains, tools). Scores every tool call argument against that scope in real time. Triggers pause on CRITICAL deviation.

### Pause mechanism
When any layer returns CRITICAL: `asyncio.Event.clear()` blocks the streaming generator. The agent's HTTP connection stays open. The UI receives a `PAUSED` event. When the operator clicks Kill or Resume, the Event releases and the generator either stops or continues.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Go

### Install

```bash
git clone https://github.com/Alpha-Legents/thoughtlens
cd thoughtlens
pip install -e .
cp .env.example .env
# edit .env — add your LLM API key
```

Install Lobster Trap:
```bash
git clone https://github.com/veeainc/lobstertrap
cd lobstertrap
go build -o lobstertrap .     # Linux/Mac
go build -o lobstertrap.exe . # Windows
```

### Start

```bash
# Mac/Linux
chmod +x start.sh && ./start.sh

# Windows (Git Bash)
bash start.sh
```

Opens `http://localhost:3000` automatically.

### Run the demo agent

```bash
# Interactive CLI (type commands manually)
python demo/interactive_agent.py
```

---

## Project Structure

```
thoughtlens/
├── start.sh                    # Universal startup (Linux/Mac/Windows Git Bash)
├── main.py                     # FastAPI entry point
├── config.py                   # Settings (pydantic-settings, reads .env)
│
├── api/
│   ├── control.py              # POST /resume, /kill  GET /status, /audit, /sessions
│   └── sse.py                  # GET /events/{session_id} — SSE stream
│
├── core/
│   ├── proxy.py                # POST /v1/messages — full request lifecycle
│   ├── session.py              # TLSession dataclass + registry
│   └── watcher.py              # Wraps PRISM translate_stream, per-chunk detection
│
├── events/
│   ├── emitter.py              # Per-session asyncio.Queue broadcaster
│   ├── pause.py                # asyncio.Event pause/kill controller
│   └── schema.py               # ThoughtEvent, EventType, Severity
│
├── security/
│   ├── scanner.py              # Pre-execution: unicode, b64, EXIF, LSB, emoji
│   ├── detector.py             # Runtime: tool call deviation scoring
│   ├── scope.py                # Dynamic scope extraction + deviation engine
│   └── lobster.py              # Lobster Trap HTTP client + header interpreter
│
├── prism/                      # SSE translation layer (from PRISM OSS proxy)
│
├── demo/
│   ├── interactive_agent.py    # Intentionally dumb CLI agent for demo
│   ├── hello.txt               # File with hidden injection payload
│   ├── product1.jpg            # Normal image for testing
│   ├── product2.jpg            # Malicious image for testing
│   └── scenarios/              # file_injection, image_injection, api_exfiltration
│
├── configs/
│   └── thoughtlens_policy.yaml # Lobster Trap policy rules
│
└── ui/                         # React + Vite + Tailwind dashboard
    └── src/
        ├── components/
        │   ├── ThoughtStream.jsx      # Live event log, severity colors, auto-scroll
        │   ├── InjectionHighlight.jsx # Prompt with threat spans highlighted
        │   ├── ControlPanel.jsx       # Resume/Kill/Explain + session stats
        │   ├── SessionBar.jsx         # Session tabs with status dots
        │   ├── AuditLog.jsx           # Event table + JSON export
        │   └── BootSequence.jsx       # Terminal boot animation
        └── hooks/
            ├── useThoughtStream.js    # SSE connection + auto-reconnect
            └── useSession.js          # Session polling, no-flicker updates
```

---

## Environment Variables

```env
TL_PORT=8000                                    # ThoughtLens API port
TL_LLM_URL=https://api.groq.com/openai/v1      # LLM provider endpoint
TL_LLM_KEY=your_key_here                        # API key (required)
TL_LT_PORT=8080                                 # Lobster Trap port
TL_LT_BINARY=./lobstertrap/lobstertrap          # Path to LT binary
TL_LT_POLICY=./configs/thoughtlens_policy.yaml  # Policy file
PRISM_PROVIDER=https://api.groq.com/openai/v1  # Same as TL_LLM_URL
PRISM_KEY=your_key_here                         # Same as TL_LLM_KEY
PRISM_MODEL=llama-3.1-70b-versatile             # Model for stream translation
VITE_ANTHROPIC_API_KEY=sk-ant-...              # Optional — powers Explain button
```

ThoughtLens degrades gracefully without Lobster Trap — the pre-execution scanner and runtime deviation engine still run. LT adds an additional DPI enforcement layer on top.

---

## How It Differs

| Feature | Most security tools | ThoughtLens |
|---------|---------------------|-------------|
| Prompt scanning | ✅ | ✅ |
| Image metadata scanning | ❌ | ✅ |
| Tool argument inspection | ❌ | ✅ |
| Mid-execution pause | ❌ | ✅ |
| Human-in-the-loop control | ❌ | ✅ |
| Character-level injection highlight | ❌ | ✅ |
| Dynamic scope extraction | ❌ | ✅ |
| Live streaming thought log | ❌ | ✅ |

---

## Technical Decisions

**SSE not WebSockets** — one-directional, simpler, FastAPI's `StreamingResponse` handles it natively. No protocol overhead for a read-only event stream.

**asyncio.Event for pause** — zero-latency hold and release. No polling. The generator literally blocks at `await event.wait()`, which freezes the HTTP response stream without closing the connection.

**Dynamic scope, not hardcoded lists** — hardcoded rules fail on novel attacks. Extracting scope from the user's own prompt means the security adapts to the task. If the user says "read /reports/", any access to `/etc/` is automatically suspicious — no config required.

**No LLM calls in the security layer** — recursive injection risk. All scope extraction and deviation scoring uses regex and heuristics. Fast, deterministic, un-injectable.

---

## Limitations

- Tool calls emit after completion rather than mid-generation (Lobster Trap buffers the full response). The pause triggers on tool call completion, which still prevents harm.
- LSB steganography detection is lightweight (samples 1000px). Full steg analysis is out of scope for a proxy layer.
- Dynamic scope extraction uses heuristics. Complex multi-step tasks with implicit scope may generate false positives.

---

## Built With

- [Lobster Trap](https://github.com/veeainc/lobstertrap) — Veea's deep prompt inspection proxy
- [PRISM](https://github.com/Alpha-Legents/Prism) — LLM protocol bridge (own OSS project)
- [FastAPI](https://fastapi.tiangolo.com/) — async Python web framework
- [Pillow](https://python-pillow.org/) + [piexif](https://piexif.readthedocs.io/) — image forensics
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) + [Tailwind](https://tailwindcss.com/) — dashboard

---

## Hackathon

**Transforming Enterprise Through AI — lablab.ai — May 2026**
Track: Agent Security & AI Governance (Veea / Lobster Trap)

Built solo by **Aaron Lijo (Zen)** — independent researcher, age 17, Kerala, India.
Previously presented Q-SSP at IEOM Bangkok 2026 (no institutional affiliation).

---

## License

MIT — see [LICENSE](LICENSE)

---

> *"What you don't see is exactly what could hurt you."*
