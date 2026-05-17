"""
Model capabilities detection - lightweight version for ThoughtLens.
"""

from dataclasses import dataclass

_caps: dict[str, 'ModelCapabilities'] = {}


@dataclass
class ModelCapabilities:
    model: str
    thinks: bool = False
    think_field: str = "thinking"
    learned: bool = False


def get_capabilities(model: str) -> ModelCapabilities:
    if model not in _caps:
        _caps[model] = ModelCapabilities(model=model)
    return _caps[model]