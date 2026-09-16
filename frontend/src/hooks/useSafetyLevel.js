/**
 * useSafetyLevel — iter199.
 *
 * Fetches the caller's most recent Safety Assessment result once,
 * caches it in-memory per session, and returns a small derived
 * summary. Consumers use `.status` for a copy switch:
 *
 *   "cleared"    → level >= 3 (no concerns / low concerns)
 *   "concerned"  → level 1 or 2 (some or significant concerns)
 *   "unknown"    → never taken / logged out / endpoint 5xx
 *
 * Never throws. Any error resolves to `{status: "unknown", level: null}`
 * so a copy-switch consumer defaults gracefully to the neutral
 * variant. Cache is module-scoped so a Landing → route → back-to-
 * Landing doesn't refetch (the assessment can't have changed
 * without a refresh).
 */
import { useEffect, useState } from "react";
import { api } from "../lib/api";

let _cached = null;
let _inflight = null;

function _fetchOnce() {
  if (_cached) return Promise.resolve(_cached);
  if (_inflight) return _inflight;
  _inflight = api
    .get("/safety-assessment/me")
    .then((r) => {
      const level = r?.data?.result?.level ?? null;
      const status =
        level == null
          ? "unknown"
          : level >= 3
          ? "cleared"
          : "concerned";
      _cached = { level, status };
      return _cached;
    })
    .catch(() => {
      _cached = { level: null, status: "unknown" };
      return _cached;
    })
    .finally(() => {
      _inflight = null;
    });
  return _inflight;
}

export function useSafetyLevel() {
  const [state, setState] = useState(_cached);
  useEffect(() => {
    if (state) return;
    let cancelled = false;
    _fetchOnce().then((r) => {
      if (!cancelled) setState(r);
    });
    return () => {
      cancelled = true;
    };
  }, [state]);
  return state || { level: null, status: "unknown" };
}

// Exposed for tests only — resets the module cache so a spec can
// re-run the fetch cycle deterministically.
export function _resetSafetyLevelCache() {
  _cached = null;
  _inflight = null;
}
