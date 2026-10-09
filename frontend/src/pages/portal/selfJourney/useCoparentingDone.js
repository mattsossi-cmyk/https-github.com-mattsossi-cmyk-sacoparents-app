import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Whether the parent has a completed Co-Parenting Relationship Assessment; re-checks each time the modal closes.
export function useCoparentingDone(userId, modalOpen) {
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (!userId || modalOpen) return undefined;
    let cancelled = false;
    api
      .get("/coparenting/me")
      .then(({ data }) => !cancelled && setDone(!!(data.exists && data.completed)))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId, modalOpen]);
  return done;
}
