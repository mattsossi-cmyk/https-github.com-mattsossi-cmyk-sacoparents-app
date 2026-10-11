import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const LOCAL_KEY = "sac_court_requested";

// Which Court-page options the parent ticked as "Asked by my professional" (account when signed in, else this browser).
export function useCourtRequested(signedIn) {
  const [keys, setKeys] = useState([]);
  const ref = useRef([]);
  const set = (next) => {
    ref.current = next;
    setKeys(next);
  };

  useEffect(() => {
    if (!signedIn) {
      try {
        set(JSON.parse(window.localStorage.getItem(LOCAL_KEY) || "[]"));
      } catch {
        set([]);
      }
      return;
    }
    api.get("/court-path/requested").then(({ data }) => set(data.keys)).catch(() => {});
  }, [signedIn]);

  const toggle = useCallback(
    async (k) => {
      const before = ref.current;
      const next = before.includes(k) ? before.filter((x) => x !== k) : [...before, k];
      set(next);
      if (!signedIn) {
        try {
          window.localStorage.setItem(LOCAL_KEY, JSON.stringify(next));
        } catch {
          /* private mode: keep it for this visit */
        }
        return;
      }
      try {
        const { data } = await api.put("/court-path/requested", { keys: next });
        set(data.keys);
      } catch {
        set(before);
        toast.error("Couldn't save that. Please try again.");
      }
    },
    [signedIn]
  );

  return { keys, toggle };
}
