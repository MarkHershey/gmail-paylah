import unittest
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from parser_grab import main, parse_grab_html


class GrabReceiptTests(unittest.TestCase):
    def test_amount_formats_and_currencies(self):
        cases = [
            ("S$12.50", "12.50", "SGD"),
            ("S$ 12.50", "12.50", "SGD"),
            ("SGD 1,234.50", "1234.50", "SGD"),
            ("฿1,234", "1234.00", "THB"),
            ("RM 11.33", "11.33", "MYR"),
            ("S$0.00", "0.00", "SGD"),
        ]
        for text, amount, currency in cases:
            with self.subTest(text=text):
                receipt = parse_grab_html(
                    f"<p>Hope you enjoyed your ride!</p><p>Total Paid</p><p>{text}</p>"
                )
                self.assertEqual(receipt["txn_amount"], amount)
                self.assertEqual(receipt["txn_currency"], currency)

    def test_total_is_used_instead_of_first_amount(self):
        receipt = parse_grab_html(
            "<p>Subtotal</p><p>S$10.00</p><p>TOTAL</p><p>S$12.50</p>"
        )
        self.assertEqual(receipt["txn_amount"], "12.50")

    def test_driver_tip_is_a_separate_transaction_type(self):
        receipt = parse_grab_html(
            "<p>Grab Tips E-Receipt</p><p>Total Paid</p><p>S$2.00</p>"
        )
        self.assertEqual(receipt["txn_type"], "Grab Transport Tip")
        self.assertEqual(receipt["txn_amount"], "2.00")

    def test_split_currency_and_amount(self):
        receipt = parse_grab_html("<p>TOTAL</p><span>S$</span><span>12.50</span>")
        self.assertEqual(receipt["txn_amount"], "12.50")

    def test_food_tip_and_cancellation_fee_are_separate_types(self):
        food_tip = parse_grab_html(
            "<p>Grab Tips E-Receipt</p><p>GrabFood</p><p>Total</p><p>SGD 2.00</p>"
        )
        cancellation = parse_grab_html(
            "<p>Grab Cancellation E-Receipt</p><p>Total Paid</p><p>SGD 4.00</p>"
        )
        self.assertEqual(food_tip["txn_type"], "Grab Food Tip")
        self.assertEqual(cancellation["txn_type"], "Grab Transport Fee")

    def test_grabpay_purchase_uses_total_after_discounts(self):
        receipt = parse_grab_html(
            "<p>You've made a payment to Example Shop 🎉</p><p>Order amount</p><p>S$10.00</p><p>Total</p><p>S$8.00</p><p>Payment to</p><p>Example Shop</p>"
        )
        self.assertEqual(receipt["txn_amount"], "8.00")
        self.assertEqual(receipt["txn_type"], "GrabPay")
        self.assertEqual(receipt["txn_to"], "Example Shop")

    def test_paylater_purchase_uses_payable_amount_not_current_zero_payment(self):
        receipt = parse_grab_html(
            "<p>Your postpaid payment is successful! 🎉</p><p>Total order value</p><p>S$30.00</p><p>Payable amount</p><p>S$24.50</p><p>Current payment</p><p>S$0.00</p><p>Ordered from</p><p>Example Shop</p>"
        )
        self.assertEqual(receipt["txn_amount"], "24.50")
        self.assertEqual(receipt["txn_type"], "Grab PayLater")

    def test_thai_food_receipt(self):
        receipt = parse_grab_html(
            "<p>ทานอาหารให้อร่อย!</p><p>รวม</p><p>฿ 254</p><p>GrabFood</p>"
        )
        self.assertEqual(receipt["txn_amount"], "254.00")
        self.assertEqual(receipt["txn_currency"], "THB")
        self.assertEqual(receipt["txn_type"], "Grab Food")

    def test_food_receipt_is_not_classified_from_ride_promotion(self):
        receipt = parse_grab_html(
            "<p>Hope you enjoyed your food!</p><p>TOTAL</p><p>S$12.50</p><p>Try a ride today</p>"
        )
        self.assertEqual(receipt["txn_type"], "Grab Food")

    def test_missing_or_unsupported_amount_is_not_recorded_as_zero(self):
        for body in (
            "<p>Receipt</p>",
            "<p>TOTAL</p><p>USD 12.50</p>",
            "<p>TOTAL</p><p>S$1,23.50</p>",
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_grab_html(body)

    def test_export_keeps_original_currency_in_both_formats(self):
        with TemporaryDirectory() as directory, patch("parser_grab.print"):
            root = Path(directory)
            (root / "grab").mkdir()
            message = {
                "id": "receipt",
                "date": "2026-09-04",
                "subject": "Your Grab E-Receipt",
                "body": "<p>Total Paid</p><p>฿1,234</p>",
            }
            (root / "grab" / "receipt.json").write_text(json.dumps(message))
            main(root)
            records = json.loads((root / "master_grab.json").read_text())
            with (root / "master_grab.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(records[0]["txn_currency"], "THB")
            self.assertEqual(records[0]["txn_amount"], "1234.00")
            self.assertEqual(rows[0]["txn_currency"], "THB")
            self.assertEqual(rows[0]["txn_amount"], "1234.00")

    def test_unparseable_receipt_preserves_existing_reports(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "grab").mkdir()
            message = {
                "id": "receipt",
                "date": "2026-09-04",
                "subject": "Your Grab E-Receipt",
                "body": "<p>No amount</p>",
            }
            (root / "grab" / "receipt.json").write_text(json.dumps(message))
            (root / "master_grab.json").write_text("previous JSON")
            (root / "master_grab.csv").write_text("previous CSV")
            with self.assertRaises(ValueError):
                main(root)
            self.assertEqual((root / "master_grab.json").read_text(), "previous JSON")
            self.assertEqual((root / "master_grab.csv").read_text(), "previous CSV")

    def test_purchase_and_cancellation_subjects_are_included_but_bill_settlement_is_not(
        self,
    ):
        cases = [
            (
                "You've made a payment to Example Shop 🎉",
                "<p>You've made a payment to Example Shop 🎉</p><p>Total</p><p>S$8.00</p><p>Payment to</p><p>Example Shop</p>",
            ),
            (
                "Your postpaid payment to Example Shop is successful 🎉",
                "<p>Your postpaid payment is successful! 🎉</p><p>Payable amount</p><p>S$24.50</p><p>Ordered from</p><p>Example Shop</p>",
            ),
            (
                "SGD 4.00 fee paid off",
                "<p>Grab Cancellation E-Receipt</p><p>Total Paid</p><p>SGD 4.00</p>",
            ),
            (
                "Thank you for your payment!",
                "<p>Your postpaid bill is fully paid!</p><p>Current payment</p><p>S$32.50</p>",
            ),
        ]
        with TemporaryDirectory() as directory, patch("parser_grab.print"):
            root = Path(directory)
            (root / "grab").mkdir()
            for i, (subject, body) in enumerate(cases):
                message = {
                    "id": str(i),
                    "date": "2026-09-04",
                    "subject": subject,
                    "body": body,
                }
                (root / "grab" / f"{i}.json").write_text(json.dumps(message))
            main(root)
            records = json.loads((root / "master_grab.json").read_text())
            self.assertEqual({row["txn_id"] for row in records}, {"0", "1", "2"})


if __name__ == "__main__":
    unittest.main()
