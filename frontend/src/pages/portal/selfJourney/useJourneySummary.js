import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

// One-time 5-of-5 celebration flag (saved on the account) + Journey Summary PDF download.
export function useJourneySummary(userId) {
  const [celebrated, setCelebrated] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/journey-summary/celebrated")
      .then(({ data }) => !cancelled && setCelebrated(!!data.celebrated))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const markCelebrated = () => {
    setCelebrated(true);
    api.post("/journey-summary/celebrated").catch(() => {});
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get("/journey-summary/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Journey_Summary.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Journey Summary is downloading.");
    } catch {
      toast.error("Couldn't build your Journey Summary right now. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return { celebrated, markCelebrated, downloadPdf, downloading };
}
