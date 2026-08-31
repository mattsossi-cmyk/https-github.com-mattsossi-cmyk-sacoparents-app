#!/usr/bin/env python3
"""Input a complete joint assessment (Parent A + Parent B) via the SA CoParents API.

Usage:
    python3 input_assessment.py                          # interactive mode (prompts for every answer)
    python3 input_assessment.py --demo educational       # instant demo data for a type
    python3 input_assessment.py --api http://localhost:8001

Assessment types: general, communication, high_conflict, ipv, medical,
                  educational, psychological, court
"""

import argparse
import getpass
import sys

import requests

TYPES = ["general", "communication", "high_conflict", "ipv", "medical", "educational", "psychological", "court"]


def ask(prompt, default=""):
    val = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return val or default


def ask_choice(question, options):
    print(f"\n{question}")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    while True:
        raw = input("  > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Please enter a number from the list.")


def ask_multi(prompt, options):
    print(f"\n{prompt} (comma-separated numbers)")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    raw = input("  > ").strip()
    picks = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(options):
            picks.append(options[int(part) - 1])
    return picks


def collect_responses(session, api, label, cfg):
    print(f"\n{'=' * 60}\n{label}'s responses\n{'=' * 60}")
    answers = {}
    for idx, t in enumerate(cfg["topics"], 1):
        answers[t["key"]] = ask_choice(f"{idx}. {t['question']}", cfg["scale"])
    concern = input(f"\n{label}'s primary concern (one or two sentences): ").strip()
    goals = ask_multi("Shared goals for the child", cfg["shared_goal_options"])
    return {"answers": answers, "primary_concern": concern, "goals": goals}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8001", help="Backend base URL (no /api suffix)")
    parser.add_argument("--demo", choices=TYPES, help="Create a case and fill it with demo data for this type")
    args = parser.parse_args()
    api = args.api.rstrip("/") + "/api"

    session = requests.Session()

    email = ask("Email")
    password = getpass.getpass("Password: ")
    r = session.post(f"{api}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"Login failed: {r.json().get('detail', r.text)}")
        sys.exit(1)
    print(f"Logged in as {r.json()['email']}")
    token = session.cookies.get("access_token")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    if args.demo:
        type_key = args.demo
    else:
        type_key = ask_choice("Choose an assessment type:", TYPES)

    if args.demo:
        case = session.post(f"{api}/cases", json={"type": type_key, "child_name": "Alex",
                                                  "parent_a_name": "Parent A", "parent_b_name": "Parent B"}).json()
        session.post(f"{api}/cases/{case['id']}/demo")
        print(f"\nDemo '{type_key}' assessment created: {case['id']}")
    else:
        cfg = session.get(f"{api}/assessment-types/{type_key}").json()
        child = ask("Child's first name (optional)")
        pa = ask("Parent A name or label", "Parent A")
        pb = ask("Parent B name or label", "Parent B")
        case = session.post(f"{api}/cases", json={"type": type_key, "child_name": child,
                                                  "parent_a_name": pa, "parent_b_name": pb}).json()
        for parent, label in (("a", pa), ("b", pb)):
            payload = collect_responses(session, api, label, cfg)
            r = session.put(f"{api}/cases/{case['id']}/responses/{parent}", json=payload)
            if r.status_code != 200:
                print(f"Failed to save {label}'s responses: {r.json().get('detail', r.text)}")
                sys.exit(1)
        print(f"\nAssessment complete: {case['id']}")

    report = session.get(f"{api}/cases/{case['id']}/report").json()
    s = report["snapshot"]
    print(f"\nReport: {report['report_title']} — {report['subtitle']}")
    print(f"Snapshot: {s['aligned']} aligned | {s['different']} different perspectives | {s['info']} need more info (of {s['total']} topics)")
    print(f"View at: /report/{case['id']}")


if __name__ == "__main__":
    main()
