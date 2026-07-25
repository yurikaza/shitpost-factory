"""Direct fallback: Instagram Reels via Meta Graph API.

Requires an Instagram BUSINESS account (Creator accounts are not supported),
a linked Facebook Page, and approved instagram_business_content_publish.

Three steps: POST /{ig-user-id}/media (media_type=REELS, public video_url)
-> poll container status until FINISHED -> POST /{ig-user-id}/media_publish.

The mp4 must sit at a publicly reachable URL at post time. Assume 25 posts/24h.

Flow:
1. Get a container: POST /{ig-user-id}/media
2. Poll container: GET /{container-id}?fields=status_code
3. Publish: POST /{ig-user-id}/media_publish
"""
from __future__ import annotations

import logging
import os
import time

import httpx

from factory.publish.base import Publisher
from factory.publish.r2_upload import R2Uploader
from factory.types import PublishResult, RenderedVideo, Script

log = logging.getLogger(__name__)

_GRAPH_API_VERSION = "v21.0"
_GRAPH_API_BASE = f"https://graph.facebook.com/{_GRAPH_API_VERSION}"


class InstagramPublisher(Publisher):
    """Direct Instagram Reels publisher via Meta Graph API."""

    platform = "instagram"

    def __init__(
        self,
        access_token: str | None = None,
        ig_business_account_id: str | None = None,
        dry_run: bool = False,
        r2_uploader: R2Uploader | None = None,
    ):
        self._access_token = access_token or os.getenv("IG_ACCESS_TOKEN", "")
        self._ig_user_id = ig_business_account_id or os.getenv("IG_BUSINESS_ACCOUNT_ID", "")
        self._dry_run = dry_run
        self._r2 = r2_uploader

    def publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Publish Reel to Instagram.

        Uploads video to Cloudflare R2 for a public URL, then publishes via Graph API.
        Cleans up the R2 object after publish completes.
        """
        if self._dry_run:
            return self._fixture_publish(video, script)

        if not self._ig_user_id:
            return PublishResult(
                platform="instagram", ok=False, post_id=None, url=None,
                error="IG_BUSINESS_ACCOUNT_ID not configured",
            )

        log.info("Instagram Reel publish: %s", video.path.name)

        # Upload video to R2 for a public URL
        video_url = None
        r2_key = None
        try:
            if self._r2 is None:
                self._r2 = R2Uploader()
            video_url, r2_key = self._r2.upload_and_get_url(video.path)
            log.info("Video hosted at: %s", video_url)
        except Exception as e:
            return PublishResult(
                platform="instagram", ok=False, post_id=None, url=None,
                error=f"R2 upload failed: {e}",
            )

        try:
            container_body = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": self._format_caption(script),
                "access_token": self._access_token,
            }

            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{_GRAPH_API_BASE}/{self._ig_user_id}/media",
                    data=container_body,
                )
                resp.raise_for_status()
                container_id = resp.json().get("id")

            if not container_id:
                return PublishResult(
                    platform="instagram", ok=False, post_id=None, url=None,
                    error="Failed to create media container",
                )

            log.info("Instagram: container_id=%s, polling status...", container_id)

            # Step 2: Poll container status (up to 5 minutes)
            status = self._poll_container(container_id)
            if status != "FINISHED":
                return PublishResult(
                    platform="instagram", ok=False, post_id=None, url=None,
                    error=f"Container status: {status}",
                )

            # Step 3: Publish
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{_GRAPH_API_BASE}/{self._ig_user_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": self._access_token,
                    },
                )
                resp.raise_for_status()
                media_id = resp.json().get("id")

            log.info("Instagram: published media_id=%s", media_id)

            return PublishResult(
                platform="instagram",
                ok=True,
                post_id=str(media_id) if media_id else None,
                url=f"https://instagram.com/reel/{media_id}" if media_id else None,
                error=None,
            )

        except httpx.HTTPStatusError as e:
            log.error("Instagram HTTP error: %s %s", e.response.status_code, e.response.text[:200])
            return PublishResult(
                platform="instagram", ok=False, post_id=None, url=None,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            log.error("Instagram error: %s", e)
            return PublishResult(
                platform="instagram", ok=False, post_id=None, url=None,
                error=str(e),
            )
        finally:
            # Clean up R2 temp file after publish
            if r2_key and self._r2:
                try:
                    self._r2.delete_video(r2_key)
                except Exception:
                    log.warning("Failed to clean up R2 key: %s", r2_key)

    def _poll_container(self, container_id: str, max_wait: int = 300) -> str:
        """Poll container status until FINISHED, ERROR, or timeout."""
        start = time.time()
        with httpx.Client(timeout=30) as client:
            while time.time() - start < max_wait:
                resp = client.get(
                    f"{_GRAPH_API_BASE}/{container_id}",
                    params={
                        "fields": "status_code,status",
                        "access_token": self._access_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status_code", "UNKNOWN")

                if status == "FINISHED":
                    return status
                if status in ("ERROR", "EXPIRED"):
                    log.error("Instagram container %s: %s", container_id, status)
                    return status

                log.debug("Instagram container %s: %s, waiting...", container_id, status)
                time.sleep(10)

        return "TIMEOUT"

    def _format_caption(self, script: Script) -> str:
        """Format caption with hashtags for Instagram."""
        caption = script.description
        if script.hashtags:
            tags = " ".join(f"#{tag}" for tag in script.hashtags[:30])
            caption = f"{caption}\n\n{tags}"
        return caption[:2200]  # Instagram caption limit

    def _fixture_publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        log.info("Instagram DRY RUN: would publish %s", video.path.name)
        return PublishResult(
            platform="instagram",
            ok=True,
            post_id="fixture_ig_001",
            url="https://instagram.com/reel/fixture_ig_001",
            error=None,
        )
