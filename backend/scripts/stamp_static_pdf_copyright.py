"""Stamp the SA CoParents copyright line onto every page of the static PDFs in frontend/public/downloads.

Idempotent: pages that already carry the line are left alone. Run: python scripts/stamp_static_pdf_copyright.py
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdf_base import stamp_copyright_on_pdf  # noqa: E402

DOWNLOADS = "/app/frontend/public/downloads"

if __name__ == "__main__":
    for f in sorted(glob.glob(os.path.join(DOWNLOADS, "*.pdf"))):
        with open(f, "rb") as fh:
            before = fh.read()
        after = stamp_copyright_on_pdf(before)
        if after is not before:
            with open(f, "wb") as fh:
                fh.write(after)
        print(f"{'stamped' if after is not before else 'already'}  {os.path.basename(f)}")
