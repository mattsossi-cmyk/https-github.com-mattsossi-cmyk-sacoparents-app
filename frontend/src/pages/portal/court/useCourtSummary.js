import { useEffect, useState } from "react";

import { api } from "../../../lib/api";

// Summary pillars (this parent's own results). Reloads whenever the Court page is shown again.
export function useCourtSummary(active) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!active) return;
    api
      .get("/court-path/summary")
      .then(({ data: d }) => setData(d))
      .catch(() => setData((d) => d || { alignment: [], difference: [], child: [] }));
  }, [active]);
  return data;
}
