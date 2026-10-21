"""Clear page for blocked Summary / Agreement share links opened in a browser. Scripts and the app still get JSON."""
from html import escape

import jwt
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from auth import JWT_ALGO, JWT_SECRET
from mediation_sharing import OLD_LINK

EXPIRED = "This link has expired. Please ask the parent for a new link."
INVALID = "This link isn't valid. Please check you copied all of it, or ask the parent for a new link."
SWITCHED_OFF = "The parent has switched off this link. Please ask them for a new one if you still need it."
GONE = "This document is no longer available. Please ask the parent for a new link."
TITLES = {OLD_LINK: "Made before a privacy update", EXPIRED: "This link has expired", INVALID: "This link isn't valid",
          SWITCHED_OFF: "This link was switched off", GONE: "No longer available"}
_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}

_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{title} · SA CoParents</title>
<style>
body{{margin:0;min-height:100vh;background:#F8F7FC;color:#1A1330;font-family:'Plus Jakarta Sans',system-ui,sans-serif}}
main{{max-width:32rem;margin:0 auto;padding:3rem 1rem}}
.eyebrow{{font-size:.6875rem;letter-spacing:.22em;text-transform:uppercase;font-weight:700;color:#3D1A78;margin-bottom:1rem}}
section{{background:#fff;border:1px solid #E5E0EE;border-radius:1.5rem;padding:1.5rem 1.75rem;box-shadow:0 1px 2px rgba(26,19,48,.06)}}
h1{{font-size:1.25rem;margin:0 0 .5rem}}
p.msg{{margin:0;color:#9A3A23;font-weight:600;line-height:1.5}}
p.foot{{font-size:.75rem;color:#6E6787;margin-top:1rem;line-height:1.6}}
</style></head><body><main data-testid="shared-link-blocked-page">
<div class="eyebrow">SA CoParents · Shared document</div>
<section><h1 data-testid="shared-link-blocked-title">{title}</h1>
<p class="msg" role="alert" data-testid="shared-link-blocked-message">{message}</p></section>
<p class="foot">Documents shared through SA CoParents only open while the parent keeps the link switched on.</p>
</main></body></html>"""


def invalid_reason(token: str) -> str:
    """Signature fine but past its date -> expired; anything else -> not valid."""
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"verify_exp": False, "require": ["kind"]})
        return EXPIRED
    except jwt.PyJWTError:
        return INVALID


def blocked(request: Request, status: int, message: str):
    if "text/html" in request.headers.get("accept", ""):
        page = _PAGE.format(title=escape(TITLES.get(message, "Link unavailable")), message=escape(message))
        return HTMLResponse(page, status_code=status, headers=_HEADERS)
    return JSONResponse({"detail": message}, status_code=status, headers=_HEADERS)
