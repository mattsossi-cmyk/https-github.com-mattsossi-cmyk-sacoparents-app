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
  Printer,
} from "lucide-react";
import { logError } from "../lib/logger";

const SECTION_META = {
  child_goals: { label: "Child Goals", icon: Target, path: "/prep/child-goals" },
  issues: { label: "Issues & Concerns", icon: AlertCircle, path: "/prep/issues" },
  priority: { label: "Priority", icon: ListOrdered, path: "/prep/priority" },
  comm_style: { label: "Communication", icon: MessageCircle, path: "/prep/communication" },
  readiness: { label: "Readiness", icon: HeartHandshake, path: "/prep/readiness" },
};

// Human-facing labels used in the printable Progress Report — softer and more
// action-forward than the internal SECTION_META names.
const REPORT_LABEL = {
  child_goals: "Identify Your Child's Needs",
  issues: "Name Your Concerns",
  priority: "Rank Your Priorities",
  comm_style: "Co-Parenting Reflection",
  readiness: "Mediation Readiness",
};
const REPORT_ORDER = ["child_goals", "comm_style", "issues", "priority", "readiness"];

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
      {hint && <div className="text-xs text-[#6E6787]">{hint}</div>}
    </div>
  );
}

function ReadinessSparkline({ points }) {
  if (!points?.length) {
    return (
      <div className="text-sm text-[#6E6787]">
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
        <div className="card-soft p-8 text-center text-sm tracking-[0.2em] uppercase text-[#6E6787] animate-pulse">
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
              A quiet snapshot of the work you&apos;ve put in — no scores, no rankings, just
              what you&apos;ve completed and how you&apos;re feeling.
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
                  <span className="text-[#6E6787] text-xl">/ {progress.steps_total}</span>
                </div>
                <div className="text-sm text-[#4B4567]">{progress.pct}%</div>
              </div>
              <div className="h-2 bg-[#E5E0EE] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3D1A78] progress-fill"
                  style={{ width: `${progress.pct}%` }}
                  data-testid="progress-bar"
                />
              </div>
              <p
                className="text-sm text-[#4B4567] mt-3 leading-relaxed italic"
                data-testid="progress-statement"
              >
                {progress.steps_done === 0
                  ? "The first step is the hardest. Start when you're ready."
                  : progress.pct === 100
                  ? "You built a full, child-focused parenting plan. Bring it to mediation."
                  : `You're ${progress.pct}% of the way toward a child-focused parenting plan.`}
              </p>
            </div>
          </div>
        </div>

        {/* Progress Report — designed to be shared with a mediator or counselor. */}
        {(() => {
          const completedKeys = REPORT_ORDER.filter((k) => progress.completed.includes(k));
          const nextKey = REPORT_ORDER.find((k) => !progress.completed.includes(k));
          const generatedOn = new Date().toLocaleDateString(undefined, {
            year: "numeric", month: "long", day: "numeric",
          });
          return (
            <div
              className="card-soft p-6 sm:p-8 print:shadow-none print:border print:border-[#3D1A78]/30"
              data-testid="progress-report-card"
            >
              <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
                <div>
                  <div className="eyebrow">Progress Report</div>
                  <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1">
                    {user?.name ? `${user.name}'s ` : "Your "}
                    co-parenting prep
                  </h2>
                  <div className="text-xs text-[#6E6787] mt-1">
                    Generated {generatedOn} · sacoparentsapp.online
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => window.print()}
                  data-testid="progress-report-print-button"
                  className="print:hidden inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2 text-sm font-semibold hover:bg-[#F8F7FC]"
                >
                  <Printer size={14} />
                  Print / Save PDF
                </button>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div data-testid="progress-report-completed">
                  <div className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-3">
                    Completed
                  </div>
                  {completedKeys.length === 0 ? (
                    <p className="text-sm text-[#6E6787] italic">
                      No steps completed yet. The first step is the hardest.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {completedKeys.map((k) => (
                        <li key={k} className="flex items-start gap-2 text-[15px] text-[#1A1330]">
                          <CheckCircle2 size={18} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                          <span>{REPORT_LABEL[k]}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div data-testid="progress-report-next-step">
                  <div className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-3">
                    Next step
                  </div>
                  {nextKey ? (
                    <div className="rounded-2xl bg-[#EFE9F9] border border-[#3D1A78]/15 p-4">
                      <div className="font-serif text-lg text-[#1A1330] leading-tight">
                        {REPORT_LABEL[nextKey]}
                      </div>
                      <Link
                        to={SECTION_META[nextKey].path}
                        className="print:hidden inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mt-2"
                        data-testid="progress-report-next-link"
                      >
                        Continue →
                      </Link>
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-[#DCEEDF] border border-[#3C7858]/25 p-4">
                      <div className="font-serif text-lg text-[#1F5C3B] leading-tight">
                        All prep steps complete.
                      </div>
                      <p className="text-sm text-[#4B4567] mt-1">
                        Bring your Summary to mediation.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-6 pt-5 border-t border-[#E5E0EE] text-xs text-[#4B4567] leading-relaxed italic">
                Professionals: parents can bring this report to mediation,
                co-parenting counseling, or family therapy sessions. It reflects
                self-reported progress inside the SA CoParents App and is not
                a clinical or legal assessment.
              </div>
            </div>
          );
        })()}

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
                    <div className="text-xs text-[#6E6787]">
                      {done ? "Today's accomplishment" : "Not yet"}
                    </div>
                  </div>
                  {done ? (
                    <CheckCircle2 size={18} className="text-[#3D1A78]" />
                  ) : (
                    <Circle size={18} className="text-[#6E6787]" />
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
                    <div className="text-xs text-[#6E6787] truncate">{s.summary_id}</div>
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
