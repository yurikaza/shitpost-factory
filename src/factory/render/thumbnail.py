"""Extracts a frame for the YouTube thumbnail. Optional per concept."""
from __future__ import annotations

import logging
from pathlib import Path

from factory.render.ffmpeg_utils import _run, get_duration

log = logging.getLogger(__name__)


def extract_thumbnail(
    video_path: Path,
    output_path: Path,
    timestamp: float | None = None,
) -> Path:
    """Extract a single frame from a video as a thumbnail.

    Args:
        video_path: Input video file.
        output_path: Where to write the thumbnail (PNG/JPG).
        timestamp: Time in seconds to extract. If None, picks 25% into the video.

    Returns:
        Path to the thumbnail file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if timestamp is None:
        duration = get_duration(video_path)
        timestamp = duration * 0.25  # pick a frame 25% in

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]
    log.info("Extracting thumbnail at %.1fs -> %s", timestamp, output_path)
    _run(cmd)
    return output_path
