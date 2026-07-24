"""Burned-in captions.

Pipeline: ffmpeg extracts audio -> faster-whisper transcribes with word-level
timestamps -> emit .ass -> ffmpeg burns in via -vf "ass=captions.ass".

ASS header must set PlayResX=1080 PlayResY=1920 or positioning will be wrong.
Style: thick outline (7-9), margin_v 120-180 to clear platform UI chrome.
Font must be an actual .ttf in assets/fonts - there is no system font resolution
on the target Linux box.

Whisper model: base or small on cpu. Anything larger is too slow.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from factory.render.ffmpeg_utils import _run, get_duration

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_FONT = _PROJECT_ROOT / "assets" / "fonts"


def _extract_audio(video_path: Path, output_wav: Path) -> Path:
    """Extract audio track from video as WAV for Whisper."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_wav),
    ]
    _run(cmd)
    return output_wav


def _transcribe(audio_path: Path, model_size: str = "base") -> list[dict]:
    """Transcribe audio with faster-whisper, returning word-level timestamps.

    Returns list of dicts: {"word": str, "start": float, "end": float}
    """
    from faster_whisper import WhisperModel

    log.info("Transcribing with faster-whisper model=%s", model_size)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
    )

    words = []
    for segment in segments:
        for word_info in segment.words:
            words.append({
                "word": word_info.word.strip(),
                "start": word_info.start,
                "end": word_info.end,
            })
    log.info("Transcribed %d words", len(words))
    return words


def _generate_ass(
    words: list[dict],
    output_path: Path,
    *,
    font_name: str = "DejaVu Sans",
    font_size: int = 96,
    primary_colour: str = "&H00FFFFFF",
    outline_colour: str = "&H00000000",
    outline: int = 8,
    margin_v: int = 150,
    style: str = "word_by_word",
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Generate an ASS subtitle file from word-level timestamps."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "[Script Info]\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "Timer: 100.0000\n"
        "WrapStyle: 0\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},{primary_colour},"
        f"&H000000FF,{outline_colour},&H80000000,"
        f"1,0,0,0,100,100,0,0,1,{outline},0,2,20,20,{margin_v},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = []
    if style == "word_by_word":
        # Each word gets its own dialogue line, highlighted
        for w in words:
            start = _format_ass_time(w["start"])
            end = _format_ass_time(w["end"])
            text = w["word"].replace("\n", "\\N")
            fade_tag = "\\fad(50,50)"
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{fade_tag}{text}"
            )
    else:
        # Line mode: group words into ~8-word chunks
        chunk_size = 8
        for i in range(0, len(words), chunk_size):
            chunk = words[i : i + chunk_size]
            start = _format_ass_time(chunk[0]["start"])
            end = _format_ass_time(chunk[-1]["end"])
            text = " ".join(w["word"] for w in chunk).replace("\n", "\\N")
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines))
        f.write("\n")

    log.info("Generated ASS: %s (%d lines)", output_path, len(lines))
    return output_path


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _find_font() -> str:
    """Find a usable .ttf font. Returns the font name for ASS."""
    if _DEFAULT_FONT.exists():
        for f in _DEFAULT_FONT.iterdir():
            if f.suffix.lower() == ".ttf":
                return f.stem  # ASS uses font name, not path
    # Fallback to DejaVu (installed by CI and setup_vm.sh)
    return "DejaVu Sans"


def generate_captions(
    video_path: Path,
    output_ass: Path,
    *,
    model_size: str = "base",
    font_size: int = 96,
    outline: int = 8,
    margin_v: int = 150,
    style: str = "word_by_word",
) -> Path:
    """Full caption pipeline: extract audio -> transcribe -> generate ASS.

    Args:
        video_path: Input video file.
        output_ass: Where to write the .ass file.
        model_size: Whisper model size (base/small).
        font_size: Caption font size.
        outline: Caption outline thickness.
        margin_v: Vertical margin to clear platform UI.
        style: 'word_by_word' or 'line'.

    Returns:
        Path to the generated .ass file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract audio
        audio_path = Path(tmpdir) / "audio.wav"
        _extract_audio(video_path, audio_path)

        # Transcribe
        words = _transcribe(audio_path, model_size=model_size)

        if not words:
            log.warning("No words transcribed from %s — generating empty captions", video_path)
            words = [{"word": "[no speech]", "start": 0.0, "end": get_duration(video_path)}]

        # Generate ASS
        font_name = _find_font()
        return _generate_ass(
            words,
            output_ass,
            font_name=font_name,
            font_size=font_size,
            outline=outline,
            margin_v=margin_v,
            style=style,
        )
