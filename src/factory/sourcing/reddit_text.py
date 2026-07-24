"""Reddit TEXT only, read-only, via PRAW.

Never touch Reddit-hosted video - posting to Reddit does not transfer copyright
(docs/research-2026.md section 4.2). Story bodies must be rewritten in
scripting/, not narrated verbatim. That rewrite is the transformation that keeps
the account monetisable.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from factory.types import SourcedClip, SourcedMaterial

log = logging.getLogger(__name__)


class RedditTextProvider:
    """Fetch Reddit post text (not video) for script material."""

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._reddit = None

    def _get_client(self):
        """Lazy-init PRAW client (requires env vars)."""
        if self._reddit is not None:
            return self._reddit
        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                user_agent=os.getenv("REDDIT_USER_AGENT", "shitpost-factory/0.1"),
            )
            return self._reddit
        except ImportError:
            log.warning("praw not installed, Reddit provider unavailable")
            return None

    def fetch_post(
        self,
        subreddit: str,
        min_upvotes: int = 2000,
        max_body_chars: int = 1200,
    ) -> SourcedMaterial | None:
        """Fetch a top post from a subreddit as text material.

        Returns SourcedMaterial with text_source set, no clips.
        Returns None if no suitable post found.
        """
        if self._dry_run:
            return self._fixture_post(subreddit)

        reddit = self._get_client()
        if reddit is None:
            return None

        log.info("Reddit: fetching top posts from r/%s (min_upvotes=%d)", subreddit, min_upvotes)
        try:
            subreddit_obj = reddit.subreddit(subreddit)
            for post in subreddit_obj.top(time_filter="day", limit=20):
                if post.score < min_upvotes:
                    continue
                if post.is_self and post.selftext:
                    body = post.selftext[:max_body_chars]
                    return SourcedMaterial(
                        concept_id="reddit-stories",
                        clips=[],
                        text_source=body,
                        source_ref=f"https://reddit.com{post.permalink}",
                    )
        except Exception as e:
            log.error("Reddit API error: %s", e)

        log.warning("Reddit: no suitable post found in r/%s", subreddit)
        return None

    def _fixture_post(self, subreddit: str) -> SourcedMaterial:
        """Return a fixture post for offline testing."""
        return SourcedMaterial(
            concept_id="reddit-stories",
            clips=[],
            text_source=(
                "So this happened yesterday. I was at the grocery store and this "
                "guy cuts in front of me in the checkout line. I politely said "
                "'excuse me, the line is back here.' He ignored me. So I said it "
                "louder. He turned around and said 'I'm in a hurry.' I said "
                "'So is everyone else, mate.' The whole line clapped. Okay not "
                "really but people were nodding."
            ),
            source_ref=f"https://reddit.com/r/{subreddit}/fixture_post",
        )

    @staticmethod
    def hash_text(text: str) -> str:
        """Hash text content for deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
