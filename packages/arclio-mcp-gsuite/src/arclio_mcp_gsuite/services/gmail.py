"""
Google Gmail service implementation.
"""

import base64
import logging
import time
import traceback
from email.mime.text import MIMEText
from typing import Any

from arclio_mcp_gsuite.services.base import BaseGoogleService

logger = logging.getLogger(__name__)


class GmailService(BaseGoogleService):
    """
    Service for interacting with Gmail API.
    """

    def __init__(self):
        """Initialize the Gmail service."""
        super().__init__("gmail", "v1")

    def query_emails(
        self, query: str | None = None, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """
        Query emails from Gmail based on a search query with pagination support.

        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            max_results: Maximum number of emails to retrieve (will be paginated if needed)

        Returns:
            List of parsed email message dictionaries
        """
        try:
            # Ensure max_results is within reasonable limits
            absolute_max = 1000  # Set a reasonable upper limit
            max_results = min(max(1, max_results), absolute_max)

            # Initialize result container
            messages = []
            next_page_token = None
            results_fetched = 0

            # Loop until we have enough results or run out of pages
            while results_fetched < max_results:
                # Calculate how many results to request in this page
                page_size = min(
                    100, max_results - results_fetched
                )  # Gmail API max page size is 100

                # Make the API request
                request_params = {
                    "userId": "me",
                    "maxResults": page_size,
                    "q": query if query else "",
                }

                # Add pageToken if we're not on the first page
                if next_page_token:
                    request_params["pageToken"] = next_page_token

                # Get this page of message IDs
                result = self.service.users().messages().list(**request_params).execute()

                # Extract messages and nextPageToken
                page_messages = result.get("messages", [])
                next_page_token = result.get("nextPageToken")

                # If no messages found or no more pages, exit the loop
                if not page_messages:
                    break

                # Fetch full message details for each message in this page
                for msg in page_messages:
                    try:
                        txt = (
                            self.service.users().messages().get(userId="me", id=msg["id"]).execute()
                        )
                        parsed_message = self._parse_message(txt=txt, parse_body=False)
                        if parsed_message:
                            messages.append(parsed_message)
                            results_fetched += 1
                    except Exception as e:
                        logger.warning(f"Error fetching message {msg['id']}: {e}")

                # If no more pages or we've reached max_results, exit the loop
                if not next_page_token or results_fetched >= max_results:
                    break

            return messages

        except Exception as e:
            return self.handle_api_error("query_emails", e)

    def get_email_by_id(self, email_id: str, parse_body: bool = True) -> dict[str, Any] | None:
        """
        Fetch a complete email message by its ID.

        Args:
            email_id: The Gmail message ID to retrieve
            parse_body: Whether to parse and include the message body

        Returns:
            Parsed email message dictionary or None if retrieval fails
        """
        try:
            # Fetch the complete message by ID
            message = self.service.users().messages().get(userId="me", id=email_id).execute()

            # Parse the message
            return self._parse_message(txt=message, parse_body=parse_body)

        except Exception as e:
            return self.handle_api_error("get_email_by_id", e)

    def get_email_with_attachments(
        self, email_id: str
    ) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
        """
        Fetch a complete email message by its ID including attachment information.

        Args:
            email_id: The Gmail message ID to retrieve

        Returns:
            Tuple containing parsed email message and attachments dictionary
        """
        try:
            # Fetch the complete message by ID
            message = self.service.users().messages().get(userId="me", id=email_id).execute()

            # Parse the message
            parsed_email = self._parse_message(txt=message, parse_body=True)

            # Extract attachment information
            attachments = {}
            if "payload" in message and "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if "attachmentId" in part.get("body", {}):
                        attachment_id = part["body"]["attachmentId"]
                        part_id = part["partId"]
                        attachment = {
                            "filename": part.get("filename", ""),
                            "mimeType": part.get("mimeType", ""),
                            "attachmentId": attachment_id,
                            "partId": part_id,
                        }
                        attachments[part_id] = attachment

            return parsed_email, attachments

        except Exception as e:
            logger.exception(f"Error fetching email with attachments: {e}")
            return None, {}

    def create_draft(
        self, to: str, subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any] | None:
        """
        Create a draft email message.

        Args:
            to: Email address of the recipient
            subject: Subject line of the email
            body: Body content of the email
            cc: List of email addresses to CC

        Returns:
            Draft message data including the draft ID if successful
        """
        try:
            # Create the message in MIME format
            mime_message = MIMEText(body)
            mime_message["to"] = to
            mime_message["subject"] = subject

            if cc:
                mime_message["cc"] = ",".join(cc)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

            # Create the draft
            return (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw_message}})
                .execute()
            )

        except Exception as e:
            return self.handle_api_error("create_draft", e)

    def delete_draft(self, draft_id: str) -> bool:
        """
        Delete a draft email message.

        Args:
            draft_id: The ID of the draft to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            self.service.users().drafts().delete(userId="me", id=draft_id).execute()
            return True

        except Exception as e:
            self.handle_api_error("delete_draft", e)
            return False

    def create_reply(
        self,
        original_message: dict[str, Any],
        reply_body: str,
        send: bool = False,
        cc: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Create a reply to an email message and either send it or save as draft.

        Args:
            original_message: The original message data
            reply_body: Body content of the reply
            send: If True, sends the reply immediately. If False, saves as draft.
            cc: List of email addresses to CC

        Returns:
            Sent message or draft data if successful
        """
        try:
            to_address = original_message.get("from")
            if not to_address:
                raise ValueError("Could not determine original sender's address")

            subject = original_message.get("subject", "")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"

            # Format the reply with quoted original content
            original_date = original_message.get("date", "")
            original_from = original_message.get("from", "")
            original_body = original_message.get("body", "")

            full_reply_body = (
                f"{reply_body}\n\n"
                f"On {original_date}, {original_from} wrote:\n"
                f"> {original_body.replace('\n', '\n> ') if original_body else '[No message body]'}"
            )

            # Create MIME message
            mime_message = MIMEText(full_reply_body)
            mime_message["to"] = to_address
            mime_message["subject"] = subject

            if cc:
                mime_message["cc"] = ",".join(cc)

            # Set reply headers
            if "message_id" in original_message:
                mime_message["In-Reply-To"] = original_message["message_id"]
                mime_message["References"] = original_message["message_id"]

            # Encode the message
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

            message_body = {"raw": raw_message}

            # Set thread ID if available
            if "threadId" in original_message:
                message_body["threadId"] = original_message["threadId"]

            if send:
                # Send the reply immediately
                result = (
                    self.service.users().messages().send(userId="me", body=message_body).execute()
                )
            else:
                # Save as draft
                result = (
                    self.service.users()
                    .drafts()
                    .create(userId="me", body={"message": message_body})
                    .execute()
                )

            return result

        except Exception as e:
            return self.handle_api_error("create_reply", e)

    def get_attachment(self, message_id: str, attachment_id: str) -> dict[str, Any] | None:
        """
        Retrieve a Gmail attachment by its ID.

        Args:
            message_id: The ID of the Gmail message containing the attachment
            attachment_id: The ID of the attachment to retrieve

        Returns:
            Attachment data dictionary including size and base64-encoded content
        """
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            return {"size": attachment.get("size"), "data": attachment.get("data")}

        except Exception as e:
            return self.handle_api_error("get_attachment", e)

    def _parse_message(
        self, txt: dict[str, Any], parse_body: bool = False
    ) -> dict[str, Any] | None:
        """
        Parse a Gmail message into a structured format.

        Args:
            txt: Raw message from Gmail API
            parse_body: Whether to parse and include the message body

        Returns:
            Parsed message dictionary
        """
        try:
            message_id = txt.get("id")
            thread_id = txt.get("threadId")
            payload = txt.get("payload", {})
            headers = payload.get("headers", [])

            metadata = {
                "id": message_id,
                "threadId": thread_id,
                "historyId": txt.get("historyId"),
                "internalDate": txt.get("internalDate"),
                "sizeEstimate": txt.get("sizeEstimate"),
                "labelIds": txt.get("labelIds", []),
                "snippet": txt.get("snippet"),
            }

            # Extract headers
            for header in headers:
                name = header.get("name", "").lower()
                value = header.get("value", "")

                if name == "subject":
                    metadata["subject"] = value
                elif name == "from":
                    metadata["from"] = value
                elif name == "to":
                    metadata["to"] = value
                elif name == "date":
                    metadata["date"] = value
                elif name == "cc":
                    metadata["cc"] = value
                elif name == "bcc":
                    metadata["bcc"] = value
                elif name == "message-id":
                    metadata["message_id"] = value
                elif name == "in-reply-to":
                    metadata["in_reply_to"] = value
                elif name == "references":
                    metadata["references"] = value
                elif name == "delivered-to":
                    metadata["delivered_to"] = value

            # Parse body if requested
            if parse_body:
                body = self._extract_body(payload)
                if body:
                    metadata["body"] = body

                metadata["mimeType"] = payload.get("mimeType")

            return metadata

        except Exception as e:
            logger.error(f"Error parsing message: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _extract_body(self, payload: dict[str, Any]) -> str | None:
        """
        Extract the email body from the payload.

        Args:
            payload: The message payload from Gmail API

        Returns:
            Extracted body text or None if extraction fails
        """
        try:
            # For single part text/plain messages
            if payload.get("mimeType") == "text/plain":
                data = payload.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

            # For multipart messages
            if payload.get("mimeType", "").startswith("multipart/"):
                parts = payload.get("parts", [])

                # First try to find a direct text/plain part
                for part in parts:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data")
                        if data:
                            return base64.urlsafe_b64decode(data).decode("utf-8")

                # If no direct text/plain, recursively check nested multipart structures
                for part in parts:
                    if part.get("mimeType", "").startswith("multipart/"):
                        nested_body = self._extract_body(part)
                        if nested_body:
                            return nested_body

                # If still no body found, try the first part as fallback
                if parts and "body" in parts[0] and "data" in parts[0]["body"]:
                    data = parts[0]["body"]["data"]
                    return base64.urlsafe_b64decode(data).decode("utf-8")

            return None

        except Exception as e:
            logger.error(f"Error extracting body: {str(e)}")
            return None

    def bulk_delete_emails(self, message_ids: list[str], user_id: str = "me") -> dict[str, Any]:
        """
        Delete multiple emails by their IDs using batch delete.

        Args:
            message_ids: List of message IDs to delete
            user_id: User ID, defaults to 'me'

        Returns:
            Dictionary with operation result
        """
        if not message_ids:
            return {"success": False, "message": "No message IDs provided"}

        # Validate message IDs
        if not all(isinstance(msg_id, str) and msg_id.strip() for msg_id in message_ids):
            return {
                "success": False,
                "message": "Invalid message IDs - all IDs must be non-empty strings",
            }

        try:
            # The batchDelete endpoint has a limit of how many IDs it can process at once
            max_batch_size = 1000  # Gmail API max batch size
            results = []
            total_count = 0

            # Process in batches with rate limiting
            for i in range(0, len(message_ids), max_batch_size):
                if i > 0:
                    # Add a small delay between batches to avoid rate limiting
                    time.sleep(0.5)

                batch = message_ids[i : i + max_batch_size]

                self.service.users().messages().batchDelete(
                    userId=user_id, body={"ids": batch}
                ).execute()

                batch_count = len(batch)
                total_count += batch_count
                results.append({"count": batch_count, "success": True})

            return {
                "success": True,
                "message": f"Batch delete request for {total_count} email(s) sent successfully. Deletion may take a moment to reflect.",
                "count_requested": total_count,
            }
        except Exception as e:
            return self.handle_api_error("bulk_delete_emails", e)

    def get_unread_count(self) -> int:
        """
        Get count of unread emails in the inbox.

        Returns:
            The count of unread emails
        """
        try:
            # Query for unread emails in inbox
            query = "is:unread in:inbox"
            results = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=1,  # We only need the count, not the actual messages
                )
                .execute()
            )

            # Get the total count
            return results.get("resultSizeEstimate", 0)

        except Exception as e:
            return self.handle_api_error("get_unread_count", e)

    def get_labels(self) -> list[dict[str, Any]]:
        """Get all Gmail labels for the authenticated user."""
        try:
            results = self.service.users().labels().list(userId="me").execute()
            return results.get("labels", [])
        except Exception as e:
            return self.handle_api_error("get_labels", e)
