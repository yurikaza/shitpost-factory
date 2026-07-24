"""Tests for sourcing providers and deduplication."""
from __future__ import annotations

import pytest

from factory.sourcing.pexels import PexelsProvider
from factory.sourcing.pixabay import PixabayProvider
from factory.sourcing.reddit_text import RedditTextProvider
from factory.sourcing.dedupe import DedupeGuard
from factory.types import SourcedClip


class TestPexelsProvider:
    def test_search_fixture(self, pexels):
        clips = pexels.search("nature", limit=3)
        assert len(clips) == 3
        assert all(c.provider == "pexels" for c in clips)
        assert all(c.url is None for c in clips)  # fixture mode

    def test_search_limit(self, pexels):
        clips = pexels.search("test", limit=1)
        assert len(clips) == 1

    def test_download_fixture(self, pexels, tmp_path):
        clips = pexels.search("test", limit=1)
        local = pexels.download(clips[0], tmp_path)
        assert local.exists()
        assert local.stat().st_size > 0


class TestPixabayProvider:
    def test_search_fixture(self, pixabay):
        clips = pixabay.search("city", limit=3)
        assert len(clips) == 3
        assert all(c.provider == "pixabay" for c in clips)


class TestRedditTextProvider:
    def test_fetch_fixture(self, reddit):
        material = reddit.fetch_post("tifu")
        assert material is not None
        assert material.text_source is not None
        assert len(material.text_source) > 0
        assert material.concept_id == "reddit-stories"

    def test_hash_text(self):
        h1 = RedditTextProvider.hash_text("hello world")
        h2 = RedditTextProvider.hash_text("hello world")
        h3 = RedditTextProvider.hash_text("different text")
        assert h1 == h2
        assert h1 != h3


class TestDedupeGuard:
    def test_filter_new_clips(self, dedupe):
        clips = [
            SourcedClip("pexels", "111", None, None, 5.0, 1080, 1920, None),
            SourcedClip("pexels", "222", None, None, 5.0, 1080, 1920, None),
        ]
        new = dedupe.filter_new_clips(clips, "test")
        assert len(new) == 2

    def test_mark_and_filter(self, dedupe):
        clips = [
            SourcedClip("pexels", "111", None, None, 5.0, 1080, 1920, None),
            SourcedClip("pexels", "222", None, None, 5.0, 1080, 1920, None),
        ]
        dedupe.mark_clips_used([clips[0]], "test")
        new = dedupe.filter_new_clips(clips, "test")
        assert len(new) == 1
        assert new[0].external_id == "222"

    def test_cross_provider_dedupe(self, dedupe):
        clip_a = SourcedClip("pexels", "111", None, None, 5.0, 1080, 1920, None)
        clip_b = SourcedClip("pixabay", "111", None, None, 5.0, 1080, 1920, None)
        dedupe.mark_clips_used([clip_a], "test")
        # Different provider, same ID — should NOT be deduped
        new = dedupe.filter_new_clips([clip_b], "test")
        assert len(new) == 1

    def test_source_dedupe(self, dedupe):
        assert dedupe.is_source_new("abc123")
        dedupe.mark_source_used("abc123", "test")
        assert not dedupe.is_source_new("abc123")
