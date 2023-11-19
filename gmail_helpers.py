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


############# Label Functions


def CreateLabel(service, user_id, label_object):
    """Creates a new label within user's mailbox, also prints Label ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      label_object: label to be added.

    Returns:
      Created Label.
    """
    try:
        label = (
            service.users().labels().create(userId=user_id, body=label_object).execute()
        )
        print(f"Label (id={label['id']}, name={label['name']}) has been creaated")
        return label
    except HttpError as err:
        print("An error occurred: {}".format(err))


def MakeLabel(label_name, mlv="show", llv="labelShow"):
    """Create Label object.

    Args:
      label_name: The name of the Label.
      mlv: Message list visibility, show/hide.
      llv: Label list visibility, labelShow/labelHide.

    Returns:
      Created Label.
    """
    label = {
        "name": label_name,
        "messageListVisibility": mlv,
        "labelListVisibility": llv,
    }
    return label


############# Update Labels Functions


def ModifyMessage(service, user_id, msg_id, msg_labels):
    """Modify the Labels on the given Message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The id of the message required.
      msg_labels: The change in labels.

    Returns:
      Modified message, containing updated labelIds, id and threadId.
    """

    try:
        message = (
            service.users()
            .messages()
            .modify(userId=user_id, id=msg_id, body=msg_labels)
            .execute()
        )

        label_ids = message["labelIds"]

        if True:
            print("Message ID: %s - With Label IDs %s" % (msg_id, label_ids))
        return message
    except HttpError as err:
        print("An error occurred: {}".format(err))


def CreateMsgLabels(to_add=[], to_delete=[]):
    """Create object to update labels.

    Returns:
      A label update object.
    """
    return {"removeLabelIds": to_delete, "addLabelIds": to_add}


############# Query Functions


def ListMessagesMatchingQuery(service, user_id, query=""):
    """List all Messages of the user's mailbox matching the query.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      query: String used to filter messages returned.
      Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
      List of Messages that match the criteria of the query. Note that the
      returned list contains Message IDs, you must use get with the
      appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = []
        if "messages" in response:
            messages.extend(response["messages"])

        while "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = (
                service.users()
                .messages()
                .list(userId=user_id, q=query, pageToken=page_token)
                .execute()
            )
            messages.extend(response["messages"])

        return messages
    except HttpError as err:
        print("An error occurred: {}".format(err))


def ListMessagesWithLabels(service, user_id, label_ids=[]):
    """List all Messages of the user's mailbox with label_ids applied.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      label_ids: Only return Messages with these labelIds applied.

    Returns:
      List of Messages that have all required Labels applied. Note that the
      returned list contains Message IDs, you must use get with the
      appropriate id to get the details of a Message.
    """
    try:
        response = (
            service.users()
            .messages()
            .list(userId=user_id, labelIds=label_ids)
            .execute()
        )
        messages = []
        if "messages" in response:
            messages.extend(response["messages"])

        while "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = (
                service.users()
                .messages()
                .list(userId=user_id, labelIds=label_ids, pageToken=page_token)
                .execute()
            )
            messages.extend(response["messages"])

        return messages
    except HttpError as err:
        print("An error occurred: {}".format(err))


############# Messages Functions


def GetMessage(service, user_id, msg_id):
    """Get a Message with given ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The ID of the Message required.

    Returns:
      A Message.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()
        return message
    except HttpError as err:
        print("An error occurred: {}".format(err))


def GetMimeMessage(service, user_id, msg_id):
    """Get a Message and use it to create a MIME Message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The ID of the Message required.

    Returns:
      A MIME Message, consisting of data from Message.
    """
    try:
        message = (
            service.users()
            .messages()
            .get(userId=user_id, id=msg_id, format="raw")
            .execute()
        )

        msg_byte = base64.urlsafe_b64decode(message["raw"].encode("ASCII"))
        msg_str = msg_byte.decode(encoding="utf-8")

        return msg_str
    except HttpError as err:
        print("An error occurred: {}".format(err))


if __name__ == "__main__":
    get_gmail_service()
