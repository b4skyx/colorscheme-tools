"""Lazygit GUI theme, emitted as a mergeable YAML fragment."""
from __future__ import annotations

import json

from ..scheme.model import Scheme
from .base import RenderContext, Target, register


@register
class Lazygit(Target):
    name = "lazygit"
    scope = "scheme"
    description = "Lazygit GUI theme (YAML fragment)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r = scheme.resolve
        values = {
            "activeBorderColor": [r("syntax.function"), "bold"],
            "inactiveBorderColor": [r("border")],
            "searchingActiveBorderColor": [r("diagnostic.warning"), "bold"],
            "optionsTextColor": [r("syntax.function")],
            "selectedLineBgColor": [r("bg_visual")],
            "inactiveViewSelectedLineBgColor": [r("bg_cursorline")],
            "cherryPickedCommitFgColor": [r("git.add")],
            "cherryPickedCommitBgColor": [r("diff_add_bg")],
            "markedBaseCommitFgColor": [r("git.change")],
            "markedBaseCommitBgColor": [r("diff_change_bg")],
            "unstagedChangesColor": [r("git.delete")],
            "defaultFgColor": [r("ui.fg")],
        }
        text = (ctx.header("#", scheme, "merge gui.theme into lazygit/config.yml") + "gui:\n  theme:\n"
                + "".join(f"    {key}: {json.dumps(value)}\n" for key, value in values.items()))
        return {f"{scheme.id}/lazygit.yml": text}
