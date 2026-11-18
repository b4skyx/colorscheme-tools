"""Recipe → ``Scheme``: editor accents, then the terminal, assembled by ``assemble_scheme``."""
from __future__ import annotations

from ..scheme.assemble import assemble_scheme
from ..scheme.model import ANSI_NAMES, Scheme
from ..vision.model import DEFAULT, VisionModel
from .editor import optimize_editor
from .recipe import Recipe
from .terminal import EXTREMES, extremes, optimize_terminal

METRIC = "CIEDE2000 on simulated colours"


def optimize_recipe(recipe: Recipe, model: VisionModel = DEFAULT) -> Scheme:
    """Optimise the editor roles and ANSI colours of ``recipe`` for ``model`` and build a v2 scheme."""
    accents = optimize_editor(recipe, model)
    term = optimize_terminal(recipe, accents, model)
    ext = extremes(recipe)
    normal = {k: term.normal.get(k, ext.get(f"normal.{k}")) for k in ANSI_NAMES}
    bright = {k: term.bright.get(k, ext.get(f"bright.{k}")) for k in ANSI_NAMES}
    meta = {
        "id": recipe.id, "name": recipe.name, "variant": recipe.variant, "family": recipe.family,
        "description": recipe.description, "tags": recipe.tags,
        "designed_for": {"vision": model.type, "severity": model.severity, "metric": METRIC},
    }
    formulas = [v for v in EXTREMES[recipe.variant].values() if isinstance(v, dict)]
    return assemble_scheme(meta, recipe.base, accents, recipe.styles, normal, bright, terminal_formulas=formulas)
