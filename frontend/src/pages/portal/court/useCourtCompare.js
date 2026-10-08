import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

// Both-parent comparison state + the parent's own "Share my results for comparison" switch.
export function useCourtCompare(active) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    api
      .get("/court-path/compare")
      .then(({ data: d }) => setData(d))
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (active) load();
  }, [active, load]);

  const setShared = async (shared) => {
    setBusy(true);
    try {
      const { data: d } = await api.post("/court-path/compare/share", { shared });
      setData(d);
      if (d.state === "safety_off") toast.message("Comparison stays off to keep you safe.");
      else toast.success(shared ? "You're sharing your results for comparison." : "You've stopped sharing. Your results are private again.");
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Couldn't update sharing. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return { data, busy, load, setShared };
}
