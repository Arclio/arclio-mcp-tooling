"""
Integration tests for Google Calendar API.

These tests require valid Google API credentials and will make actual API calls.
They should be run cautiously to avoid unwanted side effects on real accounts.
"""

import os
import uuid
from datetime import datetime, timedelta

import pytest
import pytz
from arclio_mcp_gsuite.services.calendar import CalendarService

# Skip integration tests if environment flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Integration tests are disabled. Set RUN_INTEGRATION_TESTS=1 to enable.",
)


class TestCalendarIntegration:
    """Integration tests for Google Calendar API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the CalendarService for each test."""
        # Check if credentials are available
        for var in ["GSUITE_CLIENT_ID", "GSUITE_CLIENT_SECRET", "GSUITE_REFRESH_TOKEN"]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = CalendarService()

        # Generate a unique identifier for test events
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

    def test_list_calendars_integration(self):
        """Test listing calendars with the actual API."""
        calendars = self.service.list_calendars()

        # Verify response structure
        assert isinstance(calendars, list)
        if calendars:
            # Verify at least the primary calendar exists
            primary_found = False
            for calendar in calendars:
                assert "id" in calendar
                assert "summary" in calendar
                if calendar.get("primary", False):
                    primary_found = True

            assert primary_found, "Primary calendar not found in results"

    def test_calendar_event_lifecycle_integration(self):
        """
        Test the complete lifecycle of a calendar event: create, get, delete.

        This test ensures that we can:
        1. Create a test event in the user's calendar
        2. Retrieve the event and verify its details
        3. Delete the event to clean up
        """
        # Generate unique event data
        event_summary = f"Test Event {self.test_id}"
        event_description = f"Integration test event - will be deleted automatically - {self.test_id}"

        # Schedule event for 1 day in the future (to avoid timezone issues)
        now = datetime.now(pytz.UTC)
        start_time = (now + timedelta(days=1)).isoformat()
        end_time = (now + timedelta(days=1, hours=1)).isoformat()

        try:
            # 1. Create the test event
            create_result = self.service.create_event(
                summary=event_summary,
                start_time=start_time,
                end_time=end_time,
                description=event_description,
                # Avoid sending notifications for test events
                send_notifications=False,
            )

            # Verify creation succeeded
            assert isinstance(create_result, dict)
            assert "id" in create_result, "Event creation did not return an event ID"
            event_id = create_result["id"]

            # 2. Retrieve events and verify our test event is present
            events = self.service.get_events(time_min=start_time, time_max=(now + timedelta(days=2)).isoformat())

            # Find our test event
            test_event = None
            for event in events:
                if event.get("id") == event_id:
                    test_event = event
                    break

            assert test_event is not None, "Created event not found in retrieved events"
            assert test_event["summary"] == event_summary
            assert test_event["description"] == event_description

        finally:
            # 3. Clean up by deleting the event
            if "event_id" in locals():
                delete_result = self.service.delete_event(event_id=event_id, send_notifications=False)
                assert delete_result is True, "Event deletion failed"
