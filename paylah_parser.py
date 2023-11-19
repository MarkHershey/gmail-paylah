import json
from re import compile

from bs4 import BeautifulSoup


def parse_paylah_html(html_path: str) -> dict:
    with open(html_path, "r") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")

    data_dict = {}

    ### Find the transaction ID
    tag_found = soup.find(string=compile("Transaction Ref:.*"))
    if tag_found:
        txn_id = tag_found.string.strip()
        txn_id = txn_id.split(":")[1].strip()
    else:
        txn_id = "NA"
    data_dict["type"] = "PayLah"
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
        print(f"Skipping '{html_path}' (likely not a transaction email)")
        return None

    data_dict["txn_time"] = content_str_lst[1]
    data_dict["txn_amount"] = content_str_lst[3]
    data_dict["txn_from"] = content_str_lst[5]
    data_dict["txn_to"] = content_str_lst[7]

    return data_dict


if __name__ == "__main__":
    import os

    paylah_dir = "output/paylah"
    paylah_files = os.listdir(paylah_dir)
    paylah_files = [os.path.join(paylah_dir, i) for i in paylah_files]

    all_data_dicts = []
    for paylah_file in paylah_files:
        data_dict = parse_paylah_html(paylah_file)
        if data_dict:
            all_data_dicts.append(data_dict)

    with open("master_paylah.json", "w") as f:
        json.dump(all_data_dicts, f, indent=4)
        print(f"Saved {len(all_data_dicts)} transactions to master_paylah.json")
