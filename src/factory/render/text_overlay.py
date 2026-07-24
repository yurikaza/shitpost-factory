"""Text overlay rendering for meme-style content.

Generates text overlay images with Pillow, then composites them onto video
using FFmpeg's overlay filter. Works on any FFmpeg build (no libfreetype needed).

Style: Impact font, white with thick black outline, top/bottom positioning.
This is the 'shitpost' aesthetic — text IS the content.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from factory.render.ffmpeg_utils import _run, get_video_info

log = logging.getLogger(__name__)

# Font search paths
_FONT_SEARCH_PATHS = [
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/TTF/Impact.ttf",
    "assets/fonts/Impact.ttf",
]


def _find_font() -> str | None:
    """Find Impact font or return None for default."""
    for path in _FONT_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    # Try bold alternatives
    for path in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            return path
    return None


def _render_text_image(
    text: str,
    width: int,
    height: int,
    *,
    font_size: int = 72,
    y_position: int = 80,
) -> Image.Image:
    """Render text onto a transparent PNG image.

    Args:
        text: Text to render.
        width: Image width (match video).
        height: Image height (match video).
        font_size: Text size.
        y_position: Y position from top.

    Returns:
        RGBA Image with text rendered.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
    font_path = _find_font()
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Word wrap: split text into lines that fit the width
    max_text_width = width - 60  #30px margin each side
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > max_text_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)

    # Draw each line with black outline then white fill
    line_height = font_size + 10
    total_height = len(lines) * line_height
    start_y = y_position

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2

        # Black outline (draw offset in all directions)
        outline_width = 6
        for ox in range(-outline_width, outline_width + 1):
            for oy in range(-outline_width, outline_width + 1):
                if ox*ox + oy*oy <= outline_width*outline_width:
                    draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 255))

        # White fill
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    return img


def overlay_text(
    input_path: Path,
    output_path: Path,
    hook: str,
    punchline: str,
    *,
    font_size: int = 72,
    crf: int = 23,
    preset: str = "veryfast",
) -> Path:
    """Overlay meme-style text on a video using Pillow + FFmpeg overlay.

    Args:
        input_path: Source video.
        output_path: Output video path.
        hook: Top-of-screen text (the setup).
        punchline: Bottom-of-screen text (the punchline).
        font_size: Text size.
        crf: Video quality.
        preset: Encoding speed.

    Returns:
        Path to the output video.
    """
    info = get_video_info(input_path)
    w = info.get("width", 1080)
    h = info.get("height", 1920)

    # Generate text overlay images
    work_dir = output_path.parent
    hook_img = _render_text_image(hook, w, h, font_size=font_size, y_position=80)
    hook_path = work_dir / "text_hook.png"
    hook_img.save(str(hook_path))

    punchline_img = _render_text_image(punchline, w, h, font_size=font_size, y_position=h - 250)
    punchline_path = work_dir / "text_punchline.png"
    punchline_img.save(str(punchline_path))

    # Composite: video + hook overlay + punchline overlay
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-i", str(hook_path),
        "-i", str(punchline_path),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0[bg];[bg][2:v]overlay=0:0[out]",
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    log.info("Text overlay: %s -> %s", input_path.name, output_path.name)
    return output_path


def overlay_text_long(
    input_path: Path,
    output_path: Path,
    lines: list[str],
    *,
    font_size: int = 64,
    crf: int = 23,
    preset: str = "veryfast",
    duration_per_line: float = 2.0,
) -> Path:
    """Overlay multiple text lines that appear one at a time.

    Each line appears for `duration_per_line` seconds, centered on screen.
    Generates one overlay image per line, then uses FFmpeg overlay with enable.

    Args:
        input_path: Source video.
        output_path: Output video path.
        lines: List of text lines to display sequentially.
        font_size: Text size.
        crf: Video quality.
        preset: Encoding speed.
        duration_per_line: Seconds each line is visible.

    Returns:
        Path to the output video.
    """
    info = get_video_info(input_path)
    w = info.get("width", 1080)
    h = info.get("height", 1920)

    work_dir = output_path.parent
    overlay_paths = []

    # Generate one overlay image per line
    for i, line in enumerate(lines):
        img = _render_text_image(line, w, h, font_size=font_size, y_position=(h - font_size) // 2)
        path = work_dir / f"text_line_{i}.png"
        img.save(str(path))
        overlay_paths.append(path)

    if not overlay_paths:
        import shutil
        shutil.copy2(input_path, output_path)
        return output_path

    # Build FFmpeg filter chain: overlay each image with timed enable
    inputs = ["-i", str(input_path)]
    for p in overlay_paths:
        inputs.extend(["-i", str(p)])

    # Build overlay chain
    filter_parts = []
    prev_label = "0:v"
    for i in range(len(overlay_paths)):
        start = i * duration_per_line
        end = start + duration_per_line
        out_label = f"v{i}" if i < len(overlay_paths) - 1 else "out"
        filter_parts.append(
            f"[{prev_label}][{i+1}:v]overlay=0:0:enable='between(t\\,{start:.1f}\\,{end:.1f})'[{out_label}]"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    log.info("Timed text overlay: %d lines -> %s", len(lines), output_path.name)
    return output_path
