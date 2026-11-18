"""Eza theme.yml using the keys documented by eza_colors-explanation(5)."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

# Each leaf is a role with an optional explicit bold flag.
SECTIONS: dict[str, dict[str, str]] = {
    "filekinds": {
        "normal": "ui.fg", "directory": "syntax.function bold", "symlink": "syntax.type",
        "pipe": "syntax.punctuation", "block_device": "diagnostic.warning", "char_device": "diagnostic.warning",
        "socket": "syntax.constant", "special": "syntax.constant", "executable": "git.add bold",
        "mount_point": "syntax.function bold",
    },
    "perms": {
        "user_read": "git.add", "user_write": "git.change", "user_execute_file": "git.add bold",
        "user_execute_other": "git.add", "group_read": "git.add", "group_write": "git.change",
        "group_execute": "git.add", "other_read": "ui.fg_dim", "other_write": "git.change",
        "other_execute": "git.add", "special_user_file": "diagnostic.warning", "special_other": "diagnostic.warning",
        "attribute": "syntax.attribute",
    },
    "size": {
        "major": "syntax.number", "minor": "syntax.number", "number_byte": "ui.fg_dim",
        "number_kilo": "syntax.number", "number_mega": "syntax.constant", "number_giga": "diagnostic.warning",
        "number_huge": "diagnostic.error", "unit_byte": "ui.fg_dim", "unit_kilo": "syntax.number",
        "unit_mega": "syntax.constant", "unit_giga": "diagnostic.warning", "unit_huge": "diagnostic.error",
    },
    "users": {
        "user_you": "ui.fg", "user_root": "diagnostic.warning", "user_other": "ui.fg_dim",
        "group_yours": "ui.fg", "group_other": "ui.fg_dim", "group_root": "diagnostic.warning",
    },
    "links": {"normal": "ui.fg_dim", "multi_link_file": "syntax.type"},
    "git": {
        "new": "git.add", "modified": "git.change", "deleted": "git.delete", "renamed": "git.change",
        "ignored": "ui.comment", "conflicted": "diagnostic.error",
    },
    "git_repo": {
        "branch_main": "syntax.function", "branch_other": "syntax.type", "git_clean": "git.add", "git_dirty": "git.change",
    },
    "file_type": {
        "image": "syntax.type", "video": "syntax.constant", "music": "syntax.string", "crypto": "git.add",
        "document": "syntax.string", "compressed": "git.delete", "temp": "ui.comment",
        "compiled": "syntax.number", "build": "syntax.keyword", "source": "ui.fg",
    },
}
LEAVES: dict[str, str] = {
    "punctuation": "syntax.punctuation", "date": "ui.fg_dim", "inode": "ui.comment", "blocks": "ui.fg_dim",
    "header": "syntax.function bold", "octal": "syntax.number", "flags": "syntax.attribute",
    "control_char": "diagnostic.warning", "broken_symlink": "diagnostic.error", "broken_path_overlay": "git.delete",
}


def _style(scheme: Scheme, spec: str, indent: str) -> str:
    role, *flags = spec.split()
    return (f'{indent}foreground: "{scheme.resolve(role)}"\n'
            + (f"{indent}is_bold: true\n" if "bold" in flags else ""))


@register
class Eza(Target):
    name = "eza"
    scope = "scheme"
    description = "eza file listing theme (YAML)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        text = ctx.header("#", scheme, "copy to $EZA_CONFIG_DIR/theme.yml")
        for section, values in SECTIONS.items():
            text += f"{section}:\n"
            for key, spec in values.items():
                text += f"  {key}:\n" + _style(scheme, spec, "    ")
        for key, spec in LEAVES.items():
            text += f"{key}:\n" + _style(scheme, spec, "  ")
        return {f"{scheme.id}/eza.yml": text}
