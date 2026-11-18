"""Derived-colour expressions.

A colour value is a ``"#rrggbb"`` literal (palette only), a name (``"bg"``), a role path
(``"syntax.type"``) or a one-key expression object::

    {"mix": [a, b, t]}  {"lighten": [c, dL]}  {"darken": [c, dL]}  {"raise": [c, dL]}  {"chroma": [c, C]}

Every operation rounds to hex, so nested expressions reproduce the step-by-step schema v1 reference results.
"""
from __future__ import annotations

from typing import Any, Callable, Iterator

from ..color import ops
from ..color.spaces import is_hex

ColorValue = Any  # str | dict[str, list]
Lookup = Callable[[str], str]

#: operation name → number of colour arguments followed by one number
OPERATIONS: dict[str, int] = {"mix": 2, "lighten": 1, "darken": 1, "raise": 1, "chroma": 1}


class SchemeError(ValueError):
    """Invalid scheme content: unknown reference, cycle, bad expression or misplaced literal."""


def check_shape(value: ColorValue) -> None:
    """Raise ``SchemeError`` unless ``value`` is syntactically a colour value (literals allowed)."""
    if isinstance(value, str):
        if not value:
            raise SchemeError("empty colour reference")
        return
    if not isinstance(value, dict) or len(value) != 1:
        raise SchemeError(f"colour value must be a string or a one-key expression object, got {value!r}")
    (op, args), = value.items()
    if op not in OPERATIONS:
        raise SchemeError(f"unknown operation {op!r}; expected one of {', '.join(OPERATIONS)}")
    n = OPERATIONS[op]
    if not isinstance(args, list) or len(args) != n + 1:
        raise SchemeError(f"{op!r} takes {n + 1} arguments, got {args!r}")
    if isinstance(args[-1], bool) or not isinstance(args[-1], (int, float)):
        raise SchemeError(f"last argument of {op!r} must be a number, got {args[-1]!r}")
    for a in args[:n]:
        check_shape(a)


def references(value: ColorValue) -> Iterator[str]:
    """Yield the names, role paths and literals a colour value refers to directly."""
    if isinstance(value, str):
        yield value
        return
    check_shape(value)
    (op, args), = value.items()
    for a in args[:OPERATIONS[op]]:
        yield from references(a)


def evaluate(value: ColorValue, lookup: Lookup, light: bool, allow_literal: bool = False) -> str:
    """Evaluate ``value`` to a lowercase hex string.

    ``lookup`` resolves names and role paths; ``light`` selects the direction of ``raise``.
    Literals raise ``SchemeError`` unless ``allow_literal``.
    """
    if isinstance(value, str):
        if is_hex(value):
            if not allow_literal:
                raise SchemeError(f"hex literal {value} is only allowed in palette")
            return value.lower()
        return lookup(value)
    check_shape(value)
    (op, args), = value.items()
    colours = [evaluate(a, lookup, light, allow_literal) for a in args[:OPERATIONS[op]]]
    x = float(args[-1])
    if op == "mix":
        return ops.mix(colours[0], colours[1], x)
    if op == "lighten":
        return ops.lighten(colours[0], x)
    if op == "darken":
        return ops.darken(colours[0], x)
    if op == "raise":
        return ops.raise_(colours[0], x, light)
    return ops.with_chroma(colours[0], x)
