import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Per-step "Step done" record on the account. steps: undefined = loading, null = never set, else { key: iso | "seeded" }.
export function useDashboardCelebrations(userId) {
  const [steps, setSteps] = useState(undefined);
  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/journey-summary/dashboard-celebrated")
      .then(({ data }) => !cancelled && setSteps(data.steps))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);
  const record = useCallback((keys, seeded) => {
    const stamp = seeded ? "seeded" : new Date().toISOString();
    setSteps((prev) => {
      const next = { ...(prev || {}) };
      keys.forEach((k) => {
        if (!next[k]) next[k] = stamp;
      });
      return next;
    });
    api.post("/journey-summary/dashboard-celebrated", { steps: keys, seeded }).catch(() => {});
  }, []);
  return { steps, record };
}
