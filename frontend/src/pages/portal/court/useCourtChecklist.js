import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

// Live Court checklist (server builds Cards 1-4 + case/safety/BIFF; modules come from the page).
export function useCourtChecklist({ modules, courtKey, hidden, refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const statusKey = modules.map((m) => `${m.topic}:${m.status}`).join(",");
  const body = () => ({ modules: Object.fromEntries(modules.map((m) => [m.topic, m.status])) });
  const reqRef = useRef(0);

  const load = useCallback(() => {
    const id = ++reqRef.current;
    setError(false);
    // Ignore stale responses so a slow early request can't overwrite newer module statuses.
    api
      .post("/court-path/checklist", body())
      .then(({ data: d }) => id === reqRef.current && setData(d))
      .catch(() => id === reqRef.current && setError(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusKey]);

  useEffect(() => {
    if (!hidden) load();
  }, [load, courtKey, hidden, refreshKey]);

  const download = async () => {
    setDownloading(true);
    try {
      const res = await api.post("/court-path/checklist/pdf", body(), { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Court_Checklist.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Court checklist PDF is ready.");
    } catch {
      toast.error("Couldn't build the checklist right now. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return { data, error, load, download, downloading };
}
