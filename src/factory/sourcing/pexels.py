"""Pexels video API. Primary footage source.

License: Pexels License, commercial use, no attribution required.
Limits: 200 req/hr, 20,000/mo. Respect them - back off on 429.
Docs: https://www.pexels.com/api/documentation/
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import httpx

from factory.sourcing.base import FootageProvider
from factory.types import SourcedClip

log = logging.getLogger(__name__)

_API_BASE = "https://api.pexels.com"
_RATE_LIMIT_PAUSE = 18  # seconds between requests (200/hr = ~18s apart)


class PexelsProvider(FootageProvider):
    """Pexels video search and download."""

    name = "pexels"

    def __init__(self, api_key: str | None = None, dry_run: bool = False):
        self._api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        self._dry_run = dry_run
        self._last_request_time = 0.0

    def _throttle(self):
        """Respect rate limits: 200 requests per hour."""
        elapsed = time.time() - self._last_request_time
        if elapsed < _RATE_LIMIT_PAUSE:
            pause = _RATE_LIMIT_PAUSE - elapsed
            log.debug("Pexels rate limit: sleeping %.1fs", pause)
            time.sleep(pause)
        self._last_request_time = time.time()

    def search(self, query: str, limit: int = 10) -> list[SourcedClip]:
        """Search Pexels for vertical videos matching a query."""
        if self._dry_run:
            return self._fixture_search(query, limit)

        self._throttle()
        log.info("Pexels search: query=%s limit=%d", query, limit)

        url = f"{_API_BASE}/videos/search"
        params = {
            "query": query,
            "per_page": min(limit, 15),  # Pexels max per page is 15
            "orientation": "portrait",   # prefer vertical
        }
        headers = {"Authorization": self._api_key}

        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code == 429:
                log.warning("Pexels rate limited, backing off 60s")
                time.sleep(60)
                resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        clips = []
        for video in data.get("videos", []):
            # Pick the best HD file
            best_file = None
            for vf in video.get("video_files", []):
                if vf.get("quality") == "hd" and vf.get("file_type") == "video/mp4":
                    best_file = vf
                    break
            if not best_file and video.get("video_files"):
                best_file = video["video_files"][0]

            if best_file:
                clips.append(SourcedClip(
                    provider="pexels",
                    external_id=str(video["id"]),
                    url=best_file.get("link"),
                    local_path=None,  # downloaded later
                    duration_s=float(video.get("duration", 0)),
                    width=int(best_file.get("width", 0)),
                    height=int(best_file.get("height", 0)),
                    attribution=None,  # no attribution required
                ))

        log.info("Pexels: found %d clips for '%s'", len(clips), query)
        return clips

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a Pexels video clip to dest."""
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"pexels_{clip.external_id}.mp4"

        log.info("Downloading Pexels clip %s -> %s", clip.external_id, output_path)
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", clip.url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        return output_path

    def _fixture_search(self, query: str, limit: int) -> list[SourcedClip]:
        """Return fixture clips for offline testing."""
        clips = []
        for i in range(min(limit, 3)):
            clips.append(SourcedClip(
                provider="pexels",
                external_id=f"fixture_{query.replace(' ', '_')}_{i}",
                url=None,
                local_path=None,
                duration_s=5.0 + i,
                width=1080,
                height=1920,
                attribution=None,
            ))
        log.info("Pexels fixture: %d clips for '%s'", len(clips), query)
        return clips

    def _fixture_download(self, clip: SourcedClip, dest: Path) -> Path:
        """Create a fixture video file for offline testing."""
        import subprocess

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"pexels_{clip.external_id}.mp4"
        # Generate a 5-second color bar test pattern
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=blue:s=1080x1920:d={clip.duration_s}:r=30",
            "-f", "lavfi", "-i",
            f"sine=frequency=440:duration={clip.duration_s}",
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "64k",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        log.info("Pexels fixture: created %s", output_path)
        return output_path
