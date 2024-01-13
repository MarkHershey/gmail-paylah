import csv
import json
import os
from pathlib import Path

from bs4 import BeautifulSoup


def test(output_dir="output"):
    output_dir = Path(output_dir)
    grab_dir = output_dir / "grab"
    grab_files = os.listdir(grab_dir)
    grab_files = [grab_dir / i for i in grab_files]

    count = 0
    all_data = []
    for grab_file in grab_files:
        with open(grab_file, "r") as f:
            email_data = json.load(f)

        grab_html = email_data.get("body")
        subject = email_data.get("subject")
        _date = email_data.get("date")

        has_content = grab_html is not None

        if not "Receipt" in subject:
            continue
        count += 1

        all_data.append([_date, subject, has_content])
        # NOTE: it seems like emails since 2020 have no content, body is unsuccesfully decoded

    all_data.sort(key=lambda x: x[0])
    for i in all_data:
        print(i)


if __name__ == "__main__":
    test()
