"""
AWS S3 service implementation using aioboto3 for async operations.

This service provides high-level S3 operations while maintaining the fail-safe
error handling pattern used throughout the monorepo.
"""

import asyncio
import base64
import io
import logging
import mimetypes
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from pypdf import PdfReader

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

    async def get_text_content(self, bucket_name: str, key: str) -> dict[str, Any]:
        """
        Get text content of a specific object from S3 (text files only).

        This method enforces text-only retrieval and will fail for binary files.
        Use this when you specifically need text content (e.g., for ingestion into
        vector databases or text processing pipelines).

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key (path)

        Returns:
            Success: {"content": str, "mime_type": str, "size": int}
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
                    f"Getting text content for object '{key}' from bucket '{bucket_name}'"
                )

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

                # Check if content is text - REQUIRED for this method
                is_text = self._is_text_content(mime_type, content_data)

                if not is_text:
                    return {
                        "error": True,
                        "message": f"Object '{key}' is not a text file (detected MIME type: {mime_type})",
                        "details": {
                            "bucket_name": bucket_name,
                            "key": key,
                            "mime_type": mime_type,
                            "size": len(content_data),
                            "suggestion": "Use s3_get_object_content for binary files",
                        },
                    }

                # Decode as UTF-8 text
                try:
                    content = content_data.decode("utf-8")
                except UnicodeDecodeError as e:
                    return {
                        "error": True,
                        "message": f"Object '{key}' could not be decoded as UTF-8 text",
                        "details": {
                            "bucket_name": bucket_name,
                            "key": key,
                            "mime_type": mime_type,
                            "decode_error": str(e),
                            "suggestion": "File may be using a different encoding or is binary",
                        },
                    }

                result = {
                    "content": content,
                    "mime_type": mime_type,
                    "size": len(content_data),
                }

                logger.info(
                    f"Successfully retrieved text content for object '{key}' from bucket '{bucket_name}' "
                    f"({len(content_data)} bytes, {len(content)} characters)"
                )
                return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"S3 client error getting text content for '{key}' from bucket '{bucket_name}': "
                f"{error_code} - {error_message}"
            )

            return {
                "error": True,
                "message": f"Failed to get text content for '{key}' from bucket '{bucket_name}': {error_message}",
                "details": {
                    "error_code": error_code,
                    "bucket_name": bucket_name,
                    "key": key,
                },
            }
        except Exception as e:
            logger.error(
                f"Unexpected error getting text content for '{key}' from bucket '{bucket_name}': {str(e)}"
            )
            return {
                "error": True,
                "message": f"Unexpected error getting text content: {str(e)}",
                "details": {"bucket_name": bucket_name, "key": key},
            }

    async def extract_pdf_text(self, bucket_name: str, key: str) -> dict[str, Any]:
        """
        Extract text content from a PDF file in S3.

        This method downloads a PDF from S3 and extracts all text content.
        Use this when you need to process PDF documents for text analysis or
        ingestion into vector databases.

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key (path to PDF file)

        Returns:
            Success: {"text": str, "page_count": int, "size": int}
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
                    f"Extracting PDF text from object '{key}' in bucket '{bucket_name}'"
                )

                # Get the object with retry logic
                response = await self._get_object_with_retry(
                    s3_client, bucket_name, key
                )

                # Read the PDF content
                pdf_data = await response["Body"].read()

                # Validate that it's actually a PDF
                if not pdf_data.startswith(b"%PDF"):
                    return {
                        "error": True,
                        "message": f"Object '{key}' does not appear to be a valid PDF file",
                        "details": {
                            "bucket_name": bucket_name,
                            "key": key,
                            "suggestion": "Ensure the file is a valid PDF document",
                        },
                    }

                # Extract text from PDF
                try:
                    pdf_file = io.BytesIO(pdf_data)
                    pdf_reader = PdfReader(pdf_file)

                    # Extract text from all pages
                    text_parts = []
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                            logger.debug(
                                f"Extracted {len(page_text) if page_text else 0} characters from page {page_num}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract text from page {page_num}: {str(e)}"
                            )
                            continue

                    full_text = "\n\n".join(text_parts)

                    if not full_text.strip():
                        return {
                            "error": True,
                            "message": f"PDF '{key}' appears to be empty or contains no extractable text",
                            "details": {
                                "bucket_name": bucket_name,
                                "key": key,
                                "page_count": len(pdf_reader.pages),
                                "suggestion": "PDF may contain only images or scanned content. Consider using OCR.",
                            },
                        }

                    result = {
                        "text": full_text,
                        "page_count": len(pdf_reader.pages),
                        "size": len(pdf_data),
                    }

                    logger.info(
                        f"Successfully extracted text from PDF '{key}' in bucket '{bucket_name}' "
                        f"({len(pdf_reader.pages)} pages, {len(full_text)} characters)"
                    )
                    return result

                except Exception as e:
                    logger.error(f"Error parsing PDF '{key}': {str(e)}")
                    return {
                        "error": True,
                        "message": f"Failed to parse PDF '{key}': {str(e)}",
                        "details": {
                            "bucket_name": bucket_name,
                            "key": key,
                            "parse_error": str(e),
                            "suggestion": "PDF may be corrupted or use unsupported features",
                        },
                    }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"S3 client error extracting PDF text from '{key}' in bucket '{bucket_name}': "
                f"{error_code} - {error_message}"
            )

            return {
                "error": True,
                "message": f"Failed to extract PDF text from '{key}' in bucket '{bucket_name}': {error_message}",
                "details": {
                    "error_code": error_code,
                    "bucket_name": bucket_name,
                    "key": key,
                },
            }
        except Exception as e:
            logger.error(
                f"Unexpected error extracting PDF text from '{key}' in bucket '{bucket_name}': {str(e)}"
            )
            return {
                "error": True,
                "message": f"Unexpected error extracting PDF text: {str(e)}",
                "details": {"bucket_name": bucket_name, "key": key},
            }
