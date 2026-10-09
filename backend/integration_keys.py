"""Align shared-secret matching, with an optional previous key accepted during a key switchover."""
from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def match_integration_key(provided: Optional[str]) -> Optional[str]:
    """Return "new" / "old" for the key Align sent, or None if it matches neither."""
    provided = provided or ""
    current = os.environ.get("INTEGRATION_SHARED_SECRET") or ""
    previous = os.environ.get("INTEGRATION_SHARED_SECRET_PREVIOUS") or ""
    used = None
    if current and hmac.compare_digest(provided, current):
        used = "new"
    elif previous and hmac.compare_digest(provided, previous):
        used = "old"
    if previous:
        logger.info("align integration key used=%s", used or "invalid")
    return used
