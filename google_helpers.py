import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPE_MAP = {
    "readonly": "https://www.googleapis.com/auth/gmail.readonly",
    "compose": "https://www.googleapis.com/auth/gmail.compose",
    "modify": "https://www.googleapis.com/auth/gmail.modify",
    "metadata": "https://www.googleapis.com/auth/gmail.metadata",
    "full": "https://mail.google.com/",
}

SCOPE_DESC_MAP = {
    "readonly": "Read all resources and their metadata—no write operations.",
    "compose": "Create, read, update, and delete drafts. Send messages and drafts.",
    "modify": "All read/write operations except immediate, permanent deletion of threads and messages, bypassing Trash.",
    "metadata": "Read resources metadata including labels, history records, and email message headers, but not the message body or attachments.",
    "full": "Full access to the account's mailboxes, including permanent deletion of threads and messages.",
}


def get_gmail_service(
    scope_name: str = "readonly",
    credentials_filepath: str = "credentials.json",
    credentials_token_filepath: str = "token.json",
    force_new_token: bool = False,
):
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    assert scope_name in SCOPE_MAP.keys(), f"Scope '{scope_name}' not supported"
    scopes = [SCOPE_MAP[scope_name]]
    print(f"Scope: {scope_name}")
    print(f"Description: {SCOPE_DESC_MAP[scope_name]}")
    print("-" * 80)

    credentials_filepath = Path(credentials_filepath)
    assert (
        credentials_filepath.exists()
    ), f"File '{credentials_filepath}' does not exist"

    credentials_token_filepath = Path(credentials_token_filepath)
    if credentials_token_filepath.exists() and force_new_token:
        os.remove(credentials_token_filepath)

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if credentials_token_filepath.exists():
        creds = Credentials.from_authorized_user_file(
            str(credentials_token_filepath), scopes
        )
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_filepath), scopes
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with credentials_token_filepath.open("w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


if __name__ == "__main__":
    get_gmail_service()
