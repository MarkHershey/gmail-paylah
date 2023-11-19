import base64
import datetime
import json
from pathlib import Path

from tqdm import tqdm

from gmail_helpers import GetMessage, ListMessagesMatchingQuery, get_gmail_service


def get_all_labels(service):
    """
    Query all labels and return a dictionary of label name and label id

    Args:
        service: Authorized Gmail API service instance.

    Returns:
        A dictionary with label name as key and label id as value
    """
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    label_to_id_map = dict()

    if not labels:
        print("No labels found.")
    else:
        for label in labels:
            label_to_id_map[label["name"]] = label["id"]

    return label_to_id_map


def all_msg_ids_from_sender(service, sender: str):
    """
    Query all messages from a particular sender

    Args:
        service: Authorized Gmail API service instance.
        sender: email address of the sender

    Returns:
        A list of message ids
    """
    query = f"from:{sender}"
    msg_ids = ListMessagesMatchingQuery(service, user_id="me", query=query)
    msg_ids = [i["id"] for i in msg_ids]
    return msg_ids


def decode_message_part(data):
    """Decode a base64 URL safe encoded string to a byte string, then to a UTF-8 string."""
    byte_str = base64.urlsafe_b64decode(data.encode("ASCII"))
    return byte_str.decode("utf-8")


def get_msg_metadata(msg: dict) -> dict:
    """
    Return a dictionary of metadata from a message

    Args:
        msg: a msg object returned by the Gmail API

    Returns:
        A dictionary of metadata
    """
    metadata = dict()
    metadata["id"] = msg["id"]
    metadata["threadId"] = msg["threadId"]
    metadata["labelIds"] = msg["labelIds"]

    # Unix timestamp in milliseconds
    timestamp = msg["internalDate"]
    # Convert Unix timestamp to datetime object
    datetime_obj = datetime.datetime.fromtimestamp(int(timestamp) / 1000)
    # Convert datetime object to date object
    date_obj = datetime_obj.date()
    # get datetime string
    datetime_str = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    metadata["datetime"] = datetime_str
    # get date string
    date_str = date_obj.strftime("%Y-%m-%d")
    metadata["date"] = date_str

    headers = msg["payload"]["headers"]
    for header in headers:
        if header["name"] == "From":
            metadata["from"] = header["value"]
        elif header["name"] == "To":
            metadata["to"] = header["value"]
        elif header["name"] == "Subject":
            metadata["subject"] = header["value"]

    return metadata


def get_msg_body(msg: dict) -> str:
    """
    msg is a dictionary
    Top-level keys: ['id', 'threadId', 'labelIds', 'snippet', 'payload', 'sizeEstimate', 'historyId', 'internalDate']
    """
    payload = msg["payload"]
    payload_mimeType = payload["mimeType"]

    if payload_mimeType in ("text/html", "text/plain"):
        data = payload["body"]["data"]
        decoded_body = decode_message_part(data)
        return decoded_body
    elif payload_mimeType == "multipart/mixed":
        parts = msg["payload"]["parts"]
        decoded_parts = []
        for part in parts:
            if part["mimeType"] in ("text/html", "text/plain"):
                data = part["body"]["data"]
                decoded_parts.append(decode_message_part(data))
            else:
                NotImplementedError(
                    f"[multipart] mimeType {part['mimeType']} not implemented"
                )
        return "\n".join(decoded_parts)
    else:
        NotImplementedError(f"[payload] mimeType {payload_mimeType} not implemented")


def export_email_content(
    out_dir: Path,
    sender: str,
    prefix: str = "",
    use_cache: bool = True,
):
    service = get_gmail_service(
        scope_name="readonly",
        credentials_filepath="credentials.json",
        credentials_token_filepath="token.json",
        force_new_token=False,
    )

    msg_ids = all_msg_ids_from_sender(service=service, sender=sender)
    print(f"Total number of '{sender}' messages: {len(msg_ids)}")

    for msg_id in tqdm(msg_ids):
        save_path = out_dir / f"{prefix}{msg_id}.json"
        if use_cache and save_path.exists():
            continue
        msg = GetMessage(service, user_id="me", msg_id=msg_id)
        decoded_body = get_msg_body(msg)
        data = get_msg_metadata(msg)
        data["body"] = decoded_body
        with save_path.open("w") as f:
            json.dump(data, f, indent=4)
