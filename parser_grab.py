import csv
import json
import os
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from rich import print

from file_utils import atomic_text_writer

# Include merchant purchases and cancellation fees as well as ordinary receipts.
GRAB_RECEIPT_QUERY = (
    '{subject:"e-receipt" subject:"made a payment to" '
    'subject:"postpaid payment to" subject:"fee paid off"}'
)


def get_pure_string(html_str):
    """
    Given a HTML string, this function returns a long string containing only the text data.
    """

    # parse html content
    soup = BeautifulSoup(html_str, "html.parser")

    for data in soup(["style", "script"]):
        # Remove tags
        data.decompose()

    return "\n".join(soup.stripped_strings)


def get_txt_data_lst(html_str):
    """
    Given a HTML string, this function returns a list of strings containing the text data.
    """
    # parse html content
    soup = BeautifulSoup(html_str, "html.parser")

    for data in soup(["style", "script"]):
        # Remove tags
        data.decompose()

    lst = [i.strip() for i in soup.stripped_strings if i]
    return lst


def clean_html_styles(html_str):
    """
    Removes all style attributes and <style> tags from the given HTML.

    Args:
    html_content (str): A string containing HTML content.

    Returns:
    str: The cleaned HTML without any style attributes or <style> tags.
    """
    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html_str, "lxml")

    # Remove all style attributes
    for tag in soup.find_all(style=True):
        del tag["style"]

    # Remove all <style> tags
    for style_tag in soup.find_all("style"):
        style_tag.decompose()

    # Return the prettified HTML
    return soup.prettify()


def parse_grab_html(html_str: str) -> dict:
    data_lst: List[str] = get_txt_data_lst(html_str)
    heading = "\n".join(data_lst[:15]).lower()
    service_names = {text.casefold() for text in data_lst[:15]}
    merchant_label = None

    if data_lst and data_lst[0].startswith("You've made a payment to "):
        txn_type = "GrabPay"
        merchant_label = "Payment to"
    elif data_lst and data_lst[0].startswith("Your postpaid payment is successful"):
        txn_type = "Grab PayLater"
        merchant_label = "Ordered from"
    elif "grab tips e-receipt" in heading:
        txn_type = (
            "Grab Food Tip" if "grabfood" in service_names else "Grab Transport Tip"
        )
    elif "grab cancellation e-receipt" in heading:
        txn_type = "Grab Transport Fee"
    elif "grabmart" in service_names:
        txn_type = "Grab Mart"
    elif (
        "grabfood" in service_names
        or "enjoyed your food" in heading
        or "great meal" in heading
    ):
        txn_type = "Grab Food"
    elif "ride" in heading:
        txn_type = "Grab Transport"
    else:
        txn_type = "Grab"

    # Read the labelled total, rather than a fare, subtotal, or promotion amount.
    currencies = {
        "S$": "SGD",
        "SGD": "SGD",
        "RM": "MYR",
        "MYR": "MYR",
        "฿": "THB",
        "THB": "THB",
    }
    total_labels = {"total", "total paid", "amount paid", "you paid", "รวม"}
    if txn_type == "Grab PayLater":
        total_labels = {"payable amount"}
    money_pattern = re.compile(
        r"(S\$|SGD|RM|MYR|฿|THB)\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)"
    )
    total = None
    for i, text in enumerate(data_lst[:-1]):
        if text.strip().rstrip(":").casefold() not in total_labels:
            continue
        money = data_lst[i + 1]
        if money in currencies and i + 2 < len(data_lst):
            money += data_lst[i + 2]
        total = money_pattern.fullmatch(money.strip())
        if total:
            break
    if total is None:
        raise ValueError(
            "Receipt has no supported currency amount beside its total label"
        )
    txn_currency = currencies[total.group(1)]
    txn_amount = f"{Decimal(total.group(2).replace(',', '')):.2f}"
    txn_to = "Grab"
    if merchant_label is not None:
        if merchant_label not in data_lst or data_lst.index(merchant_label) + 1 == len(
            data_lst
        ):
            raise ValueError("Payment receipt is missing its merchant")
        txn_to = data_lst[data_lst.index(merchant_label) + 1]

    data_dict = {
        "txn_type": txn_type,
        "txn_id": None,
        "txn_date": None,
        "txn_time": None,
        "txn_amount": txn_amount,
        "txn_currency": txn_currency,
        "txn_from": "me",
        "txn_to": txn_to,
    }
    # print(data_dict)

    return data_dict


def main(output_dir="output"):
    output_dir = Path(output_dir)
    grab_dir = output_dir / "grab"
    grab_files = os.listdir(grab_dir)
    grab_files = [grab_dir / i for i in grab_files if i.endswith(".json")]

    all_data_dicts = []
    errors = []
    for grab_file in grab_files:
        try:
            with open(grab_file, "r", encoding="utf-8") as f:
                email_data = json.load(f)
        except (OSError, ValueError) as exc:
            errors.append(f"{grab_file.name}: {exc}")
            continue

        _id = email_data.get("id")
        _date = email_data.get("date")
        subject = email_data.get("subject") or ""
        body = email_data.get("body")

        is_receipt = (
            "e-receipt" in subject.lower()
            or subject.startswith(
                ("You've made a payment to ", "Your postpaid payment to ")
            )
            or re.fullmatch(r"(?:SGD|S\$|MYR|RM|THB|฿)\s*[\d,.]+ fee paid off", subject)
            is not None
        )

        if not is_receipt:
            continue

        try:
            if not body:
                raise ValueError("Receipt has no body")
            if not _id or not _date:
                raise ValueError("Receipt is missing its message ID or date")
            data_dict = parse_grab_html(body)
        except (TypeError, ValueError) as exc:
            errors.append(f"{grab_file.name}: {exc}")
            continue

        data_dict["txn_id"] = _id
        data_dict["txn_date"] = _date
        all_data_dicts.append(data_dict)

    if errors:
        raise ValueError(
            f"Failed to parse {len(errors)} file(s); existing transaction reports were preserved.\n"
            + "\n".join(errors)
        )

    # sort by date
    all_data_dicts.sort(key=lambda x: x["txn_date"])

    out_json = output_dir / "master_grab.json"
    with atomic_text_writer(out_json) as f:
        json.dump(all_data_dicts, f, indent=4)
    print(f"Saved {len(all_data_dicts)} transactions to {out_json}")

    out_csv = output_dir / "master_grab.csv"
    with atomic_text_writer(out_csv, newline="") as f:
        fieldnames = [
            "txn_type",
            "txn_id",
            "txn_date",
            "txn_time",
            "txn_amount",
            "txn_currency",
            "txn_from",
            "txn_to",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for data_dict in all_data_dicts:
            writer.writerow(data_dict)
    print(f"Saved {len(all_data_dicts)} transactions to {out_csv}")
    counts = Counter(row["txn_currency"] for row in all_data_dicts)
    print(
        "Transactions by currency: "
        + ", ".join(
            f"{currency}: {count}" for currency, count in sorted(counts.items())
        )
    )


if __name__ == "__main__":
    main()
