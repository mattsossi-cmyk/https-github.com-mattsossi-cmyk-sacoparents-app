import React, { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Navigate, Link } from "react-router-dom";
import {
  Users,
  UserPlus,
  Sparkles,
  FileText,
  Mail,
  KeyRound,
  ShieldCheck,
  TrendingUp,
  Send,
  Handshake,
  X,
} from "lucide-react";
import { logError } from "../lib/logger";
import { toast } from "sonner";

const FUNNEL_STEPS = [
  { key: "child_goals", label: "Child Goals" },
  { key: "issues", label: "Issues" },
  { key: "priority", label: "Priority" },
  { key: "comm_style", label: "Communication" },
  { key: "readiness", label: "Readiness" },
];

function CheckinPreviewButton() {
  const [sending, setSending] = useState(false);
  const handleClick = async () => {
    setSending(true);
    try {
      const r = await api.post("/checkins/admin/send-me-preview");
      toast.success(
        r.data?.recap_included
          ? `Sent to ${r.data.sent_to} — recap included.`
          : `Sent to ${r.data.sent_to}. (No recap — add at least 2 journal entries in the past 7 days to include one.)`
      );
    } catch (e) {
      logError("checkin preview failed", e);
      toast.error(e?.response?.data?.detail || "Could not send the preview.");
    } finally {
      setSending(false);
    }
  };
  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={sending}
      data-testid="admin-checkin-preview-button"
      className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-white/70 hover:bg-white border border-[#3D1A78]/15 text-xs font-semibold text-[#3D1A78] transition-colors disabled:opacity-60"
    >
      <Send size={12} />
      {sending ? "Sending…" : "Preview check-in email"}
    </button>
  );
}

function Stat({ icon: Icon, label, value, hint, accent = "purple", testid }) {
  const accents = {
    purple: { bg: "bg-[#EFE9F9]", fg: "text-[#3D1A78]" },
    teal: { bg: "bg-[#D5F2F2]", fg: "text-[#0E7A7A]" },
    amber: { bg: "bg-[#FFF1E2]", fg: "text-[#B6663B]" },
  };
  const a = accents[accent] || accents.purple;
  return (
    <div className="card-soft p-5" data-testid={testid}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-9 h-9 rounded-full ${a.bg} grid place-items-center ${a.fg}`}>
          <Icon size={16} />
        </div>
        <div className="eyebrow">{label}</div>
      </div>
      <div className="font-serif text-3xl text-[#1A1330] leading-none">{value}</div>
      {hint && <div className="text-xs text-[#857E9C] mt-1.5">{hint}</div>}
    </div>
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

function SignupChart({ series }) {
  if (!series?.length) return null;
  const max = Math.max(1, ...series.map((d) => d.count));
  return (
    <div className="flex items-end gap-1 h-32" data-testid="admin-signup-chart">
      {series.map((d) => (
        <div
          key={d.date}
          className="flex-1 min-w-[3px] bg-gradient-to-t from-[#3D1A78] to-[#2DB5B5] rounded-t"
          style={{ height: `${(d.count / max) * 100}%` }}
          title={`${d.date}: ${d.count}`}
        />
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const { user, loading } = useAuth();
  const [overview, setOverview] = useState(null);
  const [recentUsers, setRecentUsers] = useState([]);
  const [signups, setSignups] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get("/analytics/admin/overview"),
      api.get("/analytics/admin/recent-users?limit=25"),
      api.get("/analytics/admin/daily-signups?days=30"),
    ])
      .then(([o, r, s]) => {
        setOverview(o.data);
        setRecentUsers(r.data.users || []);
        setSignups(s.data.series || []);
      })
      .catch((e) => {
        logError("admin analytics failed", e);
        if (e?.response?.status === 403) {
          setErr("forbidden");
        } else {
          setErr("Could not load admin analytics.");
        }
      });
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  if (err === "forbidden") {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center max-w-lg mx-auto" data-testid="admin-forbidden">
          <div className="w-12 h-12 mx-auto rounded-full bg-[#FFF1E2] grid place-items-center text-[#B6663B] mb-3">
            <ShieldCheck size={20} />
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">
            This dashboard is restricted to the SA CoParents app owner.
          </p>
        </div>
      </AppShell>
    );
  }

  if (err) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center">
          <p className="text-sm text-[#4B4567]">{err}</p>
        </div>
      </AppShell>
    );
  }

  if (!overview) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center text-sm tracking-[0.2em] uppercase text-[#857E9C] animate-pulse">
          Loading admin analytics…
        </div>
      </AppShell>
    );
  }

  const { users: U, engagement: E, magic_links: ML, funnel, consent } = overview;
  const CN = consent?.child_needs_share || null;
  const nudge = CN?.nudge_dismisses || {
    first_total: 0, permanent_total: 0, first_7d: 0, permanent_7d: 0,
  };
  const top = funnel.child_goals || 1;

  return (
    <AppShell>
      <div className="fade-up space-y-8" data-testid="admin-dashboard">
        <div className="card-soft p-7 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <div className="eyebrow mb-2">Admin</div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">
                SA CoParents — operations
              </h1>
              <p className="text-sm text-[#4B4567] mt-2">
                Quiet metrics for the people building this. Refreshed each request.
              </p>
            </div>
            <CheckinPreviewButton />
          </div>
        </div>

        {/* Top stats */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat
            icon={Users}
            label="Total users"
            value={U.total}
            hint={`+${U.new_7d} in last 7d · +${U.new_30d} in last 30d`}
            testid="admin-stat-users"
          />
          <Stat
            icon={UserPlus}
            label="Active guests"
            value={U.guests_active}
            hint={`${U.claimed_from_guest} converted to accounts`}
            accent="teal"
            testid="admin-stat-guests"
          />
          <Stat
            icon={Sparkles}
            label="AI summaries"
            value={E.summaries_total}
            hint={`+${E.summaries_7d} this week`}
            testid="admin-stat-summaries"
          />
          <Stat
            icon={Mail}
            label="Mediator emails"
            value={E.mediator_emails_total}
            hint={`+${E.mediator_emails_7d} this week`}
            accent="amber"
            testid="admin-stat-emails"
          />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Signup chart */}
          <div className="card-soft p-6 lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="eyebrow">Daily signups</div>
                <div className="font-serif text-xl text-[#1A1330]">Last 30 days</div>
              </div>
              <TrendingUp size={16} className="text-[#3D1A78]" />
            </div>
            <SignupChart series={signups} />
            <div className="flex justify-between text-[10px] text-[#857E9C] mt-2 uppercase tracking-[0.15em]">
              <span>{signups[0]?.date}</span>
              <span>{signups[signups.length - 1]?.date}</span>
            </div>
          </div>

          {/* Magic links */}
          <div className="card-soft p-6">
            <div className="eyebrow mb-2">Magic links</div>
            <div className="font-serif text-3xl text-[#1A1330]">
              {ML.conversion_pct}%
            </div>
            <div className="text-xs text-[#857E9C] mb-4">
              {ML.used} of {ML.requested} requested links used
            </div>
            <div className="flex items-center gap-2 text-xs text-[#4B4567]">
              <KeyRound size={12} />
              Email-based sign-in conversion
            </div>
          </div>
        </div>

        {/* Consent adoption — Child-Needs share (iter189) */}
        {CN && (
          <div className="card-soft p-6" data-testid="admin-consent-tile">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="eyebrow flex items-center gap-2">
                  <Handshake size={12} className="text-[#3D1A78]" />
                  Consent adoption · Child Needs share
                </div>
                <div className="font-serif text-xl text-[#1A1330] mt-1">
                  How often the joint Section 5 unlocks
                </div>
                <p className="text-xs text-[#857E9C] mt-1">
                  Same numbers we ship in the Monday admin digest —
                  aggregate only, never names or verbatim answers.
                </p>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                className="rounded-2xl border border-[#E5E0EE] bg-[#FAF8FD] p-4"
                data-testid="admin-consent-parents-tile"
              >
                <div className="eyebrow mb-2">Parents opted in</div>
                <div className="font-serif text-3xl text-[#1A1330] leading-none">
                  {CN.parents_consented}
                </div>
                <div className="text-xs text-[#857E9C] mt-1.5">
                  Cumulative — across every joint case.
                </div>
              </div>
              <div
                className="rounded-2xl border border-[#E5E0EE] bg-[#FAF8FD] p-4"
                data-testid="admin-consent-cases-tile"
              >
                <div className="eyebrow mb-2">Cases fully unlocked</div>
                <div className="font-serif text-3xl text-[#1A1330] leading-none">
                  {CN.cases_both_consented}
                  <span className="text-[#857E9C] text-lg"> / {CN.cases_total}</span>
                </div>
                <div className="text-xs text-[#857E9C] mt-1.5">
                  Section 5 visible on {CN.unlock_rate_pct}% of cases.
                </div>
              </div>
              <div
                className="rounded-2xl border border-[#E5E0EE] bg-[#FFFBF3] p-4"
                data-testid="admin-nudge-first-tile"
              >
                <div className="eyebrow mb-2 flex items-center gap-1.5">
                  <X size={11} /> Retry-hides
                </div>
                <div className="font-serif text-3xl text-[#1A1330] leading-none">
                  {nudge.first_total}
                </div>
                <div className="text-xs text-[#857E9C] mt-1.5">
                  Dismissed once · tile returns after 7d ·
                  <span className="text-[#B6663B]"> +{nudge.first_7d} this week</span>
                </div>
              </div>
              <div
                className="rounded-2xl border border-[#E5E0EE] bg-[#FBF6FF] p-4"
                data-testid="admin-nudge-permanent-tile"
              >
                <div className="eyebrow mb-2 flex items-center gap-1.5">
                  <X size={11} /> Permanent hides
                </div>
                <div className="font-serif text-3xl text-[#1A1330] leading-none">
                  {nudge.permanent_total}
                </div>
                <div className="text-xs text-[#857E9C] mt-1.5">
                  Dismissed after the retry ·
                  <span className="text-[#B6663B]"> +{nudge.permanent_7d} this week</span>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-[#857E9C] mt-4 italic">
              Rising permanent-hides with flat opt-ins means the retry
              cadence isn't converting hesitant parents. Consider
              softening the nudge copy.
            </p>
          </div>
        )}

        {/* Funnel + auth breakdown */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="card-soft p-6">
            <div className="eyebrow mb-3">Prep funnel</div>
            <div className="space-y-3" data-testid="admin-funnel">
              {FUNNEL_STEPS.map((s, i) => {
                const n = funnel[s.key] || 0;
                const prev = i === 0 ? n : funnel[FUNNEL_STEPS[i - 1].key] || 1;
                const pct = top ? Math.round((n / top) * 100) : 0;
                const dropRate = prev ? Math.round((n / prev) * 100) : 0;
                return (
                  <div key={s.key}>
                    <div className="flex items-baseline justify-between text-sm mb-1">
                      <span className="text-[#1A1330] font-medium">{s.label}</span>
                      <span className="text-[#4B4567]">
                        {n} <span className="text-[#857E9C]">({pct}% of top · {dropRate}% kept)</span>
                      </span>
                    </div>
                    <div className="h-2 bg-[#E5E0EE] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card-soft p-6">
            <div className="eyebrow mb-3">Auth method</div>
            <ul className="space-y-2" data-testid="admin-auth-breakdown">
              {Object.entries(U.auth_breakdown || {}).map(([m, n]) => (
                <li
                  key={m}
                  className="flex items-center justify-between text-sm py-2 border-b border-[#E5E0EE] last:border-0"
                >
                  <span className="capitalize text-[#1A1330]">{m}</span>
                  <span className="text-[#4B4567]">{n}</span>
                </li>
              ))}
            </ul>

            <div className="eyebrow mt-5 mb-3">Engagement</div>
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between"><span>Agreement drafts</span><span className="text-[#4B4567]">{E.agreements_total} (<span className="text-[#857E9C]">+{E.agreements_7d}/wk</span>)</span></li>
              <li className="flex justify-between"><span>Improvement plans</span><span className="text-[#4B4567]">{E.improvement_plans_total}</span></li>
            </ul>
          </div>
        </div>

        {/* Recent users */}
        <div className="card-soft p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="eyebrow">Recent signups</div>
            <div className="flex items-center gap-4">
              <Link
                to="/admin/insights"
                className="text-xs font-medium text-[#3D1A78] hover:underline"
                data-testid="admin-insights-link"
              >
                Weekly insights →
              </Link>
              <a
                href={`${process.env.REACT_APP_BACKEND_URL}/api/legal/admin/acks.csv`}
                className="text-xs font-medium text-[#3D1A78] hover:underline"
                data-testid="admin-legal-csv-link"
              >
                Legal acks CSV →
              </a>
              <Link
                to="/admin/surveys"
                className="text-xs font-medium text-[#3D1A78] hover:underline"
                data-testid="admin-surveys-link"
              >
                Post-event surveys →
              </Link>
              <Link
                to="/admin/users"
                className="text-xs font-medium text-[#3D1A78] hover:underline"
                data-testid="admin-manage-users-link"
              >
                Manage all users →
              </Link>
            </div>
          </div>
          {recentUsers.length === 0 ? (
            <div className="text-sm text-[#857E9C]">No users yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="admin-recent-users">
                <thead>
                  <tr className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C]">
                    <th className="text-left py-2 pr-3">Name</th>
                    <th className="text-left py-2 pr-3">Email</th>
                    <th className="text-left py-2 pr-3">Auth</th>
                    <th className="text-left py-2 pr-3">Joined</th>
                    <th className="text-left py-2 pr-3">Progress</th>
                    <th className="text-left py-2">AI</th>
                  </tr>
                </thead>
                <tbody>
                  {recentUsers.map((u) => (
                    <tr key={u.user_id} className="border-t border-[#E5E0EE]">
                      <td className="py-2 pr-3 text-[#1A1330] truncate max-w-[160px]">{u.name || "—"}</td>
                      <td className="py-2 pr-3 text-[#4B4567] truncate max-w-[200px]">{u.email}</td>
                      <td className="py-2 pr-3 text-[#4B4567] capitalize">{u.auth_method}</td>
                      <td className="py-2 pr-3 text-[#4B4567]">{fmtDate(u.created_at)}</td>
                      <td className="py-2 pr-3 text-[#4B4567]">{u.steps_done}/{u.steps_total}</td>
                      <td className="py-2 text-[#4B4567]">{u.summaries}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
