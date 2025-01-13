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
    """Process CSV data and return monthly statistics."""
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        transactions = list(reader)

    monthly_cost = defaultdict(lambda: defaultdict(float))
    monthly_transport_trips = defaultdict(int)
    monthly_food_orders = defaultdict(int)

    for txn in transactions:
        if not txn["txn_date"]:
            continue

        year_month = txn["txn_date"][:7]
        txn_type = txn["txn_type"]
        amount = float(txn["txn_amount"])
        monthly_cost[year_month][txn_type] += amount

        if txn_type == "Grab Transport":
            monthly_transport_trips[year_month] += 1
        elif txn_type == "Grab Food":
            monthly_food_orders[year_month] += 1

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
    """Print spending averages for a given period, excluding the current month."""
    today = datetime.today()
    current_year_month = today.strftime("%Y-%m")
    current_day = today.day
    total_days_current_month = (
        today.replace(day=28) + timedelta(days=4)
    ).day  # Approximation

    # Exclude the current month from the averages
    completed_months = [m for m in stats.months if m < current_year_month]
    selected_months = completed_months[-months_back:]

    if len(selected_months) < months_back:
        print(
            f"[red]Warning: Not enough completed months to calculate a {months_back}-month average."
        )
        return

    ride_cost = sum(stats.ride_costs[-months_back:]) / months_back
    ride_trips = sum(stats.transport_trips[m] for m in selected_months) / months_back
    food_cost = sum(stats.food_costs[-months_back:]) / months_back
    food_orders = sum(stats.food_orders[m] for m in selected_months) / months_back

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
