import React, { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ShieldCheck, Users } from "lucide-react";

import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

const Stat = ({ label, value, sub, testid }) => (
  <div className="rounded-2xl border border-[#E5E0EE] bg-white p-5" data-testid={testid}>
    <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#857E9C]">{label}</div>
    <div className="font-serif text-4xl text-[#1A1330] mt-1 tabular-nums" data-testid={`${testid}-value`}>{value ?? "–"}</div>
    {sub && <div className="text-xs text-[#4B4567] mt-1">{sub}</div>}
  </div>
);

// Admin-only, counts only: no names or emails are ever fetched here.
export default function AdminAccountCounts() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!user) return;
    api.get("/analytics/admin/account-counts").then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.status === 403 ? "forbidden" : "error"));
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center max-w-lg mx-auto" data-testid="admin-counts-forbidden">
          <ShieldCheck size={20} className="mx-auto text-[#B6663B] mb-3" />
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">This page is restricted to the SA CoParents app owner.</p>
        </div>
      </AppShell>
    );
  }
  if (!data && !err) return null;
  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-1 py-6" data-testid="admin-counts-page">
        <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
          <Users size={12} /> Accounts · counts only
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] mt-2">How many accounts</h1>
        {err === "error" && <p className="text-sm text-[#B02A2A] mt-4" data-testid="admin-counts-error">Couldn&rsquo;t load the counts. Please refresh.</p>}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          <Stat label="Total accounts" value={data?.total} testid="admin-counts-total" />
          <Stat label="Parents" value={data?.parents} testid="admin-counts-parents" />
          <Stat label="Professionals" value={data?.professionals} testid="admin-counts-professionals" />
          <Stat label="New · last 30 days" value={data?.created_last_30_days} testid="admin-counts-new30"
            sub={data ? `${data.created_last_30_days_parents} parents · ${data.created_last_30_days_professionals} professionals` : null} />
        </div>
        <p className="text-xs text-[#857E9C] mt-5 leading-relaxed max-w-2xl" data-testid="admin-counts-note">
          Accounts have no role field, so &ldquo;professional&rdquo; means an account that has created a court code or joint case;
          every other account counts as a parent. Guest sessions ({data?.guest_sessions ?? "–"}) aren&rsquo;t included.
          These are the numbers for the site you&rsquo;re signed in to.{" "}
          <Link to="/admin/consent" className="underline text-[#3D1A78]" data-testid="admin-counts-consent-link">Consent counts</Link>
          {" · "}
          <Link to="/admin/consent-trend" className="underline text-[#3D1A78]" data-testid="admin-counts-trend-link">Weekly consent trend</Link>
        </p>
      </div>
    </AppShell>
  );
}
