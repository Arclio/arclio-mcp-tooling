"""
Ingestion service for processing and vectorizing documents from various sources.

This service implements optimal text chunking strategies using tiktoken for
token-aware chunking and semantic splitting for better context preservation.
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import tiktoken
from bs4 import BeautifulSoup

from .weaviate_service import WeaviateService

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting and processing documents into Weaviate collections."""

    def __init__(self, weaviate_service: WeaviateService):
        """
        Initialize the ingestion service.

        Args:
            weaviate_service: WeaviateService instance for database operations
        """
        self.weaviate_service = weaviate_service
        self._encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding

    async def ingest_from_url(
        self,
        url: str,
        collection_name: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        max_tokens_per_chunk: int = 500,
    ) -> dict[str, Any]:
        """
        Ingest and vectorize content from a public URL.

        Uses optimal chunking strategies combining token-aware splitting
        with semantic boundary detection for better context preservation.

        Args:
            url: Public URL to ingest content from
            collection_name: Target Weaviate collection name
            chunk_size: Target character count per chunk (fallback)
            chunk_overlap: Character overlap between chunks
            max_tokens_per_chunk: Maximum tokens per chunk (primary constraint)

        Returns:
            Dictionary with success status and ingestion results or error details
        """
        try:
            logger.info(f"Starting ingestion from URL: {url}")

            # Step 1: Download and extract content
            content_result = await self._download_and_extract_content(url)
            if content_result.get("error"):
                return content_result

            content = content_result["content"]
            metadata = content_result["metadata"]

            # Step 2: Perform optimal chunking
            chunks = self._create_optimal_chunks(
                content, max_tokens_per_chunk, chunk_overlap
            )

            if not chunks:
                return {
                    "error": True,
                    "message": "No content chunks were created from the URL",
                }

            logger.info(f"Created {len(chunks)} chunks from content")

            # Step 3: Prepare objects for Weaviate insertion
            objects = []
            for i, chunk in enumerate(chunks):
                obj = {
                    "content": chunk,
                    "source_url": url,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **metadata,  # Include extracted metadata
                }
                objects.append(obj)

            # Step 4: Batch insert into Weaviate
            insert_result = await self.weaviate_service.batch_insert_objects(
                collection_name=collection_name,
                objects=objects,
                unique_properties=["source_url", "chunk_index"],
                batch_size=50,  # Smaller batches for better error handling
            )

            if insert_result.get("error"):
                return insert_result

            logger.info(
                f"Successfully ingested {len(chunks)} chunks from {url} into collection '{collection_name}'"
            )

            return {
                "success": True,
                "chunks_ingested": len(chunks),
                "collection_name": collection_name,
                "source_url": url,
                "inserted_ids": insert_result.get("inserted_ids", []),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error during URL ingestion: {e}")
            return {
                "error": True,
                "message": f"URL ingestion failed: {str(e)}",
                "details": {
                    "url": url,
                    "collection_name": collection_name,
                    "error_type": type(e).__name__,
                },
            }

    async def _download_and_extract_content(self, url: str) -> dict[str, Any]:
        """
        Download content from URL and extract text with metadata.

        Args:
            url: URL to download from

        Returns:
            Dictionary with content, metadata, or error details
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            ) as client:
                logger.info(f"Downloading content from: {url}")
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()

                # Extract metadata
                metadata = {
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "status_code": response.status_code,
                }

                # Handle different content types
                if "text/html" in content_type:
                    content, html_metadata = self._extract_html_content(
                        response.text, url
                    )
                    metadata.update(html_metadata)
                elif "text/plain" in content_type:
                    content = response.text
                    metadata["title"] = self._extract_title_from_url(url)
                elif "application/json" in content_type:
                    # Handle JSON content by converting to readable text
                    import json

                    json_data = response.json()
                    content = json.dumps(json_data, indent=2)
                    metadata["title"] = self._extract_title_from_url(url)
                else:
                    # Try to decode as text
                    try:
                        content = response.text
                        metadata["title"] = self._extract_title_from_url(url)
                    except UnicodeDecodeError:
                        return {
                            "error": True,
                            "message": f"Unsupported content type: {content_type}",
                        }

                if not content or len(content.strip()) < 10:
                    return {
                        "error": True,
                        "message": "No meaningful content extracted from URL",
                    }

                logger.info(f"Extracted {len(content)} characters from {url}")
                return {"content": content, "metadata": metadata}

        except httpx.TimeoutException:
            return {"error": True, "message": f"Timeout while downloading from {url}"}
        except httpx.HTTPStatusError as e:
            return {
                "error": True,
                "message": f"HTTP error {e.response.status_code} for {url}",
            }
        except Exception as e:
            return {"error": True, "message": f"Download error: {str(e)}"}

    def _extract_html_content(self, html: str, url: str) -> tuple[str, dict[str, Any]]:
        """
        Extract clean text content and metadata from HTML.

        Args:
            html: HTML content
            url: Source URL for context

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Extract metadata
        metadata = {}

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()
        else:
            metadata["title"] = self._extract_title_from_url(url)

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            metadata["description"] = meta_desc.get("content", "").strip()

        # Author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            metadata["author"] = meta_author.get("content", "").strip()

        # Extract main content
        # Try to find main content areas first
        main_content = None
        for selector in ["main", "article", ".content", "#content", ".post-content"]:
            element = soup.select_one(selector)
            if element:
                main_content = element
                break

        if not main_content:
            # Fall back to body
            main_content = soup.find("body") or soup

        # Get text and clean it
        text = main_content.get_text()

        # Clean up whitespace and normalize
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text, metadata

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a reasonable title from URL path."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return parsed.netloc

        # Get the last part of the path and clean it up
        title = path.split("/")[-1]
        title = re.sub(r"\.[^.]*$", "", title)  # Remove file extension first
        title = re.sub(r"[._-]", " ", title)  # Then replace separators

        return title.title() if title else parsed.netloc

    def _create_optimal_chunks(
        self,
        text: str,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
    ) -> list[str]:
        """
        Create optimal text chunks using token-aware semantic splitting.

        This method combines several strategies:
        1. Token-aware chunking using tiktoken
        2. Semantic boundary detection (paragraphs, sentences)
        3. Overlap management for context preservation

        Args:
            text: Input text to chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # First, split by paragraphs to respect semantic boundaries
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            # Fallback to sentence splitting
            paragraphs = self._split_into_sentences(text)

        chunks = []
        current_chunk = ""
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = len(self._encoding.encode(paragraph))

            # If paragraph alone exceeds max_tokens, split it further
            if paragraph_tokens > max_tokens:
                # Add current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_tokens = 0

                # Split large paragraph
                sub_chunks = self._split_large_text(
                    paragraph, max_tokens, overlap_tokens
                )
                chunks.extend(sub_chunks)
                continue

            # Check if adding this paragraph would exceed limit
            if current_tokens + paragraph_tokens > max_tokens and current_chunk.strip():
                # Save current chunk
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap_tokens)
                current_chunk = (
                    overlap_text + "\n\n" + paragraph if overlap_text else paragraph
                )
                current_tokens = len(self._encoding.encode(current_chunk))
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_tokens += paragraph_tokens

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Filter out very small chunks
        chunks = [chunk for chunk in chunks if len(self._encoding.encode(chunk)) >= 10]

        logger.info(f"Created {len(chunks)} chunks with token-aware splitting")
        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple regex."""
        # Simple sentence splitting - can be enhanced with spaCy if needed
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_large_text(
        self, text: str, max_tokens: int, overlap_tokens: int
    ) -> list[str]:
        """
        Split text that's too large into smaller chunks.

        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = len(self._encoding.encode(sentence))

            if sentence_tokens > max_tokens:
                # Split very long sentences by words
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_tokens = 0

                word_chunks = self._split_by_words(sentence, max_tokens)
                chunks.extend(word_chunks)
                continue

            if current_tokens + sentence_tokens > max_tokens and current_chunk.strip():
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap_tokens)
                current_chunk = (
                    overlap_text + " " + sentence if overlap_text else sentence
                )
                current_tokens = len(self._encoding.encode(current_chunk))
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_words(self, text: str, max_tokens: int) -> list[str]:
        """Split text by words when sentences are too long."""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            if len(self._encoding.encode(test_chunk)) > max_tokens and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk = test_chunk

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """
        Get the last part of text for overlap with next chunk.

        Args:
            text: Source text
            overlap_tokens: Number of tokens to include in overlap

        Returns:
            Overlap text
        """
        if overlap_tokens <= 0:
            return ""

        # Split into sentences and take from the end
        sentences = self._split_into_sentences(text)
        if not sentences:
            return ""

        overlap_text = ""
        current_tokens = 0

        # Build overlap from end backwards
        for sentence in reversed(sentences):
            sentence_tokens = len(self._encoding.encode(sentence))
            if current_tokens + sentence_tokens > overlap_tokens:
                break
            overlap_text = sentence + " " + overlap_text if overlap_text else sentence
            current_tokens += sentence_tokens

        return overlap_text.strip()
