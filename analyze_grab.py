import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from rich import print

MASTER_GRAB_CSV = "output/master_grab.csv"
OUT_DIR = Path("output")

# Add constants for visualization
FIGURE_SIZE = (21, 9)
POLYNOMIAL_DEGREE = 15
TRANSPORT_COLOR = "#1D263B"
FOOD_COLOR = "#4CB963"


@dataclass
class MonthlyStats:
    months: List[str]
    ride_costs: List[float]
    food_costs: List[float]
    transport_trips: Dict[str, int]
    food_orders: Dict[str, int]


def process_transaction_data(file_path: str) -> MonthlyStats:
    """Return SGD statistics; preserve separate tip costs without adding trips."""
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        transactions = list(reader)

    monthly_cost = defaultdict(lambda: defaultdict(float))
    monthly_transport_trips = defaultdict(int)
    monthly_food_orders = defaultdict(int)
    foreign_transactions = 0

    for txn in transactions:
        if txn.get("txn_currency", "SGD") != "SGD":
            foreign_transactions += 1
            continue
        if not txn["txn_date"]:
            continue

        year_month = txn["txn_date"][:7]
        txn_type = txn["txn_type"]
        amount = float(txn["txn_amount"])
        cost_type = {
            "Grab Transport Tip": "Grab Transport",
            "Grab Transport Fee": "Grab Transport",
            "Grab Food Tip": "Grab Food",
        }.get(txn_type, txn_type)
        monthly_cost[year_month][cost_type] += amount

        if txn_type == "Grab Transport":
            monthly_transport_trips[year_month] += 1
        elif txn_type == "Grab Food":
            monthly_food_orders[year_month] += 1

    if foreign_transactions:
        print(
            f"SGD analysis excludes {foreign_transactions} foreign-currency transactions; original amounts remain in the exports."
        )

    months = sorted(monthly_cost.keys())
    ride_costs = [monthly_cost[month].get("Grab Transport", 0) for month in months]
    food_costs = [monthly_cost[month].get("Grab Food", 0) for month in months]

    return MonthlyStats(
        months,
        ride_costs,
        food_costs,
        monthly_transport_trips,
        food_orders=monthly_food_orders,
    )


def plot_spending_chart(
    months: List[str], costs: List[float], title: str, color: str, output_path: Path
) -> None:
    """Create and save a spending chart."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.bar(months, costs, color=color)
    ax.set_ylabel("Amount Spent (SGD)")
    ax.set_title(title)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45)
    ax.yaxis.grid(True)

    # Add trend line
    z = np.polyfit(range(len(months)), costs, POLYNOMIAL_DEGREE)
    p = np.poly1d(z)
    ax.plot(months, p(range(len(months))), "r--")

    # Add bar labels
    for i, v in enumerate(costs):
        ax.text(i, v + 5, f"{v:.2f}", color=color, ha="center")

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig)


def print_period_averages(stats: MonthlyStats, months_back: int) -> None:
    """Average the last N completed calendar months, including months with no spending."""
    if months_back <= 0:
        raise ValueError("months_back must be positive")

    month = datetime.today().replace(day=1)
    selected_months = []
    for _ in range(months_back):
        month = (month - timedelta(days=1)).replace(day=1)
        selected_months.append(month.strftime("%Y-%m"))
    selected_months.reverse()

    if not stats.months or min(stats.months) > selected_months[0]:
        print(
            f"[red]Warning: Not enough completed months to calculate a {months_back}-month average."
        )
        return

    ride_costs = dict(zip(stats.months, stats.ride_costs))
    food_costs = dict(zip(stats.months, stats.food_costs))
    ride_cost = sum(ride_costs.get(m, 0) for m in selected_months) / months_back
    ride_trips = (
        sum(stats.transport_trips.get(m, 0) for m in selected_months) / months_back
    )
    food_cost = sum(food_costs.get(m, 0) for m in selected_months) / months_back
    food_orders = (
        sum(stats.food_orders.get(m, 0) for m in selected_months) / months_back
    )

    print(
        f"[yellow bold]Past {months_back}-Month Average[/yellow bold] ({', '.join(selected_months)}):"
    )
    print(f"  [bold]Grab Transport[/bold]")
    print(f"    Monthly Rides  : {ride_trips:.0f}")
    print(f"    Monthly Cost   : {ride_cost:.2f} SGD")

    print(f"  [bold]Grab Food[/bold]")
    print(f"    Monthly Orders : {food_orders:.0f}")
    print(f"    Monthly Cost   : {food_cost:.2f} SGD\n")


def plot_and_save_spending_charts(file_path: str) -> None:
    """Main function to process and visualize spending data."""
    OUT_DIR.mkdir(exist_ok=True)

    stats = process_transaction_data(file_path)

    # Print averages
    print_period_averages(stats, 6)
    print_period_averages(stats, 3)

    # Create charts
    plot_spending_chart(
        stats.months,
        stats.ride_costs,
        "Monthly Spending on Grab Transport",
        TRANSPORT_COLOR,
        OUT_DIR / "grab_transport_spending.png",
    )

    plot_spending_chart(
        stats.months,
        stats.food_costs,
        "Monthly Spending on Grab Food",
        FOOD_COLOR,
        OUT_DIR / "grab_food_spending.png",
    )


if __name__ == "__main__":
    # plot_stacked_monthly_spending(MASTER_GRAB_CSV)
    plot_and_save_spending_charts(MASTER_GRAB_CSV)
