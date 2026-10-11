import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const LOCAL_KEY = "sac_court_requested";

// Which Court-page options the parent ticked as "Asked by my professional" (account when signed in, else this browser).
export function useCourtRequested(signedIn) {
  const [keys, setKeys] = useState([]);
  const [pro, setPro] = useState({ keys: [], name: null });
  const ref = useRef([]);
  const set = useCallback((next) => {
    ref.current = next;
    setKeys(next);
  }, []);

  const apply = useCallback((data) => {
    set(data.keys);
    setPro({ keys: data.professional_keys || [], name: data.professional_name || null });
  }, [set]);
  const reload = useCallback(async () => {
    if (!signedIn) return ref.current;
    try {
      const { data } = await api.get("/court-path/requested");
      apply(data);
      return data.keys;
    } catch {
      return ref.current;
    }
  }, [signedIn, apply]);

  useEffect(() => {
    if (!signedIn) {
      try {
        set(JSON.parse(window.localStorage.getItem(LOCAL_KEY) || "[]"));
      } catch {
        set([]);
      }
      return;
    }
    reload();
  }, [signedIn, reload, set]);

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
        apply(data);
      } catch {
        set(before);
        toast.error("Couldn't save that. Please try again.");
      }
    },
    [signedIn, set, apply]
  );

  return { keys, toggle, reload, proKeys: pro.keys, proName: pro.name };
}
