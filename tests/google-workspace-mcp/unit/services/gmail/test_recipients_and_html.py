"""
Tests for recipient normalization and HTML email support in GmailService.

Agents frequently emit list params as JSON-array STRINGS; the service must
coerce those instead of mangling headers per-character. HTML bodies must produce
a multipart/alternative message with both plain and HTML parts.
"""

import base64

from google_workspace_mcp.services.gmail import (
    _build_mime_message,
    _normalize_recipients,
)


class TestNormalizeRecipients:
    def test_real_list_passes_through(self):
        assert _normalize_recipients(["a@x.com", "b@y.com"]) == [
            "a@x.com",
            "b@y.com",
        ]

    def test_json_array_string_is_parsed(self):
        # The exact failure mode #4 describes: agent emits a JSON string.
        assert _normalize_recipients('["a@x.com", "b@y.com"]') == [
            "a@x.com",
            "b@y.com",
        ]

    def test_single_bare_address(self):
        assert _normalize_recipients("a@x.com") == ["a@x.com"]

    def test_comma_separated_string(self):
        assert _normalize_recipients("a@x.com, b@y.com") == ["a@x.com", "b@y.com"]

    def test_none_and_empty(self):
        assert _normalize_recipients(None) == []
        assert _normalize_recipients("") == []
        assert _normalize_recipients([]) == []

    def test_strips_and_drops_blanks(self):
        assert _normalize_recipients(["  a@x.com  ", "", "  "]) == ["a@x.com"]

    def test_display_name_with_comma_not_split(self):
        # A comma inside a quoted display name must not split the address into
        # garbage fragments.
        result = _normalize_recipients('"Doe, John" <j@x.com>, a@y.com')
        assert result == ['"Doe, John" <j@x.com>', "a@y.com"]


class TestBuildMimeMessage:
    def test_plain_only(self):
        msg = _build_mime_message("hello")
        assert msg.get_content_type() == "text/plain"

    def test_html_makes_multipart_alternative(self):
        msg = _build_mime_message("plain fallback", html_body="<p>rich</p>")
        assert msg.get_content_type() == "multipart/alternative"
        parts = msg.get_payload()
        assert parts[0].get_content_type() == "text/plain"
        assert parts[1].get_content_type() == "text/html"
        # decode=True handles the transfer encoding (base64 under utf-8).
        assert b"rich" in parts[1].get_payload(decode=True)

    def test_non_ascii_html_encodes_without_error(self):
        # The ʻokina, em-dash and emoji must not raise UnicodeEncodeError.
        msg = _build_mime_message(
            "Koʻa Kea — plain", html_body="<p>Koʻa Kea — rich 🌺</p>"
        )
        raw = msg.as_bytes()  # would raise without utf-8 charset
        assert b"utf-8" in raw.lower()

    def test_plain_only_non_ascii_encodes(self):
        msg = _build_mime_message("Koʻa Kea — résumé")
        assert msg.as_bytes()  # no UnicodeEncodeError


def _decode_raw(call_kwargs):
    raw = call_kwargs["body"]["raw"]
    return base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")


class TestSendEmailIntegration:
    def test_stringified_to_is_not_mangled(self, mock_gmail_service):
        mock_gmail_service.service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "m1"
        }
        result = mock_gmail_service.send_email(
            to='["a@x.com"]', subject="Hi", body="b"
        )
        assert result == {"id": "m1"}
        _, kwargs = mock_gmail_service.service.users.return_value.messages.return_value.send.call_args
        raw = _decode_raw(kwargs)
        # Header has the clean address, NOT a per-character mangled string.
        assert "a@x.com" in raw
        assert '["a' not in raw

    def test_empty_to_after_normalization_errors(self, mock_gmail_service):
        result = mock_gmail_service.send_email(to="[]", subject="Hi", body="b")
        assert result["error"] is True
        assert result["error_type"] == "validation_error"

    def test_html_email_sends_multipart(self, mock_gmail_service):
        mock_gmail_service.service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "m2"
        }
        mock_gmail_service.send_email(
            to=["a@x.com"], subject="Hi", body="plain", html_body="<b>rich</b>"
        )
        _, kwargs = mock_gmail_service.service.users.return_value.messages.return_value.send.call_args
        raw = _decode_raw(kwargs)
        assert "multipart/alternative" in raw
        # The HTML part is present (its body is transfer-encoded under utf-8, so
        # assert on the structural content-type marker rather than raw markup).
        assert 'Content-Type: text/html; charset="utf-8"' in raw
