import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

MASTER_GRAB_CSV = "output/master_grab.csv"
OUT_DIR = Path("output")


def plot_monthly_spending(file_path):
    # Open the CSV file and read data into a list of dictionaries
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        transactions = list(reader)

    # Process data
    monthly_spend = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        if txn["txn_date"]:  # check if date exists
            year_month = txn["txn_date"][:7]  # Extract Year-Month
            txn_type = txn["txn_type"]
            amount = float(txn["txn_amount"])
            monthly_spend[year_month][txn_type] += amount

    # Prepare data for plotting
    months = sorted(monthly_spend.keys())
    transport_spends = [
        monthly_spend[month].get("Grab Transport", 0) for month in months
    ]
    food_spends = [monthly_spend[month].get("Grab Food", 0) for month in months]

    # Plotting
    fig, ax = plt.subplots()
    width = 0.35  # bar width
    x = range(len(months))  # month indices
    ax.bar(x, transport_spends, width, label="Grab Transport")
    ax.bar([p + width for p in x], food_spends, width, label="Grab Food")

    ax.set_ylabel("Total Amount Spent")
    ax.set_title("Monthly Spending on Grab Transport vs Grab Food")
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(months)
    ax.legend()

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_stacked_monthly_spending(file_path):
    # Open the CSV file and read data into a list of dictionaries
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        transactions = list(reader)

    # Process data
    monthly_spend = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        if txn["txn_date"]:  # Check if date exists
            year_month = txn["txn_date"][:7]  # Extract Year-Month
            txn_type = txn["txn_type"]
            amount = float(txn["txn_amount"])
            monthly_spend[year_month][txn_type] += amount

    # Prepare data for plotting
    months = sorted(monthly_spend.keys())
    transport_spends = [
        monthly_spend[month].get("Grab Transport", 0) for month in months
    ]
    food_spends = [monthly_spend[month].get("Grab Food", 0) for month in months]

    # Plotting
    fig, ax = plt.subplots()
    ax.bar(months, transport_spends, label="Grab Transport")
    ax.bar(months, food_spends, bottom=transport_spends, label="Grab Food")

    ax.set_ylabel("Total Amount Spent")
    ax.set_title("Monthly Spending on Grab Transport vs Grab Food")
    ax.legend()

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_and_save_spending_charts(file_path):
    OUT_DIR.mkdir(exist_ok=True)  # Create the directory if it does not exist

    # Open the CSV file and read data into a list of dictionaries
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        transactions = list(reader)

    # Process data
    monthly_spend = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        if txn["txn_date"]:  # Check if date exists
            year_month = txn["txn_date"][:7]  # Extract Year-Month
            txn_type = txn["txn_type"]
            amount = float(txn["txn_amount"])
            monthly_spend[year_month][txn_type] += amount

    # Prepare data for plotting
    months = sorted(monthly_spend.keys())
    transport_spends = [
        monthly_spend[month].get("Grab Transport", 0) for month in months
    ]
    food_spends = [monthly_spend[month].get("Grab Food", 0) for month in months]

    # Plotting for Grab Transport
    # make it 16:9 aspect ratio
    fig, ax = plt.subplots(figsize=(21, 9))
    transport_color = "#1D263B"
    ax.bar(months, transport_spends, color=transport_color)
    ax.set_ylabel("Amount Spent (SGD)")
    ax.set_title("Monthly Spending on Grab Transport")
    ax.set_xticklabels(months, rotation=45)
    # add horizontal grid lines
    ax.yaxis.grid(True)
    # add polynomial trend line
    z = np.polyfit(range(len(months)), transport_spends, 10)
    p = np.poly1d(z)
    ax.plot(months, p(range(len(months))), "r--")
    # label each bar with the amount
    for i, v in enumerate(transport_spends):
        ax.text(i, v + 5, f"{v:.2f}", color=transport_color, ha="center")
    plt.tight_layout()
    plt.savefig(
        OUT_DIR / "grab_transport_spending.png"
    )  # Save the figure as an image file
    plt.close(fig)  # Close the figure to free up memory

    # Plotting for Grab Food
    fig, ax = plt.subplots(figsize=(21, 9))
    food_color = "#4CB963"
    ax.bar(months, food_spends, color=food_color)
    ax.set_ylabel("Amount Spent (SGD)")
    ax.set_title("Monthly Spending on Grab Food")
    ax.set_xticklabels(months, rotation=45)
    # add horizontal grid lines
    ax.yaxis.grid(True)
    # add polynomial trend line
    z = np.polyfit(range(len(months)), food_spends, 10)
    p = np.poly1d(z)
    ax.plot(months, p(range(len(months))), "r--")
    # label each bar with the amount
    for i, v in enumerate(food_spends):
        ax.text(i, v + 5, f"{v:.2f}", color=food_color, ha="center")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "grab_food_spending.png")  # Save the figure as an image file
    plt.close(fig)  # Close the figure to free up memory


if __name__ == "__main__":
    plot_stacked_monthly_spending(MASTER_GRAB_CSV)
    # plot_and_save_spending_charts(MASTER_GRAB_CSV)
