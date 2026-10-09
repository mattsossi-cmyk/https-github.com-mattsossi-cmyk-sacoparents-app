import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";

// "Sent to" history for Child Needs reports (signed-in parents only).
export function useProviderShares(enabled) {
  const [shares, setShares] = useState([]);
  const refresh = useCallback(() => {
    api
      .get("/child-needs/shares")
      .then(({ data }) => setShares(data))
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);
  return { shares, refresh };
}
