import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from file_utils import atomic_text_writer
from gmail_export import export_email_content


class ExportCacheTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "raw").mkdir()
        self.raw = self.root / "raw" / "example_raw_msg.json"
        self.processed = self.root / "example.json"
        self.message = {
            "id": "example",
            "threadId": "thread",
            "labelIds": [],
            "internalDate": "0",
            "payload": {
                "mimeType": "text/plain",
                "headers": [],
                "body": {"data": "UmVjZWlwdA=="},
            },
        }
        for target, kwargs in (
            ("gmail_export.get_gmail_service", {"return_value": Mock()}),
            ("gmail_export.all_msg_ids_from_sender", {"return_value": ["example"]}),
            ("gmail_export.tqdm", {"side_effect": lambda ids: ids}),
            ("gmail_export.print", {}),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_null_raw_cache_is_replaced_even_if_processed_export_exists(self):
        self.raw.write_text("null")
        self.processed.write_text(
            json.dumps({"id": "example", "date": "1970-01-01", "body": "Receipt"})
        )
        with patch("gmail_export.GetMessage", return_value=self.message) as fetch:
            export_email_content(self.root, "example@example.com")
            fetch.assert_called_once()
        self.assertEqual(json.loads(self.raw.read_text()), self.message)

    def test_missing_or_broken_export_is_rebuilt_without_gmail_download(self):
        self.raw.write_text(json.dumps(self.message))
        for existing in (None, "{broken JSON"):
            with self.subTest(existing=existing):
                if existing is not None:
                    self.processed.write_text(existing)
                with patch("gmail_export.GetMessage") as fetch:
                    export_email_content(self.root, "example@example.com")
                    fetch.assert_not_called()
                self.assertEqual(
                    json.loads(self.processed.read_text())["body"], "Receipt"
                )

    def test_interrupted_write_preserves_original_file(self):
        self.processed.write_text("original data")
        with self.assertRaises(RuntimeError):
            with atomic_text_writer(self.processed) as stream:
                stream.write("partial data")
                raise RuntimeError("Simulated interruption")
        self.assertEqual(self.processed.read_text(), "original data")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_stale_body_is_rebuilt_from_raw_cache(self):
        self.raw.write_text(json.dumps(self.message))
        self.processed.write_text(
            json.dumps({"id": "example", "date": "1970-01-01", "body": ""})
        )
        with patch("gmail_export.GetMessage") as fetch:
            export_email_content(self.root, "example@example.com")
            fetch.assert_not_called()
        self.assertEqual(json.loads(self.processed.read_text())["body"], "Receipt")

    def test_incomplete_raw_json_is_fetched_again(self):
        self.raw.write_text(
            json.dumps({"id": "example", "payload": {}, "internalDate": "0"})
        )
        with patch("gmail_export.GetMessage", return_value=self.message) as fetch:
            export_email_content(self.root, "example@example.com")
            fetch.assert_called_once()
        self.assertEqual(json.loads(self.raw.read_text()), self.message)

    def test_missing_cached_metadata_is_rebuilt_and_header_case_is_ignored(self):
        self.message["payload"]["headers"] = [
            {"name": "subject", "value": "Your Grab E-Receipt"}
        ]
        self.raw.write_text(json.dumps(self.message))
        self.processed.write_text(
            json.dumps({"id": "example", "body": "Receipt", "date": "1970-01-01"})
        )
        with patch("gmail_export.GetMessage") as fetch:
            export_email_content(self.root, "example@example.com")
            fetch.assert_not_called()
        self.assertEqual(
            json.loads(self.processed.read_text())["subject"], "Your Grab E-Receipt"
        )

    def test_cache_without_raw_saving_does_not_download_twice(self):
        with patch("gmail_export.GetMessage", return_value=self.message) as fetch:
            export_email_content(self.root, "example@example.com", save_raw=False)
            export_email_content(self.root, "example@example.com", save_raw=False)
            fetch.assert_called_once()
        self.assertFalse(self.raw.exists())

    def test_disabling_cache_refreshes_raw_and_processed_files(self):
        self.raw.write_text(json.dumps(self.message))
        self.processed.write_text(
            json.dumps({"id": "example", "body": "Receipt", "date": "1970-01-01"})
        )
        self.message["payload"]["body"]["data"] = "TmV3"
        with patch("gmail_export.GetMessage", return_value=self.message) as fetch:
            export_email_content(self.root, "example@example.com", use_cache=False)
            fetch.assert_called_once()
        self.assertEqual(json.loads(self.processed.read_text())["body"], "New")
        self.assertEqual(json.loads(self.raw.read_text()), self.message)


if __name__ == "__main__":
    unittest.main()
