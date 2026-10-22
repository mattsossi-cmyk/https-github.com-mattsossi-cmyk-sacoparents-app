"""The old inbound Align webhooks stay off unless WEBHOOKS_ENABLED is exactly "true", whatever secrets are stored.

Production carries old secret values forward on every publish and won't accept an empty value, so a secret set to "off"
also counts as off.
"""
import os
from typing import Optional


def webhooks_on() -> bool:
    return os.environ.get("WEBHOOKS_ENABLED") == "true"


def webhook_secret(name: str) -> Optional[str]:
    value = os.environ.get(name) if webhooks_on() else None
    return None if (value or "").strip().lower() == "off" else value
