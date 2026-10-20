import { useEffect, useState } from "react";

import { accessLogHref, fillCaseCode } from "./accessLogHref";
import { api } from "./api";

const TEMPLATE = process.env.REACT_APP_ALIGN_CHECKIN_URL || "";
const ACCESS_LOG_TEMPLATE = process.env.REACT_APP_ALIGN_ACCESS_LOG_URL || "";
const ACCESS_LOG_GENERAL = process.env.REACT_APP_ALIGN_ACCESS_LOG_GENERAL_URL || "";

const caseCode = () => api.get("/family-checkin/link").then((r) => r.data?.case_id || null, () => null);
const alignLinked = () => api.get("/integrations/align-link").then((r) => Boolean(r.data?.linked), () => false);

// Runs `load` once; undefined while loading so an early tap can't open the wrong page.
function useOnce(load) {
  const [value, setValue] = useState(undefined);
  useEffect(() => {
    let live = true;
    load().then((v) => live && setValue(v));
    return () => {
      live = false;
    };
  }, [load]);
  return value;
}

// Fills the shared case code into the check-in address; not linked to a case -> the main Align site.
export function useCheckinLink(alignUrl) {
  const code = useOnce(caseCode);
  if (code === undefined) return null;
  return fillCaseCode(TEMPLATE, code) || alignUrl;
}

const loadAccessLog = async () => {
  const linked = await alignLinked();
  return { linked, code: linked ? await caseCode() : null };
};

// Align's "Who has looked at my information" page: hidden unless the parent is linked to Align.
export function useAccessLogLink() {
  const s = useOnce(loadAccessLog);
  return s ? accessLogHref({ ...s, template: ACCESS_LOG_TEMPLATE, general: ACCESS_LOG_GENERAL }) : null;
}
