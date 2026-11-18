"""Output targets. Every module in this package is imported so its ``@register`` classes appear in ``REGISTRY``."""
from __future__ import annotations

import importlib
import pkgutil

from .base import REGISTRY, RenderContext, Target, register

for _module in sorted(m.name for m in pkgutil.iter_modules(__path__)):
    if _module != "base" and not _module.startswith("_"):
        importlib.import_module(f"{__name__}.{_module}")

__all__ = ["REGISTRY", "RenderContext", "Target", "register"]
