"""Tests for audio layer: TTS, mixer, sfx."""
from __future__ import annotations

import wave
from pathlib import Path

import pytest

from factory.audio.tts import FixtureTTS, build_tts
from factory.audio.sfx import find_music, find_sfx


class TestFixtureTTS:
    def test_synthesize(self, tmp_path):
        tts = FixtureTTS()
        out = tmp_path / "test.wav"
        result = tts.synthesize("Hello world", out)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_output_is_valid_wav(self, tmp_path):
        tts = FixtureTTS()
        out = tmp_path / "test.wav"
        tts.synthesize("Test", out)
        with wave.open(str(out), "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000

    def test_duration_scales_with_text(self, tmp_path):
        tts = FixtureTTS()
        short = tmp_path / "short.wav"
        long = tmp_path / "long.wav"
        tts.synthesize("Hi", short)
        tts.synthesize("This is a much longer sentence with many words", long)
        # Longer text should produce longer audio
        with wave.open(str(short), "r") as wf:
            short_frames = wf.getnframes()
        with wave.open(str(long), "r") as wf:
            long_frames = wf.getnframes()
        assert long_frames > short_frames


class TestBuildTTS:
    def test_fixture_mode(self):
        tts = build_tts(dry_run=True)
        assert isinstance(tts, FixtureTTS)

    def test_fixture_by_name(self):
        tts = build_tts(provider="fixture")
        assert isinstance(tts, FixtureTTS)


class TestSfxLookup:
    def test_find_music_returns_none_when_empty(self):
        # assets/music/ may not exist or may be empty
        result = find_music("nonexistent-mood")
        # May return None or a match — just verify no crash
        assert result is None or result.exists()

    def test_find_sfx_returns_none_when_empty(self):
        result = find_sfx("nonexistent-sfx")
        assert result is None or result.exists()
