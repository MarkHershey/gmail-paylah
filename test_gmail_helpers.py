import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest
from httplib2 import Response

from gmail_export import EmailExportError, export_email_content
from gmail_helpers import GetMessage, ListMessagesMatchingQuery


def response(status, payload):
    return Response({"status": str(status)}), json.dumps(payload).encode("utf-8")


def error_response(status=403, reason="rateLimitExceeded"):
    return response(
        status,
        {
            "error": {
                "code": status,
                "message": "Quota exceeded for Units per minute per user",
                "errors": [{"domain": "usageLimits", "reason": reason}],
            }
        },
    )


def request_with_responses(*responses):
    transport = Mock()
    transport.request.side_effect = responses
    request = HttpRequest(
        transport,
        lambda resp, content: json.loads(content),
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/example",
    )
    # Exercise the real client's retry logic without network calls or waiting.
    request._sleep = Mock()
    request._rand = lambda: 0.5
    return request


class GmailRetryTests(unittest.TestCase):
    def setUp(self):
        logger = patch("googleapiclient.http.LOGGER")
        logger.start()
        self.addCleanup(logger.stop)
        self.service = Mock()

    def test_message_download_recovers_from_quota_errors(self):
        message = {"id": "example", "payload": {"mimeType": "text/plain"}}
        request = request_with_responses(
            error_response(), error_response(), error_response(), response(200, message)
        )
        self.service.users.return_value.messages.return_value.get.return_value = request

        self.assertEqual(GetMessage(self.service, "me", "example"), message)
        self.assertEqual(request.http.request.call_count, 4)
        self.assertEqual(
            [call.args[0] for call in request._sleep.call_args_list], [1, 2, 4]
        )

    def test_other_temporary_failures_are_retried(self):
        for status, reason in (
            (403, "userRateLimitExceeded"),
            (429, "rateLimitExceeded"),
            (503, "backendError"),
        ):
            with self.subTest(status=status, reason=reason):
                request = request_with_responses(
                    error_response(status, reason), response(200, {"id": "example"})
                )
                self.service.users.return_value.messages.return_value.get.return_value = (
                    request
                )
                self.assertEqual(
                    GetMessage(self.service, "me", "example"), {"id": "example"}
                )
                self.assertEqual(request.http.request.call_count, 2)

    def test_persistent_quota_failure_raises_original_http_error(self):
        request = request_with_responses(*[error_response() for _ in range(8)])
        self.service.users.return_value.messages.return_value.get.return_value = request

        with self.assertRaises(HttpError) as caught:
            GetMessage(self.service, "me", "example")

        self.assertEqual(caught.exception.resp.status, 403)
        self.assertIn(b"rateLimitExceeded", caught.exception.content)
        self.assertEqual(request.http.request.call_count, 8)
        self.assertEqual(request._sleep.call_count, 7)

    def test_permanent_errors_are_not_retried_or_swallowed(self):
        for status, reason in (
            (403, "forbidden"),
            (401, "authError"),
            (404, "notFound"),
        ):
            with self.subTest(status=status):
                request = request_with_responses(error_response(status, reason))
                self.service.users.return_value.messages.return_value.get.return_value = (
                    request
                )
                with self.assertRaises(HttpError):
                    GetMessage(self.service, "me", "example")
                self.assertEqual(request.http.request.call_count, 1)
                request._sleep.assert_not_called()

    def test_listing_retries_each_page_without_losing_messages(self):
        first = request_with_responses(
            error_response(),
            response(200, {"messages": [{"id": "first"}], "nextPageToken": "page-2"}),
        )
        second = request_with_responses(
            error_response(503, "backendError"),
            response(200, {"messages": [{"id": "second"}]}),
        )
        self.service.users.return_value.messages.return_value.list.side_effect = [
            first,
            second,
        ]

        self.assertEqual(
            ListMessagesMatchingQuery(self.service, "me", "from:example.com"),
            [{"id": "first"}, {"id": "second"}],
        )
        self.assertEqual(first.http.request.call_count, 2)
        self.assertEqual(second.http.request.call_count, 2)
        for (
            call
        ) in self.service.users.return_value.messages.return_value.list.call_args_list:
            self.assertEqual(call.kwargs["maxResults"], 500)

    def test_listing_failure_is_not_returned_as_none(self):
        request = request_with_responses(*[error_response() for _ in range(8)])
        self.service.users.return_value.messages.return_value.list.return_value = (
            request
        )
        with self.assertRaises(HttpError):
            ListMessagesMatchingQuery(self.service, "me")
        self.assertEqual(request.http.request.call_count, 8)

    def test_failed_download_does_not_write_null_to_raw_cache(self):
        request = request_with_responses(*[error_response() for _ in range(8)])
        self.service.users.return_value.messages.return_value.get.return_value = request
        with TemporaryDirectory() as directory, patch(
            "gmail_export.get_gmail_service", return_value=self.service
        ), patch(
            "gmail_export.all_msg_ids_from_sender", return_value=["example"]
        ), patch(
            "gmail_export.tqdm", side_effect=lambda ids: ids
        ), patch(
            "gmail_export.print"
        ):
            with self.assertRaises(EmailExportError) as caught:
                export_email_content(Path(directory), "example@example.com")
            self.assertIsInstance(caught.exception.__cause__, HttpError)
            self.assertEqual(set(caught.exception.failures), {"example"})
            self.assertEqual(list(Path(directory).rglob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
