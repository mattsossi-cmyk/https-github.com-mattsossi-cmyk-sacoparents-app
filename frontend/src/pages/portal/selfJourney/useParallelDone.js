import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Parallel Parenting plan status: "done", "in_progress" or null (not started); re-checks each time the builder closes.
export function useParallelStatus(userId, builderOpen) {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    if (!userId || builderOpen) return undefined;
    let cancelled = false;
    api
      .get("/parallel-parenting/me")
      .then(({ data }) => !cancelled && setStatus(data.completed_at ? "done" : data.updated_at ? "in_progress" : null))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId, builderOpen]);
  return status;
}
