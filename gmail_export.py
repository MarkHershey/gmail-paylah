import base64
import datetime
import json
from pathlib import Path

from googleapiclient.errors import HttpError
from tqdm import tqdm

from file_utils import atomic_text_writer
from gmail_helpers import GetMessage, ListMessagesMatchingQuery, get_gmail_service


class EmailExportError(RuntimeError):
    """One or more messages failed; transaction reports must not be regenerated."""

    def __init__(self, failures):
        self.failures = dict(failures)
        details = "\n".join(f"{msg_id}: {error}" for msg_id, error in failures.items())
        super().__init__(
            f"Failed to export {len(failures)} message(s). Existing transaction reports were preserved.\n{details}"
        )


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


def all_msg_ids_from_sender(service, sender: str, query_filter: str = ""):
    """
    Query all messages from a particular sender

    Args:
        service: Authorized Gmail API service instance.
        sender: email address of the sender
        query_filter: optional additional Gmail search criteria

    Returns:
        A list of message ids
    """
    query = f"from:{sender}"
    if query_filter:
        query += f" ({query_filter})"
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
    metadata["labelIds"] = msg.get("labelIds", [])

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
        name = header["name"].lower()
        if name in ("from", "to", "subject"):
            metadata[name] = header["value"]

    return metadata


def get_msg_body(msg: dict) -> str:
    """Extract inline plain-text and HTML bodies from a Gmail message."""
    payload = msg["payload"]
    payload_mimeType = payload["mimeType"]

    if payload_mimeType in ("text/html", "text/plain") or payload_mimeType.startswith(
        "multipart/"
    ):
        return get_multipart_payload(parts=[payload])
    else:
        raise NotImplementedError(
            f"[payload] mimeType {payload_mimeType} not implemented"
        )


def get_multipart_payload(parts: list) -> str:
    """Recursively decode inline text bodies, ignoring attachments and empty parts."""
    decoded_parts = []
    for part in parts:
        if part.get("filename"):
            continue

        mime_type = part.get("mimeType", "")
        if mime_type.startswith("multipart/"):
            _decoded_part = get_multipart_payload(part.get("parts", []))
            decoded_parts.append(_decoded_part)
        elif mime_type in ("text/html", "text/plain"):
            # Gmail can omit data for empty bodies or parts stored as attachments.
            data = part.get("body", {}).get("data")
            if data is not None:
                decoded_parts.append(decode_message_part(data))
    return "\n".join(decoded_parts)


def save_raw_message(msg: dict, save_path: Path):
    """Save a successfully fetched message, replacing any incomplete raw cache."""
    if not isinstance(msg, dict):
        raise ValueError("Cannot cache an invalid Gmail message")
    with atomic_text_writer(save_path) as f:
        json.dump(msg, f, indent=4)


def load_cached_message(path, msg_id, required_fields):
    """Return a usable cached message, or None if absent or incomplete."""
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("id") != msg_id:
        return None
    if not all(
        isinstance(data.get(key), value_type)
        for key, value_type in required_fields.items()
    ):
        return None
    return data


def _decode_message(msg):
    data = get_msg_metadata(msg)
    data["body"] = get_msg_body(msg)
    return data


def _export_message(service, msg_id, raw_path, save_path, *, use_cache, save_raw):
    msg = data = None
    if use_cache:
        msg = load_cached_message(
            raw_path, msg_id, {"payload": dict, "internalDate": str}
        )
        if msg is not None:
            try:
                data = _decode_message(msg)
            except (KeyError, TypeError, ValueError, NotImplementedError):
                # Valid JSON may still be an incomplete or damaged Gmail response.
                msg = None
        cached_export = load_cached_message(
            save_path, msg_id, {"body": str, "date": str}
        )
        if cached_export is not None:
            if msg is None and not save_raw:
                return
            if data is not None and cached_export == data:
                return

    if msg is None:
        msg = GetMessage(service, user_id="me", msg_id=msg_id)
        if save_raw:
            save_raw_message(msg=msg, save_path=raw_path)
        data = _decode_message(msg)

    with atomic_text_writer(save_path) as f:
        json.dump(data, f, indent=4)


def export_email_content(
    out_dir: Path,
    sender: str,
    prefix: str = "",
    use_cache: bool = True,
    save_raw: bool = True,
    query_filter: str = "",
):
    """
    Query all Gmail messages from a particular sender.

    Args:
        out_dir: Output directory to save the messages
        sender: email address of the sender or keyword
        prefix: prefix to add to the filename
        use_cache: if True, skip messages that have already been saved
        save_raw: if True, save the raw Message object (dict) as JSON
        query_filter: optional additional Gmail search criteria

    Raises:
        EmailExportError: One or more individual messages could not be exported.
        HttpError: A request fails after retries, or access is denied.
    """
    try:
        # Authenticate and get Gmail service
        service = get_gmail_service(
            scope_name="readonly",
            credentials_filepath="credentials.json",
            credentials_token_filepath="token.json",
            force_new_token=False,
        )
    except Exception as e:
        print(e)
        if Path("token.json").exists():
            print("Try deleting outdated token.json and try again.")
        raise

    # Query/Obtain all message ids from the sender
    msg_ids = all_msg_ids_from_sender(
        service=service, sender=sender, query_filter=query_filter
    )
    print(f"Total number of '{sender}' messages: {len(msg_ids)}")

    # Query/Obtain messages one by one
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True, parents=True)
    failures = {}
    for msg_id in tqdm(msg_ids):
        raw_path = raw_dir / f"{prefix}{msg_id}_raw_msg.json"
        save_path = out_dir / f"{prefix}{msg_id}.json"
        try:
            _export_message(
                service,
                msg_id,
                raw_path,
                save_path,
                use_cache=use_cache,
                save_raw=save_raw,
            )
        except HttpError as exc:
            if exc.resp.status != 404:
                # Stop on exhausted quota/server errors or revoked access; retrying
                # every remaining message would repeat the same failing requests.
                raise EmailExportError({**failures, msg_id: str(exc)}) from exc
            failures[msg_id] = str(exc)
        except (KeyError, TypeError, ValueError, NotImplementedError) as exc:
            failures[msg_id] = f"{type(exc).__name__}: {exc}"
        except OSError as exc:
            raise EmailExportError({**failures, msg_id: str(exc)}) from exc

    if failures:
        raise EmailExportError(failures)
