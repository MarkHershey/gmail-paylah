from pathlib import Path

from gmail_export import export_email_content
from parser_fave import main as fave_main
from parser_paylah import main as paylah_main


def main():
    OUTPUT_DIR = Path("output")

    ### Export PayLah Emails
    paylah_dir = OUTPUT_DIR / "paylah"
    paylah_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=paylah_dir,
        sender="paylah.alert@dbs.com",
        use_cache=True,
    )

    ### Export Fave Emails
    fave_dir = OUTPUT_DIR / "fave"
    fave_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=fave_dir,
        sender="hi@myfave.com",
        use_cache=True,
    )

    ### Parse All PayLah Emails
    paylah_main(output_dir=OUTPUT_DIR)

    ### Parse All Fave Emails
    fave_main(output_dir=OUTPUT_DIR)


if __name__ == "__main__":
    main()
