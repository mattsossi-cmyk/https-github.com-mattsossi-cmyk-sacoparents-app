import React, { useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { ArrowLeft, Download, ClipboardList, Loader2 } from "lucide-react";
import AppShell from "../components/AppShell";
import { api, API } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

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

function Stat({ label, value, hint, testid }) {
  return (
    <div className="card-soft p-5" data-testid={testid}>
      <div className="eyebrow mb-2">{label}</div>
      <div className="font-serif text-3xl text-[#1A1330] leading-none">{value}</div>
      {hint && <div className="text-xs text-[#6E6787] mt-1.5">{hint}</div>}
    </div>
  );
}

function Distribution({ question, rows }) {
  const counts = {};
  rows.forEach((r) => {
    const v = r.responses?.[question.id];
    if (v == null || v === "") return;
    const key = String(v);
    counts[key] = (counts[key] || 0) + 1;
  });
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (!total) {
    return (
      <div className="text-xs text-[#6E6787]">No responses yet.</div>
    );
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <div className="space-y-2">
      {entries.map(([key, n]) => {
        const pct = Math.round((n / total) * 100);
        return (
          <div key={key}>
            <div className="flex items-baseline justify-between text-xs mb-1">
              <span className="text-[#1A1330] truncate pr-2">{key}</span>
              <span className="text-[#4B4567] shrink-0">
                {n} <span className="text-[#6E6787]">({pct}%)</span>
              </span>
            </div>
            <div className="h-1.5 bg-[#E5E0EE] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5]"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AdminSurveys() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!user) return;
    api
      .get("/surveys/admin/post-event?limit=500")
      .then((r) => setData(r.data))
      .catch((e) => {
        logError("survey admin load failed", e);
        setErr(e?.response?.status === 403 ? "forbidden" : "Could not load surveys.");
      });
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center max-w-lg mx-auto">
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">
            This dashboard is restricted to the SA CoParenting App owner.
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
  if (!data) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center text-sm tracking-[0.2em] uppercase text-[#6E6787] animate-pulse">
          Loading surveys…
        </div>
      </AppShell>
    );
  }

  const { rows, questions, total, pending, sent, responded, response_rate_pct, avg_nps } = data;
  const responded_rows = rows.filter((r) => r.status === "responded");

  // CSV uses a cookie-authed endpoint; opening in a new tab keeps the admin
  // session and triggers browser download.
  const csvUrl = `${API}/surveys/admin/post-event.csv`;

  return (
    <AppShell>
      <div className="fade-up space-y-8" data-testid="admin-surveys">
        <Link
          to="/admin"
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:underline"
          data-testid="admin-surveys-back-link"
        >
          <ArrowLeft size={14} /> Back to admin
        </Link>

        <div className="card-soft p-7 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <div className="eyebrow mb-2">Post-event survey</div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] flex items-center gap-3">
                <ClipboardList className="text-[#3D1A78]" size={28} />
                &ldquo;How was mediation?&rdquo;
              </h1>
              <p className="text-sm text-[#4B4567] mt-2 max-w-lg">
                Sent automatically 7 days after each parent generates their first
                Mediation Summary. One reminder follows 7 days later if there&apos;s no
                response.
              </p>
            </div>
            <a
              href={csvUrl}
              data-testid="admin-surveys-csv-link"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2c1158] transition-colors shadow-sm shrink-0"
            >
              <Download size={14} /> CSV
            </a>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Stat label="Scheduled" value={total} testid="survey-stat-total" />
          <Stat label="Pending send" value={pending} testid="survey-stat-pending" />
          <Stat label="Emails sent" value={sent} testid="survey-stat-sent" />
          <Stat
            label="Responses"
            value={responded}
            hint={`${response_rate_pct}% response rate`}
            testid="survey-stat-responded"
          />
          <Stat
            label="NPS (avg / 10)"
            value={avg_nps == null ? "—" : avg_nps}
            testid="survey-stat-nps"
          />
        </div>

        {/* Distributions for each multi-choice / scale question */}
        <div className="grid lg:grid-cols-2 gap-6">
          {questions
            .filter((q) => q.type === "single" || q.type === "scale_0_10")
            .map((q) => (
              <div key={q.id} className="card-soft p-6">
                <div className="text-[11px] tracking-[0.22em] uppercase font-bold text-[#3D1A78] mb-2">
                  {q.id}
                </div>
                <div className="font-serif text-sm text-[#1A1330] mb-4 leading-snug">
                  {q.label}
                </div>
                <Distribution question={q} rows={responded_rows} />
              </div>
            ))}
        </div>

        {/* Open-text replies */}
        <div className="card-soft p-6">
          <div className="eyebrow mb-4">Open responses</div>
          {responded_rows.length === 0 ? (
            <div className="text-sm text-[#6E6787]">No responses yet.</div>
          ) : (
            <div className="space-y-5" data-testid="survey-open-responses">
              {responded_rows.map((r) => (
                <div
                  key={r.survey_id}
                  className="border-l-2 border-[#3D1A78]/30 pl-4 py-1"
                >
                  <div className="flex items-baseline justify-between text-xs text-[#6E6787] mb-2">
                    <span>{r.name || r.email}</span>
                    <span>{fmtDate(r.responded_at)}</span>
                  </div>
                  {questions
                    .filter((q) => q.type === "long_text")
                    .map((q) => {
                      const val = r.responses?.[q.id];
                      if (!val) return null;
                      return (
                        <div key={q.id} className="mb-3">
                          <div className="text-[10px] uppercase tracking-[0.15em] text-[#3D1A78] font-bold mb-1">
                            {q.label}
                          </div>
                          <div className="text-sm text-[#1A1330] whitespace-pre-wrap">
                            {val}
                          </div>
                        </div>
                      );
                    })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent survey rows table */}
        <div className="card-soft p-6">
          <div className="eyebrow mb-3">Recent surveys</div>
          {rows.length === 0 ? (
            <div className="text-sm text-[#6E6787]">No surveys scheduled yet.</div>
          ) : (
            <div tabIndex={0} role="region" aria-label="Scrollable table" className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="survey-rows-table">
                <thead>
                  <tr className="text-[10px] uppercase tracking-[0.15em] text-[#6E6787]">
                    <th className="text-left py-2 pr-3">Parent</th>
                    <th className="text-left py-2 pr-3">Email</th>
                    <th className="text-left py-2 pr-3">Status</th>
                    <th className="text-left py-2 pr-3">Sent</th>
                    <th className="text-left py-2 pr-3">Reminder</th>
                    <th className="text-left py-2">Responded</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 100).map((r) => (
                    <tr key={r.survey_id} className="border-t border-[#E5E0EE]">
                      <td className="py-2 pr-3 text-[#1A1330] truncate max-w-[140px]">
                        {r.name || "—"}
                      </td>
                      <td className="py-2 pr-3 text-[#4B4567] truncate max-w-[200px]">
                        {r.email}
                      </td>
                      <td className="py-2 pr-3">
                        <span
                          className={`text-[10px] uppercase tracking-[0.12em] px-2 py-0.5 rounded-full ${
                            r.status === "responded"
                              ? "bg-[#D5F2F2] text-[#0E7A7A]"
                              : "bg-[#F0EDF7] text-[#4B4567]"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-[#4B4567]">{fmtDate(r.sent_at)}</td>
                      <td className="py-2 pr-3 text-[#4B4567]">
                        {fmtDate(r.reminder_sent_at)}
                      </td>
                      <td className="py-2 text-[#4B4567]">{fmtDate(r.responded_at)}</td>
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
