import { useEffect, useState } from "react";

import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const CODE_RE = /^SA-[A-Z0-9]{4,32}$/;

// The parent's shared case code (undefined while loading, null if not linked or skipped).
function useCaseCode(enabled) {
  const [code, setCode] = useState(enabled ? undefined : null);
  useEffect(() => {
    if (!enabled) return undefined;
    let live = true;
    api
      .get("/family-checkin/link")
      .then((r) => live && setCode(r.data?.case_id || null))
      .catch(() => live && setCode(null));
    return () => {
      live = false;
    };
  }, [enabled]);
  return code;
}

function fill(template, code) {
  return template.includes("{case_id}") && CODE_RE.test(code || "") ? template.replace("{case_id}", encodeURIComponent(code)) : null;
}

// Fills the shared case code into the check-in address; not linked to a case -> the main Align site.
// Returns null until the lookup finishes so an early tap can't open the wrong page.
export function useCheckinLink(alignUrl) {
  const code = useCaseCode(true);
  if (code === undefined) return null;
  return fill(TEMPLATE, code) || alignUrl;
}
