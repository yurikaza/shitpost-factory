"""Footage provider interface. All providers return SourcedClip objects.

Rule from docs/research-2026.md section 4: CC0 stock or self-recorded only.
Never yt-dlp against YouTube/TikTok. Never Reddit video.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from factory.types import SourcedClip


class FootageProvider(ABC):
    """Base class for footage providers (Pexels, Pixabay, local)."""

    name: str

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SourcedClip]:
        """Search for clips matching a query. Returns metadata only (no download)."""
        ...

    @abstractmethod
    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a clip to dest directory. Returns the local file path."""
        ...

    def search_and_download(
        self, query: str, dest: Path, limit: int = 5
    ) -> list[SourcedClip]:
        """Convenience: search + download top results. Returns clips with local_path set."""
        clips = self.search(query, limit=limit)
        downloaded = []
        for clip in clips:
            try:
                local = self.download(clip, dest)
                clip.local_path = local
                downloaded.append(clip)
            except Exception as e:
                # Log and skip failed downloads
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to download %s from %s: %s", clip.external_id, self.name, e
                )
        return downloaded
