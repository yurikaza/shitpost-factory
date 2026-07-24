"""Stage 4. Assembles clips + audio into a 1080x1920 H.264 mp4.

Handles: concat, 9:16 reframing (scale/crop, or blurred-fill for non-vertical
sources), zoom/punch via zoompan, transitions via xfade, trimming to the concept
duration cap.

Budget: a 30-60s render must stay under ~5 min on 2 vCPU. If a change blows that,
it is the wrong change.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from factory.render.ffmpeg_utils import (
    apply_filter_graph,
    burn_captions,
    concat_media,
    get_duration,
    get_video_info,
    normalise_audio,
    transcode,
)
from factory.types import AudioTrack, Concept, RenderedVideo, SourcedMaterial, Script

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_WORK_DIR = _PROJECT_ROOT / "work"
def _get_output_dir() -> Path:
    """Return output directory (brand-specific or default)."""
    import os
    brand = os.environ.get("FACTORY_BRAND")
    if brand:
        brand_output = _PROJECT_ROOT / "social-media-pipeline" / brand / "output"
        brand_output.mkdir(parents=True, exist_ok=True)
        return brand_output
    return _PROJECT_ROOT / "output"


def _reframe_vertical(input_path: Path, output_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """Reframe a video to 9:16 by scaling + center-cropping.

    For landscape source: scale to fill height, crop width.
    For portrait source: scale to fill width, crop height.
    For square: scale to fill both, crop.
    """
    info = get_video_info(input_path)
    src_w, src_h = info["width"], info["height"]
    if src_w == 0 or src_h == 0:
        src_w, src_h = 1920, 1080  # fallback

    src_ratio = src_w / src_h
    dst_ratio = width / height

    if src_ratio > dst_ratio:
        # Source is wider than target: scale by height, crop width
        vf = f"scale={width}:{height}*{src_ratio}/{dst_ratio},crop={width}:{height}"
    else:
        # Source is taller than target: scale by width, crop height
        vf = f"scale={width}*{dst_ratio}/{src_ratio}:{height},crop={width}:{height}"

    apply_filter_graph(input_path, output_path, vf)
    return output_path


def _blur_fill(input_path: Path, output_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """Blur-fill background for non-vertical sources: blurred + scaled bg with sharp foreground overlay."""
    vf = (
        f"split[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=20:5[blurred];"
        f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[sharp];"
        f"[blurred][sharp]overlay=(W-w)/2:(H-h)/2"
    )
    apply_filter_graph(input_path, output_path, vf)
    return output_path


def _trim_to_duration(input_path: Path, output_path: Path, max_duration_s: float) -> Path:
    """Trim video to max duration."""
    duration = get_duration(input_path)
    if duration <= max_duration_s:
        return input_path
    log.info("Trimming %.1fs -> %.1fs", duration, max_duration_s)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-t", str(max_duration_s),
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
        "-c:a", "aac",
        str(output_path),
    ]
    from factory.render.ffmpeg_utils import _run
    _run(cmd)
    return output_path


def _generate_background(
    concept: Concept,
    output_path: Path,
    duration_s: float,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Generate a background video for 'generated' concepts (e.g. text-pov gradient)."""
    from factory.render.ffmpeg_utils import _run

    # For generated concepts, create a gradient background
    # Using a simple color gradient via FFmpeg's gradients filter
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"gradients=s={width}x{height}:duration={duration_s}:rate=30"
        f":c0=0x1a1a2e:c1=0x16213e:c2=0x0f3460:c3=0x533483",
        "-f", "lavfi", "-i",
        f"anullsrc=r=16000:cl=mono",
        "-t", str(duration_s),
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def compose_video(
    material: SourcedMaterial,
    script: Script,
    audio: AudioTrack,
    concept: Concept,
    *,
    work_dir: Path | None = None,
) -> RenderedVideo:
    """Assemble clips + audio + captions into the final video.

    Args:
        material: Stage 1 output (clips).
        script: Stage 2 output (unused directly here, but may be used for metadata).
        audio: Stage 3 output (narration + music paths).
        concept: Parsed concept config.
        work_dir: Scratch directory for intermediate files.

    Returns:
        RenderedVideo dataclass with path and metadata.
    """
    work = work_dir or _WORK_DIR
    work.mkdir(parents=True, exist_ok=True)

    width = 1080
    height = 1920
    crf = 23
    preset = "veryfast"
    max_duration = concept.video.max_duration_s

    # Step 1: Get or generate the base video
    if concept.sourcing.mode == "generated":
        # Generated concept: create background from scratch
        concat_path = work / "generated_bg.mp4"
        duration = audio.duration_s if audio.duration_s > 0 else float(max_duration)
        _generate_background(concept, concat_path, duration, width, height)
    elif material.clips:
        # Stock concept: reframe sourced clips to 9:16
        reframed_clips = []
        for i, clip in enumerate(material.clips):
            if clip.local_path is None or not clip.local_path.exists():
                log.warning("Clip %d has no local path, skipping", i)
                continue
            out = work / f"reframed_{i}.mp4"
            info = get_video_info(clip.local_path)
            src_ratio = info["width"] / max(info["height"], 1)
            dst_ratio = width / height
            if abs(src_ratio - dst_ratio) < 0.01:
                transcode(clip.local_path, out, crf=crf, preset=preset)
            else:
                # Use blur-fill for landscape clips — keeps full content visible
                # with blurred background behind. Much better than hard crop.
                _blur_fill(clip.local_path, out, width, height)
            reframed_clips.append(out)

        if not reframed_clips:
            raise ValueError("No valid clips to compose")

        if len(reframed_clips) == 1:
            concat_path = reframed_clips[0]
        else:
            # Use montage cuts for meme-bombs, regular concat for others
            if concept.id == "meme-bombs":
                from factory.render.transitions import concat_with_cuts
                concat_path = work / "concat.mp4"
                concat_with_cuts(
                    reframed_clips, concat_path,
                    target_duration=max_duration,
                    crf=crf, preset=preset,
                    add_effects=True,
                )
            else:
                concat_path = work / "concat.mp4"
                concat_media(reframed_clips, concat_path, crf=crf, preset=preset)
    else:
        raise ValueError("No clips and not a generated concept — nothing to render")

    # Step 2: Add audio (narration + music)
    if audio.narration_path or audio.music_path:
        audio_path = work / "with_audio.mp4"
        cmd = ["ffmpeg", "-y", "-i", str(concat_path)]
        audio_inputs = []
        if audio.narration_path:
            cmd.extend(["-i", str(audio.narration_path)])
            audio_inputs.append("1:a")
        if audio.music_path:
            cmd.extend(["-i", str(audio.music_path)])
            audio_inputs.append(f"{len(audio_inputs) + 1}:a")

        if len(audio_inputs) == 1:
            cmd.extend(["-map", "0:v", "-map", audio_inputs[0]])
        else:
            # Mix multiple audio inputs
            mix_inputs = "".join(f"[{a}]" for a in audio_inputs)
            filter_complex = f"{mix_inputs}amix=inputs={len(audio_inputs)}:duration=first[outa]"
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "0:v", "-map", "[outa]",
            ])

        cmd.extend([
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-c:a", "aac",
            str(audio_path),
        ])
        from factory.render.ffmpeg_utils import _run
        _run(cmd)
        working_video = audio_path
    else:
        working_video = concat_path

    # Step 3: Trim video to match audio duration (for stock concepts where
    # concatenated clips may be longer than the narration).
    if audio.duration_s > 0:
        video_dur = get_duration(working_video)
        # Add 0.5s buffer so the last word isn't cut off
        target_dur = audio.duration_s + 0.5
        if video_dur > target_dur + 1.0:
            log.info("Trimming video %.1fs -> %.1fs to match audio", video_dur, target_dur)
            trimmed_to_audio = work / "trimmed_audio.mp4"
            _trim_to_duration(working_video, trimmed_to_audio, target_dur)
            working_video = trimmed_to_audio

    # Step 4: Trim to max duration
    if get_duration(working_video) > max_duration:
        trimmed = work / "trimmed.mp4"
        _trim_to_duration(working_video, trimmed, max_duration)
        working_video = trimmed

    # Step 5: Normalise audio to -14 LUFS
    normalised = work / "normalised.mp4"
    from factory.render.ffmpeg_utils import _run, has_audio_stream
    if not has_audio_stream(working_video):
        # No audio stream — just copy the video
        import shutil
        shutil.copy2(working_video, normalised)
    else:
        # Extract audio, normalise, remux
        audio_only = work / "audio_raw.wav"
        _run([
            "ffmpeg", "-y", "-i", str(working_video),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_only),
        ])
        normalised_audio = work / "audio_norm.wav"
        normalise_audio(audio_only, normalised_audio, target_lufs=-14.0)
        _run([
            "ffmpeg", "-y",
            "-i", str(working_video),
            "-i", str(normalised_audio),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac",
            str(normalised),
        ])
    working_video = normalised

    # Step 6: Text overlay (meme style) or captions (narration style)
    text_style = getattr(concept.video, 'text_style', '')
    if text_style == 'impact_bold':
        # Meme-bombs style: big bold text overlay, no captions
        from factory.render.text_overlay import overlay_text
        with_text = work / "with_text.mp4"
        # Use hook as top text, first sentence of body as punchline
        body_lines = script.body.split('. ')
        punchline = body_lines[0] if body_lines else script.body
        # Truncate punchline to ~8 words
        punchline_words = punchline.split()[:8]
        punchline = ' '.join(punchline_words)
        overlay_text(
            working_video, with_text,
            hook=script.hook,
            punchline=punchline,
            font_size=48,
            crf=crf,
            preset=preset,
        )
        working_video = with_text
    elif concept.audio.narration:
        from factory.render.captions import generate_captions
        ass_path = work / "captions.ass"
        generate_captions(
            working_video,
            ass_path,
            model_size="base",
            font_size=96,
            outline=8,
            margin_v=150,
            style=concept.caption.style,
        )
        with_captions = work / "with_captions.mp4"
        burn_captions(working_video, ass_path, with_captions, crf=crf, preset=preset)
        working_video = with_captions

    # Step 7: Move to output
    output_dir = _get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{concept.id}_{timestamp}.mp4"
    working_video.rename(output_path)

    log.info("Final video: %s", output_path)
    return RenderedVideo(
        path=output_path,
        duration_s=get_duration(output_path),
        width=width,
        height=height,
        concept_id=concept.id,
        created_at=datetime.now(timezone.utc),
    )
