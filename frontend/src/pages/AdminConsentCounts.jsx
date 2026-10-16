import React, { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ShieldCheck, FileCheck2 } from "lucide-react";

import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

const SOURCE_LABELS = {
  register: "Sign-up form",
  magic_link_setup: "Email link set-up",
  coparent_invite: "Co-parent invite",
  claim: "Demo saved as account",
  gate: "Before you continue screen",
};

const Stat = ({ label, value, sub, testid }) => (
  <div className="rounded-2xl border border-[#E5E0EE] bg-white p-5" data-testid={testid}>
    <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#857E9C]">{label}</div>
    <div className="font-serif text-4xl text-[#1A1330] mt-1 tabular-nums break-words" data-testid={`${testid}-value`}>{value ?? "–"}</div>
    {sub && <div className="text-xs text-[#4B4567] mt-1">{sub}</div>}
  </div>
);

const Table = ({ testid, head, rows }) => (
  <div className="rounded-2xl border border-[#E5E0EE] bg-white overflow-x-auto" data-testid={testid}>
    <table className="w-full text-sm">
      <thead className="bg-[#F8F7FC] text-[11px] uppercase tracking-wider text-[#857E9C]">
        <tr>{head.map((h, i) => <th key={h} className={`px-4 py-2.5 font-bold ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows.length === 0 && (
          <tr><td colSpan={head.length} className="px-4 py-3 text-[#857E9C]" data-testid={`${testid}-empty`}>None yet</td></tr>
        )}
        {rows.map((r) => (
          <tr key={r[0]} className="border-t border-[#F0EDF6]" data-testid={`${testid}-row`}>
            {r.map((c, i) => <td key={i} className={`px-4 py-2.5 tabular-nums ${i ? "text-right" : "text-left font-semibold text-[#1A1330] whitespace-nowrap"}`}>{c}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// Admin-only, counts only: no names, emails or user ids are fetched here.
export default function AdminConsentCounts() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!user) return;
    api.get("/analytics/admin/consent-counts").then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.status === 403 ? "forbidden" : "error"));
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center max-w-lg mx-auto" data-testid="admin-consent-forbidden">
          <ShieldCheck size={20} className="mx-auto text-[#B6663B] mb-3" />
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">This page is restricted to the SA CoParents app owner.</p>
        </div>
      </AppShell>
    );
  }
  if (!data && !err) return null;
  const versions = (data?.by_version || []).map((v) => [v.version, v.accounts, v.demo_sessions]);
  const sources = Object.entries(data?.current_version_by_source || {}).map(([k, n]) => [SOURCE_LABELS[k] || k, n]);
  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-1 py-6 space-y-6" data-testid="admin-consent-page">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
            <FileCheck2 size={12} /> Privacy Notice consent · counts only
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] mt-2">Who has consented</h1>
          <p className="text-sm text-[#4B4567] mt-2">
            Current version: <code data-testid="admin-consent-version" className="font-mono text-[#3D1A78]">{data?.current_version ?? "–"}</code>
          </p>
        </div>
        {err === "error" && <p className="text-sm text-[#B02A2A]" data-testid="admin-consent-error">Couldn&rsquo;t load the counts. Please refresh.</p>}
        <div className="grid sm:grid-cols-3 gap-3">
          <Stat label="Accounts consented" value={data?.accounts_consented} sub={data ? `of ${data.accounts} accounts` : null} testid="admin-consent-accounts" />
          <Stat label="Still to be asked" value={data?.accounts_pending} sub="Asked at their next sign-in" testid="admin-consent-pending" />
          <Stat label="Demo sessions consented" value={data?.demo_sessions_consented} sub={data ? `of ${data.demo_sessions} demo sessions` : null} testid="admin-consent-demo" />
        </div>
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-[#1A1330]">By version</h2>
          <Table testid="admin-consent-by-version" head={["Version", "Accounts", "Demo sessions"]} rows={versions} />
        </section>
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-[#1A1330]">How consent was given (current version)</h2>
          <Table testid="admin-consent-by-source" head={["Where", "Times"]} rows={sources} />
        </section>
        <p className="text-xs text-[#857E9C] leading-relaxed max-w-2xl" data-testid="admin-consent-note">
          &ldquo;By version&rdquo; counts each account&rsquo;s latest consent. &ldquo;How consent was given&rdquo; counts every time the
          boxes were ticked, so a person can appear more than once. These are the numbers for the site you&rsquo;re signed in to.{" "}
          <Link to="/admin/accounts" className="underline text-[#3D1A78]" data-testid="admin-consent-accounts-link">Account counts</Link>
          {" · "}
          <Link to="/admin/consent-trend" className="underline text-[#3D1A78]" data-testid="admin-consent-trend-link">Weekly consent trend</Link>
        </p>
      </div>
    </AppShell>
  );
}
