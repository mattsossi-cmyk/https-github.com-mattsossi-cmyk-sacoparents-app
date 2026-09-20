"""Complete parent B by logging in with existing account."""
import json, os, sys, requests
sys.path.insert(0, os.path.dirname(__file__))
from casekit import fill

API = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/") + "/api"

data = json.load(open("/tmp/iter53_seed.json"))
FRID = data["fresh"]["rid"]
PB_EMAIL = data["fresh"]["pb_email"]

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": PB_EMAIL, "password": "testpass123"})
print("login:", r.status_code)
assert r.status_code == 200
fill(API, s, FRID, "beta")
print("PB filled")
