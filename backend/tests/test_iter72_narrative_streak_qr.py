"""Iteration 72 — Narrative Rebuild, Long-Streak Badges, Signature QR.

Verifies:
- Educational + Psychological v2 reports include per-part narrative,
  opening story, and closing story.
- 30-day and 100-day wall streak badges log correctly at the right
  streak length (and not before) and are lifetime-deduped.
- `sign_kwargs` still returns only the keys existing PDF builders
  accept (no `signed_verify_*` leaks).
- `compute_signature_id` + `verify_signature_id` round-trip and any
  tampered field breaks the check.
- Signed PDFs render successfully with the QR stamp path exercised
  (asserts bytes come out non-empty even when the QR library is
  present).
"""
import pytest

from deep_dive_narrative import build_part_narratives, build_opening_story, build_closing_story
from edu_deep_report import build_deep_dive_report as edu_report, build_deep_dive_pdf as edu_pdf
from psych_deep_report import build_deep_dive_report as psych_report, build_deep_dive_pdf as psych_pdf
from pdf_signing import (
    compute_signature_id,
    sign_kwargs,
    verify_signature_id,
)
from wall_utils import (
    BADGE_HUNDRED_DAY_STREAK,
    BADGE_MONTH_STREAK_30,
    BADGE_LABELS,
    LIFETIME_BADGES,
    maybe_log_hundred_day_streak,
    maybe_log_month_streak,
)


# -----------------------------------------------------------------------
# 1. NARRATIVE REBUILD
# -----------------------------------------------------------------------

def _all_3s():
    """Answer every one of the 25 items with a 3."""
    return {f"p{p}_q{5*(p-1)+i}": 3 for p in range(1, 6) for i in range(1, 6)}


def _mixed():
    """High for parts 1–2, low for parts 3–4, moderate for part 5."""
    out = {}
    for p in range(1, 6):
        for i in range(1, 6):
            key = f"p{p}_q{5*(p-1)+i}"
            if p in (1, 2):
                out[key] = 4
            elif p in (3, 4):
                out[key] = 0
            else:
                out[key] = 2
    return out


def test_edu_report_carries_parts_narrative():
    r = edu_report(parent_name="Sam", child_name="Alex", responses=_all_3s())
    assert len(r["parts_narrative"]) == 5
    assert r["opening_story"] and "Sam" in r["opening_story"]
    assert r["closing_story"]
    for part in r["parts_narrative"]:
        assert part["answered"] == 5
        assert part["band"] in ("high", "moderate", "low", "unrated")
        assert "narrative" in part
        assert isinstance(part["strengths"], list)
        assert isinstance(part["growth"], list)


def test_psych_report_carries_parts_narrative():
    r = psych_report(parent_name="Riley", child_name="Blake", responses=_all_3s())
    assert len(r["parts_narrative"]) == 5
    assert r["opening_story"] and "Riley" in r["opening_story"]
    assert r["closing_story"]


def test_edu_part_narrative_picks_top_strengths_and_growth():
    r = edu_report(parent_name="Sam", child_name="Alex", responses=_mixed())
    p1 = r["parts_narrative"][0]
    p3 = r["parts_narrative"][2]
    # Part 1 all 4s → 2 strengths, no growth items.
    assert len(p1["strengths"]) == 2 and all(s["value"] == 4 for s in p1["strengths"])
    assert p1["growth"] == []
    # Part 3 all 0s → 2 growth items, no strengths.
    assert p3["strengths"] == []
    assert len(p3["growth"]) == 2 and all(g["value"] == 0 for g in p3["growth"])


def test_signed_edu_pdf_still_builds():
    """Full end-to-end: report → PDF with signature (which triggers the
    QR stamp path). Just asserts bytes come out non-empty and start with
    the PDF magic header."""
    r = edu_report(parent_name="Sam", child_name="Alex", responses=_all_3s())
    b = edu_pdf(report=r, **sign_kwargs(True, "Sam Parent", "for mediation"))
    assert isinstance(b, bytes) and len(b) > 5000
    assert b.startswith(b"%PDF-")


def test_signed_psych_pdf_still_builds():
    r = psych_report(parent_name="Riley", child_name="Blake", responses=_all_3s())
    b = psych_pdf(report=r, **sign_kwargs(True, "Riley Parent"))
    assert isinstance(b, bytes) and len(b) > 5000
    assert b.startswith(b"%PDF-")


# -----------------------------------------------------------------------
# 2. LONG-STREAK BADGES
# -----------------------------------------------------------------------

def test_new_badge_labels_present():
    assert BADGE_LABELS[BADGE_MONTH_STREAK_30]
    assert BADGE_LABELS[BADGE_HUNDRED_DAY_STREAK]
    assert BADGE_MONTH_STREAK_30 in LIFETIME_BADGES
    assert BADGE_HUNDRED_DAY_STREAK in LIFETIME_BADGES


class _FakeDB:
    """Minimal Motor-compatible stub — records events instead of
    persisting them so we can assert on the log_event_once behaviour.
    The user is treated as opted-in to the public wall by default so
    the badge logger doesn't short-circuit."""

    def __init__(self, opted_in=True):
        self.events = []
        self.opted_in = opted_in

    def __getitem__(self, name):
        return _FakeCollection(self, name)


class _FakeCollection:
    def __init__(self, db, name):
        self.db = db
        self.name = name

    async def find_one(self, query=None, *_a, **_kw):
        # `get_opt_in` reads from the wall_opt_ins collection.
        if "opt" in self.name.lower():
            return {"opt_in": True} if self.db.opted_in else None
        return None

    async def insert_one(self, doc):
        self.db.events.append((self.name, doc))
        return type("R", (), {"inserted_id": "fake"})()

    async def count_documents(self, *_a, **_kw):
        return 0

    async def create_index(self, *_a, **_kw):
        return None


@pytest.mark.asyncio
async def test_month_streak_no_log_below_30():
    db = _FakeDB()
    await maybe_log_month_streak(db, "u1", 29)
    assert db.events == []


@pytest.mark.asyncio
async def test_month_streak_logs_at_30():
    db = _FakeDB()
    await maybe_log_month_streak(db, "u1", 30)
    assert any(e[1].get("badge_type") == BADGE_MONTH_STREAK_30 for e in db.events)


@pytest.mark.asyncio
async def test_hundred_day_streak_no_log_below_100():
    db = _FakeDB()
    await maybe_log_hundred_day_streak(db, "u1", 99)
    assert db.events == []


@pytest.mark.asyncio
async def test_hundred_day_streak_logs_at_100():
    db = _FakeDB()
    await maybe_log_hundred_day_streak(db, "u1", 100)
    assert any(e[1].get("badge_type") == BADGE_HUNDRED_DAY_STREAK for e in db.events)


# -----------------------------------------------------------------------
# 3. SIGNATURE QR / VERIFY
# -----------------------------------------------------------------------

def test_signature_id_roundtrips():
    sid = compute_signature_id("Sam Parent", "2026-02-06T12:34:56+00:00", "hi")
    assert len(sid) == 16
    assert verify_signature_id(sid, "Sam Parent", "2026-02-06T12:34:56+00:00", "hi")


def test_signature_id_rejects_tampered_name():
    sid = compute_signature_id("Sam Parent", "2026-02-06T12:34:56+00:00", "hi")
    assert not verify_signature_id(sid, "Someone Else", "2026-02-06T12:34:56+00:00", "hi")


def test_signature_id_rejects_tampered_note():
    sid = compute_signature_id("Sam Parent", "2026-02-06T12:34:56+00:00", "hi")
    assert not verify_signature_id(sid, "Sam Parent", "2026-02-06T12:34:56+00:00", "different note")


def test_signature_id_rejects_wrong_length():
    assert not verify_signature_id("abc", "Sam", "2026-02-06T12:34:56+00:00")


def test_sign_kwargs_shape_matches_pdf_builders():
    """sign_kwargs must ONLY return keys that existing PDF builders
    accept — otherwise the download route raises TypeError."""
    kw = sign_kwargs(True, "Sam Parent", "for mediation")
    assert set(kw.keys()) <= {"signed_by", "signed_at", "signed_note"}
    assert kw["signed_by"] == "Sam Parent"
    assert kw["signed_note"] == "for mediation"


def test_sign_kwargs_empty_when_not_signing():
    assert sign_kwargs(False, "Sam") == {}
    assert sign_kwargs(True, None) == {}
