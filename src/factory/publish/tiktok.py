"""TikTok Content Posting API publisher.

Handles OAuth2 token management and video publishing via TikTok's
Content Posting API.

Flow:
1. Run oauth_helper.py to get initial tokens (browser-based OAuth)
2. Tokens are stored in a JSON file per brand
3. Publisher auto-refreshes access tokens before posting
4. Uploads video file directly to TikTok

Requires:
- TikTok Developer App with Content Posting API enabled
- video.publish scope approved
- App must be audited for public posts (otherwise posts are private)

Environment variables:
- TIKTOK_CLIENT_KEY: App client key
- TIKTOK_CLIENT_SECRET: App client secret
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

# TikTok API endpoints
_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
_INIT_VIDEO_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# Token storage
_TOKENS_DIR = Path(__file__).parent.parent.parent.parent / "tokens"


@dataclass
class TikTokTokens:
    """TikTok OAuth tokens for a single account."""
    access_token: str
    refresh_token: str
    open_id: str
    expires_at: float  # Unix timestamp
    refresh_expires_at: float
    scope: str


def _get_credentials() -> tuple[str, str]:
    """Get client key and secret from environment."""
    client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    if not client_key or not client_secret:
        raise ValueError(
            "TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set. "
            "Get these from your TikTok Developer App."
        )
    return client_key, client_secret


def _get_token_path(brand: str) -> Path:
    """Get the token file path for a brand."""
    _TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    return _TOKENS_DIR / f"{brand}_tiktok.json"


def load_tokens(brand: str) -> TikTokTokens | None:
    """Load stored tokens for a brand."""
    path = _get_token_path(brand)
    if not path.exists():
        return None

    with open(path) as f:
        data = json.load(f)

    return TikTokTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        open_id=data["open_id"],
        expires_at=data["expires_at"],
        refresh_expires_at=data["refresh_expires_at"],
        scope=data.get("scope", ""),
    )


def save_tokens(brand: str, tokens: TikTokTokens) -> None:
    """Save tokens for a brand."""
    path = _get_token_path(brand)
    _TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump({
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "open_id": tokens.open_id,
            "expires_at": tokens.expires_at,
            "refresh_expires_at": tokens.refresh_expires_at,
            "scope": tokens.scope,
        }, f, indent=2)

    log.info("Saved TikTok tokens for brand=%s", brand)


def exchange_code(code: str, redirect_uri: str, brand: str) -> TikTokTokens:
    """Exchange authorization code for tokens.

    Args:
        code: Authorization code from OAuth callback.
        redirect_uri: Must match the one used in the auth request.
        brand: Brand name to save tokens under.

    Returns:
        TikTokTokens with access and refresh tokens.
    """
    client_key, client_secret = _get_credentials()

    resp = requests.post(_TOKEN_URL, data={
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })

    resp.raise_for_status()
    data = resp.json()

    if "error" in data and data["error"] != "ok":
        raise ValueError(f"Token exchange failed: {data}")

    now = time.time()
    tokens = TikTokTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        open_id=data["open_id"],
        expires_at=now + data["expires_in"],
        refresh_expires_at=now + data["refresh_expires_in"],
        scope=data.get("scope", ""),
    )

    save_tokens(brand, tokens)
    return tokens


def refresh_tokens(brand: str, force: bool = False) -> TikTokTokens:
    """Refresh access token if expired or about to expire.

    Args:
        brand: Brand name.
        force: Force refresh even if token is still valid.

    Returns:
        Valid TikTokTokens.

    Raises:
        ValueError: If no tokens found or refresh token expired.
    """
    tokens = load_tokens(brand)
    if not tokens:
        raise ValueError(
            f"No TikTok tokens found for brand={brand}. "
            f"Run the OAuth flow first: python -m factory.publish.tiktok_oauth --brand {brand}"
        )

    now = time.time()

    # Check if refresh token is expired (365 days)
    if now > tokens.refresh_expires_at:
        raise ValueError(
            f"Refresh token expired for brand={brand}. "
            f"Re-run the OAuth flow: python -m factory.publish.tiktok_oauth --brand {brand}"
        )

    # Check if access token is still valid (refresh if <1 hour left)
    if not force and now < tokens.expires_at - 3600:
        return tokens

    log.info("Refreshing TikTok access token for brand=%s", brand)
    client_key, client_secret = _get_credentials()

    resp = requests.post(_TOKEN_URL, data={
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": tokens.refresh_token,
    })

    resp.raise_for_status()
    data = resp.json()

    if "error" in data and data["error"] != "ok":
        raise ValueError(f"Token refresh failed: {data}")

    new_tokens = TikTokTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        open_id=data["open_id"],
        expires_at=now + data["expires_in"],
        refresh_expires_at=now + data["refresh_expires_in"],
        scope=data.get("scope", tokens.scope),
    )

    save_tokens(brand, new_tokens)
    return new_tokens


def get_creator_info(access_token: str) -> dict[str, Any]:
    """Query creator info (username, privacy options, etc.)."""
    resp = requests.post(
        _CREATOR_INFO_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    resp.raise_for_status()
    return resp.json()


def init_video_upload(
    access_token: str,
    video_path: Path,
    title: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    disable_duet: bool = False,
    disable_comment: bool = False,
    disable_stitch: bool = False,
) -> dict[str, Any]:
    """Initialize video upload and get upload URL.

    Args:
        access_token: Valid access token.
        video_path: Path to the video file.
        title: Post title (can include hashtags and @mentions).
        privacy_level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, or SELF_ONLY.
        disable_duet: Disable duets.
        disable_comment: Disable comments.
        disable_stitch: Disable stitches.

    Returns:
        Dict with publish_id and upload_url.
    """
    video_size = video_path.stat().st_size

    # TikTok recommends 10MB chunks
    chunk_size = 10 * 1024 * 1024
    total_chunks = (video_size + chunk_size - 1) // chunk_size

    resp = requests.post(
        _INIT_VIDEO_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("error", {}).get("code") != "ok":
        raise ValueError(f"Init upload failed: {data}")

    return {
        "publish_id": data["data"]["publish_id"],
        "upload_url": data["data"]["upload_url"],
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
    }


def upload_video(upload_url: str, video_path: Path, chunk_size: int) -> None:
    """Upload video file to TikTok's upload URL.

    Uses chunked upload for large files.
    """
    video_size = video_path.stat().st_size
    uploaded = 0

    with open(video_path, "rb") as f:
        while uploaded < video_size:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            end_byte = min(uploaded + len(chunk) - 1, video_size - 1)

            resp = requests.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes {uploaded}-{end_byte}/{video_size}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                },
                data=chunk,
            )
            resp.raise_for_status()
            uploaded += len(chunk)

            log.info("Uploaded %d/%d bytes", uploaded, video_size)

    log.info("Video upload complete: %s", video_path.name)


def get_post_status(access_token: str, publish_id: str) -> dict[str, Any]:
    """Check the status of a published post."""
    resp = requests.post(
        _STATUS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={"publish_id": publish_id},
    )
    resp.raise_for_status()
    return resp.json()


def publish_video(
    brand: str,
    video_path: Path,
    title: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    wait_for_status: bool = True,
    status_timeout: int = 120,
) -> dict[str, Any]:
    """Full publish flow: refresh token → init → upload → check status.

    Args:
        brand: Brand name (for token lookup).
        video_path: Path to the video file.
        title: Post title with hashtags.
        privacy_level: Privacy setting.
        wait_for_status: Wait for TikTok to process the video.
        status_timeout: Max seconds to wait for status.

    Returns:
        Dict with publish_id and status info.
    """
    # Refresh token
    tokens = refresh_tokens(brand)

    # Init upload
    log.info("Initializing TikTok upload for brand=%s", brand)
    init_result = init_video_upload(
        tokens.access_token,
        video_path,
        title,
        privacy_level=privacy_level,
    )

    publish_id = init_result["publish_id"]
    upload_url = init_result["upload_url"]
    chunk_size = init_result["chunk_size"]

    # Upload video
    log.info("Uploading video to TikTok: %s", video_path.name)
    upload_video(upload_url, video_path, chunk_size)

    # Check status
    if wait_for_status:
        log.info("Waiting for TikTok to process video...")
        start = time.time()
        while time.time() - start < status_timeout:
            status = get_post_status(tokens.access_token, publish_id)
            status_code = status.get("data", {}).get("status", "")

            if status_code == "SUCCESS":
                log.info("TikTok post published successfully: %s", publish_id)
                return {"publish_id": publish_id, "status": "SUCCESS", "data": status}
            elif status_code in ("FAILED", "CANCELLED"):
                raise ValueError(f"TikTok post failed: {status}")

            time.sleep(5)

        log.warning("Status check timed out after %ds", status_timeout)
        return {"publish_id": publish_id, "status": "PROCESSING", "data": None}

    return {"publish_id": publish_id, "status": "UPLOADED", "data": None}
