import React, { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import {
  Sparkles,
  Star,
  MessageCircle,
  Compass,
  BookOpen,
  Loader2,
  RefreshCcw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

/**
 * SectionCoachCard — AI Personal Coach after each Deep Dive section.
 *
 * Props:
 *   apiPrefix   — e.g. "/edu-deep"     (already includes leading slash)
 *   testidBase  — e.g. "edu-deep"      (used for data-testid)
 *   sectionId   — e.g. "s3"
 *   sectionName — e.g. "ARD Meetings"
 *
 * The card is collapsed by default so it never gets in the way of the
 * assessment flow. Clicking "Show my coach" fires the API call. A "Refresh"
 * link forces a fresh generation (bypasses the answer-hash cache) so the
 * parent can rerun after changing their answers.
 */
const CARD_META = [
  {
    key: "doing_well",
    title: "What you're doing well",
    icon: Star,
    tint: {
      bg: "bg-[#F1F9F4]",
      border: "border-[#B5DFC5]",
      text: "text-[#1F5C3B]",
      dot: "bg-[#1F5C3B]",
    },
  },
  {
    key: "coordination_gaps",
    title: "Where coordination could grow",
    icon: MessageCircle,
    tint: {
      bg: "bg-[#F5F1FB]",
      border: "border-[#D6CFE8]",
      text: "text-[#3D1A78]",
      dot: "bg-[#3D1A78]",
    },
  },
  {
    key: "next_steps",
    title: "Suggested next steps",
    icon: Compass,
    tint: {
      bg: "bg-[#FBEDDA]",
      border: "border-[#EDD5B0]",
      text: "text-[#8C5A2C]",
      dot: "bg-[#8C5A2C]",
    },
  },
  {
    key: "resources",
    title: "Recommended resources",
    icon: BookOpen,
    tint: {
      bg: "bg-[#EEF3FB]",
      border: "border-[#C7D6EB]",
      text: "text-[#233B6C]",
      dot: "bg-[#233B6C]",
    },
  },
];

export default function SectionCoachCard({
  apiPrefix,
  testidBase,
  sectionId,
  sectionName,
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [coach, setCoach] = useState(null);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState({ cached: false, no_answers: false });
  // Reset when the parent switches to a different section so we don't show
  // a stale card. Refs avoid the useEffect running twice in strict mode.
  const lastSectionRef = useRef(sectionId);
  useEffect(() => {
    if (lastSectionRef.current !== sectionId) {
      lastSectionRef.current = sectionId;
      setOpen(false);
      setCoach(null);
      setError("");
    }
  }, [sectionId]);

  async function loadCoach({ force = false } = {}) {
    setLoading(true);
    setError("");
    try {
      const r = await api.post(`${apiPrefix}/section/${sectionId}/coach`, { force });
      setCoach(r.data?.coach || null);
      setMeta({
        cached: !!r.data?.cached,
        no_answers: !!r.data?.no_answers,
      });
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Your AI coach is resting right now. Please try again in a moment.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleToggle() {
    const next = !open;
    setOpen(next);
    if (next && !coach && !loading) {
      loadCoach();
    }
  }

  const totalBullets = coach
    ? CARD_META.reduce((n, m) => n + ((coach[m.key] || []).length || 0), 0)
    : 0;

  return (
    <div
      className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid={`${testidBase}-section-coach`}
    >
      <button
        type="button"
        onClick={handleToggle}
        className="w-full flex items-start sm:items-center gap-3 text-left"
        data-testid={`${testidBase}-section-coach-toggle`}
      >
        <div className="shrink-0 h-9 w-9 rounded-full bg-[#F5F1FB] flex items-center justify-center text-[#3D1A78]">
          <Sparkles size={16} />
        </div>
        <div className="flex-1">
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            AI Personal Coach
          </div>
          <div className="font-serif text-lg text-[#1A1330] leading-snug mt-0.5">
            Based on your answers for{" "}
            <span className="text-[#3D1A78]">
              {sectionName ? `“${sectionName}”` : "this section"}
            </span>
            …
          </div>
          <div className="text-xs text-[#4B4567] mt-1">
            {open
              ? "Neutral, non-diagnostic reflection powered by Claude."
              : "Tap to see strengths, coordination gaps, next steps, and resources for this section."}
          </div>
        </div>
        <div className="shrink-0 text-[#3D1A78]">
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </button>

      {open && (
        <div className="mt-5">
          {loading && (
            <div
              className="flex items-center gap-2 text-sm text-[#4B4567]"
              data-testid={`${testidBase}-section-coach-loading`}
            >
              <Loader2 size={14} className="animate-spin" />
              Reading your answers and preparing your coach card…
            </div>
          )}

          {!loading && error && (
            <div
              className="rounded-2xl border border-[#EDD1D1] bg-[#FBEDED] text-[#8C3A3A] p-4 flex items-start gap-2"
              data-testid={`${testidBase}-section-coach-error`}
            >
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <div className="text-sm">
                <div className="font-semibold">Coach couldn't respond right now.</div>
                <div className="mt-1">{error}</div>
                <button
                  type="button"
                  className="mt-2 inline-flex items-center gap-1 text-xs font-semibold underline"
                  onClick={() => loadCoach({ force: true })}
                  data-testid={`${testidBase}-section-coach-retry`}
                >
                  <RefreshCcw size={12} /> Try again
                </button>
              </div>
            </div>
          )}

          {!loading && !error && coach && meta.no_answers && (
            <div
              className="rounded-2xl bg-[#FCFBFE] border border-[#EEE9F7] p-4 text-sm text-[#4B4567]"
              data-testid={`${testidBase}-section-coach-empty`}
            >
              Answer a couple of questions in this section, then come back for
              your personal coach card.
            </div>
          )}

          {!loading && !error && coach && !meta.no_answers && (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                {CARD_META.map(({ key, title, icon: Icon, tint }) => {
                  const items = coach[key] || [];
                  return (
                    <div
                      key={key}
                      className={`rounded-2xl ${tint.bg} ${tint.border} border p-4`}
                      data-testid={`${testidBase}-section-coach-${key.replace(
                        "_",
                        "-",
                      )}`}
                    >
                      <div
                        className={`flex items-center gap-2 ${tint.text} font-semibold text-[11px] uppercase tracking-[0.18em]`}
                      >
                        <Icon size={13} />
                        {title}
                      </div>
                      {items.length === 0 ? (
                        <div className="text-xs text-[#857E9C] mt-2">
                          {key === "coordination_gaps"
                            ? "Nothing flagged in this section — nice."
                            : "Nothing to add right now."}
                        </div>
                      ) : (
                        <ul className="mt-2 space-y-1.5">
                          {items.map((line, i) => (
                            <li
                              key={`${key}-${i}-${String(line).slice(0, 30)}`}
                              className="flex gap-2 text-[13px] text-[#1A1330] leading-snug"
                            >
                              <span
                                className={`shrink-0 mt-1.5 h-1.5 w-1.5 rounded-full ${tint.dot}`}
                              />
                              <span>{line}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-[#857E9C]">
                <span>
                  {meta.cached
                    ? "Coach card served from your saved cache."
                    : "Freshly generated for this section."}
                  {totalBullets > 0 ? ` · ${totalBullets} bullets` : ""}
                </span>
                <button
                  type="button"
                  onClick={() => loadCoach({ force: true })}
                  className="inline-flex items-center gap-1 text-[#3D1A78] font-semibold hover:underline"
                  data-testid={`${testidBase}-section-coach-refresh`}
                >
                  <RefreshCcw size={12} /> Refresh coach
                </button>
              </div>

              <div className="mt-3 text-[11px] text-[#857E9C] italic">
                This coach is educational — not a diagnosis or medical advice.
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
