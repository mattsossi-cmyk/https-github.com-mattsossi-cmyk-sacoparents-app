"""Draft policy pages (/privacy, /confidentiality, /sharing-consent): content matches spec, bracketed placeholders absent, noindex, version constant, unlinked."""
import json
import os
import re

SRC = "/app/frontend/src"
P = json.load(open(f"{SRC}/content/policies.json", encoding="utf-8"))


def _text(key):
    out = []
    for s in P[key]["sections"]:
        out.append(s["heading"])
        out += s.get("paragraphs", []) + s.get("bullets", []) + s.get("numbered", [])
    return "\n".join(out)


def test_version_constant_and_draft():
    assert P["version"] == "1.0" and P["status"] == "draft"
    page = open(f"{SRC}/pages/PolicyPage.jsx", encoding="utf-8").read()
    assert "export const POLICY_VERSION = POLICIES.version" in page and "Version {POLICY_VERSION} ({POLICY_STATUS})" in page


def test_privacy_text():
    t = _text("privacy")
    for s in ["SA CoParents provides two connected tools: a parent app (sacoparentsapp.online) and a professional portal (sacoparentsalign.com).",
              "Contact: mattsossi@bsossi.com, 210-224-1667.",
              "Safety screening (which version you took, A, B, or C, your answers, and a tier; we never ask for or store your sexual orientation).",
              "We don't sell your information.", "Service providers: email delivery (Resend).", "We limit access by role and keep access logs.",
              "Raw screening answers are deleted 90 days after the case closes or the account is deleted, whichever comes first. Court submissions are kept for 6 months from the date they are submitted.",
              "Deleting your account does not remove a record already submitted to a court.", "If this notice changes, we'll show it again and ask you to confirm."]:
        assert s in t
    low = t.lower()
    assert "encrypt" not in low and "perplexity" not in low and "analytics" not in low and "advertis" not in low and "technical data" not in low
    assert "drafts" not in t.split("How long we keep it")[1].split("Your choices")[0].lower()


def test_confidentiality_text():
    t = _text("confidentiality")
    assert "They never show your raw answers, your narrative, or your locations, and the version appears only as a neutral label." in t
    assert "which version you took" not in t
    assert "San Antonio, Family Violence Prevention Services 24-hour line: 210-733-8810." in t and "1-800-799-7233 (text START to 88788)" in t and "Call 911." in t
    assert "mandatory" not in t.lower() and "mandated" not in t.lower()


def test_sharing_consent_text():
    t = _text("sharing-consent")
    assert P["sharing-consent"]["sections"][1]["numbered"] == ["You select a report and a recipient.", "You see what the recipient will receive before it's sent.", "You can stop sharing going forward at any time."]
    assert "A frozen court submission can't be changed afterward." in t and "Records already submitted to a court stay with the court." in t
    assert "copies" not in t.lower() and "decline" not in t.lower()


def test_no_bracketed_placeholders_rendered():
    raw = open(f"{SRC}/content/policies.json", encoding="utf-8").read()
    assert "[" not in raw.replace('": [', "").replace("[\n", "").replace("]", "") or not re.search(r"\[[A-Za-z][^\]]*\]", raw)


def test_noindex_and_routes():
    page = open(f"{SRC}/pages/PolicyPage.jsx", encoding="utf-8").read()
    assert 'meta.name = "robots"' in page and 'meta.content = "noindex, nofollow"' in page and "font-jakarta" in page and "#3D1A78" in page
    app = open(f"{SRC}/App.js", encoding="utf-8").read()
    for slug in ("privacy", "confidentiality", "sharing-consent"):
        assert f'<Route path="/{slug}" element={{<PolicyPage slug="{slug}" />}} />' in app
    assert '<Route path="/privacy-policy" element={<Privacy />} />' in app


def test_pages_not_linked_anywhere():
    hits = []
    for root, _d, files in os.walk(SRC):
        for f in files:
            if not f.endswith((".js", ".jsx")) or f in ("App.js", "PolicyPage.jsx"):
                continue
            src = open(os.path.join(root, f), encoding="utf-8").read()
            for slug in ("/privacy", "/confidentiality", "/sharing-consent"):
                if re.search(rf'(to|href)=["\']{re.escape(slug)}["\']', src):
                    hits.append((f, slug))
    assert hits == []
    from privacy_notice import NOTICE
    assert NOTICE["footer_links"] == []


def test_retention_constants_exist_without_deletion_job():
    import retention
    assert retention.RAW_SCREENING_RETENTION_DAYS == 90 and retention.COURT_SUBMISSION_RETENTION_MONTHS == 6
    assert "delete" not in open("/app/backend/retention.py", encoding="utf-8").read().lower().replace("deletion is built", "").replace("account deletion", "")
    crons = open("/app/.emergent/crons.yml", encoding="utf-8").read().lower()
    assert "retention" not in crons and "purge" not in crons
