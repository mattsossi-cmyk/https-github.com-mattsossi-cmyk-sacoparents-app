"""Tests for professional share links (POST /api/joint/reports/professional returns
copyable per-parent links) and the parent invitation link in the create response."""
import os
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _reg(role="parent", prefix="sl"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": role,
    })
    assert r.status_code == 200, r.text
    return s, email


class TestProfessionalShareLinks:
    def test_pro_create_returns_two_parent_links(self):
        pro, _ = _reg("professional", "slpro")
        pa = f"TEST_slpa_{uuid.uuid4().hex[:8]}@example.com"
        pb = f"TEST_slpb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "Link Kid",
            "parent_a_name": "Ann", "parent_a_email": pa,
            "parent_b_name": "Jordan", "parent_b_email": pb,
        })
        assert r.status_code in (200, 201), r.text
        data = r.json()
        invs = data.get("invitations")
        assert invs and len(invs) == 2, f"expected 2 invitations, got {data.keys()}"
        by_role = {i["role"]: i for i in invs}
        assert set(by_role) == {"a", "b"}
        for role, email in (("a", pa), ("b", pb)):
            inv = by_role[role]
            assert inv["invitee_email"] == email.lower()
            assert "/join/" in inv["link"], f"missing join link: {inv}"
            assert len(inv["code"]) >= 6
        # tokens/links must be unique per parent
        assert by_role["a"]["link"] != by_role["b"]["link"]

    def test_pro_links_work_for_any_subject(self):
        pro, _ = _reg("professional", "slpro2")
        for subj in ("medical", "psychological", "co_parenting"):
            r = pro.post(f"{API}/joint/reports/professional", json={
                "subject": subj, "child_name": "Multi Kid",
                "parent_a_name": "A", "parent_a_email": f"TEST_ma_{uuid.uuid4().hex[:6]}@example.com",
                "parent_b_name": "B", "parent_b_email": f"TEST_mb_{uuid.uuid4().hex[:6]}@example.com",
            })
            assert r.status_code in (200, 201), f"{subj}: {r.text}"
            assert len(r.json().get("invitations", [])) == 2, subj

    def test_parent_create_includes_invitation_link(self):
        a, _ = _reg(prefix="slparent")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "communication", "child_name": "Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_slb_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code in (200, 201), r.text
        inv = r.json()["invitation"]
        assert "/join/" in inv["link"], f"parent create response should include the share link: {inv}"
        # the link must resolve to a valid invitation (accept page uses the token)
        token = inv["link"].rsplit("/join/", 1)[1]
        assert len(token) > 10
