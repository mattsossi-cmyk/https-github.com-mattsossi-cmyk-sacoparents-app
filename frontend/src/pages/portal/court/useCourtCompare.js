import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

// Both-parent comparison state + the parent's own "Share my results for comparison" switch.
export function useCourtCompare(active) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pointsBusy, setPointsBusy] = useState(false);
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

  const downloadPdf = async () => {
    if (data?.state !== "ready") {
      toast.message("The Comparison PDF is available once both parents are sharing.");
      return;
    }
    setPdfBusy(true);
    try {
      const res = await api.get("/court-path/compare/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Side_by_Side_Comparison.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Comparison PDF is ready.");
    } catch {
      toast.error("Couldn't build the Comparison PDF right now. Please try again.");
    } finally {
      setPdfBusy(false);
    }
  };

  const suggestPoints = async () => {
    setPointsBusy(true);
    try {
      const { data: d } = await api.post("/court-path/compare/talking-points");
      setData(d);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Couldn't suggest talking points right now. Please try again.");
    } finally {
      setPointsBusy(false);
    }
  };

  return { data, busy, load, setShared, downloadPdf, pdfBusy, suggestPoints, pointsBusy };
}
