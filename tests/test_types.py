"""Tests for dataclass types."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from factory.types import (
    Concept,
    AccountConfig,
    SourcingConfig,
    ScriptConfig,
    AudioConfig,
    VideoConfig,
    CaptionConfig,
    PublishConfig,
    SourcedClip,
    SourcedMaterial,
    Script,
    AudioTrack,
    RenderedVideo,
    PublishResult,
)


class TestConcept:
    def test_defaults(self):
        c = Concept(id="test", enabled=True)
        assert c.id == "test"
        assert c.enabled is True
        assert c.sourcing.mode == "stock"
        assert c.script.target_words == 100
        assert c.audio.narration is True
        assert c.publish.platforms == ["tiktok", "instagram", "youtube"]

    def test_nested_configs(self):
        c = Concept(
            id="test",
            enabled=True,
            sourcing=SourcingConfig(mode="reddit-text"),
            script=ScriptConfig(rewrite=True),
            audio=AudioConfig(narration=False),
        )
        assert c.sourcing.mode == "reddit-text"
        assert c.script.rewrite is True
        assert c.audio.narration is False


class TestSourcedClip:
    def test_creation(self):
        clip = SourcedClip(
            provider="pexels",
            external_id="12345",
            url="https://example.com/video.mp4",
            local_path=Path("/tmp/video.mp4"),
            duration_s=10.0,
            width=1920,
            height=1080,
            attribution=None,
        )
        assert clip.provider == "pexels"
        assert clip.duration_s == 10.0


class TestScript:
    def test_creation(self):
        s = Script(
            hook="Test hook",
            body="Test body",
            title="Test",
            description="Desc",
            hashtags=["a", "b"],
        )
        assert len(s.hashtags) == 2
        assert s.clip_queries == []


class TestPublishResult:
    def test_success(self):
        r = PublishResult(
            platform="youtube",
            ok=True,
            post_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            error=None,
        )
        assert r.ok is True

    def test_failure(self):
        r = PublishResult(
            platform="tiktok",
            ok=False,
            post_id=None,
            url=None,
            error="Rate limited",
        )
        assert r.ok is False
        assert r.error == "Rate limited"
