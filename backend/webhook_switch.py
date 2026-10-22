"""The old inbound Align webhooks stay off unless WEBHOOKS_ENABLED is exactly "true", whatever secrets are stored.

Production carries old secret values forward on every publish and won't accept an empty value, so the secrets alone can't switch them off.
"""
import os
from typing import Optional


def webhooks_on() -> bool:
    return os.environ.get("WEBHOOKS_ENABLED") == "true"


def webhook_secret(name: str) -> Optional[str]:
    return os.environ.get(name) if webhooks_on() else None
