"""Colour-vision-deficiency simulation (Machado, Oliveira & Fernandes 2009) in linear sRGB."""
from __future__ import annotations

from ..color.difference import ciede2000
from ..color.spaces import Triple, hex_to_linear, linear_to_hex, linear_to_lab

Matrix = list[list[float]]

# Machado et al. 2009, severity 1.0, linear sRGB
M_PROTAN: Matrix = [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]
M_DEUTAN: Matrix = [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]
M_TRITAN: Matrix = [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]
IDENTITY: Matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def mat_mix(a: Matrix, b: Matrix, w: float) -> Matrix:
    """Element-wise blend ``(1 - w) * a + w * b``."""
    return [[(1 - w) * a[i][j] + w * b[i][j] for j in range(3)] for i in range(3)]


def mat_apply(m: Matrix, v: list[float]) -> list[float]:
    """Matrix × vector."""
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def cvd_matrix(protan: float = 0.0, deutan: float = 0.0, mix: float | None = None) -> Matrix:
    """Severity model.

    With ``mix`` (0 = pure deutan … 1 = pure protan) build a blended dichromat with severity
    ``max(protan, deutan)``; otherwise compose the two partial matrices (protan after deutan).
    """
    if mix is not None:
        s = max(protan, deutan)
        return mat_mix(IDENTITY, mat_mix(M_DEUTAN, M_PROTAN, mix), s)
    a, b = mat_mix(IDENTITY, M_DEUTAN, deutan), mat_mix(IDENTITY, M_PROTAN, protan)
    return [[sum(b[i][k] * a[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def simulate(h: str, m: Matrix) -> str:
    """Hex colour as seen through matrix ``m`` (clamped to sRGB)."""
    return linear_to_hex(mat_apply(m, hex_to_linear(h)))


def seen_lab(h: str, m: Matrix) -> Triple:
    """CIELAB of ``h`` as seen through matrix ``m``."""
    return linear_to_lab(mat_apply(m, hex_to_linear(h)))


def de_seen(h1: str, h2: str, m: Matrix) -> float:
    """CIEDE2000 between two colours after simulation through ``m``."""
    return ciede2000(seen_lab(h1, m), seen_lab(h2, m))
