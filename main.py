import argparse
from pathlib import Path

from gmail_export import export_email_content
from parser_fave import main as parse_fave
from parser_grab import GRAB_RECEIPT_QUERY, main as parse_grab
from parser_paylah import main as parse_paylah

OUTPUT_DIR = Path("output")


def paylah_main(output_dir: Path = OUTPUT_DIR):
    ### Export PayLah Emails
    paylah_dir = output_dir / "paylah"
    paylah_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=paylah_dir,
        sender="paylah.alert@dbs.com",
        use_cache=True,
    )
    ### Parse All PayLah Emails
    parse_paylah(output_dir=output_dir)


def fave_main(output_dir: Path = OUTPUT_DIR):
    ### Export Fave Emails
    fave_dir = output_dir / "fave"
    fave_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=fave_dir,
        sender="hi@myfave.com",
        use_cache=True,
    )
    ### Parse All Fave Emails
    parse_fave(output_dir=output_dir)


def grab_main(output_dir: Path = OUTPUT_DIR, *, receipts_only: bool = True):
    ### Export Grab Emails
    grab_dir = output_dir / "grab"
    grab_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=grab_dir,
        sender="no-reply@grab.com",
        use_cache=True,
        query_filter=GRAB_RECEIPT_QUERY if receipts_only else "",
    )
    ### Parse All Grab Emails
    parse_grab(output_dir=output_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export and parse Grab transactions from Gmail."
    )
    download_mode = parser.add_mutually_exclusive_group()
    download_mode.add_argument(
        "--receipts-only",
        action="store_true",
        help="Download receipt, merchant-purchase, and cancellation-fee emails only (default).",
    )
    download_mode.add_argument(
        "--all-messages",
        dest="receipts_only",
        action="store_false",
        help="Download every email from Grab, including non-transaction messages.",
    )
    parser.set_defaults(receipts_only=True)
    args = parser.parse_args(argv)
    grab_main(receipts_only=args.receipts_only)


if __name__ == "__main__":
    main()
