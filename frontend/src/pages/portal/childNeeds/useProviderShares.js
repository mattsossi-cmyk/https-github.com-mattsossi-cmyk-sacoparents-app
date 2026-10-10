import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";

// "Sent to" history list (Child Needs reports by default; pass another path for other share logs).
export function useProviderShares(enabled, path = "/child-needs/shares") {
  const [shares, setShares] = useState([]);
  const refresh = useCallback(() => {
    api
      .get(path)
      .then(({ data }) => setShares(data))
      .catch(() => {});
  }, [path]);
  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);
  return { shares, refresh };
}
