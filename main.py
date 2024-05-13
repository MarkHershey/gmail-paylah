from pathlib import Path

from gmail_export import export_email_content
from parser_fave import main as parse_fave
from parser_grab import main as parse_grab
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


def grab_main(output_dir: Path = OUTPUT_DIR):
    ### Export Grab Emails
    grab_dir = output_dir / "grab"
    grab_dir.mkdir(exist_ok=True, parents=True)
    export_email_content(
        out_dir=grab_dir,
        sender="no-reply@grab.com",
        use_cache=True,
    )
    ### Parse All Grab Emails
    parse_grab(output_dir=output_dir)


if __name__ == "__main__":
    # fave_main()
    # paylah_main()
    grab_main()
