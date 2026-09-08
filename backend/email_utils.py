"""Email delivery + outbound-content safety checks (extracted from server.py)."""
import asyncio
import ipaddress
import logging
import os
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ["EMERGENT_EMAIL_KEY"]
EMAIL_FROM_NAME = os.environ["EMAIL_FROM_NAME"]
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _check_no_form_fields(tags) -> None:
    if tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")


def _check_no_credential_asks(subject: str, html: str) -> None:
    body = f"{subject}\n{html}".lower()
    for phrase in _CRED_ASK:
        if phrase in body:
            raise ValueError(f"Email asks the recipient for credentials: {phrase!r} (G2)")


def _check_link_url(url: str) -> None:
    low = url.strip().lower()
    if low.startswith(("mailto:", "tel:", "cid:", "#")):
        return
    if not low.startswith("https://"):
        raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
    host = urlparse(low).hostname or ""
    if not _host_ok(host) or urlparse(low).username is not None:
        raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")


def _check_anchor_matches_target(href: str, text: str) -> None:
    real = urlparse(href.strip().lower()).hostname or ""
    if not real:
        return
    for m in _HOSTISH.finditer(text):
        if not _same_site(m.group(1).lower(), real):
            raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    _check_no_form_fields(scan.tags)
    _check_no_credential_asks(subject, html)
    for url in scan.urls:
        _check_link_url(url)
    for href, text in scan.anchors:
        _check_anchor_matches_target(href, text)


FIXTURE_EMAIL_RE = re.compile(r"@(example\.com|x\.com|example\.org)$", re.I)


def _email_payload(to: str, subject: str, html: str, reply_to: str | None) -> dict:
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    contact = reply_to or EMAIL_REPLY_TO
    if contact:
        payload["contact_email"] = contact
    return payload


async def _post_email(payload: dict) -> str | None:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def _send_failure(status: int | None) -> HTTPException:
    if status == 429:
        return HTTPException(status_code=503, detail="Our email service is busy right now. Please try again in a few minutes.")
    return HTTPException(status_code=502, detail="Failed to send email")


async def _post_with_retry(payload: dict, attempts: int = 3) -> str | None:
    last_status: int | None = None
    for attempt in range(attempts):
        try:
            return await _post_email(payload)
        except httpx.HTTPStatusError as e:
            last_status = e.response.status_code
            logger.error(f"Email send failed: {last_status} {e.response.text}")
            if last_status != 429:
                break
            await asyncio.sleep(2 * (attempt + 1))
        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send email")
    raise _send_failure(last_status)


async def send_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> str | None:
    _assert_safe_email(subject, html)
    if FIXTURE_EMAIL_RE.search(to):
        logger.info(f"Skipping email to fixture address {to}")
        return None
    return await _post_with_retry(_email_payload(to, subject, html, reply_to))
