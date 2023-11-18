import base64
from re import compile

from bs4 import BeautifulSoup

# from sample_message_paylah import msg


def extract_info_from_msg(msg: dict) -> dict:
    if msg["payload"]["mimeType"] == "text/html":
        # Fave
        content_base64 = msg["payload"]["body"]["data"]
        content_byte = base64.urlsafe_b64decode(content_base64)
        content_html = content_byte.decode(encoding="utf-8")

        soup = BeautifulSoup(content_html, "html.parser")

        p_tags = soup.find_all("p")
        content_str_lst = []

        for tag in p_tags:
            try:
                content_str_lst.append(tag.string.strip())
            except:
                pass

        check_date = check_amount = check_id = check_merchant = False
        date = amount = merchant = receipt_id = None
        for i in content_str_lst:
            if check_id:
                receipt_id = i.strip()
                check_id = False
                break
            if check_merchant:
                merchant = i.strip()
                check_merchant = False
            if check_date:
                date = i.strip()[4:15]
                check_date = False
            if check_amount:
                amount = i.strip()[2:]
                check_amount = False
                check_date = True

            if "Where" in i:
                check_merchant = True
            elif "Transaction receipt" in i:
                check_amount = True
            elif "Receipt ID" in i:
                check_id = True
            else:
                pass

    elif msg["payload"]["mimeType"] == "multipart/mixed":
        # PayLah
        content_base64 = msg["payload"]["parts"][0]["body"]["data"]
        content_byte = base64.urlsafe_b64decode(content_base64)
        content_html = content_byte.decode(encoding="utf-8")

        soup = BeautifulSoup(content_html, "html.parser")

        tag_found = soup.find(string=compile("^ Transaction Ref:"))
        receipt_id = tag_found.string[17:].strip()

        tag_found = soup.find(string="Date & Time:")
        td_tags = tag_found.find_parent("tbody").find_all("td")

        content_str_lst = []
        for tag in td_tags:
            try:
                content_str_lst.append(tag.string.strip())
            except:
                pass

        year = msg["payload"]["headers"][1]["value"][-25:-21]

        date = content_str_lst[1][:6] + " " + year
        amount = content_str_lst[3][3:]
        merchant = content_str_lst[7]

    else:
        print("something is wrong")

    return {
        "date": date,
        "receipt_id": receipt_id,
        "amount": amount,
        "merchant": merchant,
    }


if __name__ == "__main__":
    print(extract_info_from_msg(msg))
