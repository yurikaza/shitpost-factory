"""Upload rendered videos to Cloudflare R2 for public hosting.

R2 is S3-compatible, so we use boto3 with a custom endpoint.
Videos are uploaded to a temp path and auto-expire via lifecycle rule
(or you can set up a cleanup cron).

Requires: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)


class R2Uploader:
    """Upload files to Cloudflare R2 and return public URLs."""

    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket: str | None = None,
        public_url: str | None = None,
    ):
        self._account_id = account_id or os.getenv("R2_ACCOUNT_ID", "")
        self._access_key_id = access_key_id or os.getenv("R2_ACCESS_KEY_ID", "")
        self._secret_access_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY", "")
        self._bucket = bucket or os.getenv("R2_BUCKET", "shitpost-factory")
        self._public_url = (public_url or os.getenv("R2_PUBLIC_URL", "")).rstrip("/")

        if not all([self._account_id, self._access_key_id, self._secret_access_key]):
            raise ValueError(
                "R2 credentials not configured. Set R2_ACCOUNT_ID, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env"
            )

        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{self._account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def upload_video(self, local_path: Path, key: str | None = None) -> str:
        """Upload a video file to R2 and return its public URL.

        Args:
            local_path: Path to the local video file.
            key: Optional S3 key. Defaults to `videos/{uuid4}.mp4`.

        Returns:
            Public URL of the uploaded video.
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Video not found: {local_path}")

        if key is None:
            key = f"videos/{uuid.uuid4().hex}.mp4"

        content_type = "video/mp4"
        file_size = local_path.stat().st_size
        log.info("Uploading %s (%d bytes) to R2://%s/%s", local_path.name, file_size, self._bucket, key)

        with open(local_path, "rb") as f:
            self._client.upload_fileobj(
                f,
                self._bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=3600",
                },
            )

        public_url = f"{self._public_url}/{key}"
        log.info("Uploaded: %s", public_url)
        return public_url

    def delete_video(self, key: str) -> None:
        """Delete a video from R2 (cleanup after publish)."""
        self._client.delete_object(Bucket=self._bucket, Key=key)
        log.info("Deleted R2://%s/%s", self._bucket, key)

    def upload_and_get_url(self, local_path: Path) -> tuple[str, str]:
        """Upload and return (public_url, key) for later cleanup."""
        key = f"videos/{uuid.uuid4().hex}.mp4"
        url = self.upload_video(local_path, key=key)
        return url, key
