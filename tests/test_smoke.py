"""Smoke tests — quick sanity checks that core imports and basics work."""
from __future__ import annotations


def test_imports():
    """All core modules import without error."""
    from factory.types import Concept, Script, AudioTrack, RenderedVideo, PublishResult
    from factory.config import load_settings, load_concept, list_enabled_concepts
    from factory.state.store import Store
    from factory.render.ffmpeg_utils import FFmpegError, probe, get_duration
    from factory.scripting.llm_client import build_client, FixtureLLMClient
    from factory.scripting.writer import write_script
    from factory.audio.tts import build_tts, FixtureTTS
    from factory.sourcing.pexels import PexelsProvider
    from factory.sourcing.dedupe import DedupeGuard
    from factory.publish.postiz import PostizPublisher
    from factory.pipeline import produce, produce_all


def test_concept_count():
    """Exactly 4 concepts exist, 2 enabled."""
    from factory.config import list_enabled_concepts
    from pathlib import Path

    all_concepts = list(Path("config/concepts").glob("*.yaml"))
    assert len(all_concepts) == 4

    enabled = list_enabled_concepts()
    assert len(enabled) == 2
    assert "text-pov" in enabled
    assert "fact-bombs" in enabled
