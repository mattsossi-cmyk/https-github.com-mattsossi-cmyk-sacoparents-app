import React, { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ShieldCheck, TrendingUp } from "lucide-react";

import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

const HEAD = ["Week of (Monday, UTC)", "Sign-ups", "Accepted the Privacy Notice", "Gave sensitive-info consent", "Still need re-consent"];
const fmtWeek = (d) => new Date(`${d}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

function WeekRow({ w, isCurrent }) {
  const label = `${fmtWeek(w.week_start)}${isCurrent ? " (so far)" : ""}`;
  return (
    <tr className="border-t border-[#F0EDF6]" data-testid="admin-trend-row" data-week={w.week_start}>
      <td className="px-4 py-2.5 font-semibold text-[#1A1330] whitespace-nowrap">{label}</td>
      {w.fewer_than_5 ? (
        <td colSpan={4} className="px-4 py-2.5 text-left text-[#857E9C] italic" data-testid="admin-trend-suppressed">fewer than 5</td>
      ) : (
        [w.signups, w.privacy_notice_accepted, w.sensitive_info_consent, w.needs_reconsent].map((n, i) => (
          <td key={HEAD[i + 1]} className="px-4 py-2.5 text-right tabular-nums" data-testid={`admin-trend-cell-${i}`}>{n}</td>
        ))
      )}
    </tr>
  );
}

function Forbidden() {
  return (
    <AppShell>
      <div className="card-soft p-8 text-center max-w-lg mx-auto" data-testid="admin-trend-forbidden">
        <ShieldCheck size={20} className="mx-auto text-[#B6663B] mb-3" />
        <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
        <p className="text-sm text-[#4B4567] mt-2">This page is restricted to the SA CoParents app owner.</p>
      </div>
    </AppShell>
  );
}

// Admin-only, weekly totals only: the server never sends names, emails, user ids or per-person dates.
export default function AdminConsentTrend() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!user) return;
    api.get("/analytics/admin/consent-trend").then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.status === 403 ? "forbidden" : "error"));
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") return <Forbidden />;
  if (!data && !err) return null;
  const weeks = data?.weeks || [];
  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-1 py-6 space-y-6" data-testid="admin-trend-page">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
            <TrendingUp size={12} /> Privacy Notice consent · weekly totals only
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] mt-2">Consent trend</h1>
          <p className="text-sm text-[#4B4567] mt-2">
            Last 12 weeks, accounts only (no demo sessions). Current version:{" "}
            <code data-testid="admin-trend-version" className="font-mono text-[#3D1A78]">{data?.current_version ?? "–"}</code>
          </p>
        </div>
        {err === "error" && <p className="text-sm text-[#B02A2A]" data-testid="admin-trend-error">Couldn&rsquo;t load the totals. Please refresh.</p>}
        <div className="rounded-2xl border border-[#E5E0EE] bg-white overflow-x-auto" data-testid="admin-trend-table">
          <table className="w-full text-sm">
            <thead className="bg-[#F8F7FC] text-[11px] uppercase tracking-wider text-[#857E9C]">
              <tr>{HEAD.map((h, i) => <th key={h} className={`px-4 py-2.5 font-bold ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {weeks.map((w, i) => <WeekRow key={w.week_start} w={w} isCurrent={i === weeks.length - 1} />)}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-[#857E9C] leading-relaxed max-w-3xl" data-testid="admin-trend-note">
          Each account is counted once, in the week it was created. The last three columns are for those accounts as they stand today:
          ticked for the current Privacy Notice version, or still to be asked again. We only keep each person&rsquo;s latest consent, so
          past weeks can&rsquo;t show what was true at the time. Weeks with fewer than 5 sign-ups show no numbers.{" "}
          <Link to="/admin/consent" className="underline text-[#3D1A78]" data-testid="admin-trend-counts-link">Consent counts</Link>
        </p>
      </div>
    </AppShell>
  );
}
