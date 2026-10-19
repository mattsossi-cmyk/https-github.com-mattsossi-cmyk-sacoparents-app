import { useEffect, useState } from "react";

import { api } from "./api";

const TTL_MS = 60_000;
let cache = { at: 0, ok: null };

// Admin-only yes/no for the Align link dot, shared across pages for a minute.
export function useAlignLinkHealth(enabled) {
  const [ok, setOk] = useState(cache.ok);
  useEffect(() => {
    if (!enabled) return undefined;
    if (Date.now() - cache.at < TTL_MS && cache.ok !== null) {
      setOk(cache.ok);
      return undefined;
    }
    let live = true;
    api.get("/admin/safety-audit-log/link-health")
      .then((r) => {
        cache = { at: Date.now(), ok: !!r.data.ok };
        if (live) setOk(cache.ok);
      })
      .catch(() => {});
    return () => { live = false; };
  }, [enabled]);
  return enabled ? ok : null;
}
