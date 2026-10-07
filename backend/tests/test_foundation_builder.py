import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import foundation_builder_pdf  # noqa: E402
from foundation_builder_routes import CONTENT, FBFields  # noqa: E402

FRONTEND_COPY = Path("/app/frontend/src/pages/portal/foundationBuilderContent.json")


def test_copy_in_lockstep():
    assert json.loads(FRONTEND_COPY.read_text(encoding="utf-8")) == CONTENT


def test_unknown_fields_dropped_and_capped():
    f = FBFields(fields={"core_goals": "x" * 5000, "bogus": "y", "commitments": "Pause first"})
    assert set(f.fields) == {"core_goals", "commitments"} and len(f.fields["core_goals"]) == 3000


def test_pdf_renders_with_partial_fields():
    out = foundation_builder_pdf.build_foundation_builder_pdf(
        content=CONTENT,
        fields={"parent_names": "Sarah & Mark", "child_info": "Emma (8)", "core_goals": "Emma feels safe — always."},
    )
    assert out[:4] == b"%PDF" and len(out) > 2000
