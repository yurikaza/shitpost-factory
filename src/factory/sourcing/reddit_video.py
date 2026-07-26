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

        with httpx.Client(timeout=30, headers={"User-Agent": "shitpost-factory/1.0"}) as client:
            for attempt in range(3):
                resp = client.get(_API_BASE, params=params)
                if resp.status_code == 429:
                    import time
                    wait = int(resp.headers.get("Retry-After", 10))
                    log.warning("Pullpush rate limited, waiting %ds", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 403:
                    import time
                    log.warning("Pullpush 403, retrying in 5s (attempt %d/3)", attempt + 1)
                    time.sleep(5)
                    continue
                resp.raise_for_status()
                break
            else:
                raise RuntimeError(f"Pullpush API failed after 3 attempts for r/{subreddit}")
            data = resp.json()

        clips = []
        for post in data.get("data", []):
            score = post.get("score", 0)
            if score < min_upvotes:
                continue

            url = post.get("url", "")
            if not url:
                continue

            # Only v.redd.it links (imgur CDN downloads need different handling)
            if "v.redd.it" not in url:
                continue

            title = post.get("title", "")
            post_id = post.get("id", "")

            # Extract video info from media field
            media = post.get("media") or post.get("secure_media") or {}
            media_info = media.get("reddit_video", {})

            clips.append(SourcedClip(
                provider="reddit-video",
                external_id=post_id,
                url=url,
                local_path=None,
                duration_s=float(media_info.get("duration", 10)),
                width=int(media_info.get("width", 1080)),
                height=int(media_info.get("height", 1920)),
                attribution=f"r/{subreddit} u/{post.get('author', 'unknown')}",
            ))

            if len(clips) >= limit:
                break

        log.info("Reddit: found %d video clips in r/%s", len(clips), subreddit)
        return clips

    def download(self, clip: SourcedClip, dest: Path) -> Path:
        """Download a Reddit video from v.redd.it CDN.

        Reddit serves video and audio as separate streams.
        We download both and merge with ffmpeg.
        """
        if self._dry_run:
            return self._fixture_download(clip, dest)

        if not clip.url:
            raise ValueError(f"No URL for clip {clip.external_id}")

        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / f"reddit_{clip.external_id}.mp4"

        # Extract v.redd.it video ID from URL
        video_id = clip.url.split("v.redd.it/")[-1].split("/")[0].split("?")[0] if "v.redd.it" in (clip.url or "") else clip.external_id

        log.info("Downloading Reddit clip %s (vreddit=%s)", clip.external_id, video_id)

        # Headers that v.redd.it accepts
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # Try multiple resolutions for video stream
        video_path = dest / f"reddit_{clip.external_id}_video.mp4"
        audio_path = dest / f"reddit_{clip.external_id}_audio.mp4"
        video_ok = False
        audio_ok = False

        for res in ["480", "360", "720", "1080"]:
            url = f"https://v.redd.it/{video_id}/DASH_{res}.mp4"
            try:
                resp = httpx.get(url, timeout=60, follow_redirects=True, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    video_path.write_bytes(resp.content)
                    video_ok = True
                    log.info("Video stream %s: %d bytes", res, len(resp.content))
                    break
            except Exception as e:
                log.debug("Resolution %s failed: %s", res, e)
                continue

        if not video_ok:
            raise RuntimeError(f"All CDN resolutions failed for {video_id} (post={clip.external_id})")

        # Try to download audio stream
        for audio_url in [
            f"https://v.redd.it/{video_id}/DASH_AUDIO_128.mp4",
            f"https://v.redd.it/{video_id}/DASH_audio.mp4",
        ]:
            try:
                resp = httpx.get(audio_url, timeout=30, follow_redirects=True, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    audio_path.write_bytes(resp.content)
                    audio_ok = True
                    log.info("Audio stream: %d bytes", len(resp.content))
                    break
            except Exception:
                continue

        # Merge video + audio, or just use video
        import subprocess as _sp
        if audio_ok:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac",
                str(output_path),
            ]
            result = _sp.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log.warning("ffmpeg merge failed, using video only: %s", result.stderr[:200])
                video_path.rename(output_path)
            else:
                video_path.unlink(missing_ok=True)
                audio_path.unlink(missing_ok=True)
        else:
            log.info("No audio stream available, using video only")
            video_path.rename(output_path)

        log.info("Downloaded %s (%d bytes)", clip.external_id, output_path.stat().st_size)

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
