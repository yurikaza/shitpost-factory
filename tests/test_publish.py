"""Tests for publishing layer: all publishers in fixture mode."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from factory.publish.postiz import PostizPublisher
from factory.publish.youtube import YouTubePublisher
from factory.publish.tiktok import TikTokPublisher
from factory.publish.instagram import InstagramPublisher
from factory.types import RenderedVideo, Script


@pytest.fixture
def fixture_video(tmp_path):
    """Create a minimal video for publish tests."""
    import subprocess
    video_path = tmp_path / "test.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=5:r=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "64k",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return RenderedVideo(
        path=video_path,
        duration_s=5.0,
        width=1080,
        height=1920,
        concept_id="test",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fixture_script():
    return Script(
        hook="Test hook",
        body="Test body content",
        title="Test Title",
        description="Test description for publishing",
        hashtags=["test", "pipeline", "automated"],
    )


class TestPostizPublisher:
    def test_publish_dry_run(self, postiz_publisher, fixture_video, fixture_script):
        result = postiz_publisher.publish(fixture_video, fixture_script)
        assert result.ok is True
        assert result.post_id is not None
        assert result.platform == "postiz"

    def test_close(self, postiz_publisher):
        postiz_publisher.close()  # should not raise


class TestYouTubePublisher:
    def test_publish_dry_run(self, youtube_publisher, fixture_video, fixture_script):
        result = youtube_publisher.publish(fixture_video, fixture_script)
        assert result.ok is True
        assert result.post_id is not None
        assert result.platform == "youtube"


class TestTikTokPublisher:
    def test_draft_mode(self, tiktok_publisher, fixture_video, fixture_script):
        result = tiktok_publisher.publish(fixture_video, fixture_script)
        assert result.ok is True
        assert result.post_id is not None
        # Draft mode: no public URL
        assert result.url is None

    def test_direct_mode(self, fixture_video, fixture_script):
        pub = TikTokPublisher(dry_run=True, mode="direct")
        result = pub.publish(fixture_video, fixture_script)
        assert result.ok is True
        assert result.url is not None  # Direct mode has URL


class TestInstagramPublisher:
    def test_publish_dry_run(self, instagram_publisher, fixture_video, fixture_script):
        result = instagram_publisher.publish(fixture_video, fixture_script)
        assert result.ok is True
        assert result.post_id is not None
        assert result.platform == "instagram"
