"""Tests for config loading and concept parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from factory.config import (
    load_concept,
    load_settings,
    list_enabled_concepts,
    _deep_merge,
)


class TestDeepMerge:
    def test_basic_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_non_dict(self):
        base = {"a": "old"}
        override = {"a": "new"}
        result = _deep_merge(base, override)
        assert result["a"] == "new"


class TestLoadSettings:
    def test_loads_defaults(self):
        settings = load_settings()
        assert "video" in settings
        assert settings["video"]["width"] == 1080
        assert settings["video"]["height"] == 1920
        assert settings["video"]["fps"] == 30

    def test_captions_defaults(self):
        settings = load_settings()
        assert settings["captions"]["model"] == "base"
        assert settings["captions"]["device"] == "cpu"


class TestLoadConcept:
    def test_text_pov(self):
        c = load_concept("text-pov")
        assert c.id == "text-pov"
        assert c.enabled is True
        assert c.sourcing.mode == "generated"
        assert c.script.target_words == 90
        assert c.video.max_duration_s == 35
        assert c.audio.narration is False

    def test_fact_bombs(self):
        c = load_concept("fact-bombs")
        assert c.id == "fact-bombs"
        assert c.enabled is True
        assert c.sourcing.mode == "stock"
        assert c.audio.narration is True
        assert c.caption.style == "word_by_word"

    def test_reddit_stories_disabled(self):
        c = load_concept("reddit-stories")
        assert c.enabled is False
        assert c.sourcing.mode == "reddit-text"
        assert c.script.rewrite is True

    def test_satisfying_loops_disabled(self):
        c = load_concept("satisfying-loops")
        assert c.enabled is False
        assert c.video.loop_seamless is True

    def test_nonexistent_concept(self):
        with pytest.raises(FileNotFoundError):
            load_concept("nonexistent-concept")


class TestListEnabledConcepts:
    def test_returns_enabled_only(self):
        enabled = list_enabled_concepts()
        assert "text-pov" in enabled
        assert "fact-bombs" in enabled
        assert "reddit-stories" not in enabled
        assert "satisfying-loops" not in enabled
