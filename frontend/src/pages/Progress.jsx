import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import {
  Target,
  AlertCircle,
  ListOrdered,
  MessageCircle,
  HeartHandshake,
  FileText,
  Sparkles,
  Mail,
  TrendingUp,
  CalendarClock,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { logError } from "../lib/logger";

const SECTION_META = {
  child_goals: { label: "Child Goals", icon: Target, path: "/prep/child-goals" },
  issues: { label: "Issues & Concerns", icon: AlertCircle, path: "/prep/issues" },
  priority: { label: "Priority", icon: ListOrdered, path: "/prep/priority" },
  comm_style: { label: "Communication", icon: MessageCircle, path: "/prep/communication" },
  readiness: { label: "Readiness", icon: HeartHandshake, path: "/prep/readiness" },
};

function StatCard({ icon: Icon, label, value, hint, testid }) {
  return (
    <div
      className="card-soft p-5 flex flex-col gap-2"
      data-testid={testid}
    >
      <div className="flex items-center gap-2 text-[#3D1A78]">
        <div className="w-9 h-9 rounded-full bg-[#EFE9F9] grid place-items-center">
          <Icon size={16} />
        </div>
        <div className="eyebrow">{label}</div>
      </div>
      <div className="font-serif text-3xl text-[#1A1330] leading-none">{value}</div>
      {hint && <div className="text-xs text-[#857E9C]">{hint}</div>}
    </div>
  );
}

function ReadinessSparkline({ points }) {
  if (!points?.length) {
    return (
      <div className="text-sm text-[#857E9C]">
        Generate a summary to start tracking your readiness over time.
      </div>
    );
  }
  const w = 280;
  const h = 80;
  const pad = 6;
  const xs = points.map((_, i) => pad + (i * (w - 2 * pad)) / Math.max(points.length - 1, 1));
  const ys = points.map(
    (p) => h - pad - ((p.score || 0) / 100) * (h - 2 * pad)
  );
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" aria-label="Readiness trend">
      <defs>
        <linearGradient id="readGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#3D1A78" />
          <stop offset="100%" stopColor="#2DB5B5" />
        </linearGradient>
      </defs>
      <path d={path} stroke="url(#readGrad)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      {xs.map((x, i) => (
        <circle key={`pt-${i}-${ys[i]?.toFixed?.(1) || i}`} cx={x} cy={ys[i]} r={3} fill="#3D1A78" />
      ))}
    </svg>
  );
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function ProgressPage() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api
      .get("/analytics/me")
      .then((r) => setData(r.data))
      .catch((e) => {
        logError("analytics/me failed", e);
        setErr("Could not load your progress.");
      });
  }, []);

  if (err) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center">
          <h2 className="font-serif text-2xl text-[#1A1330]">Something went wrong</h2>
          <p className="text-sm text-[#4B4567] mt-2">{err}</p>
        </div>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center text-sm tracking-[0.2em] uppercase text-[#857E9C] animate-pulse">
          Loading your progress…
        </div>
      </AppShell>
    );
  }

  const { progress, readiness, activity, recent_summaries: recent, user } = data;

  return (
    <AppShell>
      <div className="fade-up space-y-8" data-testid="progress-page">
        {/* Hero */}
        <div className="card-soft p-8 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative">
            <div className="eyebrow mb-3">Your progress</div>
            <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight">
              How prep is going.
            </h1>
            <p className="text-[#4B4567] mt-3 max-w-xl">
              A quiet snapshot of the work you've put in — no scores, no rankings, just
              what you've completed and how you're feeling.
            </p>
            {user?.mediation_date && (
              <div
                className="mt-5 inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full bg-[#EFE9F9] text-[#3D1A78]"
                data-testid="progress-mediation-date"
              >
                <CalendarClock size={12} />
                Mediation: {fmtDate(user.mediation_date)}
              </div>
            )}

            {/* Progress bar */}
            <div className="mt-7 max-w-md">
              <div className="flex items-end justify-between mb-2">
                <div className="font-serif text-3xl text-[#1A1330]">
                  {progress.steps_done}{" "}
                  <span className="text-[#857E9C] text-xl">/ {progress.steps_total}</span>
                </div>
                <div className="text-sm text-[#4B4567]">{progress.pct}% complete</div>
              </div>
              <div className="h-2 bg-[#E5E0EE] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3D1A78] progress-fill"
                  style={{ width: `${progress.pct}%` }}
                  data-testid="progress-bar"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Sparkles}
            label="AI summaries"
            value={activity.summaries}
            hint={activity.summaries > 0 ? "Synthesized for mediation" : "Generate one when ready"}
            testid="stat-summaries"
          />
          <StatCard
            icon={FileText}
            label="Agreement drafts"
            value={activity.agreements}
            hint={activity.agreements > 0 ? "Ready to review" : "Optional, after summary"}
            testid="stat-agreements"
          />
          <StatCard
            icon={Mail}
            label="Sent to mediator"
            value={activity.mediator_emails}
            hint={activity.mediator_emails > 0 ? "Documents emailed" : "When you're ready"}
            testid="stat-emails"
          />
          <StatCard
            icon={TrendingUp}
            label="Readiness"
            value={readiness.current != null ? `${readiness.current}%` : "—"}
            hint={readiness.current != null ? "Latest self-rating" : "Complete the Readiness check"}
            testid="stat-readiness"
          />
        </div>

        {/* Readiness trend */}
        <div className="card-soft p-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="eyebrow">Readiness trend</div>
              <div className="font-serif text-2xl text-[#1A1330]">
                Your last {readiness.trend?.length || 0} check-ins
              </div>
            </div>
            <Link
              to="/prep/readiness"
              className="text-sm text-[#3D1A78] hover:underline"
              data-testid="progress-readiness-link"
            >
              Re-check
            </Link>
          </div>
          <ReadinessSparkline points={readiness.trend || []} />
        </div>

        {/* Section checklist */}
        <div>
          <div className="eyebrow mb-3">Modules</div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(SECTION_META).map(([key, meta]) => {
              const done = progress.completed.includes(key);
              const Icon = meta.icon;
              return (
                <Link
                  key={key}
                  to={meta.path}
                  className="card-soft p-5 flex items-center gap-4 hover:-translate-y-0.5 transition-transform"
                  data-testid={`progress-section-${key}`}
                >
                  <div
                    className={`w-10 h-10 rounded-full grid place-items-center ${
                      done ? "bg-[#3D1A78] text-white" : "bg-[#EFE9F9] text-[#3D1A78]"
                    }`}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-lg text-[#1A1330]">{meta.label}</div>
                    <div className="text-xs text-[#857E9C]">
                      {done ? "Completed" : "Not yet"}
                    </div>
                  </div>
                  {done ? (
                    <CheckCircle2 size={18} className="text-[#3D1A78]" />
                  ) : (
                    <Circle size={18} className="text-[#857E9C]" />
                  )}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Recent summaries */}
        {recent && recent.length > 0 && (
          <div className="card-soft p-6">
            <div className="eyebrow mb-3">Recent summaries</div>
            <ul className="divide-y divide-[#E5E0EE]">
              {recent.map((s) => (
                <li
                  key={s.summary_id}
                  className="py-3 flex items-center justify-between gap-3"
                  data-testid={`recent-summary-${s.summary_id}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm text-[#1A1330]">{fmtDate(s.generated_at)}</div>
                    <div className="text-xs text-[#857E9C] truncate">{s.summary_id}</div>
                  </div>
                  {s.readiness_score != null && (
                    <div className="text-xs px-2 py-1 rounded-full bg-[#EFE9F9] text-[#3D1A78]">
                      Readiness {s.readiness_score}/10
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <Link
              to="/summary"
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mt-4"
              data-testid="progress-view-summary-link"
            >
              Open current summary →
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  );
}
