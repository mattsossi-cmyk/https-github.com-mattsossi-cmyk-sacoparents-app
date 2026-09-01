"""iter128 - Regression: share-link 14-day duration was silently
downgraded to 7 by `create_share_token` because
`SHARE_TOKEN_WINDOWS` was missing 14 while the route layer and both
share dialogs advertised 14 as a valid option.

Also asserts every duration the UI offers actually round-trips
through `create_share_token` at the requested `exp`, so future
mismatches are caught immediately.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# The four durations the UI + route layer advertise as valid.
_ADVERTISED_WINDOWS = [1, 7, 14, 30]


def test_all_advertised_share_link_windows_round_trip():
    """Every window the UI offers must produce a token whose decoded
    `exp` is ~N days out (within a small clock-skew tolerance). If
    `SHARE_TOKEN_WINDOWS` is missing a value, `create_share_token`
    silently downgrades to `SHARE_TOKEN_EXPIRE_DAYS` (7) and this test
    catches the drift."""
    from auth import create_share_token, decode_share_token

    for days in _ADVERTISED_WINDOWS:
        token = create_share_token(
            doc_type="joint_agreement",
            doc_id=f"sh_{days}",
            user_id="uA",
            expire_days=days,
        )
        payload = decode_share_token(token)
        assert payload is not None, f"decode failed for {days}d"
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        actual_seconds = (exp - iat).total_seconds()
        expected_seconds = days * 24 * 60 * 60
        # 60s tolerance for clock-skew / test scheduling
        assert abs(actual_seconds - expected_seconds) < 60, (
            f"{days}d option produced a token with {actual_seconds}s lifetime; "
            f"expected ~{expected_seconds}s. Check auth.SHARE_TOKEN_WINDOWS."
        )


def test_disallowed_duration_still_downgrades_to_default():
    """Non-advertised values must fall back to the default 7 rather
    than mint a rogue lifetime the UI didn't offer."""
    from auth import create_share_token, decode_share_token, SHARE_TOKEN_EXPIRE_DAYS

    token = create_share_token(
        doc_type="joint_agreement",
        doc_id="sh_bad",
        user_id="uA",
        expire_days=99,  # not in SHARE_TOKEN_WINDOWS
    )
    payload = decode_share_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    actual_days = (exp - iat).total_seconds() / 86400
    assert abs(actual_days - SHARE_TOKEN_EXPIRE_DAYS) < 0.01, (
        f"invalid duration should downgrade to {SHARE_TOKEN_EXPIRE_DAYS}d, "
        f"got {actual_days}d"
    )


def test_share_token_windows_matches_route_choices():
    """`_SHARE_LINK_EXPIRE_CHOICES` in each joint-artefact route module
    must be a subset of `SHARE_TOKEN_WINDOWS` — anything else guarantees
    a silent downgrade."""
    from auth import SHARE_TOKEN_WINDOWS
    from joint_agreement_routes import _SHARE_LINK_EXPIRE_CHOICES as jae
    from joint_professional_report_routes import _REPORT_LINK_EXPIRE_CHOICES as jre

    assert jae.issubset(SHARE_TOKEN_WINDOWS), (
        f"Joint Agreement offers {jae - SHARE_TOKEN_WINDOWS} but "
        "SHARE_TOKEN_WINDOWS does not."
    )
    assert jre.issubset(SHARE_TOKEN_WINDOWS), (
        f"Joint Report offers {jre - SHARE_TOKEN_WINDOWS} but "
        "SHARE_TOKEN_WINDOWS does not."
    )
