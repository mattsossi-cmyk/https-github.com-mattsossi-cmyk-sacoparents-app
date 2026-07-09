import { useEffect, useRef, useState } from "react";
import { Compass, HeartHandshake, Sprout, ArrowRight } from "lucide-react";
import { api } from "../lib/api";

/**
 * SectionCoaching
 *
 * Replaces the bare "your score is 68" pattern with 3 warm coaching insights
 * synthesized by Claude (via /api/mediation/section-coaching):
 *   • Opener      — one framing sentence, no score
 *   • Strengths   — what the parent is doing well
 *   • Attention   — one gentle growth area
 *   • Next step   — a specific, this-week-doable action
 *
 * Props:
 *   section  — "readiness" | "comm-style" | "safety"
 *   data     — the raw section payload (answers, score, level, etc.)
 *   ready    — boolean; true means the section is complete enough to coach
 *   testid   — root data-testid; defaults to "section-coaching-{section}"
 *
 * Caching:
 *   A shallow serialization of `data` is used as the cache key so repeated
 *   renders with unchanged inputs don't re-hit the LLM.
 */

const CACHE = new Map();

function keyFor(section, data) {
  try {
    return `${section}::${JSON.stringify(data)}`;
  } catch {
    return null;
  }
}

export default function SectionCoaching({ section, data, ready, testid }) {
  const rootTestId = testid || `section-coaching-${section}`;
  const [state, setState] = useState({ status: "idle", data: null, error: null });
  const requestId = useRef(0);

  useEffect(() => {
    if (!ready) {
      setState({ status: "idle", data: null, error: null });
      return;
    }
    const k = keyFor(section, data);
    if (k && CACHE.has(k)) {
      setState({ status: "ready", data: CACHE.get(k), error: null });
      return;
    }
    const rid = ++requestId.current;
    setState({ status: "loading", data: null, error: null });
    api
      .post("/mediation/section-coaching", { section, data })
      .then((r) => {
        if (rid !== requestId.current) return; // stale
        if (k) CACHE.set(k, r.data);
        setState({ status: "ready", data: r.data, error: null });
      })
      .catch((e) => {
        if (rid !== requestId.current) return;
        const detail = e?.response?.data?.detail || "Coaching temporarily unavailable.";
        setState({ status: "error", data: null, error: detail });
      });
  }, [ready, section, data]);

  if (!ready) return null;

  return (
    <div
      className="rounded-2xl p-6 sm:p-7 border border-black/5 shadow-sm bg-[#F1EBFA]"
      data-testid={rootTestId}
    >
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
        <Compass size={12} />
        Coaching insights
      </div>

      {state.status === "loading" && (
        <div className="mt-3 space-y-2" data-testid={`${rootTestId}-loading`}>
          <div className="h-4 w-3/4 rounded bg-white/60 animate-pulse" />
          <div className="h-4 w-5/6 rounded bg-white/60 animate-pulse" />
          <div className="h-4 w-2/3 rounded bg-white/60 animate-pulse" />
        </div>
      )}

      {state.status === "error" && (
        <p className="mt-2 text-sm text-[#4B4567]" data-testid={`${rootTestId}-error`}>
          {state.error} — the score above is still yours to reflect on.
        </p>
      )}

      {state.status === "ready" && state.data && (
        <>
          {state.data.opener && (
            <p
              className="font-serif text-lg sm:text-xl text-[#1A1330] mt-2 leading-snug"
              data-testid={`${rootTestId}-opener`}
            >
              {state.data.opener}
            </p>
          )}

          <div className="mt-5 space-y-4">
            {state.data.strengths && (
              <div>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] font-semibold text-[#2DB5B5]">
                  <HeartHandshake size={13} /> What you&apos;re doing well
                </div>
                <p
                  className="text-sm text-[#1A1330] mt-1 leading-relaxed"
                  data-testid={`${rootTestId}-strengths`}
                >
                  {state.data.strengths}
                </p>
              </div>
            )}
            {state.data.attention && (
              <div>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] font-semibold text-[#B8891C]">
                  <Sprout size={13} /> What may deserve attention
                </div>
                <p
                  className="text-sm text-[#1A1330] mt-1 leading-relaxed"
                  data-testid={`${rootTestId}-attention`}
                >
                  {state.data.attention}
                </p>
              </div>
            )}
            {state.data.next_step && (
              <div>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78]">
                  <ArrowRight size={13} /> One next step
                </div>
                <p
                  className="text-sm text-[#1A1330] mt-1 leading-relaxed font-medium"
                  data-testid={`${rootTestId}-next-step`}
                >
                  {state.data.next_step}
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
