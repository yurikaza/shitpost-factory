"""Tests for render layer: ffmpeg utils, captions, compose."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory.render.ffmpeg_utils import (
    FFmpegError,
    probe,
    get_duration,
    get_video_info,
    transcode,
    normalise_audio,
)


def _create_test_video(output: Path, duration: float = 2.0) -> Path:
    """Create a minimal test video with ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=1080x1920:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "64k",
        str(output),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


def _create_test_audio(output: Path, duration: float = 2.0) -> Path:
    """Create a minimal test audio file."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


class TestProbe:
    def test_probe_video(self, tmp_path):
        video = _create_test_video(tmp_path / "test.mp4")
        info = probe(video)
        assert "streams" in info
        assert "format" in info

    def test_get_duration(self, tmp_path):
        video = _create_test_video(tmp_path / "test.mp4", duration=3.0)
        duration = get_duration(video)
        assert 2.5 <= duration <= 3.5  # allow some tolerance

    def test_get_video_info(self, tmp_path):
        video = _create_test_video(tmp_path / "test.mp4")
        info = get_video_info(video)
        assert info["width"] == 1080
        assert info["height"] == 1920
        assert info["codec"] == "h264"


class TestTranscode:
    def test_transcode(self, tmp_path):
        src = _create_test_video(tmp_path / "src.mp4")
        dst = tmp_path / "dst.mp4"
        transcode(src, dst)
        assert dst.exists()
        assert dst.stat().st_size > 0


class TestNormaliseAudio:
    def test_normalise(self, tmp_path):
        src = _create_test_audio(tmp_path / "src.wav")
        dst = tmp_path / "dst.wav"
        normalise_audio(src, dst, target_lufs=-14.0)
        assert dst.exists()
