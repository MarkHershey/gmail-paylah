from __future__ import print_function

import base64
import email
import os.path
import pickle

from apiclient import errors
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from bs_extract import extract_info_from_msg
from google_helpers import get_gmail_service

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
    except errors.HttpError as err:
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
    except errors.HttpError as err:
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
    except errors.HttpError as err:
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
    except errors.HttpError as err:
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
    except errors.HttpError as err:
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
    except errors.HttpError as err:
        print("An error occurred: {}".format(err))


###############################################################################
############# Main Function


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


def main2():
    service = get_gmail_service(
        scope_name="readonly",
        credentials_filepath="credentials.json",
        credentials_token_filepath="token.json",
        force_new_token=False,
    )
    label_to_id_map = get_all_labels(service)
    # for label_name, label_id in label_to_id_map.items():
    #     print(f"Label (id={label_id}, name={label_name}) found!")

    msg_ids_paylah = all_msg_ids_from_sender(
        service=service,
        sender="no_reply@notification.sg.moomoo.com",
    )
    print(f"Total number of PayLah messages: {len(msg_ids_paylah)}")

    for msg_id in msg_ids_paylah:
        msg = GetMessage(service, user_id="me", msg_id=msg_id)
        print(msg)
        break


def main():
    debug = True

    ### Auth
    service = get_gmail_service(
        scope_name="readonly",
        credentials_filepath="credentials.json",
        credentials_token_filepath="token.json",
        force_new_token=True,
    )

    ### Get all labels
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    labels_name_id = dict()

    if not labels:
        print("No labels found.")
    else:
        for label in labels:
            labels_name_id[label["name"]] = label["id"]

        labels_needed = ("PayLah", "Fave", "Processed")
        for label in labels_needed:
            if label in labels_name_id:
                print(f"Label (id={labels_name_id[label]}, name={label}) found!")
            else:
                print("Label ({label}) not found...")
                label_obj = MakeLabel(label)
                CreateLabel(service=service, user_id="me", label_object=label_obj)

    paylah_label_id = labels_name_id["PayLah"]
    fave_label_id = labels_name_id["Fave"]
    processed_label_id = labels_name_id["Processed"]
    # TO REMOVE:
    sutd_label_id = labels_name_id["SUTD"]

    ### Get Message List

    ## PayLah Alert -----------------------------------------------------------

    # Query all emails sent by paylah.alert@dbs.com
    query_paylah = "from: paylah.alert@dbs.com"
    list_a = ListMessagesMatchingQuery(service, user_id="me", query=query_paylah)
    # set_a = set(list(map(lambda x: x["id"], list_a)))
    set_a = set(map(lambda x: x["id"], list_a))

    # Query all emails with label 'PayLah' and 'Processed'
    list_b = ListMessagesWithLabels(
        service, user_id="me", label_ids=[paylah_label_id, processed_label_id]
    )
    set_b = set(map(lambda x: x["id"], list_b))

    # Get to be processed list of message ids
    paylah_to_be_processed = list(set_a.difference(set_b))

    if debug:
        print(f"# PayLah Receipts                : {len(set_a)}")
        print(f"# PayLah Receipts Processed      : {len(set_b)}")
        print(f"# PayLah Receipts to be Processed: {len(paylah_to_be_processed)}\n")

    for message_id in paylah_to_be_processed:
        # extract transaction information
        msg = GetMessage(service, user_id="me", msg_id=message_id)
        info = extract_info_from_msg(msg)

        # TODO: add to database
        print(info)

        if not debug:
            # add label 'PayLah', 'Processed'
            msg_labels = CreateMsgLabels(
                to_add=[paylah_label_id, processed_label_id],
                to_delete=["UNREAD", sutd_label_id],
            )
            ModifyMessage(
                service, user_id="me", msg_id=message_id, msg_labels=msg_labels
            )

    ## Fave -------------------------------------------------------------------

    # Query all emails sent by paylah.alert@dbs.com
    query_fave = "from: hi@myfave.com"
    list_c = ListMessagesMatchingQuery(service, user_id="me", query=query_fave)
    # set_a = set(list(map(lambda x: x["id"], list_a)))
    set_c = set(map(lambda x: x["id"], list_c))

    # Query all emails with label 'Fave' and 'Processed'
    list_d = ListMessagesWithLabels(
        service, user_id="me", label_ids=[fave_label_id, processed_label_id]
    )
    set_d = set(map(lambda x: x["id"], list_d))

    # Get to be processed list of message ids
    fave_to_be_processed = list(set_c.difference(set_d))

    if debug:
        print(f"# Fave Receipts                : {len(set_c)}")
        print(f"# Fave Receipts Processed      : {len(set_d)}")
        print(f"# Fave Receipts to be Processed: {len(fave_to_be_processed)}\n")

    for message_id in fave_to_be_processed:
        # extract transaction information
        msg = GetMessage(service, user_id="me", msg_id=message_id)
        info = extract_info_from_msg(msg)

        # TODO: add to database
        print(info)

        if not debug:
            # add label 'Fave', 'Processed'
            msg_labels = CreateMsgLabels(
                to_add=[fave_label_id, processed_label_id],
                to_delete=["UNREAD", sutd_label_id],
            )
            ModifyMessage(
                service, user_id="me", msg_id=message_id, msg_labels=msg_labels
            )

    # # -------------------------------
    # # testing
    # tt = ListMessagesWithLabels(service, "me", label_ids=[processed_label_id])[0]
    # xt = tt["id"]
    # msg = GetMessage(service, user_id="me", msg_id=xt)
    # print(msg["labelIds"])
    #
    # msg_labels = CreateMsgLabels(
    #     to_add=[processed_label_id, "UNREAD", "INBOX"], to_delete=[]
    # )
    # ModifyMessage(service, "me", xt, msg_labels)


if __name__ == "__main__":
    main2()
