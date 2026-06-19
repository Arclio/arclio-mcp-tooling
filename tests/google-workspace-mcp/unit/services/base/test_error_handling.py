"""
Unit tests for BaseGoogleService error handling and retry behavior.

Covers the three highest-leverage fixes: parsing Google's real error body,
normalized semantic error codes, 401 refresh-retry, and 429/5xx backoff.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.base import BaseGoogleService
from googleapiclient.errors import HttpError


def _http_error(status: int, content: bytes = b"", reason: str = "Error", headers=None):
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    resp.get.side_effect = (headers or {}).get
    return HttpError(resp=resp, content=content)


@pytest.fixture
def service():
    return BaseGoogleService(service_name="sheets", version="v4")


class TestHandleApiError:
    def test_parses_google_error_body_as_message(self, service):
        content = b'{"error": {"code": 400, "message": "Requested range is out of grid", "status": "INVALID_ARGUMENT"}}'
        result = service.handle_api_error("read_range", _http_error(400, content))
        assert result["error"] is True
        assert result["message"] == "Requested range is out of grid"
        assert result["api_status"] == "INVALID_ARGUMENT"
        assert result["error_code"] == "INVALID_ARGUMENT"

    def test_semantic_code_for_known_statuses(self, service):
        assert service.handle_api_error("x", _http_error(401))["error_code"] == "AUTH_EXPIRED"
        assert service.handle_api_error("x", _http_error(403))["error_code"] == "PERMISSION_DENIED"
        assert service.handle_api_error("x", _http_error(404))["error_code"] == "NOT_FOUND"
        assert service.handle_api_error("x", _http_error(429))["error_code"] == "RATE_LIMITED"
        assert service.handle_api_error("x", _http_error(503))["error_code"] == "TRANSIENT"

    def test_429_includes_retry_after(self, service):
        result = service.handle_api_error(
            "x", _http_error(429, headers={"retry-after": "7"})
        )
        assert result["retry_after"] == 7.0

    def test_malformed_body_does_not_crash(self, service):
        result = service.handle_api_error("x", _http_error(500, b"not json"))
        assert result["error"] is True
        assert result["error_code"] == "TRANSIENT"

    def test_non_http_error(self, service):
        result = service.handle_api_error("x", ValueError("boom"))
        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["type"] == "ValueError"


class TestExecuteWithRetry:
    def test_returns_result_on_success(self, service):
        request = MagicMock()
        request.execute.return_value = {"ok": True}
        assert service.execute_with_retry(request) == {"ok": True}
        assert request.execute.call_count == 1

    def test_retries_on_429_then_succeeds(self, service):
        request = MagicMock()
        request.execute.side_effect = [
            _http_error(429, headers={"retry-after": "0"}),
            {"ok": True},
        ]
        with patch("time.sleep"):  # don't actually wait
            result = service.execute_with_retry(request, "op")
        assert result == {"ok": True}
        assert request.execute.call_count == 2

    def test_gives_up_after_max_retries(self, service):
        request = MagicMock()
        request.execute.side_effect = _http_error(503)
        with patch("time.sleep"):
            with pytest.raises(HttpError):
                service.execute_with_retry(request, "op")
        # initial try + 3 retries
        assert request.execute.call_count == 4

    def test_401_triggers_one_refresh_then_retry(self, service):
        request = MagicMock()
        request.execute.side_effect = [_http_error(401), {"ok": True}]
        with patch.object(service, "_try_refresh_credentials", return_value=True) as refresh:
            result = service.execute_with_retry(request, "op")
        assert result == {"ok": True}
        refresh.assert_called_once()

    def test_401_not_retried_when_refresh_fails(self, service):
        request = MagicMock()
        request.execute.side_effect = _http_error(401)
        with patch.object(service, "_try_refresh_credentials", return_value=False):
            with pytest.raises(HttpError):
                service.execute_with_retry(request, "op")

    def test_non_retryable_4xx_raises_immediately(self, service):
        request = MagicMock()
        request.execute.side_effect = _http_error(404)
        with pytest.raises(HttpError):
            service.execute_with_retry(request, "op")
        assert request.execute.call_count == 1
