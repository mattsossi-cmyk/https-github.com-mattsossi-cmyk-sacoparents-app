"""
Generate anonymised sample PDFs for the public `/samples` library.

Each renderer is called with hard-coded fictitious data (Sam & Riley
Parent, kids Jordan & Alex) so mediators can preview the exact
output format the tool produces before committing.

Run: `python /app/backend/generate_samples.py`
Files land in /app/frontend/public/downloads/.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")

from foundation_statement_pdf import build_foundation_statement_pdf
from case_status_pdf import build_case_status_pdf
from activities_costs_pdf import build_cost_ledger_pdf


OUT_DIR = "/app/frontend/public/downloads"


# ------------------------------------------------------------------
# Fictitious anonymised fixtures — Sam & Riley Parent, kids Jordan
# & Alex. All content deliberately generic, mediator-safe.
# ------------------------------------------------------------------

def _foundation_reflection() -> dict:
    return {
        "child_lens": (
            "Through Jordan's eyes I see a kid who wants both of us at "
            "his soccer games — he does not care who bought the boots. "
            "He watches how we talk to each other more than he listens "
            "to what we actually say. When Riley and I are cordial at "
            "handovers, Jordan settles within ten minutes. When we are "
            "tense, he stays quiet for the rest of the evening. I want "
            "him to remember his childhood as loved and steady, not as a "
            "series of loyalty tests."
        ),
        "own_part": (
            "My own part is that I let small annoyances build up rather "
            "than raising them the same week. By the time I bring "
            "something up it has become an accusation instead of a "
            "request. I also default to text messages when a five-minute "
            "phone call would be quicker and warmer. I am working on "
            "waiting until I am calm before I send, and picking up the "
            "phone for anything longer than one sentence."
        ),
        "best_outcome": (
            "A predictable week-on / week-off schedule that both of us "
            "trust. Clear rules on who handles which appointments so "
            "neither of us is guessing. A shared calendar for the kids' "
            "activities. Space for either of us to swap a weekend "
            "without it becoming a negotiation. Above all, a working "
            "relationship where Jordan and Alex can talk to either of "
            "us about the other without worrying."
        ),
        "coparent_feedback": (
            "Through Riley's eyes I imagine they see me as still holding "
            "on to how things ended. They probably wish I would let go "
            "of the 60/40 argument from last year and focus on what "
            "works from here. They may feel I am quicker to reply to my "
            "own family than to their messages. I would want them to "
            "know I am doing this work because I want us to co-parent "
            "well, not because I have anything to prove."
        ),
    }


def _case_status_fixture() -> dict:
    return {
        "case_id": "SA-482731",
        "assessment_type": "co-parenting",
        "status": "in_progress",
        "origin": "in_app_professional",
        "align_case_reference": "MED-2026-0148",
        "created_at": datetime(2026, 2, 14, 9, 30, tzinfo=timezone.utc),
        "case_expires_at": datetime(2026, 4, 15, 9, 30, tzinfo=timezone.utc),
        "professional": {
            "name": "Adele van Wyk (Accredited Family Mediator)",
            "email": "adele@example-mediation.co.za",
        },
        "parents": [
            {
                "name": "Sam Parent",
                "email": "sam@example.com",
                "accepted_at": datetime(2026, 2, 15, 8, 20, tzinfo=timezone.utc),
                "assessment_completed_at": datetime(2026, 2, 17, 19, 45, tzinfo=timezone.utc),
            },
            {
                "name": "Riley Parent",
                "email": "riley@example.com",
                "accepted_at": datetime(2026, 2, 15, 10, 5, tzinfo=timezone.utc),
                "assessment_completed_at": None,
            },
        ],
    }


def _cost_split_payload() -> dict:
    """Compare-payload shape expected by build_cost_ledger_pdf."""
    return {
        "self": {
            "total_cents": 348_50 * 100 // 100,  # 34_850
            "entries": [
                {"activity": "Soccer club fees — Jordan",   "category": "sport",       "amount_cents": 12_00_00, "occurred_on": "2026-01-15", "note": "Term 1 dues incl. kit."},
                {"activity": "Piano lessons — Alex",         "category": "music",       "amount_cents":  8_50_00, "occurred_on": "2026-01-22", "note": None},
                {"activity": "School stationery",            "category": "education",   "amount_cents":  4_20_00, "occurred_on": "2026-02-02", "note": "Both kids."},
                {"activity": "Dental cleaning — Jordan",     "category": "medical",     "amount_cents":  9_80_00, "occurred_on": "2026-02-11", "note": None},
            ],
        },
        "coparent": {
            "total_cents": 279_00 * 100 // 100,  # 27_900
            "entries": [
                {"activity": "Winter swimming — Alex",       "category": "sport",       "amount_cents":  7_20_00, "occurred_on": "2026-01-10"},
                {"activity": "Art supplies",                 "category": "hobby",       "amount_cents":  3_10_00, "occurred_on": "2026-01-28"},
                {"activity": "Extra maths tutor — Jordan",   "category": "education",   "amount_cents": 11_50_00, "occurred_on": "2026-02-05"},
                {"activity": "Optometrist visit — Alex",     "category": "medical",     "amount_cents":  6_10_00, "occurred_on": "2026-02-14"},
            ],
        },
        "combined_total_cents": 62_75_00,
        "per_category_pair": [
            {"key": "sport",     "label": "Sport",     "self_cents": 12_00_00, "coparent_cents":  7_20_00},
            {"key": "music",     "label": "Music",     "self_cents":  8_50_00, "coparent_cents":       0},
            {"key": "hobby",     "label": "Hobby",     "self_cents":       0, "coparent_cents":  3_10_00},
            {"key": "education", "label": "Education", "self_cents":  4_20_00, "coparent_cents": 11_50_00},
            {"key": "medical",   "label": "Medical",   "self_cents":  9_80_00, "coparent_cents":  6_10_00},
        ],
    }


CATEGORIES = [
    {"key": "sport",     "label": "Sport"},
    {"key": "music",     "label": "Music"},
    {"key": "hobby",     "label": "Hobby"},
    {"key": "education", "label": "Education"},
    {"key": "medical",   "label": "Medical"},
]


# ------------------------------------------------------------------
# Sample generators — each returns (filename, bytes).
# ------------------------------------------------------------------

def sample_foundation_statement() -> tuple[str, bytes]:
    pdf = build_foundation_statement_pdf(
        author_name="Sam Parent",
        reflection=_foundation_reflection(),
        generated_at=datetime(2026, 2, 20, 21, 15, tzinfo=timezone.utc),
    )
    return "sacoparents-foundation-statement-sample.pdf", pdf


def sample_case_status_report() -> tuple[str, bytes]:
    pdf = build_case_status_pdf(
        _case_status_fixture(),
        watermark_firm_name="Adele van Wyk Family Mediation",
    )
    return "sacoparents-case-status-report-sample.pdf", pdf


def sample_cost_ledger() -> tuple[str, bytes]:
    pdf = build_cost_ledger_pdf(
        compare_payload=_cost_split_payload(),
        self_name="Sam Parent",
        coparent_name="Riley Parent",
        mode="income",
        self_income=42_000,
        coparent_income=58_000,
        custom_pct=None,
        categories=CATEGORIES,
    )
    return "sacoparents-cost-splitter-sample.pdf", pdf


# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------

def generate_all() -> list[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    generated = []
    for gen in (
        sample_foundation_statement,
        sample_case_status_report,
        sample_cost_ledger,
    ):
        filename, data = gen()
        path = os.path.join(OUT_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
        generated.append(path)
        print(f"WROTE {path} ({len(data):,} bytes)")
    return generated


if __name__ == "__main__":
    generate_all()
