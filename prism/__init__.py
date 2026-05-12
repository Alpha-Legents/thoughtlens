"""
Prism - LLM protocol bridge for ThoughtLens
Lightweight version - only what's needed for stream translation
"""

from .slots import extract, detect_format
from .translate.stream import translate_stream

__all__ = ["extract", "detect_format", "translate_stream"]