"""Ducks the music bed under narration and normalises the final mix to -14 LUFS.

Uses ffmpeg loudnorm. Two-pass for accuracy.
"""
from __future__ import annotations

import logging
from pathlib import Path

from factory.render.ffmpeg_utils import apply_filter_graph, normalise_audio

log = logging.getLogger(__name__)


def duck_music_under_narration(
    narration_path: Path,
    music_path: Path,
    output_path: Path,
    *,
    music_gain_db: float = -18.0,
    target_lufs: float = -14.0,
) -> Path:
    """Mix narration + music, ducking music when narration is active.

    Uses FFmpeg's sidechaincompress filter: the narration signal ducks the music.

    Args:
        narration_path: Path to narration audio (WAV/MP3).
        music_path: Path to music bed audio.
        output_path: Where to write the mixed output.
        music_gain_db: Reduce music volume by this many dB.
        target_lufs: Target loudness for the final mix.

    Returns:
        Path to the mixed audio file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build filter: music gain reduction + sidechaincompress keyed on narration
    filter_graph = (
        f"[1:a]volume={music_gain_db}dB[bg];"
        f"[0:a][bg]sidechaincompress=threshold=0.02:ratio=4:attack=5:release=200[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration_path),   # input 0: narration (trigger)
        "-i", str(music_path),        # input 1: music (ducked)
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

    from factory.render.ffmpeg_utils import _run
    log.info("Ducking music under narration: %s", output_path)
    _run(cmd)

    # Normalise to target LUFS
    normalised = output_path.with_suffix(".norm.wav")
    normalise_audio(output_path, normalised, target_lufs=target_lufs)
    return normalised


def mix_sfx(
    base_audio: Path,
    sfx_paths: list[Path],
    output_path: Path,
) -> Path:
    """Overlay sound effects onto a base audio track.

    SFX are mixed in at their original volume on top of the base audio.

    Args:
        base_audio: The narration+music mix.
        sfx_paths: Paths to SFX files to overlay.
        output_path: Where to write the result.

    Returns:
        Path to the mixed output.
    """
    if not sfx_paths:
        return base_audio

    output_path.parent.mkdir(parents=True, exist_ok=True)

    from factory.render.ffmpeg_utils import _run

    cmd = ["ffmpeg", "-y", "-i", str(base_audio)]
    for sfx in sfx_paths:
        cmd.extend(["-i", str(sfx)])

    n_inputs = 1 + len(sfx_paths)
    inputs = "".join(f"[{i}:a]" for i in range(n_inputs))
    filter_graph = f"{inputs}amix=inputs={n_inputs}:duration=first[out]"

    cmd.extend([
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(output_path),
    ])
    log.info("Mixing %d SFX tracks", len(sfx_paths))
    _run(cmd)
    return output_path
