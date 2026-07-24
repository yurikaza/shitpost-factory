"""Pixabay video + audio API. Secondary source.

License: Pixabay License, commercial use, no attribution required.
Constraint: must download to our own storage, no permanent hotlinking.
Docs: https://pixabay.com/api/docs/
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

_API_BASE = "https://pixabay.com/api"


class PixabayProvider(FootageProvider):
    """Pixabay video search and download."""

    name = "pixabay"

    def __init__(self, api_key: str | None = None, dry_run: bool = False):
        self._api_key = api_key or os.getenv("PIXABAY_API_KEY", "")
        self._dry_run = dry_run

    def search(self, query: str, limit: int = 10) -> list[SourcedClip]:
        """Search Pixabay for vertical videos."""
        if self._dry_run:
            return self._fixture_search(query, limit)

        log.info("Pixabay search: query=%s limit=%d", query, limit)

        url = f"{_API_BASE}/videos/"
        params = {
            "key": self._api_key,
            "q": query,
            "per_page": min(limit, 200),
            "orientation": "vertical",
            "video_type": "film",
        }

        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                log.warning("Pixabay rate limited, backing off 60s")
                time.sleep(60)
                resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        clips = []
        for hit in data.get("hits", []):
            videos = hit.get("videos", {})
            # Prefer "large" (1920px) then "medium" (1280px)
            video_info = videos.get("large") or videos.get("medium") or {}
            url_val = video_info.get("url")
            if url_val:
                clips.append(SourcedClip(
                    provider="pixabay",
                    external_id=str(hit.get("id", "")),
                    url=url_val,
                    local_path=None,
                    duration_s=float(hit.get("duration", 0)),
                    width=int(video_info.get("width", 0)),
                    height=int(video_info.get("height", 0)),
                    attribution=None,
                ))

        log.info("Pixabay: found %d clips for '%s'", len(clips), query)
        return clips

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a Pixabay video. Pixabay requires downloading to own server."""
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"pixabay_{clip.external_id}.mp4"

        log.info("Downloading Pixabay clip %s -> %s", clip.external_id, output_path)
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", clip.url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        return output_path

    def search_audio(self, query: str, limit: int = 5) -> list[SourcedClip]:
        """Search Pixabay for audio (music/SFX)."""
        if self._dry_run:
            return []

        log.info("Pixabay audio search: query=%s", query)
        url = f"{_API_BASE}/videos/"
        # Pixabay doesn't have a separate audio API; audio comes with videos
        # For music, we'd use a different approach. For now, return empty.
        return []

    def _fixture_search(self, query: str, limit: int) -> list[SourcedClip]:
        clips = []
        for i in range(min(limit, 3)):
            clips.append(SourcedClip(
                provider="pixabay",
                external_id=f"fixture_{query.replace(' ', '_')}_{i}",
                url=None,
                local_path=None,
                duration_s=4.0 + i,
                width=1920,
                height=1080,
                attribution=None,
            ))
        return clips

    def _fixture_download(self, clip: SourcedClip, dest: Path) -> Path:
        import subprocess

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"pixabay_{clip.external_id}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=green:s=1920x1080:d={clip.duration_s}:r=30",
            "-f", "lavfi", "-i",
            f"sine=frequency=880:duration={clip.duration_s}",
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "64k",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
