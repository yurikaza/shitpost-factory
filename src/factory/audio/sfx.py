"""Stage 3b. Music bed and sound effects.

Only CC0 / Pixabay License audio (docs/research-2026.md section 5.4).
"Royalty-free" does not mean cleared on every platform - bake pre-cleared audio
into the render, platform-native audio libraries are not reachable via API.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_MUSIC_DIR = _PROJECT_ROOT / "assets" / "music"
_SFX_DIR = _PROJECT_ROOT / "assets" / "sfx"


def find_music(mood: str) -> Path | None:
    """Find a music bed file matching the requested mood.

    Looks in assets/music/ for a file containing the mood string in its name.
    Returns None if not found — the caller decides whether that's an error.
    """
    if not _MUSIC_DIR.exists():
        log.warning("Music directory not found: %s", _MUSIC_DIR)
        return None

    mood_lower = mood.lower()
    matches = []
    for path in sorted(_MUSIC_DIR.iterdir()):
        if path.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a") and mood_lower in path.stem.lower():
            matches.append(path)

    if matches:
        chosen = random.choice(matches)
        log.info("Found music: %s (mood=%s, %d matches)", chosen.name, mood, len(matches))
        return chosen

    log.warning("No music file matching mood '%s' in %s", mood, _MUSIC_DIR)
    return None


def find_sfx(name: str) -> Path | None:
    """Find an SFX file by name.

    Looks in assets/sfx/ for a file containing the name string.
    """
    if not _SFX_DIR.exists():
        log.warning("SFX directory not found: %s", _SFX_DIR)
        return None

    name_lower = name.lower()
    for path in sorted(_SFX_DIR.iterdir()):
        if path.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a") and name_lower in path.stem.lower():
            log.info("Found SFX: %s (name=%s)", path.name, name)
            return path

    log.warning("No SFX file matching name '%s' in %s", name, _SFX_DIR)
    return None


def find_sfx_batch(names: list[str]) -> list[Path]:
    """Find multiple SFX files. Returns only those that exist."""
    results = []
    for name in names:
        path = find_sfx(name)
        if path is not None:
            results.append(path)
    return results
