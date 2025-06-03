"""
Integration tests for Google Gmail API.

These tests require valid Google API credentials and will make actual API calls.
They should be run cautiously to avoid unwanted side effects on real accounts.
"""

import contextlib
import os
import uuid

import pytest
from arclio_mcp_gsuite.services.gmail import GmailService

# Skip integration tests if environment flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Integration tests are disabled. Set RUN_INTEGRATION_TESTS=1 to enable.",
)


class TestGmailIntegration:
    """Integration tests for Google Gmail API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the GmailService for each test."""
        # Check if credentials are available
        for var in ["GSUITE_CLIENT_ID", "GSUITE_CLIENT_SECRET", "GSUITE_REFRESH_TOKEN"]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = GmailService()

        # Generate a unique identifier for test content
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

        # Store created resources for cleanup
        self.drafts_to_delete = []

    def teardown_method(self):
        """Clean up any created resources."""
        # Delete any created drafts
        for draft_id in self.drafts_to_delete:
            with contextlib.suppress(Exception):
                self.service.delete_draft(draft_id)

    def test_query_emails_integration(self):
        """Test querying emails with the actual API."""
        # Query most recent emails (limit to 5 for speed)
        emails = self.service.query_emails(max_results=5)

        # Verify response structure without asserting specific content
        assert isinstance(emails, list)
        if emails:
            # Check structure of first email
            email = emails[0]
            assert "id" in email
            assert "threadId" in email
            assert "snippet" in email or "body" in email

    def test_email_draft_lifecycle_integration(self):
        """
        Test the draft email lifecycle: create, get, delete.

        This tests creating a draft email (without sending it),
        then retrieving it, and finally deleting it.
        """
        # Generate unique draft content
        draft_subject = f"Test Draft {self.test_id}"
        draft_body = f"This is a test draft created by integration tests. It will be deleted automatically. ID: {self.test_id}"

        # Who to address the draft to - typically the same account
        # Get email address from environment or use a placeholder
        to_email = os.environ.get("TEST_EMAIL_ADDRESS", "me@example.com")

        try:
            # 1. Create a draft email
            draft_result = self.service.create_draft(to=to_email, subject=draft_subject, body=draft_body)

            # Verify draft creation
            assert isinstance(draft_result, dict)
            assert "id" in draft_result, "Draft creation did not return an ID"
            draft_id = draft_result["id"]
            self.drafts_to_delete.append(draft_id)

            # 2. Query for drafts that match our test draft
            # We use the test_id in the body to find our specific draft
            emails = self.service.query_emails(query=f"in:drafts {self.test_id}", max_results=10)

            # Verify we can find our draft
            assert len(emails) >= 1, "Created draft not found in query results"

            # Get at least one matching draft's ID to verify details
            # (The draft ID in API queries is different from the one returned on creation)
            if emails and len(emails) > 0:
                # Get the first matching email's ID
                email_id = emails[0]["id"]

                # 3. Get the full draft content
                email_details = self.service.get_email_by_id(email_id, parse_body=True)

                # Verify email content matches what we created
                assert email_details["subject"] == draft_subject
                assert self.test_id in email_details.get("body", ""), "Draft body does not contain test ID"

        finally:
            # 4. Clean up by deleting the draft
            if hasattr(self, "drafts_to_delete") and self.drafts_to_delete:
                for draft_id in self.drafts_to_delete:
                    delete_result = self.service.delete_draft(draft_id)
                    assert delete_result is True, f"Failed to delete draft {draft_id}"
