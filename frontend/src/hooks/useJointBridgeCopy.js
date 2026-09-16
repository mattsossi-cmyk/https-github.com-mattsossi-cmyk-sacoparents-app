/**
 * useJointBridgeCopy — iter199.
 *
 * Fetches the two-variant configurable copy for the Individual→Joint
 * bridge section from `/api/public/nudge-copy/individual-to-joint-bridge`
 * and exposes helpers to log impressions / clicks. Falls back to the
 * baked-in defaults (matching the backend defaults) when the fetch
 * fails so a network hiccup never blanks the section.
 *
 * Usage:
 *   const { copy, trackImpression, trackClick } = useJointBridgeCopy();
 *   const variant = copy[safetyStatus === "concerned" ? "concerned" : "cleared"];
 *   useEffect(() => trackImpression(variantName), []);
 *   <Link onClick={() => trackClick(variantName, "sample-joint-preview")}/>
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

const DEFAULTS = {
  cleared: {
    eyebrow: "When you're ready to go further — no concerns about family violence",
    headline: "Want to compare perspectives?",
    body:
      "Invite your co-parent — or connect with a mediator, attorney or " +
      "therapist — to move from individual reflection into joint alignment.",
    cta_label: "See a sample joint preview",
    cta_route: "/samples",
  },
  concerned: {
    eyebrow:
      "When you're ready, on your own timeline — safe paths for when family violence is present",
    headline: "Keep working on your own — safely, at your pace.",
    body:
      "Joint tools aren't the next step for you right now. Continue building " +
      "your private reflection, journal, and safety plan — and connect with a " +
      "domestic-violence advocate whenever it feels right.",
    cta_label: "See safe individual paths",
    cta_route: "/safety",
  },
  is_default: true,
};

let _cached = null;
let _inflight = null;

function _fetchOnce() {
  if (_cached) return Promise.resolve(_cached);
  if (_inflight) return _inflight;
  _inflight = api
    .get("/public/nudge-copy/individual-to-joint-bridge")
    .then((r) => {
      _cached = { ...DEFAULTS, ...(r?.data || {}) };
      return _cached;
    })
    .catch(() => {
      _cached = { ...DEFAULTS };
      return _cached;
    })
    .finally(() => {
      _inflight = null;
    });
  return _inflight;
}

export function useJointBridgeCopy() {
  const [copy, setCopy] = useState(_cached || DEFAULTS);
  useEffect(() => {
    if (_cached) return;
    let cancelled = false;
    _fetchOnce().then((c) => {
      if (!cancelled) setCopy(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Dedupe impressions per (variant, mount) so a re-render doesn't
  // stack fake impressions. Clicks are always tracked (real user action).
  const impressed = useRef(new Set());

  const trackImpression = useCallback((variant) => {
    if (!variant || impressed.current.has(variant)) return;
    impressed.current.add(variant);
    api
      .post("/public/nudge-copy/individual-to-joint-bridge/track", {
        variant,
        event: "impression",
      })
      .catch(() => {
        /* fire-and-forget */
      });
  }, []);

  const trackClick = useCallback((variant, target) => {
    if (!variant) return;
    api
      .post("/public/nudge-copy/individual-to-joint-bridge/track", {
        variant,
        event: "click",
        target: target || null,
      })
      .catch(() => {
        /* fire-and-forget */
      });
  }, []);

  return { copy, trackImpression, trackClick };
}

// Test-only cache reset.
export function _resetJointBridgeCache() {
  _cached = null;
  _inflight = null;
}
