/**
 * useSlideProgress — iter201.
 *
 * Fetches the parent's assessment completion signals ONCE per session
 * and returns a boolean map keyed by slide key. Powers the green
 * completion ring on each DashboardSlideshow frame.
 *
 * Sources (both public, both cached module-side):
 *   - GET /api/dashboard/progress — 4 numeric/boolean pills
 *   - GET /api/safety-assessment/me — presence of a safety result
 *
 * Mapping:
 *   situation      → safety-assessment.me exists (any level, any date)
 *   child-needs    → dashboard/progress.child_needs_identified
 *   relationship   → dashboard/progress.foundation_completed
 *                    (writing a Foundation Statement IS how the app
 *                     models "you've clarified your co-parenting
 *                     relationship"; separate flag would be over-
 *                     engineering right now)
 *   communication  → dashboard/progress.communication_readiness >= 50
 *   foundation     → dashboard/progress.foundation_completed
 *
 * Never throws. Any error resolves to all-false so a missing progress
 * endpoint doesn't fill the slideshow with fake green rings.
 */
import { useEffect, useState } from "react";
import { api } from "../lib/api";

let _cached = null;
let _inflight = null;

const EMPTY = {
  situation: false,
  "child-needs": false,
  relationship: false,
  communication: false,
  foundation: false,
};

function _fetchOnce() {
  if (_cached) return Promise.resolve(_cached);
  if (_inflight) return _inflight;
  // The in-app safety screen is off, so "situation" is never marked from saved answers.
  _inflight = Promise.all([api.get("/dashboard/progress").catch(() => ({ data: {} }))])
    .then(([progressRes]) => {
      const p = progressRes?.data || {};
      const commReadiness =
        typeof p.communication_readiness === "number"
          ? p.communication_readiness
          : 0;
      _cached = {
        situation: false,
        "child-needs": !!p.child_needs_identified,
        relationship: !!p.foundation_completed,
        communication: commReadiness >= 50,
        foundation: !!p.foundation_completed,
      };
      return _cached;
    })
    .catch(() => {
      _cached = { ...EMPTY };
      return _cached;
    })
    .finally(() => {
      _inflight = null;
    });
  return _inflight;
}

export function useSlideProgress() {
  const [state, setState] = useState(_cached || EMPTY);
  useEffect(() => {
    if (_cached) return;
    let cancelled = false;
    _fetchOnce().then((r) => {
      if (!cancelled) setState(r);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}

// Test-only cache reset.
export function _resetSlideProgressCache() {
  _cached = null;
  _inflight = null;
}
