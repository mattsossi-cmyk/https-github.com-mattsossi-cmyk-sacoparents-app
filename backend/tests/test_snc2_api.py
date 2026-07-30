"""API integration tests for the Special Needs Co-Parenting v2 product.

Covers /api/snc2/* endpoints and regression checks that the old
/api/snc/*, /api/family-report/* endpoints have been removed.
"""
from __future__ import annotations

import time


FORBIDDEN_PHRASES = [
    "correct parent", "wrong parent", "winner",
    "right parent", "incorrect parent",
]


# -----------------------------------------------------------------------
# Regression: old products should be gone (404)
# -----------------------------------------------------------------------
class TestOldEndpointsRemoved:
    def test_old_snc_schema_404(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc/schema")
        assert r.status_code == 404

    def test_old_snc_report_status_404(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc/report/status")
        assert r.status_code == 404

    def test_old_snc_invite_mine_404(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc/invite/mine")
        assert r.status_code == 404

    def test_old_family_report_status_404(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/family-report/status")
        assert r.status_code == 404


# -----------------------------------------------------------------------
# Public schema / pathway endpoints
# -----------------------------------------------------------------------
class TestPathwaysAndSchema:
    def test_pathways_returns_4_and_scale(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc2/pathways")
        assert r.status_code == 200
        data = r.json()
        ids = [p["id"] for p in data["pathways"]]
        assert ids == ["medical", "educational", "psychological", "multiple"]
        assert isinstance(data["response_scale"], list)
        assert len(data["response_scale"]) == 6  # 1-5 + na

    def test_schema_medical_has_8_steps_with_pathway_block(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc2/schema", params={"pathways": "medical"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["steps"]) == 8
        step1 = data["steps"][0]
        assert len(step1["pathways"]) == 1
        med = step1["pathways"][0]
        assert med["id"] == "medical"
        first_prompt = med["items"][0].get("prompt", "").lower()
        assert "medical concern" in first_prompt

    def test_schema_multiple_resolves_to_three(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/snc2/schema", params={"pathways": "multiple"})
        assert r.status_code == 200
        data = r.json()
        for step in data["steps"]:
            ids = [p["id"] for p in step["pathways"]]
            assert ids == ["medical", "educational", "psychological"]


# -----------------------------------------------------------------------
# Selection / answers / completion
# -----------------------------------------------------------------------
def _seed_answer_map():
    """Same seed used in unit tests, but keyed by qid strings."""
    a = {}
    a["step1_medical_current_impact"] = 4
    a["step3_medical_recs_understand"] = 4
    for k in ("same_info", "attend_appts", "discuss_openly",
              "shared_language", "believe_understood"):
        a[f"step4_medical_{k}"] = 3
    for k in ("routines_consistent", "follow_recs", "share_updates",
              "carry_over_supplies", "handoffs_reliable"):
        a[f"step5_medical_{k}"] = 3
    return a


class TestSelectAnswerComplete:
    def test_full_lifecycle(self, auth_client, base_url):
        # Cleanup first
        auth_client.delete(f"{base_url}/api/snc2/me")

        # Reject empty selection
        r = auth_client.post(f"{base_url}/api/snc2/select", json={"pathways": []})
        assert r.status_code == 400

        # Valid select with child_name
        r = auth_client.post(f"{base_url}/api/snc2/select",
                             json={"pathways": ["medical"], "child_name": "Kiddo"})
        assert r.status_code == 200
        assert r.json().get("child_name") == "Kiddo"

        # Answer validation - accept int 4
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "step1_medical_current_impact", "value": 4})
        assert r.status_code == 200

        # Accept 'na'
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "step4_medical_same_info", "value": "na"})
        assert r.status_code == 200

        # Reject 7
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "step4_medical_same_info", "value": 7})
        assert r.status_code == 400

        # Reject 'yes'
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "step4_medical_same_info", "value": "yes"})
        assert r.status_code == 400

        # Reject unknown question id
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "bogus_key", "value": 3})
        assert r.status_code == 400

        # Bulk - all valid
        r = auth_client.post(f"{base_url}/api/snc2/answers/bulk",
                             json={"answers": _seed_answer_map()})
        assert r.status_code == 200

        # Bulk - mix in a bad key → reject entire batch
        bad_batch = dict(_seed_answer_map())
        bad_batch["totally_bogus"] = 3
        r = auth_client.post(f"{base_url}/api/snc2/answers/bulk",
                             json={"answers": bad_batch})
        assert r.status_code == 400

        # Complete
        r = auth_client.post(f"{base_url}/api/snc2/complete")
        assert r.status_code == 200
        doc = r.json()
        assert doc.get("completed") is True
        assert "scores" in doc and doc["scores"].get("pathways")

    def test_scores_endpoint(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/snc2/scores")
        assert r.status_code == 200
        data = r.json()
        assert data.get("pathways")
        pw = data["pathways"][0]
        for block in ("understanding", "coordination", "impact"):
            assert block in pw
            score = pw[block]["score"]
            assert score is None or (1 <= float(score) <= 5)
            assert isinstance(pw[block]["classification"], str)


# -----------------------------------------------------------------------
# Cached report lifecycle + guardrails
# -----------------------------------------------------------------------
class TestReportCacheAndGuardrails:
    def test_report_cache_and_stale_and_pdf(self, auth_client, base_url):
        # Assume previous test left doc with answers+completed.
        # First generate → cached:false
        r = auth_client.post(f"{base_url}/api/snc2/report/generate")
        assert r.status_code == 200, r.text
        first = r.json()
        assert first.get("cached") is False

        # Second generate → cached:true
        r = auth_client.post(f"{base_url}/api/snc2/report/generate")
        assert r.status_code == 200
        assert r.json().get("cached") is True

        # Modify an answer → status.stale should be True
        time.sleep(0.05)
        r = auth_client.post(f"{base_url}/api/snc2/answer",
                             json={"question_id": "step1_medical_current_impact", "value": 5})
        assert r.status_code == 200
        r = auth_client.get(f"{base_url}/api/snc2/report/status")
        assert r.status_code == 200
        assert r.json().get("stale") is True

        # Regenerate → cached:false
        r = auth_client.post(f"{base_url}/api/snc2/report/regenerate")
        assert r.status_code == 200
        assert r.json().get("cached") is False

        # PDF
        r = auth_client.get(f"{base_url}/api/snc2/report/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 50 * 1024

        # Guardrails on PDF bytes
        low = r.content.lower()
        for bad in FORBIDDEN_PHRASES:
            assert bad.encode() not in low, f"PDF contains forbidden phrase: {bad}"

    def test_report_payload_has_no_forbidden_phrases(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/snc2/report")
        assert r.status_code == 200
        text = str(r.json()).lower()
        for bad in FORBIDDEN_PHRASES:
            assert bad not in text
