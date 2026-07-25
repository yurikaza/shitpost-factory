"""Reddit video sourcing via pullpush.io (public archive, no API key needed).

Uses pullpush.io to search for video posts, then downloads with yt-dlp.
No Reddit API credentials required.
"""
from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

import httpx

from factory.sourcing.base import FootageProvider
from factory.types import SourcedClip

log = logging.getLogger(__name__)

_API_BASE = "https://api.pullpush.io/reddit/search/submission/"


class RedditVideoProvider(FootageProvider):
    """Fetch short video clips from Reddit via pullpush.io."""

    name = "reddit-video"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run

    def search(
        self,
        subreddit: str,
        limit: int = 10,
        min_upvotes: int = 5000,
        max_duration_s: float = 15,
        min_duration_s: float = 3,
    ) -> list[SourcedClip]:
        """Search a subreddit for video posts."""
        if self._dry_run:
            return self._fixture_search(subreddit, limit)

        log.info("Reddit search: r/%s limit=%d min_upvotes=%d", subreddit, limit, min_upvotes)

        params = {
            "subreddit": subreddit,
            "is_video": "true",
            "sort": "desc",
            "sort_type": "score",
            "size": limit * 2,  # fetch extra to filter
        }

        with httpx.Client(timeout=30) as client:
            resp = client.get(_API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        clips = []
        for post in data.get("data", []):
            score = post.get("score", 0)
            if score < min_upvotes:
                continue

            url = post.get("url", "")
            if not url:
                continue

            # Only v.redd.it and imgur links
            if "v.redd.it" not in url and "imgur.com" not in url:
                continue

            title = post.get("title", "")
            post_id = post.get("id", "")

            clips.append(SourcedClip(
                provider="reddit-video",
                external_id=post_id,
                url=url,
                local_path=None,
                duration_s=10.0,  # unknown until download
                width=1080,
                height=1920,
                attribution=f"r/{subreddit} u/{post.get('author', 'unknown')}",
            ))

            if len(clips) >= limit:
                break

        log.info("Reddit: found %d video clips in r/%s", len(clips), subreddit)
        return clips

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a Reddit video via direct CDN URL.

        Uses v.redd.it CDN directly (no yt-dlp needed).
        Reddit CDN serves video+audio separately; we download video only
        since the pipeline adds its own TTS narration.
        """
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"reddit_{clip.external_id}.mp4"

        # Extract v.redd.it video ID from URL (not the post ID)
        # URL format: https://v.redd.it/{video_id}
        video_id = clip.url.split("v.redd.it/")[-1].split("/")[0].split("?")[0] if "v.redd.it" in (clip.url or "") else clip.external_id

        log.info("Downloading Reddit clip %s (vreddit=%s) from CDN", clip.external_id, video_id)

        # Try multiple resolutions
        for res in ["480", "360", "720"]:
            url = f"https://v.redd.it/{video_id}/DASH_{res}.mp4"
            try:
                resp = httpx.get(url, timeout=60, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200 and len(resp.content) > 1000:
                    output_path.write_bytes(resp.content)
                    log.info("Downloaded %s (%d bytes, %sp)", video_id, len(resp.content), res)
                    break
            except Exception as e:
                log.debug("Resolution %s failed: %s", res, e)
                continue
        else:
            raise RuntimeError(f"All CDN resolutions failed for {video_id} (post={clip.external_id})")

        # Update duration from downloaded file
        try:
            from factory.render.ffmpeg_utils import get_duration
            clip.duration_s = get_duration(output_path)
        except Exception:
            pass

        return output_path

    def _fixture_search(self, subreddit: str, limit: int) -> list[SourcedClip]:
        clips = []
        for i in range(min(limit, 3)):
            clips.append(SourcedClip(
                provider="reddit-video",
                external_id=f"fixture_{subreddit}_{i}",
                url=None,
                local_path=None,
                duration_s=8.0 + i * 2,
                width=1080,
                height=1920,
                attribution=f"r/{subreddit}",
            ))
        return clips

    def _fixture_download(self, clip: SourcedClip, dest: Path) -> Path:
        import subprocess
        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"reddit_{clip.external_id}.mp4"
        colors = ["red", "blue", "green", "purple", "orange"]
        color = colors[hash(clip.external_id) % len(colors)]
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c={color}:s=1080x1920:d={clip.duration_s}:r=30",
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
