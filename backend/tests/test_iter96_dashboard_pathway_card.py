"""Iter 96 — Dashboard Pathway Card behaviour contract.

The `PathwayReportCard` on the Dashboard hits `/pathway-report/preview`
and self-hides for parents with no data on file yet. This suite pins
the backend contract the card depends on so any future change to the
preview endpoint stays compatible:

    * Endpoint requires auth.
    * Response contains `data_inputs_present` with the four boolean
      keys the card checks (`safety_screen`, `dimension_companion`,
      `nd_risk`, `compliance`).
    * Response contains `primary_pathway_label`,
      `primary_pathway_summary`, `hard_locked_by`, and `is_dual_party`
      — the exact fields the card reads.
    * `is_dual_party` is `False` for the single-parent preview (the
      only shape the dashboard card uses).
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT_EMAIL = "parent1@test.com"
PARENT_PASSWORD = "TestPass123!"  # noqa: S105  test fixture


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_preview_requires_auth():
    r = requests.get(f"{API}/pathway-report/preview", timeout=10)
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_preview_returns_card_contract():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": PARENT_EMAIL, "password": PARENT_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip("parent1 login unavailable")
    tok = login.json().get("access_token") or login.json().get("token")
    r = requests.get(
        f"{API}/pathway-report/preview",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Fields the Dashboard card reads.
    for k in ("primary_pathway_label", "primary_pathway_summary",
              "hard_locked_by", "is_dual_party", "data_inputs_present"):
        assert k in body, f"missing {k}: keys={list(body.keys())}"

    # Card is intended for the single-parent preview only.
    assert body["is_dual_party"] is False

    # `hard_locked_by` is always a list so the card can safely spread it.
    assert isinstance(body["hard_locked_by"], list)

    # `data_inputs_present` has the four booleans the card's
    # `hasAnyInputs()` helper checks. Missing any of them would silently
    # break the self-hide behaviour for real users.
    inputs = body["data_inputs_present"]
    for k in ("safety_screen", "dimension_companion", "nd_risk", "compliance"):
        assert k in inputs, f"data_inputs_present missing {k}: {list(inputs.keys())}"
        assert isinstance(inputs[k], bool)
