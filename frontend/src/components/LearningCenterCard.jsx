import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { BookOpen, ArrowRight, Loader2, CheckCircle2 } from "lucide-react";
import { logError } from "../lib/logger";

/**
 * LearningCenterCard — small dashboard entry point.
 * Shows total read progress across all three hubs. Never blocks the
 * dashboard: if the API fails we just render nothing.
 */
export default function LearningCenterCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/learning/progress");
      setData(r.data || null);
    } catch (err) {
      logError("learning progress failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <section
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="learning-card-loading"
      >
        <Loader2 size={14} className="animate-spin" />
        Loading learning center…
      </section>
    );
  }
  if (!data) return null;

  const pct = data.total_articles
    ? Math.round((data.read_count / data.total_articles) * 100)
    : 0;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="learning-card"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 h-10 w-10 rounded-xl bg-[#F5F1FB] flex items-center justify-center text-[#3D1A78]">
          <BookOpen size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            Learning center
          </div>
          <div className="font-serif text-xl text-[#1A1330] leading-snug mt-0.5">
            {data.started
              ? `You've read ${data.read_count} of ${data.total_articles} short reads.`
              : "Short reads on communication, boundaries, and mediation."}
          </div>
          <div className="text-xs text-[#4B4567] mt-1">
            {data.started
              ? "Small learnings compound. Pick up where you left off."
              : "~2-3 min each. Skim what draws you in."}
          </div>
        </div>
        <Link
          to="/learning"
          className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-[#3D1A78] text-white hover:brightness-110 transition-all"
          data-testid="learning-card-open"
        >
          {data.started ? "Continue" : "Explore"}
          <ArrowRight size={12} />
        </Link>
      </div>

      {/* Per-hub tiny progress row */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        {data.per_hub.map((h) => (
          <div
            key={h.slug}
            className="rounded-xl border border-[#E5E0EE] p-3 bg-[#FCFBFE]"
            data-testid={`learning-card-hub-${h.slug}`}
          >
            <div className="flex items-center gap-1.5">
              {h.read === h.total && h.total > 0 ? (
                <CheckCircle2 size={12} className="text-[#1F5C3B]" />
              ) : (
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: h.accent }}
                  aria-hidden
                />
              )}
              <div className="text-[0.6875rem] font-semibold text-[#1A1330] truncate">
                {h.name}
              </div>
            </div>
            <div className="text-[0.6875rem] text-[#4B4567] mt-1">
              {h.read}/{h.total} read
            </div>
          </div>
        ))}
      </div>

      {data.started && (
        <div className="mt-3 h-1.5 w-full rounded-full bg-[#F5F1FB] overflow-hidden">
          <div
            className="h-full rounded-full bg-[#3D1A78] transition-all"
            style={{ width: `${pct}%` }}
            data-testid="learning-card-progress-bar"
          />
        </div>
      )}
    </section>
  );
}
