"""Direct fallback: YouTube Data API v3 videos.insert.

Quota: ~100 units per upload (was 1600 before Dec 2025), ~100 uploads/day in a
dedicated bucket. Avoid search.list - 100 units a call will drain the shared pool.

Unverified apps upload as PRIVATE until the compliance audit passes.

Flow:
1. Authenticate via OAuth2 (credentials in credentials/youtube_client_secret.json)
2. videos.insert with resumable upload
3. Set title, description, tags, categoryId
4. Video lands as PRIVATE until compliance audit passes
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from factory.publish.base import Publisher
from factory.types import PublishResult, RenderedVideo, Script

log = logging.getLogger(__name__)

_YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_YT_API_URL = "https://www.googleapis.com/youtube/v3"


class YouTubePublisher(Publisher):
    """Direct YouTube Data API v3 publisher."""

    platform = "youtube"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._credentials = None

    def _get_credentials(self):
        """Load OAuth2 credentials from disk."""
        if self._credentials is not None:
            return self._credentials

        secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "./credentials/youtube_client_secret.json")
        token_file = os.getenv("YOUTUBE_TOKEN_FILE", "./credentials/youtube_token.json")

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow

            if Path(token_file).exists():
                self._credentials = Credentials.from_authorized_user_file(token_file)
                log.info("Loaded YouTube credentials from %s", token_file)
            elif Path(secrets_file).exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    secrets_file,
                    scopes=["https://www.googleapis.com/auth/youtube.upload"],
                )
                self._credentials = flow.run_local_server(port=0)
                # Save for next time
                Path(token_file).parent.mkdir(parents=True, exist_ok=True)
                with open(token_file, "w") as f:
                    f.write(self._credentials.to_json())
                log.info("YouTube OAuth completed, saved token to %s", token_file)
            else:
                log.error("No YouTube credentials found at %s or %s", secrets_file, token_file)
                return None

        except ImportError:
            log.error("google-api-python-client / google-auth-oauthlib not installed")
            return None

        return self._credentials

    def publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        """Upload video to YouTube via videos.insert (resumable upload)."""
        if self._dry_run:
            return self._fixture_publish(video, script)

        log.info("YouTube upload: %s", video.path.name)

        try:
            creds = self._get_credentials()
            if creds is None:
                return PublishResult(
                    platform="youtube", ok=False, post_id=None, url=None,
                    error="No YouTube credentials configured",
                )

            # Build request body
            body = {
                "snippet": {
                    "title": script.title[:100],  # YouTube max 100 chars
                    "description": script.description[:5000],
                    "tags": script.hashtags[:30],  # YouTube max 30 tags
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "private",  # always private until audit passes
                    "selfDeclaredMadeForKids": False,
                },
            }

            # Resumable upload
            headers = {
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(video.path.stat().st_size),
            }

            with httpx.Client(timeout=30) as client:
                # Initiate resumable upload
                resp = client.post(
                    f"{_YT_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                upload_url = resp.headers.get("Location")
                if not upload_url:
                    raise ValueError("No upload URL returned by YouTube")

            # Upload the actual video file
            with open(video.path, "rb") as f:
                upload_headers = {
                    "Authorization": f"Bearer {creds.token}",
                    "Content-Type": "video/mp4",
                }
                with httpx.Client(timeout=600) as client:
                    upload_resp = client.put(
                        upload_url,
                        content=f.read(),
                        headers=upload_headers,
                    )
                    upload_resp.raise_for_status()
                    result = upload_resp.json()

            youtube_id = result.get("id")
            log.info("YouTube: uploaded video_id=%s (status=private)", youtube_id)

            return PublishResult(
                platform="youtube",
                ok=True,
                post_id=youtube_id,
                url=f"https://youtube.com/watch?v={youtube_id}" if youtube_id else None,
                error=None,
            )

        except Exception as e:
            log.error("YouTube upload error: %s", e)
            return PublishResult(
                platform="youtube", ok=False, post_id=None, url=None,
                error=str(e),
            )

    def _fixture_publish(self, video: RenderedVideo, script: Script) -> PublishResult:
        log.info("YouTube DRY RUN: would upload %s (privacyStatus=private)", video.path.name)
        return PublishResult(
            platform="youtube",
            ok=True,
            post_id="fixture_yt_001",
            url="https://youtube.com/watch?v=fixture_yt_001",
            error=None,
        )
