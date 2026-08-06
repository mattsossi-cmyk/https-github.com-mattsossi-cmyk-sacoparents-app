"""Reviewer Panel — public transparency endpoint listing which independent
professionals have reviewed the Safety Screen content.

Data lives in a JSON file (`reviewer_panel.json`) rather than the database
because it needs to be human-editable + version-controlled: the operator
adds a reviewer entry ONLY once that reviewer has signed off in writing.
Editable schema per entry:

    {
      "name":       "Full Name, Credentials",   # required
      "role":       "DV advocate | forensic psychologist | family-law attorney | other",
      "org":        "Optional organisation",
      "review_date":"YYYY-MM-DD",              # required
      "review_scope": "Which parts of the screen were reviewed",
      "attestation": "Short public quote or note from the reviewer"
    }

Also exposes a `/packet` endpoint that returns a single PDF reviewer
packet (current questions + scoring rules + methodology + review
checklist) — one file to hand to each candidate reviewer.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/reviewer-panel", tags=["reviewer-panel"])

DATA_PATH = os.path.join(os.path.dirname(__file__), "reviewer_panel.json")


def _load() -> Dict[str, Any]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"review_scope": "", "review_scope_version": "", "reviewers": []}
    reviewers = list(data.get("reviewers") or [])
    reviewers.sort(key=lambda r: r.get("review_date") or "", reverse=True)
    data["reviewers"] = reviewers
    return data


@router.get("")
async def get_reviewer_panel():
    data = _load()
    return {
        "review_scope":         data.get("review_scope", ""),
        "review_scope_version": data.get("review_scope_version", ""),
        "last_updated":         data.get("last_updated", ""),
        "reviewers":            data.get("reviewers", []),
        "count":                len(data.get("reviewers") or []),
        "status":               "reviewed" if data.get("reviewers") else "pending",
    }


@router.get("/packet")
async def get_reviewer_packet():
    """Generate a single PDF containing everything a candidate reviewer
    needs to evaluate: the current screen questions, scoring rules, a
    sample of the generated output, and a review checklist keyed to the
    MASIC-S coverage gaps.
    """
    try:
        from reviewer_packet_pdf import build_reviewer_packet_pdf
    except ImportError as e:
        raise HTTPException(500, f"Reviewer packet generator unavailable: {e}") from e

    pdf_bytes = build_reviewer_packet_pdf(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                'attachment; filename="sa-coparents-safety-screen-reviewer-packet.pdf"',
        },
    )
