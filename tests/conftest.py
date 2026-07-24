"""Shared fixtures.

The whole pipeline must be runnable offline: every external client (Pexels,
LLM, TTS, Postiz) has a fixture mode. Tests never hit the network.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Ensure Homebrew ffmpeg is on PATH for subprocess calls in tests
if shutil.which("ffmpeg") is None:
    for brew_path in ["/opt/homebrew/bin", "/usr/local/bin"]:
        if os.path.exists(os.path.join(brew_path, "ffmpeg")):
            os.environ["PATH"] = brew_path + os.pathsep + os.environ.get("PATH", "")
            break

from factory.config import load_concept, load_settings
from factory.scripting.llm_client import FixtureLLMClient
from factory.audio.tts import FixtureTTS
from factory.publish.postiz import PostizPublisher
from factory.publish.youtube import YouTubePublisher
from factory.publish.tiktok import TikTokPublisher
from factory.publish.instagram import InstagramPublisher
from factory.sourcing.pexels import PexelsProvider
from factory.sourcing.pixabay import PixabayProvider
from factory.sourcing.reddit_text import RedditTextProvider
from factory.state.store import Store
from factory.sourcing.dedupe import DedupeGuard
from factory.types import Concept, SourcedMaterial, Script, AudioTrack


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings():
    """Load settings (uses defaults since settings.yaml may not exist)."""
    return load_settings()


@pytest.fixture
def text_pov_concept(settings):
    """Load the text-pov concept."""
    return load_concept("text-pov", settings)


@pytest.fixture
def fact_bombs_concept(settings):
    """Load the fact-bombs concept."""
    return load_concept("fact-bombs", settings)


@pytest.fixture
def reddit_stories_concept(settings):
    """Load the reddit-stories concept."""
    return load_concept("reddit-stories", settings)


# ---------------------------------------------------------------------------
# Client fixtures (all dry-run / fixture mode)
# ---------------------------------------------------------------------------

@pytest.fixture
def llm_client():
    """Fixture LLM client — returns canned responses, no network."""
    return FixtureLLMClient()


@pytest.fixture
def tts_engine():
    """Fixture TTS engine — generates silent WAV."""
    return FixtureTTS()


@pytest.fixture
def pexels():
    """Fixture Pexels provider."""
    return PexelsProvider(dry_run=True)


@pytest.fixture
def pixabay():
    """Fixture Pixabay provider."""
    return PixabayProvider(dry_run=True)


@pytest.fixture
def reddit():
    """Fixture Reddit provider."""
    return RedditTextProvider(dry_run=True)


@pytest.fixture
def postiz_publisher():
    """Fixture Postiz publisher."""
    return PostizPublisher(dry_run=True)


@pytest.fixture
def youtube_publisher():
    """Fixture YouTube publisher."""
    return YouTubePublisher(dry_run=True)


@pytest.fixture
def tiktok_publisher():
    """Fixture TikTok publisher."""
    return TikTokPublisher(dry_run=True)


@pytest.fixture
def instagram_publisher():
    """Fixture Instagram publisher."""
    return InstagramPublisher(dry_run=True)


# ---------------------------------------------------------------------------
# State fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    """Temp SQLite store — auto-cleaned after test."""
    db = Store(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def dedupe(store):
    """Dedupe guard backed by a temp store."""
    return DedupeGuard(store, window_days=90)


# ---------------------------------------------------------------------------
# Material fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sourced_material():
    """A minimal SourcedMaterial for testing."""
    return SourcedMaterial(
        concept_id="test",
        clips=[],
        text_source="Sample text source for testing",
        source_ref="https://example.com/test",
    )


@pytest.fixture
def sample_script():
    """A minimal Script for testing."""
    return Script(
        hook="Did you know?",
        body="This is a test script body.",
        title="Test Title",
        description="A test description.",
        hashtags=["test", "fact", "didyouknow"],
        clip_queries=["test query"],
    )


@pytest.fixture
def sample_audio_track(tmp_path):
    """A minimal AudioTrack with a fixture WAV file."""
    import wave
    wav_path = tmp_path / "test_audio.wav"
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)  # 1 second
    return AudioTrack(
        narration_path=wav_path,
        music_path=None,
        sfx_paths=[],
        duration_s=1.0,
    )


# ---------------------------------------------------------------------------
# Temp directory fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def work_dir(tmp_path):
    """Temp work directory for render tests."""
    d = tmp_path / "work"
    d.mkdir()
    return d
