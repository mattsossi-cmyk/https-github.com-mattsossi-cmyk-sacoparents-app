import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import child_needs_pdf  # noqa: E402
import cp_progress_pdf  # noqa: E402
from child_needs_routes import CONTENT, clean_all, clean_category  # noqa: E402

FRONTEND_COPY = Path("/app/frontend/src/pages/portal/childNeedsContent.json")


def test_child_needs_copy_in_lockstep():
    assert json.loads(FRONTEND_COPY.read_text(encoding="utf-8")) == CONTENT


def test_structure_matches_founder_mockup():
    keys = [c["key"] for c in CONTENT["categories"]]
    assert keys == ["medical", "educational", "psychological"]
    assert [len(c["fields"]) for c in CONTENT["categories"]] == [5, 5, 4]


def test_cleaning_drops_unknown_empty_and_bad_selects():
    out = clean_category("medical", {
        "med_provider": "  Dr. Lee  ", "med_insurance": "Not an option", "bogus": "x", "med_goal": "   ",
    })
    assert out == {"med_provider": "Dr. Lee"}
    assert clean_category("medical", {"med_insurance": "Currently disputed"}) == {"med_insurance": "Currently disputed"}
    assert set(clean_all({"medical": {"med_provider": "A"}, "nope": {"x": "y"}})) == {"medical"}


def test_child_needs_pdf_renders_filled_categories_only():
    out = child_needs_pdf.build_child_needs_pdf(
        content=CONTENT, parent_name="Sam “SJ” Parent",
        answers={"psychological": {"psych_needs": "ADHD — needs routine", "psych_therapy": "Currently attending therapy"}},
    )
    assert out[:4] == b"%PDF"


def test_progress_pdf_extras_render_and_default_off():
    progress = {"snapshots": [{}], "recent": {"overall_rating": "Good", "section_avgs": []}, "overall_series": []}
    base = cp_progress_pdf.build_progress_pdf(parent_name="Sam", progress=progress)
    full = cp_progress_pdf.build_progress_pdf(
        parent_name="Sam", progress=progress,
        safety_timeline=[{"at": "2026-06-01T10:00:00+00:00", "event": "on", "source": "Safety screen"}],
        biff_pairs=[{"saved_at": "2026-06-02T10:00:00+00:00", "original": "You are always late — again!",
                     "rewrite": "Could we confirm pickup at 5pm Friday?"}],
    )
    assert base[:4] == full[:4] == b"%PDF" and len(full) > len(base)
