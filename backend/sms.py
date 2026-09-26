"""Twilio SMS — one-way urgent-safety alerts to judges. Fails soft; never includes message content beyond the cause number."""
import asyncio
import logging
import os
import re

logger = logging.getLogger("sms")
E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def sms_configured() -> bool:
    return all(os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"))


def normalize_mobile(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits and not digits.startswith("+"):
        digits = "+1" + digits if len(digits) == 10 else "+" + digits
    return digits if E164.match(digits or "") else None


async def send_sms(to: str, body: str) -> str | None:
    """Returns the Twilio message SID, or None when unconfigured / failed."""
    if not sms_configured():
        return None
    from twilio.rest import Client

    def _send():
        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        return client.messages.create(to=to, from_=os.environ["TWILIO_FROM_NUMBER"], body=body[:320]).sid
    try:
        return await asyncio.to_thread(_send)
    except Exception as exc:
        logger.warning("sms to %s failed: %s", to[-4:], exc)
        return None
