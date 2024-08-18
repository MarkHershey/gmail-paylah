import csv
import json
import os
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from rich import print


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
    pure_str: str = get_pure_string(html_str).lower()

    data_lst: List[str] = get_txt_data_lst(html_str)

    if "ride" in pure_str:
        txn_type = "Grab Transport"
    elif "food" in pure_str:
        txn_type = "Grab Food"
    else:
        txn_type = "Grab"
        # print(data_lst)
        # raise ValueError("Unknown Grab transaction type")

    money_lst = [i for i in data_lst if i.startswith("S$") or i.startswith("SGD")]
    if not money_lst:
        txn_amount = "0.00"
        print(f"[red][ERROR][/red] Could not find transaction amount.")
        print(data_lst)
        # raise ValueError("Unknown Grab transaction type")
    else:
        money = money_lst[0]
        txn_amount = money.split()[-1]
        txn_amount = f"{float(txn_amount):.2f}"

    data_dict = {
        "txn_type": txn_type,
        "txn_id": None,
        "txn_date": None,
        "txn_time": None,
        "txn_amount": txn_amount,
        "txn_from": "me",
        "txn_to": "Grab",
    }
    # print(data_dict)

    return data_dict


def main(output_dir="output"):
    output_dir = Path(output_dir)
    grab_dir = output_dir / "grab"
    grab_files = os.listdir(grab_dir)
    grab_files = [grab_dir / i for i in grab_files if i.endswith(".json")]

    all_data_dicts = []
    for grab_file in grab_files:
        with open(grab_file, "r") as f:
            email_data = json.load(f)

        _id = email_data.get("id")
        _date = email_data.get("date")
        subject = email_data.get("subject")
        body = email_data.get("body")

        is_receipt = "e-receipt" in subject.lower()

        if not is_receipt:
            continue

        if not body:
            print(f"Skipping '{grab_file}' as no body")
            continue

        data_dict = parse_grab_html(body)

        data_dict["txn_id"] = _id
        data_dict["txn_date"] = _date
        all_data_dicts.append(data_dict)

    # sort by date
    all_data_dicts.sort(key=lambda x: x["txn_date"])

    out_json = output_dir / "master_grab.json"
    with out_json.open("w") as f:
        json.dump(all_data_dicts, f, indent=4)
        print(f"Saved {len(all_data_dicts)} transactions to {out_json}")

    out_csv = output_dir / "master_grab.csv"
    with out_csv.open("w") as f:
        fieldnames = [
            "txn_type",
            "txn_id",
            "txn_date",
            "txn_time",
            "txn_amount",
            "txn_from",
            "txn_to",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for data_dict in all_data_dicts:
            writer.writerow(data_dict)
        print(f"Saved {len(all_data_dicts)} transactions to {out_csv}")


if __name__ == "__main__":
    main()
