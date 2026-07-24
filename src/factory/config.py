"""Loads .env, config/settings.yaml and config/concepts/*.yaml into typed objects.

Precedence: concept yaml > settings.yaml > defaults. Env vars only carry secrets.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from factory.types import (
    AccountConfig,
    AudioConfig,
    CaptionConfig,
    Concept,
    PublishConfig,
    ScriptConfig,
    SourcingConfig,
    VideoConfig,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SETTINGS: dict[str, Any] = {
    "runtime": {
        "timezone": "UTC",
        "videos_per_run": 1,
        "dry_run": True,
        "work_dir": "./work",
        "output_dir": "./output",
    },
    "video": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "min_duration_s": 15,
        "max_duration_s": 60,
        "video_codec": "libx264",
        "crf": 23,
        "preset": "veryfast",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "loudness_lufs": -14,
    },
    "captions": {
        "engine": "faster-whisper",
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "font_file": "",
        "font_size": 96,
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 8,
        "margin_v": 150,
        "style": "word_by_word",
    },
    "llm": {
        "provider": "gemini",
        "temperature": 0.9,
        "max_output_tokens": 800,
    },
    "sourcing": {
        "providers": ["pexels", "pixabay"],
        "min_clip_duration_s": 4,
        "prefer_vertical": True,
        "dedupe_window_days": 90,
    },
    "publishing": {
        "layer": "postiz",
        "platforms": ["youtube", "tiktok", "instagram"],
        "tiktok_mode": "draft",
        "stagger_minutes": 20,
    },
    "limits": {
        "instagram_posts_per_24h": 25,
        "youtube_uploads_per_24h": 100,
        "tiktok_requests_per_min": 6,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (mutates base)."""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_env(project_root: Path | None = None) -> None:
    """Load .env into os.environ. Call once at startup."""
    root = project_root or _PROJECT_ROOT
    load_dotenv(root / ".env")


def _get_brand_root() -> Path | None:
    """Return brand root path if FACTORY_BRAND env var is set."""
    brand = os.environ.get("FACTORY_BRAND")
    if brand:
        brand_root = _PROJECT_ROOT / "social-media-pipeline" / brand
        if brand_root.exists():
            return brand_root
    return None


def _get_concepts_dir() -> Path:
    """Return concepts directory (brand-specific or default)."""
    brand_root = _get_brand_root()
    if brand_root:
        brand_concepts = brand_root / "config" / "concepts"
        if brand_concepts.exists():
            return brand_concepts
    return _PROJECT_ROOT / "config" / "concepts"


def _get_output_dir() -> Path:
    """Return output directory (brand-specific or default)."""
    brand_root = _get_brand_root()
    if brand_root:
        output_dir = brand_root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    return _PROJECT_ROOT / "output"


def load_settings(path: Path | None = None) -> dict:
    """Load config/settings.yaml, merged over hardcoded defaults."""
    settings_path = path or (_PROJECT_ROOT / "config" / "settings.yaml")
    file_settings = _load_yaml(settings_path)

    # Override output_dir if brand is set
    brand_root = _get_brand_root()
    if brand_root:
        file_settings.setdefault("output_dir", str(brand_root / "output"))

    merged = _deep_merge(dict(_DEFAULT_SETTINGS), file_settings)
    return merged


def load_concept(concept_id: str, settings: dict | None = None) -> Concept:
    """Load and merge one concept YAML into a Concept dataclass.

    Merge order: hardcoded defaults -> settings.yaml overrides -> concept overrides.
    """
    concepts_dir = _get_concepts_dir()
    concept_path = concepts_dir / f"{concept_id}.yaml"
    if not concept_path.exists():
        raise FileNotFoundError(f"Concept not found: {concept_path}")

    raw = _load_yaml(concept_path)

    # Extract top-level fields
    concept = Concept(
        id=raw.get("id", concept_id),
        enabled=raw.get("enabled", False),
        description=raw.get("description", ""),
        originality_risk=raw.get("originality_risk", ""),
        automatability=raw.get("automatability", ""),
    )

    # Build nested configs, letting concept YAML override settings
    if "account" in raw:
        concept.account = AccountConfig(**{
            k: v for k, v in raw["account"].items()
            if k in AccountConfig.__dataclass_fields__
        })

    sourcing = dict(settings.get("sourcing", {})) if settings else {}
    if "sourcing" in raw:
        _deep_merge(sourcing, raw["sourcing"])
    concept.sourcing = SourcingConfig(**{
        k: v for k, v in sourcing.items()
        if k in SourcingConfig.__dataclass_fields__
    })

    script = dict(settings.get("script", {})) if settings else {}
    if "script" in raw:
        _deep_merge(script, raw["script"])
    concept.script = ScriptConfig(**{
        k: v for k, v in script.items()
        if k in ScriptConfig.__dataclass_fields__
    })

    if "audio" in raw:
        concept.audio = AudioConfig(**{
            k: v for k, v in raw["audio"].items()
            if k in AudioConfig.__dataclass_fields__
        })

    if "video" in raw:
        concept.video = VideoConfig(**{
            k: v for k, v in raw["video"].items()
            if k in VideoConfig.__dataclass_fields__
        })

    if "caption" in raw:
        concept.caption = CaptionConfig(**{
            k: v for k, v in raw["caption"].items()
            if k in CaptionConfig.__dataclass_fields__
        })

    if "publish" in raw:
        concept.publish = PublishConfig(**{
            k: v for k, v in raw["publish"].items()
            if k in PublishConfig.__dataclass_fields__
        })

    return concept


def list_enabled_concepts() -> list[str]:
    """Return IDs of all enabled concepts."""
    concepts_dir = _get_concepts_dir()
    enabled = []
    for path in sorted(concepts_dir.glob("*.yaml")):
        raw = _load_yaml(path)
        if raw.get("enabled", False):
            enabled.append(raw.get("id", path.stem))
    return enabled
