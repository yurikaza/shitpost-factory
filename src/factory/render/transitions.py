"""Video transitions and effects for shitpost-style edits.

Adds quick cuts, zoom punches, speed ramps, and glitch effects
to make videos more dynamic and engaging. Uses FFmpeg filters.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

from factory.render.ffmpeg_utils import _run, get_duration, get_video_info

log = logging.getLogger(__name__)


def add_zoom_punch(
    input_path: Path,
    output_path: Path,
    *,
    zoom_start: float = 1.0,
    zoom_end: float = 1.3,
    duration_s: float | None = None,
    crf: int = 23,
    preset: str = "veryfast",
) -> Path:
    """Add a zoom-in effect (punch) to a video.

    Common in shitpost edits — zooms in slightly to emphasize a moment.

    Args:
        input_path: Source video.
        output_path: Output path.
        zoom_start: Starting zoom level (1.0 = normal).
        zoom_end: Ending zoom level (1.3 =30% zoom in).
        duration_s: Duration of the zoom effect. None = full video.
        crf: Video quality.
        preset: Encoding speed.

    Returns:
        Path to output video.
    """
    dur = duration_s or get_duration(input_path)
    info = get_video_info(input_path)
    w = info.get("width", 1080)
    h = info.get("height", 1920)

    # zoompan: zoom from zoom_start to zoom_end over duration
    # z is zoom level, x/y center the zoom
    fps = info.get("fps", 30)
    total_frames = int(dur * fps)

    vf = (
        f"zoompan=z='min({zoom_start}+({zoom_end}-{zoom_start})*on/{total_frames},{zoom_end})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={w}x{h}:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    log.info("Zoom punch: %s", output_path.name)
    return output_path


def add_speed_ramp(
    input_path: Path,
    output_path: Path,
    *,
    speed: float = 1.5,
    crf: int = 23,
    preset: str = "veryfast",
) -> Path:
    """Speed up or slow down a video.

    Args:
        input_path: Source video.
        output_path: Output path.
        speed: Speed multiplier (1.5 =50% faster, 0.5 = half speed).
        crf: Video quality.
        preset: Encoding speed.

    Returns:
        Path to output video.
    """
    # setpts adjusts timestamps: PTS/speed makes it faster
    pts = 1.0 / speed
    vf = f"setpts={pts}*PTS"
    af = f"atempo={min(speed, 2.0)}"  # atempo only supports 0.5-2.0

    # For speeds >2x, chain multiple atempo filters
    if speed > 2.0:
        atempo_filters = []
        remaining = speed
        while remaining > 2.0:
            atempo_filters.append("atempo=2.0")
            remaining /= 2.0
        atempo_filters.append(f"atempo={remaining}")
        af = ",".join(atempo_filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "aac",
        str(output_path),
    ]
    _run(cmd)
    log.info("Speed ramp %fx: %s", speed, output_path.name)
    return output_path


def add_shake(
    input_path: Path,
    output_path: Path,
    *,
    intensity: int = 10,
    crf: int = 23,
    preset: str = "veryfast",
) -> Path:
    """Add camera shake effect.

    Crops slightly and randomly offsets each frame to simulate shake.

    Args:
        input_path: Source video.
        output_path: Output path.
        intensity: Shake intensity in pixels (10 = subtle, 30 = violent).
        crf: Video quality.
        preset: Encoding speed.

    Returns:
        Path to output video.
    """
    info = get_video_info(input_path)
    w = info.get("width", 1080)
    h = info.get("height", 1920)

    # Crop slightly smaller then overlay with random offset
    crop_w = w - intensity * 2
    crop_h = h - intensity * 2

    # Use random offset via expression
    vf = (
        f"crop={crop_w}:{crop_h}:"
        f"'{intensity}+{intensity}*sin(t*15)':"
        f"'{intensity}+{intensity}*cos(t*13)',"
        f"scale={w}:{h}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    log.info("Shake effect: %s", output_path.name)
    return output_path


def concat_with_cuts(
    clips: list[Path],
    output_path: Path,
    *,
    target_duration: float = 15.0,
    crf: int = 23,
    preset: str = "veryfast",
    add_effects: bool = True,
) -> Path:
    """Concatenate clips with shitpost-style cuts and effects.

    Instead of smooth concatenation, this:
    1. Picks random segments from each clip (jump cuts)
    2. Optionally adds zoom punch or speed ramp to some clips
    3. Hard cuts between segments (no crossfade)

    Args:
        clips: List of video clip paths.
        output_path: Output path.
        target_duration: Target total duration in seconds.
        crf: Video quality.
        preset: Encoding speed.
        add_effects: Whether to add random effects.

    Returns:
        Path to output video.
    """
    if not clips:
        raise ValueError("No clips to concatenate")

    work_dir = output_path.parent
    processed_clips = []

    # Calculate time per clip
    time_per_clip = target_duration / len(clips)

    for i, clip in enumerate(clips):
        clip_dur = get_duration(clip)
        if clip_dur <= 0:
            continue

        # Pick a random segment from the clip
        max_start = max(0, clip_dur - time_per_clip - 1)
        start = random.uniform(0, max_start) if max_start > 0 else 0
        segment_dur = min(time_per_clip, clip_dur - start)

        # Trim to segment
        segment_path = work_dir / f"segment_{i}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(clip),
            "-t", str(segment_dur),
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-c:a", "aac",
            str(segment_path),
        ]
        _run(cmd)

        # Optionally add effects
        if add_effects and random.random() > 0.5:
            effect_type = random.choice(["zoom", "speed", "none"])
            if effect_type == "zoom":
                effect_path = work_dir / f"effect_{i}.mp4"
                add_zoom_punch(segment_path, effect_path, zoom_end=random.uniform(1.1, 1.4))
                segment_path = effect_path
            elif effect_type == "speed":
                effect_path = work_dir / f"effect_{i}.mp4"
                add_speed_ramp(segment_path, effect_path, speed=random.uniform(1.2, 1.8))
                segment_path = effect_path

        processed_clips.append(segment_path)

    if not processed_clips:
        raise ValueError("No valid segments to concatenate")

    # Concatenate with hard cuts
    if len(processed_clips) == 1:
        import shutil
        shutil.copy2(processed_clips[0], output_path)
    else:
        # Use concat demuxer for hard cuts
        concat_list = work_dir / "concat_effects.txt"
        with open(concat_list, "w") as f:
            for p in processed_clips:
                f.write(f"file '{p}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-c:a", "aac",
            str(output_path),
        ]
        _run(cmd)

    log.info("Montage: %d clips -> %s", len(processed_clips), output_path.name)
    return output_path


def add_glitch_transition(
    input_path: Path,
    output_path: Path,
    *,
    timestamp: float = 0.0,
    duration: float = 0.2,
    crf: int = 23,
    preset: str = "veryfast",
) -> Path:
    """Add a brief glitch/distortion effect at a specific timestamp.

    Args:
        input_path: Source video.
        output_path: Output path.
        timestamp: When to add the glitch (seconds).
        duration: How long the glitch lasts (seconds).
        crf: Video quality.
        preset: Encoding speed.

    Returns:
        Path to output video.
    """
    # RGB shift + noise at the specified timestamp
    vf = (
        f"split[main][glitch];"
        f"[glitch]crop=iw-20:ih:10:0,"
        f"rgbashift=rh=-5:bh=5,"
        f"noise=alls=40:allf=t,"
        f"scale={get_video_info(input_path)['width']}:{get_video_info(input_path)['height']}[g];"
        f"[main][g]overlay=0:0:enable='between(t,{timestamp},{timestamp + duration})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    log.info("Glitch transition at %.1fs: %s", timestamp, output_path.name)
    return output_path
