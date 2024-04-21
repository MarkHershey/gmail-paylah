import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from rich import print

OUT_DIR = Path("output")
MASTER_PAYLAH_JSON = OUT_DIR / "master_paylah.json"
assert MASTER_PAYLAH_JSON.exists(), "Master PayLah JSON file not found"


def stats_on_paylah_transactions():
    with open(MASTER_PAYLAH_JSON) as jsonfile:
        transactions = json.load(jsonfile)

    txn_count = len(transactions)
    total_spent = sum(float(txn["txn_amount"]) for txn in transactions)
    median_spent = np.median([float(txn["txn_amount"]) for txn in transactions])
    avg_spent = total_spent / txn_count
    std = np.std([float(txn["txn_amount"]) for txn in transactions])

    large_amount_threshold = avg_spent + std

    unique_txn_to = set(txn["txn_to"] for txn in transactions)
    unique_txn_to = sorted(list(unique_txn_to))

    print(f"Total number of transactions: {txn_count}")
    print(f"Total amount spent: ${total_spent:.2f}")
    print(f"Average amount spent per transaction: ${avg_spent:.2f}")
    print(f"Median amount spent per transaction: ${median_spent:.2f}")
    print(f"Standard deviation of amount spent: {std:.2f}")

    for txn in transactions:
        if float(txn["txn_amount"]) > large_amount_threshold:
            print(
                f"[bold red]Large transaction[/bold red]: ${txn['txn_amount']} to {txn['txn_to']} on {txn['txn_date']}"
            )


def plot_monthly_spending():
    with open(MASTER_PAYLAH_JSON) as jsonfile:
        transactions = json.load(jsonfile)

    monthly_spend = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        if txn["txn_date"]:
            year_month = txn["txn_date"][:7]
            txn_type = txn["txn_type"]
            amount = float(txn["txn_amount"])
            monthly_spend[year_month][txn_type] += amount

    months = sorted(monthly_spend.keys())

    # plot monthly spending
    fig, ax = plt.subplots(figsize=(21, 9))
    width = 0.5
    x = range(len(months))
    for txn_type in monthly_spend[months[0]]:
        spends = [monthly_spend[month].get(txn_type, 0) for month in months]
        ax.bar(x, spends, width, label=txn_type)
        x = [p + width for p in x]

    ax.set_ylabel("Total Amount Spent")
    ax.set_title("Monthly Spending on PayLah")
    ax.set_xticks([p + width / 2 for p in range(len(months))])
    ax.set_xticklabels(months)
    ax.legend()

    # add horizontal grid lines
    ax.yaxis.grid(True)
    # add polynomial trend line
    z = np.polyfit(
        range(len(months)), [sum(monthly_spend[month].values()) for month in months], 10
    )
    p = np.poly1d(z)
    ax.plot(months, p(range(len(months))), "r--")
    # label each bar with the total amount spent
    for i, month in enumerate(months):
        total_spent = sum(monthly_spend[month].values())
        ax.text(i, total_spent, f"${total_spent:.2f}", ha="center", va="bottom")

    plt.xticks(rotation=45)
    plt.tight_layout()
    # save the plot as an image
    plt.savefig(OUT_DIR / "paylah_monthly_spending.png")


if __name__ == "__main__":
    plot_monthly_spending()
    stats_on_paylah_transactions()
