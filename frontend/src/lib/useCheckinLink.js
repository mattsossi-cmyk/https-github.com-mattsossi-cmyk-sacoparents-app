import { useEffect, useState } from "react";

import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const CODE_RE = /^SA-[A-Z0-9]{4,32}$/;

// Fills the shared case code into the check-in address; not linked to a case -> the main Align site.
// Returns null until the lookup finishes so an early tap can't open the wrong page.
export function useCheckinLink(alignUrl) {
  const [code, setCode] = useState(undefined);
  useEffect(() => {
    let live = true;
    api
      .get("/family-checkin/link")
      .then((r) => live && setCode(r.data?.case_id || null))
      .catch(() => live && setCode(null));
    return () => {
      live = false;
    };
  }, []);
  if (code === undefined) return null;
  if (!TEMPLATE.includes("{case_id}") || !CODE_RE.test(code || "")) return alignUrl;
  return TEMPLATE.replace("{case_id}", encodeURIComponent(code));
}
