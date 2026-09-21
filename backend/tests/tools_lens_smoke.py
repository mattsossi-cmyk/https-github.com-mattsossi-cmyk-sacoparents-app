import sys, requests, pymupdf
api = sys.argv[1]; s = requests.Session()
print("login", s.post(f"{api}/api/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"}).status_code)
cid = s.get(f"{api}/api/professional-report/cases").json()[0]["id"]
r = s.get(f"{api}/api/cases/{cid}/professional-report"); print("get", r.status_code, "providers:", [p["label"] for p in r.json()["library"]["providers"]][:1])
r = s.put(f"{api}/api/cases/{cid}/professional-report", json={"fields": {"joint_rating": 5, "parent_a_rating": 6, "parent_b_rating": 4, "joint_resources": ["Child-Centered Mediation"], "joint_provider": {"name": "X", "specialty": "Y", "contact": "Z"}}})
print("save", r.status_code, r.json()["classification"]["joint"]["label"], r.json()["report"]["joint_provider"])
print("bad status ->", s.put(f"{api}/api/cases/{cid}/professional-report", json={"fields": {}, "status": "bogus"}).status_code)
r = s.post(f"{api}/api/cases/{cid}/professional-report/ai-draft", json={"model": "openai", "fields": {"joint_rating": 5}}); print("ai-draft", r.status_code, r.json()["model"], len(r.json()["ai_drafts"]))
pdf = s.get(f"{api}/api/cases/{cid}/professional-report/pdf"); t = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
print("pdf", pdf.status_code, "appendix:", "AI-Assisted Drafting Disclosure" in t)
