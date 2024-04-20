import json
import os
from pathlib import Path

from rich import print

from gmail_export import get_msg_body


def fix_grab(output_dir: Path):
    ### Fix Grab Emails
    grab_dir = output_dir / "grab"
    raw_dir = grab_dir / "raw"

    raw_files_lst = os.listdir(raw_dir)
    raw_files_lst = [raw_dir / i for i in raw_files_lst if i.endswith("_raw_msg.json")]
    n_raw_files = len(raw_files_lst)
    print(f"Found {n_raw_files} raw files")

    data_files_lst = os.listdir(grab_dir)
    data_files_lst = [grab_dir / i for i in data_files_lst if i.endswith(".json")]
    n_data_files = len(data_files_lst)
    print(f"Found {n_data_files} data files\n")

    all_data = []

    for data_file_path in data_files_lst:
        with data_file_path.open("r") as f:
            data = json.load(f)

        all_data.append(data)

    all_data.sort(key=lambda x: x["date"])

    to_be_fixed = []

    for data in all_data:
        body = data.get("body")
        _id = data.get("id")
        _date = data.get("date")
        subject = data.get("subject", "")

        is_receipt = "e-receipt" in subject.lower()
        has_body = body is not None

        # if is_receipt:
        #     print(f"{_date}: {has_body} {subject} {_id}")

        if is_receipt and not has_body:
            to_be_fixed.append(data)

    print(f"Found {len(to_be_fixed)} emails to be fixed")

    del all_data

    for data in to_be_fixed:
        _id = data.get("id")
        _date = data.get("date")
        subject = data.get("subject", "")

        print(f"Fixing {_date} {_id} {subject}")

        raw_file_path = raw_dir / f"{_id}_raw_msg.json"
        with raw_file_path.open("r") as f:
            raw_data = json.load(f)

        body = get_msg_body(raw_data)

        if body:
            data["body"] = body
            with (grab_dir / f"{_id}.json").open("w") as f:
                json.dump(data, f, indent=4)
            print(f"Fixed.")
        else:
            print(f"Failed.")


if __name__ == "__main__":
    OUTPUT_DIR = Path("output")
    fix_grab(output_dir=OUTPUT_DIR)
