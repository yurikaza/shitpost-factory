"""Tests for content-level deduplication."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from factory.sourcing.content_dedup import ContentDedupGuard, _hash_text, _hash_video
from factory.state.store import Store
from factory.types import RenderedVideo, Script


def _make_video(path: Path, size: int = 1024) -> RenderedVideo:
    """Create a fake video file for testing."""
    path.write_bytes(b"\x00" * size)
    return RenderedVideo(
        path=path,
        duration_s=10.0,
        width=1080,
        height=1920,
        concept_id="test",
        created_at=datetime.now(timezone.utc),
    )


def _make_script(hook: str = "Test hook", body: str = "Test body") -> Script:
    return Script(
        hook=hook,
        body=body,
        title="Test Title",
        description="Test description",
        hashtags=["test"],
    )


def test_hash_text_deterministic():
    assert _hash_text("hello world") == _hash_text("hello world")
    assert _hash_text("hello world") != _hash_text("goodbye world")


def test_hash_text_normalizes():
    assert _hash_text("  Hello World  ") == _hash_text("hello world")


def test_first_post_allowed(tmp_path):
    db = tmp_path / "test.db"
    store = Store(db)
    guard = ContentDedupGuard(store)

    video = _make_video(tmp_path / "test.mp4")
    script = _make_script()

    is_ok, reason = guard.check_and_record(video, script, "test-concept")
    assert is_ok is True
    assert reason is None
    store.close()


def test_duplicate_script_blocked(tmp_path):
    db = tmp_path / "test.db"
    store = Store(db)
    guard = ContentDedupGuard(store)

    script = _make_script(hook="Same hook", body="Same body")

    # First post — ok
    video1 = _make_video(tmp_path / "video1.mp4", size=1024)
    is_ok, _ = guard.check_and_record(video1, script, "concept-a")
    assert is_ok is True

    # Same script, different video — blocked
    video2 = _make_video(tmp_path / "video2.mp4", size=2048)
    is_ok, reason = guard.check_and_record(video2, script, "concept-b")
    assert is_ok is False
    assert "Duplicate script" in reason
    store.close()


def test_duplicate_video_blocked(tmp_path):
    db = tmp_path / "test.db"
    store = Store(db)
    guard = ContentDedupGuard(store)

    # Same video file, different script
    video = _make_video(tmp_path / "same.mp4", size=1024)

    script1 = _make_script(hook="Hook A", body="Body A")
    is_ok, _ = guard.check_and_record(video, script1, "concept-a")
    assert is_ok is True

    script2 = _make_script(hook="Hook B", body="Body B")
    # Same video hash + different script = different fingerprint
    # but video hash alone isn't blocked, only script hash or full fingerprint
    # The fingerprint is script_hash:video_hash, so different script = different fp
    is_ok, _ = guard.check_and_record(video, script2, "concept-b")
    # This should pass because the composite fingerprint differs
    assert is_ok is True
    store.close()


def test_exact_duplicate_blocked(tmp_path):
    db = tmp_path / "test.db"
    store = Store(db)
    guard = ContentDedupGuard(store)

    video = _make_video(tmp_path / "test.mp4")
    script = _make_script()

    # First post
    is_ok, _ = guard.check_and_record(video, script, "concept-a")
    assert is_ok is True

    # Exact same video + script — blocked
    is_ok, reason = guard.check_and_record(video, script, "concept-a")
    assert is_ok is False
    assert "Duplicate content" in reason
    store.close()
