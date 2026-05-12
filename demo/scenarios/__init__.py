"""
Security testing scenarios for ThoughtLens.

These scenarios demonstrate various attack vectors against an AI agent:
- File injection: Hidden file access in prompt
- Image injection: EXIF data exfiltration via images
- API exfiltration: Hidden domain exfiltration in API calls
"""

__version__ = "1.0.0"
__all__ = [
    "file_injection",
    "image_injection",
    "api_exfiltration"
]