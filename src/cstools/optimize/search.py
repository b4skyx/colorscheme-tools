"""Seeded hill-climb over named OKLCH points.

Each step perturbs one randomly chosen point with Gaussian noise (full step sizes for the first 60 % of
the iterations, then 40 %), clamps lightness and chroma to the point's bounds, and keeps the candidate
if the objective improves. Restarts begin from jittered copies of the start points. The random-number
consumption order is fixed (choice, gauss L, gauss C, gauss h per step; gauss L, gauss h per point per
jitter) so results reproduce exactly for a given seed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Mapping

#: OKLCH ``(L, C, hue_degrees)``.
Point = tuple[float, float, float]
Points = dict[str, Point]
#: ``objective(candidate, origin)``: higher is better; ``origin`` holds the current restart's start points.
Objective = Callable[[Points, Points], float]


@dataclass(frozen=True)
class Bounds:
    """Hard clamps applied after each perturbation: ``min(hi, max(lo, x))``."""

    l_min: float
    l_max: float
    c_min: float
    c_max: float


@dataclass(frozen=True)
class Schedule:
    """Perturbation step sizes (standard deviations) and restart jitter."""

    sigma_l: float = 0.03
    sigma_c: float = 0.015
    sigma_h: float = 7.0
    late_fraction: float = 0.6
    late_scale: float = 0.4
    jitter_l: float = 0.02
    jitter_h: float = 8.0


@dataclass(frozen=True)
class SearchResult:
    """Best points found and their objective value."""

    points: Points
    score: float


def climb(start: Mapping[str, Point], objective: Objective, bounds: Callable[[str], Bounds], iterations: int,
          rnd: random.Random, schedule: Schedule = Schedule(), origin: Mapping[str, Point] | None = None
          ) -> SearchResult:
    """One hill-climb from ``start``; ``origin`` (default ``start``) is passed through to ``objective``."""
    origin_points = dict(origin if origin is not None else start)
    cur = dict(start)
    s = objective(cur, origin_points)
    for i in range(iterations):
        k = rnd.choice(list(cur))
        L, C, h = cur[k]
        scale = 1.0 if i < iterations * schedule.late_fraction else schedule.late_scale
        b = bounds(k)
        nxt = dict(cur)
        nxt[k] = (min(b.l_max, max(b.l_min, L + rnd.gauss(0, schedule.sigma_l * scale))),
                  min(b.c_max, max(b.c_min, C + rnd.gauss(0, schedule.sigma_c * scale))),
                  (h + rnd.gauss(0, schedule.sigma_h * scale)) % 360)
        s2 = objective(nxt, origin_points)
        if s2 > s:
            cur, s = nxt, s2
    return SearchResult(cur, s)


def search(start: Mapping[str, Point], objective: Objective, bounds: Callable[[str], Bounds], iterations: int,
           restarts: int = 1, seed: int = 1, schedule: Schedule = Schedule()) -> SearchResult:
    """Best of ``restarts`` climbs. Restart ``r + 1`` starts from restart ``r``'s start points with
    lightness and hue jittered; that jittered set is also the ``origin`` its objective sees."""
    rnd = random.Random(seed)
    origin = dict(start)
    best: SearchResult | None = None
    for r in range(restarts):
        result = climb(origin, objective, bounds, iterations, rnd, schedule)
        if best is None or result.score > best.score:
            best = result
        if r < restarts - 1:
            origin = {k: (L + rnd.gauss(0, schedule.jitter_l), C, (h + rnd.gauss(0, schedule.jitter_h)) % 360)
                      for k, (L, C, h) in origin.items()}
    if best is None:
        raise ValueError("search: restarts must be at least 1")
    return best
