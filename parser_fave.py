import csv
import json
import os
from pathlib import Path

from bs4 import BeautifulSoup


def parse_fave_html(html_str: str) -> dict:
    # make soup
    soup = BeautifulSoup(html_str, "html.parser")

    p_tags = soup.find_all("p")
    content_str_lst = []

    for tag in p_tags:
        try:
            content_str_lst.append(tag.string.strip())
        except:
            pass

    # pprint(len(content_str_lst))

    check_time = check_amount = check_id = check_merchant = False
    txn_time = txn_amount = txn_to = txn_id = None
    for i in content_str_lst:
        if check_id:
            txn_id = i.strip()
            check_id = False
        if check_merchant:
            txn_to = i.strip()
            check_merchant = False
        if "AM" in i or "PM" in i:
            txn_time = i.strip()
            txn_time = txn_time.split(",")[1].strip()
            txn_time = txn_time[:-2]
        if check_amount:
            txn_amount = i.strip()[2:]
            txn_amount = f"{float(txn_amount):.2f}"
            check_amount = False
            break

        if "Where" in i:
            check_merchant = True
        elif "Total" in i:
            check_amount = True
        elif "Receipt ID" in i:
            check_id = True
        else:
            pass

    data_dict = {
        "txn_type": "Fave",
        "txn_id": txn_id,
        "txn_date": None,
        "txn_time": txn_time,
        "txn_amount": txn_amount,
        "txn_from": "me",
        "txn_to": txn_to,
    }

    return data_dict


def main(output_dir="output"):
    output_dir = Path(output_dir)
    fave_dir = output_dir / "fave"
    fave_files = os.listdir(fave_dir)
    fave_files = [fave_dir / i for i in fave_files]

    all_data_dicts = []
    for fave_file in fave_files:
        with open(fave_file, "r") as f:
            email_data = json.load(f)

        fave_html = email_data.get("body")
        subject = email_data.get("subject")
        if not subject.startswith("Your FavePay Receipt"):
            continue

        data_dict = parse_fave_html(fave_html)
        if not data_dict:
            print(f"Skipping '{fave_file}' (likely not a transaction email)")
            continue

        date_str = email_data["date"]
        data_dict["txn_date"] = date_str
        all_data_dicts.append(data_dict)

    # sort by date
    all_data_dicts.sort(key=lambda x: x["txn_date"])

    out_json = output_dir / "master_fave.json"
    with out_json.open("w") as f:
        json.dump(all_data_dicts, f, indent=4)
        print(f"Saved {len(all_data_dicts)} transactions to {out_json}")

    out_csv = output_dir / "master_fave.csv"
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
        print(f"Saved {len(all_data_dicts)} transactions to {out_csv}")


if __name__ == "__main__":
    main()
