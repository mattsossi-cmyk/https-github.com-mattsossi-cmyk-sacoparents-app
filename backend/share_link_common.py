"""Shared helpers for public share-link + OG-preview endpoints.

Both `joint_agreement_routes` and `joint_professional_report_routes`
expose the same shape of URL flow (mint → shared JSON / shared PDF →
bot-aware OG preview HTML). This module centralises the pieces that
are truly identical between them so the two routes stay in sync when
we tune the crawler list, the OG image path, or the fallback title.

Nothing here reaches into the DB — resource loading stays in each
route module so the domain payload shape is not smeared across files.
"""
from __future__ import annotations

import html as _html
from typing import Iterable

from fastapi import Request


_BOT_UA_SIGNALS: tuple[str, ...] = (
    "slackbot", "twitterbot", "facebookexternalhit", "facebot",
    "linkedinbot", "whatsapp", "discordbot", "telegrambot",
    "bingbot", "googlebot", "duckduckbot", "pinterest",
    "redditbot", "applebot", "skypeuripreview", "vkshare",
    "outbrain", "quora link preview", "showyoubot",
    "developers.google.com/+/web/snippet",
    "cfnetwork", "imessage",  # iMessage previews
    "embedly", "iframely", "opengraph",
)


def is_link_preview_bot(user_agent: str) -> bool:
    """Cheap substring match — the crawlers we care about all self-declare."""
    ua = (user_agent or "").lower()
    return any(sig in ua for sig in _BOT_UA_SIGNALS)


def absolute_origin(request: Request) -> str:
    """Derive the public origin for absolute OG URLs, trusting the
    reverse-proxy headers the ingress sets."""
    proto = (
        request.headers.get("x-forwarded-proto")
        or request.url.scheme
        or "https"
    ).split(",")[0].strip()
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.hostname
        or "sacoparentsapp.online"
    ).split(",")[0].strip()
    return f"{proto}://{host}"


def html_escape(s: str) -> str:
    return _html.escape(str(s or ""), quote=True)


def render_preview_html(
    *,
    title: str,
    description: str,
    canonical_url: str,
    og_image_url: str,
    og_image_alt: str = "SA CoParents",
) -> str:
    """Minimal OG/Twitter-tagged HTML for social preview crawlers.

    Real users won't see this — the routes issue a 302 to the SPA for
    non-bot user agents. Even so, we set a meta-refresh + a body link
    as belt-and-braces so a curl / naive fetcher still gets to the
    canonical page.
    """
    title_e = html_escape(title)
    desc_e = html_escape(description)
    url_e = html_escape(canonical_url)
    img_e = html_escape(og_image_url)
    alt_e = html_escape(og_image_alt)
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>{title_e}</title>
    <meta name="description" content="{desc_e}" />

    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="SA CoParents" />
    <meta property="og:url" content="{url_e}" />
    <meta property="og:title" content="{title_e}" />
    <meta property="og:description" content="{desc_e}" />
    <meta property="og:image" content="{img_e}" />
    <meta property="og:image:secure_url" content="{img_e}" />
    <meta property="og:image:type" content="image/png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="{alt_e}" />

    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{title_e}" />
    <meta name="twitter:description" content="{desc_e}" />
    <meta name="twitter:image" content="{img_e}" />
    <meta name="twitter:image:alt" content="{alt_e}" />

    <meta http-equiv="refresh" content="0; url={url_e}" />
    <link rel="canonical" href="{url_e}" />
</head>
<body>
    <p>{title_e}</p>
    <p><a href="{url_e}">Open the shared page</a></p>
</body>
</html>"""


def clean_note(raw: object, *, max_len: int = 500) -> str | None:
    """Trim + length-cap an optional user-authored landing note. Rejects
    non-string input silently. Returns None for empty strings so JSON
    serialisation stays tidy."""
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    return trimmed[:max_len]


__all__: Iterable[str] = (
    "is_link_preview_bot",
    "absolute_origin",
    "html_escape",
    "render_preview_html",
    "clean_note",
)
