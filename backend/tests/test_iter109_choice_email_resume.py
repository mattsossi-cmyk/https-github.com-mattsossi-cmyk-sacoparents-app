"""Iter-109 (owner-approved 2026-10-16): neutral invitation email, same four choice options for every parent, switch-later line,
updated content note, and real resume (private draft)."""
import os
import pytest
import re

from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from test_iter108_required_step import _case  # noqa: E402
import joint_helpers  # noqa: E402
from safety_screening import CHOICE_LABEL, CHOICE_SWITCH_NOTE, TRIGGER_WARNING  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"


def test_invitation_email_is_neutral_and_mentions_private_check_in():
    spec = joint_helpers.InviteSpec(report_id="r1", role="a", invitee_name="Alex", invitee_email="a@x", child_name="Zoe Child", subject_label="Education", inviter_name="Jordan Pro", code="SA-26-EDU-ABC123", via_professional=True)
    subject, html = joint_helpers._invite_email_content(spec, "tok")
    assert subject == "An invitation from SA CoParents"
    assert "Zoe Child" not in html and "Education" not in html and "Jordan Pro" in html
    assert "This invitation includes a private check-in before the assessment. Please complete it on a device only you can access." in html
    assert html.index("private check-in") > html.index("SA-26-EDU-ABC123") and html.index("private check-in") < html.index("Complete My Assessment")
    assert not re.search(r"safety|violence|abuse|screening|flagged", html, re.I)


def _case_with_genders():
    import uuid
    from casekit import new_user
    pro = new_user(API, "professional", "Gate Pro", email=f"t_{uuid.uuid4().hex[:8]}@example.com")
    d = pro.post(f"{API}/joint/reports/professional", json={"subject": "education", "child_name": "G.", "parent_a_name": "Alex", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
                                                             "parent_b_name": "Blake", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com", "parent_a_gender": "woman", "parent_b_gender": "man"}).json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    emails = {i["role"]: i["invitee_email"] for i in d["invitations"]}
    ses = {}
    for role in ("a", "b"):
        s = new_user(API, "parent", f"Parent {role.upper()}", email=emails[role], invite=toks[role])
        assert s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]}).json().get("ok")
        ses[role] = s
    return pro, ses["a"], ses["b"], d["id"]


@pytest.mark.skip(reason="Superseded 2026-10-16: the Family check-in (FV) replaces the A/B/C choice; see test_iter110_family_checkin.py")


def test_choice_screen_same_four_options_for_everyone_switch_note_and_content_note():
    pro, pa, pb, rid = _case_with_genders()  # genders on file, yet nothing is inferred
    for s in (pa, pb):
        c = s.get(f"{API}/joint/reports/{rid}/safety-screening").json()["choice"]
        assert [o["label"] for o in c["options"]] == ["Questions written for women (Version A)", "Questions written for men (Version B)", "Questions written for LGBTQ+ relationships (Version C)", "Prefer not to say (I'll help you choose)"]
        assert c["options"][3]["help"] and c["note"] == CHOICE_SWITCH_NOTE == "You can switch to a different set of questions later."
        assert c["trigger_warning"] == TRIGGER_WARNING == "Content note: these questions ask about fear, control, and physical or sexual harm in a relationship. Take a break at any time; your progress is saved so you can come back later."
    assert CHOICE_LABEL["C"] == "Questions written for LGBTQ+ relationships (Version C)"
    # Any version may be chosen; only the letter is stored.
    assert pa.put(f"{API}/joint/reports/{rid}/safety-screening/choose", json={"version": "B"}).status_code == 200
    assert pa.put(f"{API}/joint/reports/{rid}/safety-screening/choose", json={"version": "help"}).status_code == 400
    st = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]["a"]
    assert st["version"] == "B" and "orientation" not in st


def test_resume_keeps_private_draft_until_submit():
    pro, pa, pb, rid = _case()
    assert pa.put(f"{API}/joint/reports/{rid}/safety-screening/choose", json={"version": "A"}).status_code == 200
    assert pa.put(f"{API}/joint/reports/{rid}/safety-screening/draft", json={"responses": {"a1": "often", "a2": "skip"}}).json() == {"ok": True, "saved": True}
    assert pa.get(f"{API}/joint/reports/{rid}/safety-screening").json()["my_draft"] == {"a1": "often", "a2": "skip"}
    assert pb.get(f"{API}/joint/reports/{rid}/safety-screening").json()["my_draft"] is None
    body = pro.get(f"{API}/joint/reports/{rid}/safety-screening").text
    assert "often" not in body and '"my_draft":null' in body
    assert pro.put(f"{API}/joint/reports/{rid}/safety-screening/draft", json={"responses": {"x": "y"}}).status_code == 403
    assert pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {}, "safe_contact": None}).status_code == 200
    assert pa.get(f"{API}/joint/reports/{rid}/safety-screening").json()["my_draft"] is None
