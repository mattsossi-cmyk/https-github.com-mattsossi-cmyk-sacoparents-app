import { useEffect, useState } from "react";

import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const REF_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

// Fills this parent's own align_ref into the check-in address; not linked to a case -> the main Align site.
// Returns null until the lookup finishes so an early tap can't open the wrong page.
export function useCheckinLink(alignUrl) {
  const [ref, setRef] = useState(undefined);
  useEffect(() => {
    let live = true;
    api
      .get("/family-checkin/link")
      .then((r) => live && setRef(r.data?.align_ref || null))
      .catch(() => live && setRef(null));
    return () => {
      live = false;
    };
  }, []);
  if (ref === undefined) return null;
  if (!TEMPLATE.includes("{align_ref}") || !REF_RE.test(ref || "")) return alignUrl;
  return TEMPLATE.replace("{align_ref}", ref);
}
