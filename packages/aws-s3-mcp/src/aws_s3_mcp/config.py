"""
Configuration management for AWS S3 MCP server.

Handles environment variable parsing and validation following the
<PACKAGE>_<COMPONENT>_<SETTING> standard.
"""

import logging
import os

logger = logging.getLogger(__name__)


class S3Config:
    """Configuration class for AWS S3 MCP server."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # AWS credentials and region
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # S3-specific configuration
        self.s3_buckets = self._parse_bucket_list(os.getenv("S3_BUCKETS"))
        self.s3_max_buckets = int(os.getenv("S3_MAX_BUCKETS", "5"))
        self.s3_object_max_keys = int(os.getenv("S3_OBJECT_MAX_KEYS", "1000"))

        # Validate configuration
        self._validate()

    def _parse_bucket_list(self, bucket_string: str | None) -> list[str] | None:
        """Parse comma-separated bucket list from environment variable."""
        if not bucket_string:
            return None
        return [bucket.strip() for bucket in bucket_string.split(",") if bucket.strip()]

    def _validate(self) -> None:
        """Validate configuration and raise errors for missing required values."""
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.warning(
                "AWS credentials not found in environment variables. "
                "Will attempt to use default AWS credential chain."
            )

        if self.s3_max_buckets <= 0:
            raise ValueError("S3_MAX_BUCKETS must be greater than 0")

        if self.s3_object_max_keys <= 0:
            raise ValueError("S3_OBJECT_MAX_KEYS must be greater than 0")

        logger.info(f"S3 MCP configured for region: {self.aws_region}")
        if self.s3_buckets:
            logger.info(f"Configured buckets: {self.s3_buckets}")
        else:
            logger.info(
                "No specific buckets configured - will expose all accessible buckets"
            )


# Global configuration instance
config = S3Config()
