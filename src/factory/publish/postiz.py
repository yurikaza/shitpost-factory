"""PRIMARY publishing layer. Self-hosted Postiz.

Handles TikTok, Instagram and YouTube behind one API, so we do not implement
chunked uploads, token refresh and multi-step container flows three times.

It does NOT bypass TikTok's content-posting audit or Meta's app review - those
are platform-side. It only removes our implementation burden.

Postiz also ships an MCP server if we later want agent-driven scheduling.

Postiz API docs: https://docs.postiz.com/api-reference
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from factory.publish.base import Publisher
from factory.types import PublishResult, RenderedVideo, Script

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "http://localhost:5000/api/public/v1"


class PostizPublisher(Publisher):
    """Publish via a self-hosted Postiz instance."""

    platform = "postiz"

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        dry_run: bool = False,
    ):
        self._api_url = (api_url or os.getenv("POSTIZ_API_URL", _DEFAULT_API_URL)).rstrip("/")
        self._api_key = api_key or os.getenv("POSTIZ_API_KEY", "")
        self._dry_run = dry_run
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._api_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=120,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Publish video to all configured platforms via Postiz.

        Postiz flow:
        1. Upload the video file to Postiz
        2. Create a post with title, description, hashtags
        3. Post to selected platforms
        """
        if self._dry_run:
            return self._fixture_publish(video, script)

        log.info(
            "Postiz publish: %s -> platforms=%s",
            video.path.name,
            ",".join(script.hashtags[:3]),
        )

        try:
            # Step 1: Upload media
            client = self._get_client()
            with open(video.path, "rb") as f:
                upload_resp = client.post(
                    "/media/upload",
                    files={"file": (video.path.name, f, "video/mp4")},
                )
                upload_resp.raise_for_status()
            media_id = upload_resp.json().get("id")
            log.info("Postiz: uploaded media_id=%s", media_id)

            # Step 2: Create and publish post
            post_data = {
                "content": script.body,
                "title": script.title,
                "description": script.description,
                "tags": script.hashtags,
                "media": [media_id] if media_id else [],
                "platforms": self._get_platform_ids(),
                "integration": self._get_integration_ids(),
            }
            post_resp = client.post("/posts", json=post_data)
            post_resp.raise_for_status()
            post_id = post_resp.json().get("id")
            log.info("Postiz: created post_id=%s", post_id)

            return PublishResult(
                platform="postiz",
                ok=True,
                post_id=str(post_id) if post_id else None,
                url=None,
                error=None,
            )

        except httpx.HTTPStatusError as e:
            log.error("Postiz HTTP error: %s %s", e.response.status_code, e.response.text[:200])
            return PublishResult(
                platform="postiz", ok=False, post_id=None, url=None,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            log.error("Postiz error: %s", e)
            return PublishResult(
                platform="postiz", ok=False, post_id=None, url=None,
                error=str(e),
            )

    def _get_platform_ids(self) -> list[str]:
        """Fetch available platform integration IDs from Postiz."""
        try:
            client = self._get_client()
            resp = client.get("/integrations")
            resp.raise_for_status()
            integrations = resp.json()
            # Postiz returns a list of integration objects
            if isinstance(integrations, list):
                return [str(i.get("id")) for i in integrations if i.get("id")]
            return []
        except Exception as e:
            log.warning("Could not fetch Postiz integrations: %s", e)
            return []

    def _get_integration_ids(self) -> list[str]:
        """Alias for _get_platform_ids — Postiz uses 'integration' in its API."""
        return self._get_platform_ids()

    def _fixture_publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Simulate a successful publish for dry-run mode."""
        log.info("Postiz DRY RUN: would publish %s", video.path.name)
        return PublishResult(
            platform="postiz",
            ok=True,
            post_id="fixture_post_001",
            url="https://example.com/post/fixture",
            error=None,
        )


class PostizClient:
    """Lower-level Postiz API client for direct operations."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self._api_url = (api_url or os.getenv("POSTIZ_API_URL", _DEFAULT_API_URL)).rstrip("/")
        self._api_key = api_key or os.getenv("POSTIZ_API_KEY", "")

    def list_integrations(self) -> list[dict]:
        """List all configured platform integrations."""
        with httpx.Client(
            base_url=self._api_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30,
        ) as client:
            resp = client.get("/integrations")
            resp.raise_for_status()
            return resp.json()

    def list_channels(self) -> list[dict]:
        """List available posting channels."""
        with httpx.Client(
            base_url=self._api_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30,
        ) as client:
            resp = client.get("/channels")
            resp.raise_for_status()
            return resp.json()

    def upload_media(self, file_path: Path) -> dict:
        """Upload a media file to Postiz."""
        with httpx.Client(
            base_url=self._api_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=120,
        ) as client:
            with open(file_path, "rb") as f:
                resp = client.post(
                    "/media/upload",
                    files={"file": (file_path.name, f, "video/mp4")},
                )
                resp.raise_for_status()
                return resp.json()
