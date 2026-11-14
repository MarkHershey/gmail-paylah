import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import datetime

from analyze_grab import MonthlyStats, print_period_averages, process_transaction_data


class GrabAnalysisTests(unittest.TestCase):
    def average_output(self, stats, months_back, today=datetime(2026, 11, 14)):
        with patch("analyze_grab.datetime") as clock, patch(
            "analyze_grab.print"
        ) as output:
            clock.today.return_value = today
            print_period_averages(stats, months_back)
        return "\n".join(call.args[0] for call in output.call_args_list)

    def test_completed_month_average_excludes_current_and_future_spending(self):
        stats = MonthlyStats(
            months=["2026-09", "2026-10", "2026-11", "2026-12"],
            ride_costs=[100, 100, 1000, 9000],
            food_costs=[20, 40, 1000, 9000],
            transport_trips={"2026-09": 2, "2026-10": 4, "2026-11": 100},
            food_orders={"2026-09": 1, "2026-10": 3, "2026-11": 100},
        )
        output = self.average_output(stats, 2)
        self.assertIn("2026-09, 2026-10", output)
        self.assertIn("Monthly Cost   : 100.00 SGD", output)
        self.assertIn("Monthly Cost   : 30.00 SGD", output)
        self.assertIn("Monthly Rides  : 3", output)
        self.assertIn("Monthly Orders : 2", output)

    def test_calendar_months_with_no_spending_count_as_zero(self):
        stats = MonthlyStats(["2026-08", "2026-10"], [30, 90], [0, 0], {}, {})
        output = self.average_output(stats, 3)
        self.assertIn("2026-08, 2026-09, 2026-10", output)
        self.assertIn("Monthly Cost   : 40.00 SGD", output)
        self.assertIn("Monthly Rides  : 0", output)

    def test_calendar_window_crosses_year_boundary_without_current_month_row(self):
        stats = MonthlyStats(["2026-11", "2026-12"], [200, 400], [0, 0], {}, {})
        output = self.average_output(stats, 2, datetime(2027, 1, 1))
        self.assertIn("2026-11, 2026-12", output)
        self.assertIn("Monthly Cost   : 300.00 SGD", output)

    def test_insufficient_history_does_not_produce_an_average(self):
        for months in ([], ["2026-10"]):
            stats = MonthlyStats(months, [10] * len(months), [0] * len(months), {}, {})
            output = self.average_output(stats, 2)
            self.assertIn("Not enough completed months", output)
            self.assertNotIn("Monthly Cost", output)

    def test_nonpositive_average_window_is_rejected(self):
        stats = MonthlyStats([], [], [], {}, {})
        for months in (0, -1):
            with self.assertRaises(ValueError):
                print_period_averages(stats, months)

    def test_foreign_currency_is_not_added_to_sgd_and_tips_are_not_extra_trips(self):
        with TemporaryDirectory() as directory, patch("analyze_grab.print"):
            path = Path(directory) / "transactions.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["txn_date", "txn_type", "txn_amount", "txn_currency"])
                writer.writerows(
                    [
                        ["2026-09-04", "Grab Transport", "12.50", "SGD"],
                        ["2026-09-04", "Grab Transport Tip", "2.00", "SGD"],
                        ["2026-09-04", "Grab Transport Fee", "4.00", "SGD"],
                        ["2026-09-04", "Grab Food", "10.00", "SGD"],
                        ["2026-09-04", "Grab Food Tip", "1.00", "SGD"],
                        ["2026-09-04", "Grab Transport", "1234.00", "THB"],
                    ]
                )
            stats = process_transaction_data(path)
            self.assertEqual(stats.ride_costs, [18.50])
            self.assertEqual(stats.transport_trips["2026-09"], 1)
            self.assertEqual(stats.food_costs, [11.00])
            self.assertEqual(stats.food_orders["2026-09"], 1)


if __name__ == "__main__":
    unittest.main()
