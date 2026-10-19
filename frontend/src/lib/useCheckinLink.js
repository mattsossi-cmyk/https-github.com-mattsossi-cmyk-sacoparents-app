import { useEffect, useState } from "react";

import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const REF_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

// Fills this parent's own align_ref into the check-in address; not linked to a case -> the main Align site.
export function useCheckinLink(alignUrl) {
  const [ref, setRef] = useState(null);
  useEffect(() => {
    let live = true;
    api
      .get("/family-checkin/link")
      .then((r) => live && setRef(r.data?.align_ref || null))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!TEMPLATE.includes("{align_ref}") || !REF_RE.test(ref || "")) return alignUrl;
  return TEMPLATE.replace("{align_ref}", ref);
}
