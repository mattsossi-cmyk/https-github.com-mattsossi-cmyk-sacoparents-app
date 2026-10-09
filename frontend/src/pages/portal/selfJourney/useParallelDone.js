import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Whether the parent has reached their Parallel Parenting plan summary; re-checks each time the builder closes.
export function useParallelDone(userId, builderOpen) {
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (!userId || builderOpen) return undefined;
    let cancelled = false;
    api
      .get("/parallel-parenting/me")
      .then(({ data }) => !cancelled && setDone(!!data.completed_at))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId, builderOpen]);
  return done;
}
