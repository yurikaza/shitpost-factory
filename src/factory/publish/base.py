"""Publisher interface. Returns PublishResult, never raises past the boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod

from factory.types import PublishResult, RenderedVideo, Script


class Publisher(ABC):
    """Base class for all publishing backends.

    Contract: publish() returns a PublishResult. It must never raise exceptions
    past this boundary — errors become PublishResult(ok=False, error=...).
    """

    platform: str

    @abstractmethod
    def publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Publish a video + metadata to the platform.

        Args:
            video: The rendered video file and metadata.
            script: The script with title, description, hashtags.

        Returns:
            PublishResult with ok=True on success, or ok=False with error details.
        """
        ...

    def close(self) -> None:
        """Clean up any resources (HTTP clients, file handles)."""
        pass
