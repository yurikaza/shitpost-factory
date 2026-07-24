"""Direct fallback: TikTok Content Posting API.

Pre-audit reality: only SELF_ONLY (private) posts. 5 users/24h, 6 req/min per
token, access token 24h / refresh 365d. No scheduling parameter - we own the queue.

Default mode is CREATOR DRAFT: the video lands in the TikTok inbox and a human
publishes it. This works without the audit. Switch to direct post only after
approval (2-6 weeks).

Flow (Creator Draft):
1. POST /v2/post/publish/video/init/ — initialize upload, get upload URL + publish_id
2. PUT upload_url — upload the video bytes
3. POST /v2/post/publish/video/complete/ — finalize

Flow (Direct Post — requires audit):
Same as above but with publish_to_posts: "PUBLIC" instead of draft.
"""
from __future__ import annotations

import logging
import os
import time

import httpx

from factory.publish.base import Publisher
from factory.types import PublishResult, RenderedVideo, Script

log = logging.getLogger(__name__)

_TT_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPublisher(Publisher):
    """Direct TikTok Content Posting API publisher."""

    platform = "tiktok"

    def __init__(
        self,
        access_token: str | None = None,
        mode: str = "draft",    # draft | direct
        dry_run: bool = False,
    ):
        self._access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self._mode = mode  # draft works without audit; direct requires audit
        self._dry_run = dry_run

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Publish video to TikTok.

        In draft mode, the video lands in TikTok inbox for manual publishing.
        In direct mode, it posts publicly (requires content posting audit).
        """
        if self._dry_run:
            return self._fixture_publish(video, script)

        log.info("TikTok publish (mode=%s): %s", self._mode, video.path.name)

        try:
            # Step 1: Initialize upload
            init_body = {
                "post_info": {
                    "title": script.title[:150],  # TikTok max 150 chars
                    "privacy_level": "PUBLIC_TO_EVERYONE" if self._mode == "direct" else "SELF_ONLY",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video.path.stat().st_size,
                },
            }

            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{_TT_API_BASE}/post/publish/video/init/",
                    json=init_body,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

            upload_url = data.get("upload_url")
            publish_id = data.get("publish_id")

            if not upload_url or not publish_id:
                return PublishResult(
                    platform="tiktok", ok=False, post_id=None, url=None,
                    error=f"Init failed: {data}",
                )

            log.info("TikTok: publish_id=%s, uploading...", publish_id)

            # Step 2: Upload video bytes
            with open(video.path, "rb") as f:
                video_bytes = f.read()

            with httpx.Client(timeout=120) as client:
                upload_resp = client.put(
                    upload_url,
                    content=video_bytes,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{len(video_bytes) - 1}/{len(video_bytes)}",
                    },
                )
                upload_resp.raise_for_status()

            log.info("TikTok: upload complete, finalizing...")

            # Step 3: Finalize publish
            with httpx.Client(timeout=30) as client:
                complete_resp = client.post(
                    f"{_TT_API_BASE}/post/publish/video/complete/",
                    json={"publish_id": publish_id},
                    headers=self._headers(),
                )
                complete_resp.raise_for_status()
                result = complete_resp.json()

            log.info("TikTok: published publish_id=%s mode=%s", publish_id, self._mode)

            return PublishResult(
                platform="tiktok",
                ok=True,
                post_id=publish_id,
                url=f"https://tiktok.com/@me/video/{publish_id}" if self._mode == "direct" else None,
                error=None,
            )

        except httpx.HTTPStatusError as e:
            log.error("TikTok HTTP error: %s %s", e.response.status_code, e.response.text[:200])
            return PublishResult(
                platform="tiktok", ok=False, post_id=None, url=None,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            log.error("TikTok error: %s", e)
            return PublishResult(
                platform="tiktok", ok=False, post_id=None, url=None,
                error=str(e),
            )

    def _fixture_publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        log.info("TikTok DRY RUN (mode=%s): would publish %s", self._mode, video.path.name)
        return PublishResult(
            platform="tiktok",
            ok=True,
            post_id="fixture_tt_001",
            url="https://tiktok.com/@me/video/fixture_tt_001" if self._mode == "direct" else None,
            error=None,
        )
