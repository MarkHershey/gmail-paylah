import base64
import unittest

from gmail_export import get_msg_body


def text_part(mime_type, text):
    return {
        "mimeType": mime_type,
        "body": {"data": base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")},
    }


class MessageBodyTests(unittest.TestCase):
    def test_receipt_with_pdf_attachments_preserves_html(self):
        # Reproduce the failing message's MIME structure without private email data.
        html = "<p>Your receipt: S$12.50</p>"
        msg = {
            "payload": {
                "mimeType": "multipart/mixed",
                "body": {"size": 0},
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "body": {"size": 0},
                        "parts": [text_part("text/plain", ""), text_part("text/html", html)],
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "receipt.pdf",
                        "body": {"attachmentId": "receipt-attachment", "size": 100},
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "invoice.pdf",
                        "body": {"attachmentId": "invoice-attachment", "size": 100},
                    },
                ],
            }
        }
        self.assertEqual(get_msg_body(msg), "\n" + html)

    def test_related_message_ignores_inline_binary_data(self):
        msg = {
            "payload": {
                "mimeType": "multipart/related",
                "parts": [
                    text_part("text/html", "<p>Receipt</p>"),
                    {
                        "mimeType": "image/png",
                        "body": {"data": base64.urlsafe_b64encode(b"\x89PNG\xff").decode("ascii")},
                    },
                ],
            }
        }
        self.assertEqual(get_msg_body(msg), "<p>Receipt</p>")

    def test_empty_parts_do_not_hide_the_receipt(self):
        msg = {
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"size": 0}},
                    {"mimeType": "text/html"},
                    text_part("text/html", "<p>Receipt</p>"),
                ],
            }
        }
        self.assertEqual(get_msg_body(msg), "<p>Receipt</p>")

    def test_single_part_messages(self):
        for mime_type in ("text/plain", "text/html"):
            with self.subTest(mime_type=mime_type):
                self.assertEqual(
                    get_msg_body({"payload": text_part(mime_type, "Receipt – S$12.50")}),
                    "Receipt – S$12.50",
                )
                self.assertEqual(
                    get_msg_body({"payload": {"mimeType": mime_type, "body": {"size": 0}}}),
                    "",
                )

    def test_text_attachments_are_not_included_in_body(self):
        attachment = text_part("text/plain", "Unrelated attachment content")
        attachment["filename"] = "notes.txt"
        msg = {
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [text_part("text/plain", "Receipt"), attachment],
            }
        }
        self.assertEqual(get_msg_body(msg), "Receipt")

    def test_alternative_bodies_keep_their_order(self):
        msg = {
            "payload": {
                "mimeType": "multipart/alternative",
                "parts": [
                    text_part("text/plain", "Receipt"),
                    text_part("text/html", "<p>Receipt</p>"),
                ],
            }
        }
        self.assertEqual(get_msg_body(msg), "Receipt\n<p>Receipt</p>")


if __name__ == "__main__":
    unittest.main()
