"""Content-level deduplication. Prevents posting similar videos.

Unlike sourcing/dedupe.py which guards against reusing source clips,
this module guards against posting similar *output* content:
- Same script text → same hash → blocked
- Same video file → same hash → blocked
- Fingerprint combines script + video hashes for a composite check
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from factory.state.store import Store
from factory.types import RenderedVideo, Script

log = logging.getLogger(__name__)


def _hash_text(text: str) -> str:
    """SHA-256 of normalized text (lowercase, stripped)."""
    normalized = text.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _hash_video(path: Path, sample_bytes: int = 1_048_576) -> str:
    """Hash first 1MB of video file + file size for content fingerprinting.

    Fast enough for pre-publish checks. Catches identical files and
    near-identical renders (same source + same config = same output).
    """
    h = hashlib.sha256()
    size = path.stat().st_size
    h.update(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(sample_bytes))
    return h.hexdigest()[:16]


def compute_fingerprint(video: RenderedVideo, script: Script) -> dict[str, str]:
    """Compute content fingerprints for a video + script combo.

    Returns dict with keys: script_hash, video_hash, fingerprint.
    """
    script_hash = _hash_text(f"{script.hook}|{script.body}")
    video_hash = _hash_video(video.path)
    # Composite: both must match for a hard block
    fingerprint = _hash_text(f"{script_hash}:{video_hash}")
    return {
        "script_hash": script_hash,
        "video_hash": video_hash,
        "fingerprint": fingerprint,
    }


class ContentDedupGuard:
    """Pre-publish deduplication. Checks if similar content was already posted."""

    def __init__(self, store: Store, window_days: int = 90):
        self._store = store
        self._window_days = window_days

    def check_and_record(
        self, video: RenderedVideo, script: Script, concept_id: str
    ) -> tuple[bool, str | None]:
        """Check if content is duplicate. Returns (is_ok, reason).

        If is_ok=True, the fingerprint is recorded (caller should proceed).
        If is_ok=False, reason explains why it was blocked.
        """
        fp = compute_fingerprint(video, script)

        # Check 1: Exact same video+script combo
        if self._store.is_fingerprint_used(fp["fingerprint"], self._window_days):
            return False, (
                f"Duplicate content: identical video+script was already posted "
                f"(fingerprint={fp['fingerprint']})"
            )

        # Check 2: Same script text (even if video differs slightly)
        if self._store.is_script_hash_used(fp["script_hash"], self._window_days):
            return False, (
                f"Duplicate script: same narration text was already posted "
                f"(script_hash={fp['script_hash']})"
            )

        # All clear — record the fingerprint
        self._store.record_fingerprint(
            fingerprint=fp["fingerprint"],
            concept_id=concept_id,
            script_hash=fp["script_hash"],
            video_hash=fp["video_hash"],
            duration_s=video.duration_s,
        )
        log.info(
            "Content dedup OK: concept=%s fp=%s script=%s video=%s",
            concept_id, fp["fingerprint"], fp["script_hash"], fp["video_hash"],
        )
        return True, None
