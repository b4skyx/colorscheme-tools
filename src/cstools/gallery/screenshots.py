"""PNG previews of gallery schemes via headless Firefox.

Uses a throwaway profile per shot (never the user's profile). Snap-packaged Firefox can only read and
write under ``$HOME``, so profiles then live in ``~/snap/firefox/common`` and are removed afterwards.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable


def find_firefox() -> str | None:
    """Path of a Firefox binary, or ``None``."""
    return shutil.which("firefox")


def _profile_root() -> Path:
    snap_home = Path.home() / "snap" / "firefox" / "common"
    if Path("/snap/firefox").exists():
        snap_home.mkdir(parents=True, exist_ok=True)
        return snap_home
    return Path(tempfile.gettempdir())


def preview_url(gallery_dir: str | Path, scheme_id: str, lang: str = "lua") -> str:
    """URL of the chromeless single-scheme preview in a built gallery."""
    return (Path(gallery_dir).resolve() / "index.html").as_uri() + f"?mode=preview&sel={scheme_id}&lang={lang}"


def capture_previews(gallery_dir: str | Path, scheme_ids: Iterable[str], out_dir: str | Path, *, lang: str = "lua",
                     size: tuple[int, int] = (1600, 900), firefox: str | None = None,
                     timeout: float = 120) -> list[Path]:
    """Screenshot ``mode=preview`` for each scheme into ``out_dir/<id>.png``; returns the written paths."""
    firefox = firefox or find_firefox()
    if not firefox:
        raise RuntimeError("firefox not found; screenshots need a headless-capable Firefox")
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for sid in scheme_ids:
        png = out / f"{sid}.png"
        profile = tempfile.mkdtemp(prefix="cstools-ff-", dir=_profile_root())
        try:
            subprocess.run([firefox, "--headless", "--no-remote", "--profile", profile, f"--window-size={size[0]},{size[1]}",
                            "--screenshot", str(png), preview_url(gallery_dir, sid, lang)],
                           check=True, timeout=timeout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           env={**os.environ, "MOZ_HEADLESS": "1"})
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        if not png.exists() or png.stat().st_size == 0:
            raise RuntimeError(f"firefox produced no screenshot for {sid}")
        written.append(png)
    return written
