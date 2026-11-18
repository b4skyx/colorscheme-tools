"""Vision model: which simulation the scores and optimisers use."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cvd import IDENTITY, M_TRITAN, Matrix, cvd_matrix, mat_mix

VISION_TYPES = ("deutan", "protan", "tritan", "normal")


@dataclass(frozen=True)
class VisionModel:
    """A CVD type with a severity in 0..1 (``normal`` ignores severity)."""

    type: str = "deutan"
    severity: float = 1.0

    def __post_init__(self) -> None:
        if self.type not in VISION_TYPES:
            raise ValueError(f"unknown vision type {self.type!r}; expected one of {', '.join(VISION_TYPES)}")
        if not 0.0 <= float(self.severity) <= 1.0:
            raise ValueError(f"severity must be within 0..1, got {self.severity}")

    @property
    def matrix(self) -> Matrix:
        """Linear-sRGB simulation matrix."""
        if self.type == "deutan":
            return cvd_matrix(deutan=self.severity)
        if self.type == "protan":
            return cvd_matrix(protan=self.severity)
        if self.type == "tritan":
            return mat_mix(IDENTITY, M_TRITAN, self.severity)
        return [row[:] for row in IDENTITY]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisionModel":
        """Build from ``{"type": ..., "severity": ...}`` (e.g. a ``--model`` JSON file)."""
        return cls(type=data.get("type", "deutan"), severity=float(data.get("severity", 1.0)))


DEFAULT = VisionModel()
