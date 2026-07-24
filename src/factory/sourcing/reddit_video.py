"""Reddit video sourcing. Fetches short funny video clips from subreddits.

Uses PRAW (Python Reddit API Wrapper) to find video posts, then downloads
the MP4 directly from Reddit's CDN or i.redd.it.

Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path

import httpx

from factory.sourcing.base import FootageProvider
from factory.types import SourcedClip

log = logging.getLogger(__name__)


class RedditVideoProvider(FootageProvider):
    """Fetch short video clips from Reddit subreddits."""

    name = "reddit-video"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self._client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self._user_agent = os.getenv("REDDIT_USER_AGENT", "shitpost-factory/0.1")
        self._reddit = None

    def _get_reddit(self):
        """Lazy-init PRAW Reddit instance."""
        if self._reddit is None:
            import praw
            self._reddit = praw.Reddit(
                client_id=self._client_id,
                client_secret=self._client_secret,
                user_agent=self._user_agent,
            )
        return self._reddit

    def search(
        self,
        subreddit: str,
        limit: int = 10,
        min_upvotes: int = 5000,
        max_duration_s: float = 15,
        min_duration_s: float = 3,
    ) -> list[SourcedClip]:
        """Search a subreddit for video posts matching criteria."""
        if self._dry_run:
            return self._fixture_search(subreddit, limit)

        reddit = self._get_reddit()
        clips = []

        log.info("Reddit video search: r/%s limit=%d min_upvotes=%d", subreddit, limit, min_upvotes)

        for submission in reddit.subreddit(subreddit).hot(limit=limit * 3):
            # Filter: must be a video post with enough upvotes
            if submission.score < min_upvotes:
                continue
            if submission.is_self:
                continue

            # Get video URL
            video_url = self._extract_video_url(submission)
            if not video_url:
                continue

            # Check duration if available
            duration = getattr(submission, "media", {})
            if isinstance(duration, dict):
                reddit_video = duration.get("reddit_video", {})
                dur = reddit_video.get("duration", 0)
                if dur and (dur < min_duration_s or dur > max_duration_s):
                    continue

            clips.append(SourcedClip(
                provider="reddit-video",
                external_id=submission.id,
                url=video_url,
                local_path=None,
                duration_s=float(dur) if dur else 10.0,
                width=1080,
                height=1920,
                attribution=f"r/{subreddit} u/{submission.author}",
            ))

            if len(clips) >= limit:
                break

        log.info("Reddit: found %d video clips in r/%s", len(clips), subreddit)
        return clips

    def _extract_video_url(self, submission) -> str | None:
        """Extract the direct MP4 URL from a Reddit submission."""
        # Reddit hosted video
        if hasattr(submission, "media") and submission.media:
            reddit_video = submission.media.get("reddit_video", {})
            fallback_url = reddit_video.get("fallback_url")
            if fallback_url:
                return fallback_url

        # i.redd.it video
        if submission.url and "v.redd.it" in submission.url:
            return submission.url

        # External video link (imgur, streamable, etc.)
        if submission.url:
            url = submission.url
            if "imgur.com" in url and not url.endswith(".jpg"):
                # Imgur gifv/mp4
                if url.endswith(".gifv"):
                    url = url.replace(".gifv", ".mp4")
                return url
            if "streamable.com" in url:
                return url

        return None

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a video clip to dest."""
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"reddit_{clip.external_id}.mp4"

        log.info("Downloading Reddit clip %s -> %s", clip.external_id, output_path)

        headers = {"User-Agent": self._user_agent}
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", clip.url, headers=headers) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        return output_path

    def _fixture_search(self, subreddit: str, limit: int) -> list[SourcedClip]:
        """Return fixture clips for offline testing."""
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
        """Create a fixture video for offline testing."""
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
