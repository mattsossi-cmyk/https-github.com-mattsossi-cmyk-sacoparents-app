"""Public one-page methodology handout PDF."""
import os

import requests
from pypdf import PdfReader
from io import BytesIO

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_methodology_pdf_is_one_page_handout() -> None:
    r = requests.get(f"{API}/methodology/pdf", headers={"User-Agent": "pytest"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert "sa-coparents-align-methodology.pdf" in r.headers.get("content-disposition", "")
    assert r.content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for needle in ("Align Model", "REFLECTION", "AGREEMENT", "Joint Alignment Summary", "Copyright 2026 SA CoParents"):
        assert needle in text, needle
