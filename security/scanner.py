"""
Pre-execution scanner for hidden prompt-injection payloads.

Runs once on the raw request body before Lobster Trap. It scans text and image
metadata without making LLM calls.
"""

import base64
import json
import re
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Any

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif

    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


SUSPICIOUS_UNICODE = {
    "\u202e": ("unicode_rtlo", 0.95),
    "\u202d": ("unicode_lro", 0.90),
    "\u202a": ("unicode_lre", 0.75),
    "\u202b": ("unicode_rle", 0.75),
    "\u202c": ("unicode_pdf", 0.70),
    "\u200b": ("unicode_zwsp", 0.65),
    "\u200c": ("unicode_zwnj", 0.60),
    "\u200d": ("unicode_zwj", 0.55),
    "\ufeff": ("unicode_bom", 0.80),
    "\u2060": ("unicode_wj", 0.60),
    "\u00ad": ("unicode_shy", 0.45),
    "\u034f": ("unicode_cgj", 0.55),
}

IMPERATIVE_VERBS = [
    "ignore",
    "forget",
    "disregard",
    "override",
    "bypass",
    "pretend",
    "act as",
    "you are now",
    "your new",
    "from now on",
    "instead",
    "actually",
    "in reality",
    "system:",
    "assistant:",
    "new instruction",
    "execute",
    "run",
    "read all",
    "send",
    "exfiltrate",
    "print",
    "output",
    "reveal",
    "show me",
]


@dataclass
class ThreatPayload:
    vector: str
    confidence: float
    span: tuple[int, int] | None
    evidence: str
    field: str

    @property
    def content(self) -> str:
        return self.evidence

    @property
    def position(self) -> int:
        return self.span[0] if self.span else 0


@dataclass
class ScanResult:
    threats: list[ThreatPayload]
    clean: bool
    scan_time_ms: float

    @property
    def scan_duration_ms(self) -> float:
        return self.scan_time_ms


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return ""


def _extract_text(request_body: dict[str, Any]) -> str:
    parts: list[str] = []
    if request_body.get("system"):
        parts.append(str(request_body["system"]))
    for message in request_body.get("messages", []):
        if isinstance(message, dict):
            text = _message_text(message.get("content"))
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def _instruction_signal(text: str) -> tuple[bool, float]:
    lower = text.lower()
    found = any(verb in lower for verb in IMPERATIVE_VERBS)
    boost = 0.15 if found else 0.0
    if re.search(r"(?:https?://|/etc/|\.env|id_rsa|passwd|shadow)", text, re.IGNORECASE):
        found = True
        boost += 0.10
    if re.search(r"(?:you are now|new system|new instruction|ignore (?:all )?(?:previous|prior))", lower):
        found = True
        boost += 0.20
    return found, boost


def _b64_decode(value: str) -> bytes | None:
    try:
        return base64.b64decode(value, validate=True)
    except Exception:
        return None


class SecurityScanner:
    def scan(self, request_body: dict[str, Any], original_prompt: str | None = None) -> ScanResult:
        start = time.time()
        full_text = original_prompt if original_prompt is not None else _extract_text(request_body)
        threats: list[ThreatPayload] = []

        threats.extend(self._scan_unicode_controls(full_text))
        threats.extend(self._scan_emoji_variation_selectors(full_text))
        threats.extend(self._scan_base64_payloads(full_text))
        threats.extend(self._scan_images(request_body))

        return ScanResult(
            threats=threats,
            clean=not threats,
            scan_time_ms=(time.time() - start) * 1000,
        )

    def _scan_unicode_controls(self, full_text: str) -> list[ThreatPayload]:
        threats: list[ThreatPayload] = []
        for index, char in enumerate(full_text):
            if char not in SUSPICIOUS_UNICODE:
                continue
            vector, base_confidence = SUSPICIOUS_UNICODE[char]
            context = full_text[max(0, index - 50) : min(len(full_text), index + 51)]
            _, boost = _instruction_signal(context)
            threats.append(
                ThreatPayload(
                    vector=vector,
                    confidence=min(base_confidence + boost, 1.0),
                    span=(index, index + 1),
                    evidence=context,
                    field="user_message",
                )
            )
        return threats

    def _scan_emoji_variation_selectors(self, full_text: str) -> list[ThreatPayload]:
        threats: list[ThreatPayload] = []
        pattern = re.compile(r"[\U0001f300-\U0001faff]([\ufe00-\ufe0f]{2,})")
        for match in pattern.finditer(full_text):
            selectors = match.group(1)
            nibbles = [ord(char) - 0xFE00 for char in selectors]
            if len(nibbles) < 16:
                continue
            decoded = bytes((nibbles[i] << 4) | nibbles[i + 1] for i in range(0, len(nibbles) - 1, 2))
            decoded_text = decoded.decode("ascii", errors="ignore")
            has_instruction, boost = _instruction_signal(decoded_text)
            if has_instruction:
                threats.append(
                    ThreatPayload(
                        vector="emoji_vs_smuggling",
                        confidence=min(0.85 + boost, 1.0),
                        span=match.span(),
                        evidence=decoded_text,
                        field="user_message",
                    )
                )
        return threats

    def _scan_base64_payloads(self, full_text: str) -> list[ThreatPayload]:
        threats: list[ThreatPayload] = []
        pattern = r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{20,}={0,2})(?![A-Za-z0-9+/=])"
        for match in re.finditer(pattern, full_text):
            encoded = match.group(1)
            decoded = _b64_decode(encoded)
            if not decoded:
                continue
            decoded_text = decoded.decode("utf-8", errors="ignore")
            has_instruction, boost = _instruction_signal(decoded_text)
            if has_instruction:
                threats.append(
                    ThreatPayload(
                        vector="b64_hidden_payload",
                        confidence=min(0.80 + boost, 1.0),
                        span=match.span(1),
                        evidence=decoded_text,
                        field="user_message",
                    )
                )
        return threats

    def _scan_images(self, request_body: dict[str, Any]) -> list[ThreatPayload]:
        threats: list[ThreatPayload] = []
        for field, image_bytes in self._extract_base64_images(request_body):
            image_threats = self._scan_image_metadata(field, image_bytes)
            threats.extend(image_threats)
            if not image_threats:
                threats.extend(self._scan_lsb(field, image_bytes))
        return threats

    def _extract_base64_images(self, value: Any, field: str = "request") -> list[tuple[str, bytes]]:
        images: list[tuple[str, bytes]] = []
        if isinstance(value, dict):
            if value.get("type") in {"image", "image_url"}:
                source = value.get("source") if isinstance(value.get("source"), dict) else value
                raw = source.get("data") or source.get("base64") or source.get("url")
                if isinstance(raw, str):
                    image_bytes = self._decode_image_string(raw)
                    if image_bytes:
                        images.append((field, image_bytes))
            for key, nested in value.items():
                images.extend(self._extract_base64_images(nested, f"{field}.{key}"))
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                images.extend(self._extract_base64_images(nested, f"{field}[{index}]"))
        elif isinstance(value, str):
            image_bytes = self._decode_image_string(value)
            if image_bytes:
                images.append((field, image_bytes))
        return images

    def _decode_image_string(self, value: str) -> bytes | None:
        if value.startswith("data:image") and "," in value:
            return _b64_decode(value.split(",", 1)[1])
        if re.fullmatch(r"[A-Za-z0-9+/]{100,}={0,2}", value):
            return _b64_decode(value)
        return None

    def _scan_image_metadata(self, field: str, image_bytes: bytes) -> list[ThreatPayload]:
        threats: list[ThreatPayload] = []
        if not PIL_AVAILABLE:
            return threats

        try:
            image = Image.open(BytesIO(image_bytes))
        except Exception:
            return threats

        for key, value in image.info.items():
            if key == "exif":
                continue
            text = self._metadata_to_text(value)
            has_instruction, boost = _instruction_signal(text)
            if has_instruction:
                threats.append(
                    ThreatPayload(
                        vector=f"png_text_{key}",
                        confidence=min(0.90 + boost, 1.0),
                        span=None,
                        evidence=text,
                        field=f"image_png_{key}",
                    )
                )

        if not PIEXIF_AVAILABLE:
            return threats

        try:
            exif_bytes = image.info.get("exif", b"")
            exif = piexif.load(exif_bytes or image_bytes)
        except Exception:
            return threats

        for ifd_name, values in exif.items():
            if not isinstance(values, dict):
                continue
            for tag, value in values.items():
                text = self._metadata_to_text(value)
                has_instruction, boost = _instruction_signal(text)
                if has_instruction:
                    tag_name = str(tag)
                    threats.append(
                        ThreatPayload(
                            vector=f"exif_{ifd_name}_{tag_name}",
                            confidence=min(0.90 + boost, 1.0),
                            span=None,
                            evidence=text,
                            field=f"image_exif_{ifd_name}_{tag_name}",
                        )
                    )
        return threats

    def _scan_lsb(self, field: str, image_bytes: bytes) -> list[ThreatPayload]:
        if not PIL_AVAILABLE or len(image_bytes) > 5 * 1024 * 1024:
            return []
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return []

        bits: list[int] = []
        width, height = image.size
        limit = min(width * height, 1000)
        for index, pixel in enumerate(image.getdata()):
            if index >= limit:
                break
            bits.append(pixel[0] & 1)

        payload = bytes(
            int("".join(str(bit) for bit in bits[i : i + 8]), 2)
            for i in range(0, len(bits) - 7, 8)
        )
        text = payload.decode("ascii", errors="ignore")
        has_instruction, boost = _instruction_signal(text)
        if not has_instruction:
            return []
        return [
            ThreatPayload(
                vector="lsb_steganography",
                confidence=min(0.70 + boost, 1.0),
                span=None,
                evidence=text,
                field=f"{field}.lsb",
            )
        ]

    def _metadata_to_text(self, value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            return value
        if isinstance(value, (tuple, list)):
            return " ".join(self._metadata_to_text(item) for item in value)
        return str(value)


def scan(request_body: dict[str, Any], original_prompt: str | None = None) -> ScanResult:
    return SecurityScanner().scan(request_body, original_prompt)


def scan_request(request_body: dict[str, Any]) -> ScanResult:
    return scan(request_body)


__all__ = ["ScanResult", "ThreatPayload", "SecurityScanner", "scan", "scan_request"]
