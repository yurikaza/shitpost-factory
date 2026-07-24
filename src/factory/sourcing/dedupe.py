"""Guards against reusing the same clip or story across any concept.

Backed by state.store. Window is configurable (default 90 days).
"""
from __future__ import annotations

import logging
from pathlib import Path

from factory.state.store import Store
from factory.types import SourcedClip

log = logging.getLogger(__name__)


class DedupeGuard:
    """Wraps state.store to filter out already-used clips and sources."""

    def __init__(self, store: Store, window_days: int = 90):
        self._store = store
        self._window_days = window_days

    def filter_new_clips(self, clips: list[SourcedClip], concept_id: str) -> list[SourcedClip]:
        """Return only clips not seen within the dedup window."""
        new_clips = []
        for clip in clips:
            if not self._store.is_clip_used(
                clip.provider, clip.external_id, within_days=self._window_days
            ):
                new_clips.append(clip)
            else:
                log.debug(
                    "Dedupe: skipping %s/%s (already used)", clip.provider, clip.external_id
                )
        log.info(
            "Dedupe: %d/%d clips are new for concept=%s",
            len(new_clips), len(clips), concept_id,
        )
        return new_clips

    def mark_clips_used(self, clips: list[SourcedClip], concept_id: str) -> None:
        """Record clips as used so they won't be reused."""
        for clip in clips:
            self._store.record_clip_used(clip.provider, clip.external_id, concept_id)

    def is_source_new(self, source_hash: str) -> bool:
        """Check if a text source (e.g. Reddit post hash) has been used."""
        return not self._store.is_source_used(source_hash, within_days=self._window_days)

    def mark_source_used(self, source_hash: str, concept_id: str) -> None:
        """Record a text source as used."""
        self._store.record_source_used(source_hash, concept_id)
