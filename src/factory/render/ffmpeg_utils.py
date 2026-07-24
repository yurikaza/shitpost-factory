"""Thin, tested wrappers around ffmpeg/ffprobe subprocess calls.

Direct subprocess is the primary render path - it is faster and far more
predictable on a 2-vCPU box than MoviePy compositing.

Every function here must log the exact command it ran so failures on the VM are
reproducible locally.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    """Raised when an ffmpeg/ffprobe subprocess returns non-zero."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"ffmpeg exited {returncode}: {' '.join(cmd)}\n{stderr}"
        )


def _run(cmd: list[str], capture_stderr: bool = True) -> str:
    """Run a command, log it, raise on failure. Returns stderr (or empty)."""
    log.info("exec: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=capture_stderr,
        text=True,
    )
    if result.returncode != 0:
        raise FFmpegError(cmd, result.returncode, result.stderr)
    return result.stderr or ""


# ---------------------------------------------------------------------------
# ffprobe
# ---------------------------------------------------------------------------

def probe(file: Path) -> dict:
    """Return ffprobe JSON metadata for a media file."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file),
    ]
    stderr = _run(cmd)
    # ffprobe prints JSON to stdout; we need to capture it differently
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(cmd, result.returncode, result.stderr)
    return json.loads(result.stdout)


def get_duration(file: Path) -> float:
    """Return duration in seconds."""
    info = probe(file)
    # Try format-level duration first
    if "format" in info and "duration" in info["format"]:
        return float(info["format"]["duration"])
    # Fall back to first video stream
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video" and "duration" in stream:
            return float(stream["duration"])
    return 0.0


def has_audio_stream(file: Path) -> bool:
    """Check if a file has an audio stream."""
    info = probe(file)
    return any(s.get("codec_type") == "audio" for s in info.get("streams", []))


def get_video_info(file: Path) -> dict:
    """Return width, height, fps, codec for the first video stream."""
    info = probe(file)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            # Parse frame rate (e.g. "30/1" or "30000/1001")
            fps_str = stream.get("r_frame_rate", "30/1")
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
            return {
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
                "fps": fps,
                "codec": stream.get("codec_name", ""),
                "duration": float(stream.get("duration", 0)),
            }
    return {"width": 0, "height": 0, "fps": 30.0, "codec": "", "duration": 0.0}


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------

def transcode(
    input_file: Path,
    output_file: Path,
    *,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "veryfast",
    extra_args: list[str] | None = None,
) -> None:
    """Basic transcode with codec/quality settings."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(str(output_file))
    _run(cmd)


def concat_media(
    input_files: list[Path],
    output_file: Path,
    *,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "veryfast",
) -> None:
    """Concat multiple files using the concat demuxer."""
    if not input_files:
        raise ValueError("No input files to concatenate")

    # Write concat list to a temp file
    concat_list = output_file.parent / f"concat_{output_file.stem}.txt"
    with open(concat_list, "w") as f:
        for p in input_files:
            f.write(f"file '{p.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        str(output_file),
    ]
    try:
        _run(cmd)
    finally:
        concat_list.unlink(missing_ok=True)


def apply_filter_graph(
    input_file: Path,
    output_file: Path,
    filter_graph: str,
    *,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "veryfast",
) -> None:
    """Apply an arbitrary FFmpeg filter graph."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-vf", filter_graph,
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        str(output_file),
    ]
    _run(cmd)


def burn_captions(
    video_file: Path,
    ass_file: Path,
    output_file: Path,
    *,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "veryfast",
) -> None:
    """Burn ASS subtitles into video.

    Uses the ass filter with filename= option for reliable path handling.
    Falls back to copying the video if the ass filter is not available.
    """
    # Check if the ass filter is available (look for exact filter name, not substring)
    check = subprocess.run(
        ["ffmpeg", "-filters"], capture_output=True, text=True
    )
    has_ass = any(
        line.strip().startswith((".. ass ", "TS ass ", "T. ass "))
        or " ass " in line.split("=")[0] if "=" in line else " ass " in line
        for line in check.stdout.splitlines()
    )
    if not has_ass:
        log.warning("FFmpeg ass filter not available (libass not compiled in). Skipping caption burn-in.")
        import shutil
        shutil.copy2(video_file, output_file)
        return

    # Escape filename for FFmpeg filter parser: ' -> \', \ -> \\, : -> \:
    escaped = str(ass_file).replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
    vf = f"ass=filename='{escaped}'"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-vf", vf,
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        str(output_file),
    ]
    _run(cmd)


def mix_audio(
    video_file: Path,
    audio_files: list[Path],
    output_file: Path,
    *,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "veryfast",
    audio_filter: str | None = None,
) -> None:
    """Mix additional audio tracks into a video file."""
    cmd = ["ffmpeg", "-y", "-i", str(video_file)]
    for af in audio_files:
        cmd.extend(["-i", str(af)])

    n_inputs = 1 + len(audio_files)
    # Build amerge or amix filter
    filter_parts = []
    if audio_filter:
        filter_parts.append(audio_filter)
    else:
        # Simple amix: all audio inputs mixed together
        filter_str = f"[0:a][1:a]amix=inputs={n_inputs}:duration=first[outa]"
        if len(audio_files) > 1:
            # Chain amix for >2 inputs
            filter_str = f"[0:a]" + "".join(f"[{i}:a]" for i in range(1, n_inputs))
            filter_str += f"amix=inputs={n_inputs}:duration=first[outa]"
        filter_parts.append(filter_str)

    cmd.extend([
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[outa]" if not audio_filter else "1:a",
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        str(output_file),
    ])
    _run(cmd)


def normalise_audio(
    input_file: Path,
    output_file: Path,
    target_lufs: float = -14.0,
) -> None:
    """Two-pass loudnorm to target LUFS."""
    # Pass 1: measure
    cmd_measure = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    log.info("exec (pass 1 measure): %s", " ".join(cmd_measure))
    result = subprocess.run(cmd_measure, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(cmd_measure, result.returncode, result.stderr)

    # Parse measured values from stderr
    stderr = result.stderr
    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}") + 1
    if json_start == -1 or json_end == 0:
        # Could not parse — likely silent audio. Just copy.
        log.warning("Could not parse loudnorm output, copying file as-is")
        import shutil
        shutil.copy2(input_file, output_file)
        return
    measured = json.loads(stderr[json_start:json_end])

    # Check for silent audio (measured_I will be -inf or very low)
    measured_i = measured.get("input_i", "-inf")
    if measured_i == "-inf" or (isinstance(measured_i, str) and "inf" in measured_i):
        log.warning("Audio appears silent (measured_I=-inf), skipping loudnorm")
        import shutil
        shutil.copy2(input_file, output_file)
        return

    # Pass 2: apply
    af = (
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
        f":measured_I={measured['input_i']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        f":linear=true"
    )
    cmd_apply = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-af", af,
        str(output_file),
    ]
    _run(cmd_apply)
