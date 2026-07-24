"""Archive.org video sourcing. Public domain footage, no API key needed.

Searches the Internet Archive for short video clips. Great for weird,
retro, and bizarre footage that works perfectly as shitpost backgrounds.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from factory.sourcing.base import FootageProvider
from factory.types import SourcedClip

log = logging.getLogger(__name__)

_API_BASE = "https://archive.org/advancedsearch.php"


class ArchiveOrgProvider(FootageProvider):
    """Search and download public domain videos from Archive.org."""

    name = "archive-org"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run

    def search(self, query: str, limit: int = 5) -> list[SourcedClip]:
        """Search Archive.org for video clips matching a query."""
        if self._dry_run:
            return self._fixture_search(query, limit)

        log.info("Archive.org search: query=%s limit=%d", query, limit)

        params = {
            "q": f'mediatype:movies AND format:"mpeg4" AND {query}',
            "fl[]": "identifier,title,description,runtime",
            "sort[]": "downloads desc",
            "rows": limit,
            "output": "json",
        }

        with httpx.Client(timeout=30) as client:
            resp = client.get(_API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        clips = []
        for doc in data.get("response", {}).get("docs", []):
            identifier = doc.get("identifier", "")
            title = doc.get("title", "")
            # Build the direct MP4 URL
            video_url = f"https://archive.org/download/{identifier}/{identifier}.mp4"

            clips.append(SourcedClip(
                provider="archive-org",
                external_id=identifier,
                url=video_url,
                local_path=None,
                duration_s=float(doc.get("runtime", 0) or 0),
                width=1080,
                height=1920,
                attribution=f"archive.org: {title}",
            ))

        log.info("Archive.org: found %d clips for '%s'", len(clips), query)
        return clips

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a video from Archive.org."""
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"archive_{clip.external_id}.mp4"

        log.info("Downloading Archive.org clip %s -> %s", clip.external_id, output_path)
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", clip.url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        return output_path

    def _fixture_search(self, query: str, limit: int) -> list[SourcedClip]:
        clips = []
        for i in range(min(limit, 3)):
            clips.append(SourcedClip(
                provider="archive-org",
                external_id=f"fixture_archive_{i}",
                url=None,
                local_path=None,
                duration_s=10.0 + i * 5,
                width=1080,
                height=1920,
                attribution="archive.org fixture",
            ))
        return clips

    def _fixture_download(self, clip: SourcedClip, dest: Path) -> Path:
        import subprocess
        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"archive_{clip.external_id}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=purple:s=1080x1920:d={clip.duration_s}:r=30",
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
