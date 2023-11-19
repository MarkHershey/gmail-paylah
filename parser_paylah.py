import csv
import json
import os
from pathlib import Path
from re import compile

from bs4 import BeautifulSoup


def parse_paylah_html(html_str: str) -> dict:
    # make soup
    soup = BeautifulSoup(html_str, "html.parser")

    data_dict = {}

    ### Find the transaction ID
    tag_found = soup.find(string=compile("Transaction Ref:.*"))
    if tag_found:
        txn_id = tag_found.string.strip()
        txn_id = txn_id.split(":")[1].strip()
    else:
        txn_id = "NA"
    data_dict["txn_type"] = "PayLah"
    data_dict["txn_id"] = txn_id

    ### Find the main data table
    tag_found = soup.find(string="Date & Time:")
    td_tags = tag_found.find_parent("tbody").find_all("td") if tag_found else []

    ### Put all the content strings into a list
    content_str_lst = []
    for tag in td_tags:
        try:
            content_str_lst.append(tag.string.strip())
        except:
            pass

    if len(content_str_lst) != 8:
        # print(f"Expected 8 td tags, got {len(content_str_lst)}")
        # print(content_str_lst)
        return None

    data_dict["txn_time"] = content_str_lst[1]
    data_dict["txn_amount"] = content_str_lst[3]
    data_dict["txn_from"] = content_str_lst[5]
    data_dict["txn_to"] = content_str_lst[7]

    # strip away 'SGD' from txn_amount
    data_dict["txn_amount"] = data_dict["txn_amount"][3:]
    # strip away date from txn_time
    data_dict["txn_time"] = data_dict["txn_time"][6:12].strip()
    # simplify txn_from
    if "0920" in data_dict["txn_from"]:
        data_dict["txn_from"] = "me"
    return data_dict


def main(output_dir="output"):
    output_dir = Path(output_dir)
    paylah_dir = output_dir / "paylah"
    paylah_files = os.listdir(paylah_dir)
    paylah_files = [paylah_dir / i for i in paylah_files]

    all_data_dicts = []
    for paylah_file in paylah_files:
        with open(paylah_file, "r") as f:
            email_data = json.load(f)

        paylah_html = email_data.get("body")
        if email_data["subject"] != "Transaction Alerts":
            print(f"Skipping '{paylah_file}' (likely not a transaction email)")
            continue

        data_dict = parse_paylah_html(paylah_html)
        if not data_dict:
            print(f"Skipping '{paylah_file}' (likely not a transaction email)")
            continue

        date_str = email_data["date"]
        data_dict["txn_date"] = date_str
        all_data_dicts.append(data_dict)

    # sort by date
    all_data_dicts.sort(key=lambda x: x["txn_date"])

    out_json = output_dir / "master_paylah.json"
    with out_json.open("w") as f:
        json.dump(all_data_dicts, f, indent=4)
        print(f"Saved {len(all_data_dicts)} transactions to master_paylah.json")

    out_csv = output_dir / "master_paylah.csv"
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
        writer.writerows(all_data_dicts)
        print(f"Saved {len(all_data_dicts)} transactions to master_paylah.csv")


if __name__ == "__main__":
    main()
