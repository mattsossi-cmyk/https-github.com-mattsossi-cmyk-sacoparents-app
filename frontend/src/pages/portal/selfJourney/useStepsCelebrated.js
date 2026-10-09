import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// One-time "6 of 6 finished" sparkle flag, saved on the account.
export function useStepsCelebrated(userId) {
  const [celebrated, setCelebrated] = useState(true);
  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/journey-summary/steps-celebrated")
      .then(({ data }) => !cancelled && setCelebrated(!!data.celebrated))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);
  const mark = () => {
    setCelebrated(true);
    api.post("/journey-summary/steps-celebrated").catch(() => {});
  };
  return { celebrated, mark };
}
