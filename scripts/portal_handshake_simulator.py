#!/usr/bin/env python3
"""
Portal Handshake Simulator
==========================

A preview-only CLI that reproduces every request the
sacoparentsalign.com professional portal MUST make against the
SA CoParents Report-Share API. Point it at any environment where
you know a valid `permission_id`, feed it the shared integration
secret, and it will:

    1. Verify the permission is currently active
       (GET /api/integrations/report-permissions/{permission_id})
    2. Record a `view` event
       (POST /api/integrations/report-permissions/{permission_id}/events)
    3. Optionally record `download`, `accepted`, or `declined`
       events on request.
    4. Print the full request + response for every hop so your
       portal engineers can compare byte-for-byte against their
       implementation.

Nothing here writes to production storage that a real portal call
wouldn't also write — this is deliberately the SAME code path the
production portal must hit.

Usage
-----
    python scripts/portal_handshake_simulator.py \\
        --base-url https://sacoparentsapp.online \\
        --integration-key "$INTEGRATION_SHARED_SECRET" \\
        --permission-id 6f5a41d2b8e94e10a92cc4b1d43b7a2f \\
        --events view download

Env fallbacks:
    SACOPARENTSAPP_BASE_URL      → --base-url
    INTEGRATION_SHARED_SECRET    → --integration-key

Exits 0 when every hop succeeds, 1 otherwise. Prints a
copy-pasteable curl snippet for every request so a portal engineer
can literally paste it into their terminal to reproduce.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    print("This script requires `requests`. Install with `pip install requests`.")
    sys.exit(2)


ALLOWED_EVENTS = {"view", "download", "accepted", "declined"}
DIVIDER = "─" * 72


def _headers(integration_key: str) -> Dict[str, str]:
    return {
        "X-Integration-Key": integration_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _print_kv(label: str, value: Any) -> None:
    print(f"  {label:20s} {value}")


def _print_request(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]]) -> None:
    print(DIVIDER)
    print(f"REQUEST → {method.upper()} {url}")
    for k, v in headers.items():
        if k.lower() == "x-integration-key":
            print(f"  {k}: {'●' * 8}{v[-4:] if len(v) > 4 else '●●●●'}   (redacted)")
        else:
            print(f"  {k}: {v}")
    if body is not None:
        print("  body:")
        print(textwrap.indent(json.dumps(body, indent=2), "    "))


def _print_response(r: requests.Response) -> None:
    print(f"RESPONSE ← {r.status_code} {r.reason}")
    ct = r.headers.get("content-type", "")
    if "json" in ct:
        try:
            print(textwrap.indent(json.dumps(r.json(), indent=2), "  "))
        except ValueError:
            print(textwrap.indent(r.text, "  "))
    else:
        print(textwrap.indent(r.text[:1200], "  "))
    print()


def _print_curl(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]]) -> None:
    parts = [f"curl -X {method.upper()} '{url}' \\"]
    for k, v in headers.items():
        if k.lower() == "x-integration-key":
            parts.append(f"  -H '{k}: '\"$INTEGRATION_SHARED_SECRET\" \\")
        else:
            parts.append(f"  -H '{k}: {v}' \\")
    if body is not None:
        parts.append(f"  -d '{json.dumps(body)}'")
    else:
        parts[-1] = parts[-1].rstrip(" \\")
    print("PORTAL ENGINEERS — replay locally (export INTEGRATION_SHARED_SECRET first):")
    print(textwrap.indent("\n".join(parts), "  "))
    print()


def check_permission(
    base_url: str, integration_key: str, permission_id: str,
) -> requests.Response:
    url = f"{base_url.rstrip('/')}/api/integrations/report-permissions/{permission_id}"
    headers = _headers(integration_key)
    _print_request("GET", url, headers, None)
    r = requests.get(url, headers=headers, timeout=10)
    _print_response(r)
    _print_curl("GET", url, headers, None)
    return r


def record_event(
    base_url: str, integration_key: str, permission_id: str,
    event: str, user_agent: str = "portal-handshake-simulator/1.0",
) -> requests.Response:
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"event must be one of {sorted(ALLOWED_EVENTS)}")
    url = (
        f"{base_url.rstrip('/')}/api/integrations/report-permissions/"
        f"{permission_id}/events"
    )
    body = {"event": event, "user_agent": user_agent}
    headers = _headers(integration_key)
    _print_request("POST", url, headers, body)
    r = requests.post(url, headers=headers, json=body, timeout=10)
    _print_response(r)
    _print_curl("POST", url, headers, body)
    return r


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="portal_handshake_simulator",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("SACOPARENTSAPP_BASE_URL", "http://localhost:8001"),
        help="Base URL of the SA CoParents backend (env: SACOPARENTSAPP_BASE_URL)",
    )
    p.add_argument(
        "--integration-key",
        default=os.environ.get("INTEGRATION_SHARED_SECRET", ""),
        help="Shared HMAC secret (env: INTEGRATION_SHARED_SECRET)",
    )
    p.add_argument(
        "--permission-id",
        required=True,
        help="A permission_id minted by /parent/professional-invitations create.",
    )
    p.add_argument(
        "--events",
        nargs="*",
        default=["view"],
        choices=sorted(ALLOWED_EVENTS),
        help="Which events to record after the permission check (default: view).",
    )
    p.add_argument(
        "--skip-permission-check",
        action="store_true",
        help="Skip the initial GET step (rarely useful).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.integration_key:
        print("ERROR: --integration-key is required (or set INTEGRATION_SHARED_SECRET).")
        return 2

    print(DIVIDER)
    print("PORTAL HANDSHAKE SIMULATOR")
    print(DIVIDER)
    _print_kv("Base URL",      args.base_url)
    _print_kv("Permission ID", args.permission_id)
    _print_kv("Events",        ", ".join(args.events) or "(none)")
    print()

    failures = 0

    if not args.skip_permission_check:
        r = check_permission(
            args.base_url, args.integration_key, args.permission_id,
        )
        if r.status_code != 200:
            print("✖ Permission-check failed — portal must handle non-200 gracefully.")
            failures += 1
        else:
            body = r.json()
            active = body.get("active")
            reason = body.get("reason")
            if active:
                print("✓ Permission is ACTIVE — portal may render the report.")
            else:
                print(f"⚠ Permission INACTIVE (reason={reason}) — portal must deny.")

    for ev in args.events:
        r = record_event(
            args.base_url, args.integration_key, args.permission_id, ev,
        )
        if r.status_code not in {200, 201}:
            print(f"✖ Event '{ev}' failed with {r.status_code}.")
            failures += 1
        else:
            print(f"✓ Event '{ev}' recorded.")

    print(DIVIDER)
    print(f"DONE — {failures} failure{'s' if failures != 1 else ''}.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
