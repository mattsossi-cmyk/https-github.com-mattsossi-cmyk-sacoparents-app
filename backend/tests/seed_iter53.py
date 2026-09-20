"""Seed a completed case and (separately) a fresh pro case for iter 53 legal report tests."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case, new_case, CaseSpec  # noqa: E402

API = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/") + "/api"


def main():
    # A) Completed case for legal report flow
    pro, pa, pb, d, detail = completed_case(API, subject="education")
    completed = {"rid": d["id"], "pro_email": pro.email, "pa_email": pa.email, "pb_email": pb.email}

    # B) Fresh (non-completed) case for foundation-statement flow
    pro2, pa2, pb2, d2 = new_case(API, CaseSpec(subject="education"))
    fresh = {"rid": d2["id"], "pro_email": pro2.email, "pa_email": pa2.email, "pb_email": pb2.email,
             "invitations": d2["invitations"]}

    out = {"completed": completed, "fresh": fresh, "password": "testpass123"}
    with open("/tmp/iter53_seed.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
