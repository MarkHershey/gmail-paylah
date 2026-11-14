import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from googleapiclient.errors import HttpError
from httplib2 import Response

import main
from gmail_export import EmailExportError, all_msg_ids_from_sender, export_email_content
from parser_grab import GRAB_RECEIPT_QUERY


def valid_message(msg_id):
    return {
        "id": msg_id,
        "threadId": msg_id,
        "labelIds": [],
        "internalDate": "0",
        "payload": {
            "mimeType": "text/plain",
            "headers": [],
            "body": {"data": "UmVjZWlwdA=="},
        },
    }


class PipelineTests(unittest.TestCase):
    def test_individual_failures_are_reported_after_good_messages_are_saved(self):
        bad = valid_message("malformed")
        bad["internalDate"] = "invalid date"
        missing = HttpError(
            Response({"status": "404"}), b'{"error":{"message":"Not found"}}'
        )
        with TemporaryDirectory() as directory, patch(
            "gmail_export.get_gmail_service"
        ), patch(
            "gmail_export.all_msg_ids_from_sender",
            return_value=["malformed", "deleted", "good"],
        ), patch(
            "gmail_export.GetMessage", side_effect=[bad, missing, valid_message("good")]
        ), patch(
            "gmail_export.tqdm", side_effect=lambda ids: ids
        ), patch(
            "gmail_export.print"
        ):
            root = Path(directory)
            with self.assertRaises(EmailExportError) as caught:
                export_email_content(root, "example@example.com")
            self.assertEqual(set(caught.exception.failures), {"malformed", "deleted"})
            self.assertEqual(
                json.loads((root / "good.json").read_text())["body"], "Receipt"
            )
            self.assertFalse((root / "malformed.json").exists())

    def test_account_wide_failure_stops_before_other_messages(self):
        denied = HttpError(
            Response({"status": "403"}), b'{"error":{"message":"Forbidden"}}'
        )
        with TemporaryDirectory() as directory, patch(
            "gmail_export.get_gmail_service"
        ), patch(
            "gmail_export.all_msg_ids_from_sender", return_value=["first", "second"]
        ), patch(
            "gmail_export.GetMessage", side_effect=denied
        ) as fetch, patch(
            "gmail_export.tqdm", side_effect=lambda ids: ids
        ), patch(
            "gmail_export.print"
        ):
            with self.assertRaises(EmailExportError) as caught:
                export_email_content(Path(directory), "example@example.com")
            self.assertEqual(set(caught.exception.failures), {"first"})
            self.assertIs(caught.exception.__cause__, denied)
            fetch.assert_called_once()

    def test_authentication_and_listing_failures_preserve_reports_and_do_not_parse(
        self,
    ):
        for target in ("get_gmail_service", "all_msg_ids_from_sender"):
            with self.subTest(target=target), TemporaryDirectory() as directory, patch(
                "gmail_export.get_gmail_service", return_value=Mock()
            ), patch("gmail_export.print"), patch("main.parse_grab") as parse, patch(
                f"gmail_export.{target}", side_effect=RuntimeError("Simulated failure")
            ):
                root = Path(directory)
                report = root / "master_grab.json"
                report.write_text("original report")
                with self.assertRaises(RuntimeError):
                    main.grab_main(root)
                parse.assert_not_called()
                self.assertEqual(report.read_text(), "original report")

    def test_message_export_failure_prevents_report_generation(self):
        with TemporaryDirectory() as directory, patch(
            "main.export_email_content",
            side_effect=EmailExportError({"failed-id": "Decode error"}),
        ), patch("main.parse_grab") as parse:
            with self.assertRaises(EmailExportError):
                main.grab_main(Path(directory))
            parse.assert_not_called()

    def test_query_filter_is_grouped_with_sender_constraint(self):
        with patch(
            "gmail_export.ListMessagesMatchingQuery", return_value=[{"id": "receipt"}]
        ) as listing:
            ids = all_msg_ids_from_sender(
                Mock(), "no-reply@grab.com", GRAB_RECEIPT_QUERY
            )
        self.assertEqual(ids, ["receipt"])
        self.assertEqual(
            listing.call_args.kwargs["query"],
            f"from:no-reply@grab.com ({GRAB_RECEIPT_QUERY})",
        )

    def test_receipts_only_mode_reaches_exporter(self):
        with TemporaryDirectory() as directory, patch(
            "main.export_email_content"
        ) as export, patch("main.parse_grab"):
            main.grab_main(Path(directory), receipts_only=True)
            self.assertEqual(
                export.call_args.kwargs["query_filter"], GRAB_RECEIPT_QUERY
            )
            main.grab_main(Path(directory))
            self.assertEqual(
                export.call_args.kwargs["query_filter"], GRAB_RECEIPT_QUERY
            )
            main.grab_main(Path(directory), receipts_only=False)
            self.assertEqual(export.call_args.kwargs["query_filter"], "")

    def test_cli_flag_and_default(self):
        with patch("main.grab_main") as run:
            main.main(["--receipts-only"])
            run.assert_called_with(receipts_only=True)
            main.main([])
            run.assert_called_with(receipts_only=True)
            main.main(["--all-messages"])
            run.assert_called_with(receipts_only=False)


if __name__ == "__main__":
    unittest.main()
