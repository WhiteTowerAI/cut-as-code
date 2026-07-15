"""Open the animated content-card theme gallery in the default browser."""

import argparse
import webbrowser
from pathlib import Path


def gallery_path():
    path = Path(__file__).resolve().parents[1] / "examples/gallery-animated.html"
    if not path.is_file():
        raise FileNotFoundError(f"animated gallery not found: {path}")
    return path


def open_gallery(launch=True):
    uri = gallery_path().as_uri()
    if launch:
        webbrowser.open(uri)
    return uri


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-open", action="store_true", help="print the URI without opening it")
    args = parser.parse_args(argv)
    print(open_gallery(launch=not args.no_open))


if __name__ == "__main__":
    main()
