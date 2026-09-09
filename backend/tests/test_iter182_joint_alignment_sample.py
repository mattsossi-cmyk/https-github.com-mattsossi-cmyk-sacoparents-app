"""Iteration 182 — Public Joint Alignment Sample Preview.

The sample preview is a purely-static React page (no live API, no
auth). We assert:
  * The page HTML actually reaches the browser at the public path
    `/samples/joint-alignment-preview` and is NOT gated to 404 by
    the SPA fallback that short-circuits some marketing URLs.
  * The response is text/html (i.e. React SPA payload, not a 404
    from the FastAPI ingress).

The rich UI assertions live in the Playwright smoke run that already
verified all 15 test-ids on the page in the main-agent output. This
test only guards the SERVER-SIDE contract — that the route is public
and reachable.
"""
from __future__ import annotations

import sys

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def test_sample_preview_route_is_publicly_reachable():
    r = requests.get(
        f"{BASE_URL}/samples/joint-alignment-preview",
        allow_redirects=True,
        timeout=15,
    )
    # The React SPA fallback resolves any path that isn't `/api/**`
    # to the index bundle, so we should get a 200. 404 would mean the
    # ingress or a route file has excluded this path.
    assert r.status_code == 200, (
        f"expected 200, got {r.status_code}: {r.text[:200]}"
    )
    assert "text/html" in r.headers.get("content-type", ""), (
        f"expected HTML, got {r.headers.get('content-type')!r}"
    )
    # Loose smoke on the shipped HTML — it must include the SPA root.
    assert "<div id=\"root\"" in r.text or "id=\"root\"" in r.text
