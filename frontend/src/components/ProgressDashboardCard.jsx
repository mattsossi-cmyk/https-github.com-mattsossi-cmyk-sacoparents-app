import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { CheckCircle2, Circle, Loader2, Sparkles, Flame } from "lucide-react";
import { logError } from "../lib/logger";
import FoundationReadyCelebration, { FoundationReadyBadge } from "./FoundationReadyCelebration";
import ProgressSparkline from "./ProgressSparkline";
import useStreakCelebration from "../hooks/useStreakCelebration";

/**
 * ProgressDashboardCard — five ✓ pills showing the parent's real progress
 * across the app. Fetches /api/dashboard/progress and renders both the
 * headline count (e.g. "3 of 5 milestones") and per-pill detail lines.
 */
export default function ProgressDashboardCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/dashboard/progress")
      .then((r) => setData(r.data || null))
      .catch((err) => logError("Failed to load progress:", err))
      .finally(() => setLoading(false));
  }, []);

  // Fire a small confetti burst the first time this parent reaches
  // 30 or 100 consecutive days on the dashboard. Idempotent per
  // threshold via localStorage — will never fire twice on the same
  // device.
  useStreakCelebration(data?.streak_days);

  if (loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="dashboard-progress-loading"
      >
        <Loader2 size={14} className="animate-spin" />
        Reading your progress…
      </div>
    );
  }
  if (!data) return null;

  const done = data.completed_count || 0;
  const total = data.total || (data.pills || []).length;
  const pctBar = total > 0 ? Math.round((done / total) * 100) : 0;

  const headline =
    done === 0
      ? "Every parent starts here — pick one pill below to light up."
      : done === total
        ? "All five milestones lit. That's a full, child-focused foundation."
        : `${done} of ${total} milestones lit — you're on your way.`;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="dashboard-progress"
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold flex items-center gap-1.5">
            <Sparkles size={12} />
            Your progress
          </div>
          <h2
            className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-snug"
            data-testid="dashboard-progress-headline"
          >
            {headline}
          </h2>
        </div>
        <div
          className="text-sm font-semibold text-[#3D1A78] shrink-0 flex items-center gap-2 flex-wrap justify-end"
          data-testid="dashboard-progress-count"
        >
          <ProgressSparkline history={data.history} />
          {typeof data.streak_days === "number" && data.streak_days > 0 && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#FBEDDA] text-[#8C5A2C] border border-[#EDD5B0]"
              data-testid="dashboard-progress-streak"
              title={`${data.streak_days}-day dashboard streak`}
            >
              <Flame size={11} className="text-[#8C5A2C]" />
              {data.streak_days}d
            </span>
          )}
          <FoundationReadyBadge done={done} total={total} />
          {done}/{total}
        </div>
      </div>

      <FoundationReadyCelebration done={done} total={total} />

      {/* Progress bar */}
      <div
        className="mt-4 h-2 w-full rounded-full bg-[#F1EDF9] overflow-hidden"
        data-testid="dashboard-progress-bar"
      >
        <div
          className="h-full bg-gradient-to-r from-[#3D1A78] to-[#7A55C7] transition-all duration-500 ease-out"
          style={{ width: `${pctBar}%` }}
        />
      </div>

      {/* Pills */}
      <ul className="mt-5 grid gap-2.5 sm:grid-cols-2">
        {(data.pills || []).map((p) => {
          const Icon = p.done ? CheckCircle2 : Circle;
          return (
            <li
              key={p.id}
              className={`flex items-start gap-3 rounded-2xl border p-3.5 transition-colors ${
                p.done
                  ? "border-[#B5DFC5] bg-[#F1F9F4]"
                  : "border-[#EEE9F7] bg-[#FCFBFE]"
              }`}
              data-testid={`dashboard-progress-pill-${p.id}`}
            >
              <div
                className={`shrink-0 mt-0.5 ${
                  p.done ? "text-[#1F5C3B]" : "text-[#B0A9C4]"
                }`}
              >
                <Icon size={18} strokeWidth={p.done ? 2.5 : 1.8} />
              </div>
              <div className="min-w-0">
                <div
                  className={`text-sm font-semibold leading-snug ${
                    p.done ? "text-[#1F5C3B]" : "text-[#1A1330]"
                  }`}
                  data-testid={`dashboard-progress-pill-${p.id}-label`}
                >
                  {p.label}
                </div>
                <div
                  className={`text-xs mt-0.5 leading-snug ${
                    p.done ? "text-[#3B6E4A]" : "text-[#4B4567]"
                  }`}
                  data-testid={`dashboard-progress-pill-${p.id}-detail`}
                >
                  {p.detail}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
