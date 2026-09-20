"""Seed a completed case for Legal Lens frontend testing."""
import json
import os
import sys

sys.path.insert(0, "/app/backend/tests")
from casekit import completed_case  # noqa

API = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/") + "/api"

pro, pa, pb, d, detail = completed_case(API, subject="education")
seed = {
    "rid": d["id"],
    "pro_email": pro.email,
    "pa_email": pa.email,
    "pb_email": pb.email,
    "password": "testpass123",
}
print(json.dumps(seed))
with open("/tmp/iter54_seed.json", "w") as f:
    json.dump(seed, f)
