"""Setup for iter123 UI: an agreement case with both parents submitted + a fresh parent for the Foundation editor."""
import sys, uuid
sys.path.insert(0, "/app/backend/tests")
from casekit import new_user, new_case
from test_iter123_wellness_legal_notice_live import API, _accept_privacy, _answers

pro = new_user(API, "professional", "UI Pro")
ea, eb = f"t_ui_pa_{uuid.uuid4().hex[:6]}@example.com", f"t_ui_pb_{uuid.uuid4().hex[:6]}@example.com"
d = pro.post(f"{API}/joint/agreements", json={"child_name": "Avery", "parent_a_name": "Parent A", "parent_a_email": ea, "parent_b_name": "Parent B", "parent_b_email": eb}).json()
toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
for em, role in ((ea, "a"), (eb, "b")):
    s = new_user(API, "parent", f"Parent {role.upper()}", email=em, invite=toks[role])
    s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]})
    _accept_privacy(s)
    s.post(f"{API}/joint/reports/{d['id']}/safety-screening/decline")
    assert s.put(f"{API}/joint/reports/{d['id']}/responses", json={"answers": _answers()}).status_code == 200
_pro2, fpa, _fpb, d2 = new_case(API, subject="education")
print(f"AGREEMENT_ID={d['id']}\nPA_EMAIL={ea}\nFOUNDATION_PARENT={fpa.email}\nCASE2={d2['id']}")
