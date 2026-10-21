import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Server facts behind the dashboard steps. `ready` once every source answered; `ok` if none failed.
export function useDashboardData(userId, isCourt) {
  const [data, setData] = useState({ ready: false, ok: false, agreements: [] });
  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    let ok = true;
    const get = (req) =>
      req.then((r) => r.data).catch(() => {
        ok = false;
        return null;
      });
    Promise.all([
      get(api.get("/self-assessment/me")),
      get(api.get("/mediation/prep")),
      get(api.get("/mediation/agreements")),
      isCourt ? get(api.post("/court-path/checklist")) : Promise.resolve(null),
      get(api.get("/court-path/requested")),
    ]).then(([draft, prep, agreements, checklist, requested]) => {
      if (!cancelled) setData({ ready: true, ok, draft, prep, agreements: agreements || [], checklist, requested });
    });
    return () => {
      cancelled = true;
    };
  }, [userId, isCourt]);
  return data;
}
