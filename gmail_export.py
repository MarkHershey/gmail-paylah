import base64
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


def parse_msg(msg: dict) -> str:
    """
    msg is a dictionary
    Top-level keys: ['id', 'threadId', 'labelIds', 'snippet', 'payload', 'sizeEstimate', 'historyId', 'internalDate']
    """
    parts = msg["payload"]["parts"]
    decoded_parts = []
    for part in parts:
        if part["mimeType"] in ("text/html", "text/plain"):
            data = part["body"]["data"]
            decoded_parts.append(decode_message_part(data))
        else:
            NotImplementedError(f"mimeType {part['mimeType']} not implemented")

    return "\n".join(decoded_parts)


def export_email_content(out_dir: Path, sender: str):
    service = get_gmail_service(
        scope_name="readonly",
        credentials_filepath="credentials.json",
        credentials_token_filepath="token.json",
        force_new_token=False,
    )

    msg_ids = all_msg_ids_from_sender(service=service, sender=sender)
    print(f"Total number of '{sender}' messages: {len(msg_ids)}")

    for msg_id in tqdm(msg_ids):
        msg = GetMessage(service, user_id="me", msg_id=msg_id)
        decoded_body = parse_msg(msg)
        save_path = out_dir / f"{msg_id}.html"
        with save_path.open("w") as f:
            f.write(decoded_body)


def main():
    OUTPUT_DIR = Path("output")
    paylah_dir = OUTPUT_DIR / "paylah"
    paylah_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(out_dir=paylah_dir, sender="paylah.alert@dbs.com")


if __name__ == "__main__":
    main()
