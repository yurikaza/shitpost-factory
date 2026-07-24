"""Dataclasses passed between pipeline stages.

Contract: every stage takes one of these in and returns one out.
Never pass raw dicts across a stage boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Concept — parsed from config/concepts/*.yaml
# ---------------------------------------------------------------------------

@dataclass
class AccountConfig:
    handle_youtube: str = ""
    handle_tiktok: str = ""
    handle_instagram: str = ""


@dataclass
class SourcingConfig:
    mode: str = "stock"                  # stock | generated | reddit-text
    providers: list[str] = field(default_factory=lambda: ["pexels", "pixabay"])
    clips_per_video: int = 3
    query_strategy: str = "manual"       # manual | from_script
    queries: list[str] = field(default_factory=list)
    subreddits: list[str] = field(default_factory=list)
    min_upvotes: int = 2000
    max_body_chars: int = 1200
    background: str = ""                 # gradient | local | ""
    prefer_vertical: bool = True
    dedupe_window_days: int = 90
    min_clip_duration_s: float = 4.0


@dataclass
class ScriptConfig:
    target_words: int = 100
    hook_max_words: int = 8
    tone: str = ""
    banned_words: list[str] = field(default_factory=list)
    facts_per_video: int = 0
    rewrite: bool = False


@dataclass
class AudioConfig:
    narration: bool = True
    music_mood: str = ""
    music_gain_db: float = -18.0
    sfx: list[str] = field(default_factory=list)


@dataclass
class VideoConfig:
    max_duration_s: int = 60
    loop_seamless: bool = False


@dataclass
class CaptionConfig:
    style: str = "word_by_word"          # word_by_word | line


@dataclass
class PublishConfig:
    hashtags_count: int = 5
    platforms: list[str] = field(
        default_factory=lambda: ["tiktok", "instagram", "youtube"]
    )


@dataclass
class Concept:
    """A parsed config/concepts/*.yaml file. One concept == one account."""
    id: str
    enabled: bool
    description: str = ""
    originality_risk: str = ""
    automatability: str = ""
    account: AccountConfig = field(default_factory=AccountConfig)
    sourcing: SourcingConfig = field(default_factory=SourcingConfig)
    script: ScriptConfig = field(default_factory=ScriptConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    caption: CaptionConfig = field(default_factory=CaptionConfig)
    publish: PublishConfig = field(default_factory=PublishConfig)


# ---------------------------------------------------------------------------
# Pipeline stage dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SourcedClip:
    """One piece of raw footage. Stage 1 output."""
    provider: str          # pexels | pixabay | local
    external_id: str       # used for dedupe, see state.store
    url: str | None
    local_path: Path | None
    duration_s: float
    width: int
    height: int
    attribution: str | None


@dataclass
class SourcedMaterial:
    """Stage 1 output."""
    concept_id: str
    clips: list[SourcedClip] = field(default_factory=list)
    text_source: str | None = None      # reddit body, fact list, etc
    source_ref: str | None = None       # permalink for the ledger


@dataclass
class Script:
    """Stage 2 output. Everything the LLM writes."""
    hook: str
    body: str
    title: str
    description: str
    hashtags: list[str]
    clip_queries: list[str] = field(default_factory=list)


@dataclass
class AudioTrack:
    """Stage 3 output."""
    narration_path: Path | None
    music_path: Path | None
    sfx_paths: list[Path] = field(default_factory=list)
    duration_s: float = 0.0


@dataclass
class RenderedVideo:
    """Stage 4 output."""
    path: Path
    duration_s: float
    width: int
    height: int
    concept_id: str
    created_at: datetime


@dataclass
class PublishResult:
    """Stage 5 output, one per platform."""
    platform: str
    ok: bool
    post_id: str | None
    url: str | None
    error: str | None
