import { useEffect, useState } from "react";

import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const CASE_RE = /^SA-[A-Z0-9]{4,10}$/;

// Fills the parent's own case number into the check-in address; no single linked case -> the main Align site.
export function useCheckinLink(alignUrl) {
  const [caseId, setCaseId] = useState(null);
  useEffect(() => {
    let live = true;
    api
      .get("/family-checkin/link")
      .then((r) => live && setCaseId(r.data?.case_id || null))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!TEMPLATE.includes("{case_id}") || !CASE_RE.test(caseId || "")) return alignUrl;
  return TEMPLATE.replace("{case_id}", encodeURIComponent(caseId));
}
