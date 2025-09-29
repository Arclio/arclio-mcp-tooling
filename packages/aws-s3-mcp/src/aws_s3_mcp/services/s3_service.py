"""
AWS S3 service implementation using aioboto3 for async operations.

This service provides high-level S3 operations while maintaining the fail-safe
error handling pattern used throughout the monorepo.
"""

import asyncio
import base64
import logging
import mimetypes
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from aws_s3_mcp.config import config

logger = logging.getLogger(__name__)


class S3Service:
    """
    Service class for AWS S3 operations using aioboto3 exclusively.

    Implements the stateless/fail-safe pattern with proper async I/O.
    """

    def __init__(self):
        """Initialize S3 service with configuration."""
        # Configure boto3 with retries and timeouts
        self.boto_config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=60,
            max_pool_connections=50,
        )

        # Create aioboto3 session
        self.session = aioboto3.Session()

        # Validate credentials on initialization
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate that AWS credentials are available."""
        try:
            # Try to create a session to validate credentials
            session = aioboto3.Session()
            # Check if credentials are available (this is synchronous)
            credentials = session.get_credentials()
            if credentials is None:
                raise NoCredentialsError()
        except NoCredentialsError:
            raise ValueError(
                "AWS credentials not found. Please set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables or configure "
                "AWS credentials file."
            ) from None

    async def list_objects(
        self, bucket_name: str, prefix: str = "", max_keys: int = 1000
    ) -> dict[str, Any]:
        """
        List objects in a specific S3 bucket.

        Args:
            bucket_name: Name of the S3 bucket
            prefix: Object prefix for filtering
            max_keys: Maximum number of objects to return

        Returns:
            Success: {"count": int, "objects": [{"key": str, "last_modified": str, "size": int, "etag": str}]}
            Error: {"error": True, "message": str, "details": dict}
        """
        # Validate bucket access if configured buckets are specified
        if config.s3_buckets and bucket_name not in config.s3_buckets:
            return {
                "error": True,
                "message": f"Bucket '{bucket_name}' not in configured bucket list",
                "details": {"configured_buckets": config.s3_buckets},
            }

        try:
            async with self.session.client(
                "s3", region_name=config.aws_region, config=self.boto_config
            ) as s3_client:

                logger.debug(
                    f"Listing objects in bucket '{bucket_name}' with prefix '{prefix}'"
                )

                response = await s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix,
                    MaxKeys=min(max_keys, config.s3_object_max_keys),
                )

                objects = []
                for obj in response.get("Contents", []):
                    objects.append(
                        {
                            "key": obj["Key"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "size": obj["Size"],
                            "etag": obj["ETag"].strip('"'),  # Remove quotes from ETag
                        }
                    )

                result = {"count": len(objects), "objects": objects}

                logger.info(
                    f"Successfully listed {len(objects)} objects from bucket '{bucket_name}'"
                )
                return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"S3 client error listing objects in bucket '{bucket_name}': {error_code} - {error_message}"
            )

            return {
                "error": True,
                "message": f"Failed to list objects in bucket '{bucket_name}': {error_message}",
                "details": {
                    "error_code": error_code,
                    "bucket_name": bucket_name,
                    "prefix": prefix,
                },
            }
        except Exception as e:
            logger.error(
                f"Unexpected error listing objects in bucket '{bucket_name}': {str(e)}"
            )
            return {
                "error": True,
                "message": f"Unexpected error listing objects: {str(e)}",
                "details": {"bucket_name": bucket_name, "prefix": prefix},
            }

    async def get_object_content(self, bucket_name: str, key: str) -> dict[str, Any]:
        """
        Get content of a specific object from S3.

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key (path)

        Returns:
            Success: {"content": str, "mime_type": str, "encoding": str, "size": int}
            Error: {"error": True, "message": str, "details": dict}
        """
        # Validate bucket access if configured buckets are specified
        if config.s3_buckets and bucket_name not in config.s3_buckets:
            return {
                "error": True,
                "message": f"Bucket '{bucket_name}' not in configured bucket list",
                "details": {"configured_buckets": config.s3_buckets},
            }

        try:
            async with self.session.client(
                "s3", region_name=config.aws_region, config=self.boto_config
            ) as s3_client:

                logger.debug(f"Getting object '{key}' from bucket '{bucket_name}'")

                # Get the object with retry logic
                response = await self._get_object_with_retry(
                    s3_client, bucket_name, key
                )

                # Read the content from the stream
                content_data = await response["Body"].read()

                # Determine MIME type
                mime_type = response.get("ContentType", "application/octet-stream")
                if not mime_type or mime_type == "binary/octet-stream":
                    # Fallback to guessing from file extension
                    guessed_type, _ = mimetypes.guess_type(key)
                    mime_type = guessed_type or "application/octet-stream"

                # Determine if content is text or binary
                is_text = self._is_text_content(mime_type, content_data)

                if is_text:
                    try:
                        content = content_data.decode("utf-8")
                        encoding = "utf-8"
                    except UnicodeDecodeError:
                        # If UTF-8 decoding fails, treat as binary
                        content = base64.b64encode(content_data).decode("ascii")
                        encoding = "base64"
                        mime_type = "application/octet-stream"
                else:
                    # Binary content - encode as base64
                    content = base64.b64encode(content_data).decode("ascii")
                    encoding = "base64"

                result = {
                    "content": content,
                    "mime_type": mime_type,
                    "encoding": encoding,
                    "size": len(content_data),
                }

                logger.info(
                    f"Successfully retrieved object '{key}' from bucket '{bucket_name}' "
                    f"({len(content_data)} bytes, {encoding} encoding)"
                )
                return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"S3 client error getting object '{key}' from bucket '{bucket_name}': {error_code} - {error_message}"
            )

            return {
                "error": True,
                "message": f"Failed to get object '{key}' from bucket '{bucket_name}': {error_message}",
                "details": {
                    "error_code": error_code,
                    "bucket_name": bucket_name,
                    "key": key,
                },
            }
        except Exception as e:
            logger.error(
                f"Unexpected error getting object '{key}' from bucket '{bucket_name}': {str(e)}"
            )
            return {
                "error": True,
                "message": f"Unexpected error getting object: {str(e)}",
                "details": {"bucket_name": bucket_name, "key": key},
            }

    async def _get_object_with_retry(
        self, s3_client, bucket_name: str, key: str, max_retries: int = 3
    ):
        """Get object with exponential backoff retry logic."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await s3_client.get_object(Bucket=bucket_name, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    # Don't retry for missing keys
                    raise
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_time} seconds: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)

        raise last_exception

    def _is_text_content(self, mime_type: str, content_data: bytes) -> bool:
        """
        Determine if content should be treated as text based on MIME type and content analysis.

        Args:
            mime_type: The MIME type of the content
            content_data: The raw content bytes

        Returns:
            True if content should be treated as text, False for binary
        """
        # Check MIME type first
        text_mime_types = {
            "text/plain",
            "text/markdown",
            "text/html",
            "text/css",
            "text/javascript",
            "text/csv",
            "text/xml",
            "application/json",
            "application/xml",
            "application/yaml",
            "application/x-yaml",
        }

        if mime_type in text_mime_types or mime_type.startswith("text/"):
            return True

        # For unknown MIME types, do a simple heuristic check
        if mime_type == "application/octet-stream":
            try:
                # Try to decode a sample of the content
                sample = content_data[:1024]  # Check first 1KB
                sample.decode("utf-8")

                # Check for null bytes (common in binary files)
                if b"\x00" in sample:
                    return False

                # If we can decode and no null bytes, likely text
                return True
            except UnicodeDecodeError:
                pass

        return False
