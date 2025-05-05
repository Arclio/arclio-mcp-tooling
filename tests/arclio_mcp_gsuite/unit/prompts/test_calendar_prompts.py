"""Unit tests for Calendar prompts."""

import pytest
from arclio_mcp_gsuite.prompts.calendar import draft_calendar_agenda
from mcp.server.fastmcp.prompts.base import UserMessage

pytestmark = pytest.mark.anyio


class TestDraftCalendarAgendaPrompt:
    """Tests for the draft_calendar_agenda prompt."""

    async def test_draft_agenda_success(self):
        """Test successful generation of the agenda drafting prompt (using simulation)."""
        event_id = "evt_12345"
        calendar_id = "primary"
        args = {
            "event_id": event_id,
            "calendar_id": calendar_id,
            "user_id": "calendar_user@example.com",
            # ctx is not strictly needed for this version, but pass None
            "ctx": None,
        }

        messages = await draft_calendar_agenda(**args)

        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        assert messages[0].role == "user"
        # Check content based on the simulation
        expected_details = (
            f"Meeting: {event_id} on Calendar: {calendar_id} - Details unavailable."
        )
        expected_content = f"Please draft a simple meeting agenda based on the following event information:\n\n{expected_details}"
        assert messages[0].content.text == expected_content

    # TODO: Add a test case that mocks ctx.read_resource once the event details resource exists
    # async def test_draft_agenda_with_context_mock(self, mocker):
    #     event_id = "evt_real_678"
    #     calendar_id = "team_cal"
    #     user_id = "cal_user_ctx@example.com"

    #     # Mock the context and its read_resource method
    #     mock_ctx = AsyncMock(spec=Context)
    #     mock_event_details = {
    #         "summary": "Project Kickoff",
    #         "start": {"dateTime": "2024-07-01T09:00:00-07:00"},
    #         "end": {"dateTime": "2024-07-01T10:00:00-07:00"},
    #         "description": "Initial meeting to discuss project scope."
    #     }
    #     mock_ctx.read_resource.return_value = mock_event_details

    #     args = {
    #         "event_id": event_id,
    #         "calendar_id": calendar_id,
    #         "user_id": user_id,
    #         "ctx": mock_ctx
    #     }

    #     messages = await draft_calendar_agenda(**args)

    #     mock_ctx.read_resource.assert_awaited_once_with(f"calendar://{calendar_id}/event/{event_id}")

    #     assert len(messages) == 1
    #     assert isinstance(messages[0], UserMessage)
    #     # Assert based on the mocked details
    #     expected_details_str = (
    #         f"Meeting: Project Kickoff\n"
    #         f"Time: 2024-07-01T09:00:00-07:00 - 2024-07-01T10:00:00-07:00\n"
    #         f"Description: Initial meeting to discuss project scope."
    #     )
    #     expected_content = (
    #         f"Please draft a simple meeting agenda based on the following event information:\n\n{expected_details_str}"
    #     )
    #     assert messages[0].content.text == expected_content
