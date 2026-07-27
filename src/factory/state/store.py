"""SQLite ledger. The pipeline's memory.

Tables:
  used_clips     provider + external_id + first_used_at  (cross-concept dedupe)
  used_sources   permalink/hash of story material
  posts          concept, platform, post_id, url, posted_at, status
  runs           run_id, concept, stage reached, error

Dedupe is a hard requirement - reposting our own material is exactly what
TikTok's originality system flags.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS used_clips (
    provider    TEXT NOT NULL,
    external_id TEXT NOT NULL,
    concept_id  TEXT NOT NULL,
    first_used_at TEXT NOT NULL,
    PRIMARY KEY (provider, external_id)
);

CREATE TABLE IF NOT EXISTS used_sources (
    source_hash TEXT NOT NULL PRIMARY KEY,
    concept_id  TEXT NOT NULL,
    first_used_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    post_id     TEXT PRIMARY KEY,
    concept_id  TEXT NOT NULL,
    platform    TEXT NOT NULL,
    platform_post_id TEXT,
    url         TEXT,
    posted_at   TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS video_fingerprints (
    fingerprint TEXT NOT NULL PRIMARY KEY,
    concept_id  TEXT NOT NULL,
    script_hash TEXT,
    video_hash  TEXT,
    duration_s  REAL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    concept_id  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    error       TEXT
);
"""


class Store:
    """SQLite-backed pipeline state. Deduplication and run tracking."""

    def __init__(self, db_path: Path | str = "state.db"):
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_DB_SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- dedupe -------------------------------------------------------------

    def is_clip_used(
        self, provider: str, external_id: str, within_days: int = 90
    ) -> bool:
        """Check if a clip has been used within the deduplication window."""
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        row = conn.execute(
            "SELECT 1 FROM used_clips WHERE provider = ? AND external_id = ?"
            " AND first_used_at > ?",
            (provider, external_id, cutoff),
        ).fetchone()
        return row is not None

    def record_clip_used(
        self, provider: str, external_id: str, concept_id: str
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO used_clips (provider, external_id, concept_id, first_used_at)"
            " VALUES (?, ?, ?, ?)",
            (provider, external_id, concept_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    def is_source_used(self, source_hash: str, within_days: int = 90) -> bool:
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        row = conn.execute(
            "SELECT 1 FROM used_sources WHERE source_hash = ? AND first_used_at > ?",
            (source_hash, cutoff),
        ).fetchone()
        return row is not None

    def record_source_used(self, source_hash: str, concept_id: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO used_sources (source_hash, concept_id, first_used_at)"
            " VALUES (?, ?, ?)",
            (source_hash, concept_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    # -- posts --------------------------------------------------------------

    def record_post(
        self,
        concept_id: str,
        platform: str,
        platform_post_id: str | None = None,
        url: str | None = None,
        status: str = "posted",
    ) -> str:
        post_id = uuid.uuid4().hex[:12]
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO posts (post_id, concept_id, platform, platform_post_id, url, posted_at, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (post_id, concept_id, platform, platform_post_id, url,
             datetime.now(timezone.utc).isoformat(), status),
        )
        conn.commit()
        return post_id

    def count_posts_today(self, platform: str) -> int:
        conn = self._get_conn()
        today = datetime.now(timezone.utc).date().isoformat()
        row = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE platform = ? AND posted_at >= ? AND status != 'failed'",
            (platform, today),
        ).fetchone()
        return row[0] if row else 0

    # -- video fingerprint dedup -------------------------------------------

    def is_fingerprint_used(self, fingerprint: str, within_days: int = 90) -> bool:
        """Check if a video fingerprint has been posted within the dedup window."""
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        row = conn.execute(
            "SELECT 1 FROM video_fingerprints WHERE fingerprint = ? AND created_at > ?",
            (fingerprint, cutoff),
        ).fetchone()
        return row is not None

    def record_fingerprint(
        self,
        fingerprint: str,
        concept_id: str,
        script_hash: str | None = None,
        video_hash: str | None = None,
        duration_s: float = 0.0,
    ) -> None:
        """Record a video fingerprint to prevent reposting similar content."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO video_fingerprints"
            " (fingerprint, concept_id, script_hash, video_hash, duration_s, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (fingerprint, concept_id, script_hash, video_hash, duration_s,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    def is_script_hash_used(self, script_hash: str, within_days: int = 90) -> bool:
        """Check if a script with this hash was already posted recently."""
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        row = conn.execute(
            "SELECT 1 FROM video_fingerprints WHERE script_hash = ? AND created_at > ?",
            (script_hash, cutoff),
        ).fetchone()
        return row is not None

    # -- runs ---------------------------------------------------------------

    def start_run(self, concept_id: str) -> str:
        run_id = uuid.uuid4().hex[:12]
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO runs (run_id, concept_id, stage, started_at)"
            " VALUES (?, ?, 'start', ?)",
            (run_id, concept_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return run_id

    def finish_run(self, run_id: str, stage: str, error: str | None = None) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE runs SET stage = ?, finished_at = ?, error = ? WHERE run_id = ?",
            (stage, datetime.now(timezone.utc).isoformat(), error, run_id),
        )
        conn.commit()
