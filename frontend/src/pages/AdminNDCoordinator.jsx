/**
 * AdminNDCoordinator — admin-only heat-map dashboard for the ND Risk
 * Assessment. Shows every parent's latest assessment as a 4x4 grid
 * (threat_score across columns, vulnerability_score down rows) with
 * per-cell counts, plus an "active cases" list of high/critical
 * assessments the coordinator should follow up on.
 *
 * Access is gated by `GET /api/admin/nd-risk-coordinator` — the backend
 * returns 403 for non-admins. This page surfaces that state gracefully
 * with an "admin-only" placeholder rather than crashing.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Loader2, ShieldAlert, Users, AlertTriangle, ArrowLeft, Mail,
} from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const TIER_META = {
  low:      { label: "Low",      bg: "#F1F9F4", border: "#B5DFC5", ink: "#1F5C3B" },
  medium:   { label: "Medium",   bg: "#FFF9EB", border: "#E4D8B8", ink: "#8A6B12" },
  high:     { label: "High",     bg: "#FCEDEB", border: "#EFB4B4", ink: "#B02A2A" },
  critical: { label: "Critical", bg: "#F8D7D7", border: "#D68B8B", ink: "#7A1A1A" },
};

const formatWhen = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch {
    return iso;
  }
};

export default function AdminNDCoordinator() {
  const [state, setState] = useState({ loading: true, data: null, error: null, forbidden: false });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/admin/nd-risk-coordinator");
        if (!cancelled) setState({ loading: false, data: res.data, error: null, forbidden: false });
      } catch (err) {
        logError("admin nd coordinator", err);
        if (!cancelled) {
          const forbidden = err?.response?.status === 403;
          setState({
            loading:  false,
            data:     null,
            forbidden,
            error:    forbidden
              ? null
              : (err?.response?.data?.detail || "Couldn't load the coordinator dashboard right now."),
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (state.loading) {
    return (
      <div className="min-h-screen bg-[#FCFBFE] px-4 py-12"
        data-testid="admin-nd-coordinator-loading">
        <div className="max-w-4xl mx-auto inline-flex items-center gap-2 text-sm text-[#4B4567]">
          <Loader2 size={14} className="animate-spin" /> Loading coordinator dashboard…
        </div>
      </div>
    );
  }

  if (state.forbidden) {
    return (
      <div className="min-h-screen bg-[#FCFBFE] px-4 py-12"
        data-testid="admin-nd-coordinator-forbidden">
        <div className="max-w-lg mx-auto rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Admin only
          </div>
          <h1 className="mt-1 font-serif text-2xl text-[#1A1330]">
            This page is restricted to platform administrators.
          </h1>
          <p className="text-sm text-[#4B4567] mt-3">
            If you believe you should have access, contact the operator
            listed on the Methodology page.
          </p>
          <Link
            to="/"
            className="inline-flex mt-5 items-center gap-1.5 text-sm text-[#3D1A78] underline"
          >
            <ArrowLeft size={12} /> Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="min-h-screen bg-[#FCFBFE] px-4 py-12"
        data-testid="admin-nd-coordinator-error">
        <div className="max-w-lg mx-auto rounded-2xl border border-[#EFB4B4] bg-[#FCEDEB] p-4 text-sm text-[#B02A2A]">
          {state.error}
        </div>
      </div>
    );
  }

  const d = state.data;
  const totalParents = d?.total_parents ?? 0;
  const activeCount = d?.active_case_count ?? 0;
  const tierCounts = d?.tier_counts || {};
  const heatmap = d?.heatmap || [];
  const active = d?.active_cases || [];
  const alerts = d?.coordinator_alerts || { total: 0, emailed: 0 };

  return (
    <div
      className="min-h-screen bg-[#FCFBFE] px-4 py-8 sm:py-12"
      data-testid="admin-nd-coordinator-root"
    >
      <div className="max-w-5xl mx-auto">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4"
          data-testid="admin-nd-coordinator-back"
        >
          <ArrowLeft size={12} /> SA CoParents home
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          Admin · ND Risk Coordinator
        </div>
        <h1 className="mt-1 font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          Active ND risk cases at a glance
        </h1>
        <p className="text-sm text-[#4B4567] mt-2 max-w-2xl leading-relaxed">
          Latest assessment per parent, bucketed on the 4×4 threat ×
          vulnerability grid. High and critical cases are surfaced
          below the map for immediate follow-up.
        </p>

        {/* KPI strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6"
          data-testid="admin-nd-coordinator-kpis">
          <Kpi testid="kpi-total-parents"
            icon={<Users size={16} />}
            label="Parents assessed" value={totalParents} />
          <Kpi testid="kpi-active-cases"
            icon={<AlertTriangle size={16} />}
            label="Active (High + Critical)" value={activeCount}
            tone={activeCount > 0 ? "danger" : "neutral"} />
          <Kpi testid="kpi-critical-count"
            icon={<ShieldAlert size={16} />}
            label="Critical" value={tierCounts.critical || 0}
            tone={(tierCounts.critical || 0) > 0 ? "danger" : "neutral"} />
          <Kpi testid="kpi-coord-alerts"
            icon={<Mail size={16} />}
            label="Coordinator emails sent" value={alerts.emailed} />
        </div>

        {/* Heat map */}
        <section className="mt-8" data-testid="admin-nd-coordinator-heatmap">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Threat × Vulnerability heat map
          </div>
          {totalParents === 0 ? (
            <div className="rounded-2xl border border-[#E5E0EE] bg-white p-6 text-sm text-[#4B4567]"
              data-testid="admin-nd-coordinator-empty">
              No parents have completed an ND Risk Assessment yet. When
              they do, their latest assessment will appear here.
            </div>
          ) : (
            <div className="rounded-3xl border border-[#E5E0EE] bg-white p-4 sm:p-6 overflow-x-auto">
              <div className="min-w-[420px]">
                <div className="flex items-end gap-1 mb-1">
                  <div className="w-12" />
                  <div className="text-[10px] uppercase tracking-[0.18em] text-[#4B4567] flex-1 text-center">
                    Threat score →
                  </div>
                </div>
                <div className="flex gap-1">
                  <div className="w-12 flex flex-col justify-between text-[10px] uppercase tracking-[0.14em] text-[#4B4567] py-1">
                    <span className="rotate-[-90deg] whitespace-nowrap origin-left translate-y-24">
                      ← Vulnerability
                    </span>
                  </div>
                  <div className="flex-1 grid grid-cols-4 gap-1">
                    {heatmap.map((row, rIdx) =>
                      row.map((cell) => {
                        const meta = TIER_META[cell.tier] || TIER_META.low;
                        const hasCases = cell.count > 0;
                        return (
                          <div
                            key={`${cell.threat}-${cell.vulnerability}`}
                            data-testid={`heatmap-cell-t${cell.threat}-v${cell.vulnerability}`}
                            className="aspect-square rounded-xl border p-1 sm:p-2 flex flex-col justify-between transition-shadow"
                            style={{
                              background: meta.bg,
                              borderColor: meta.border,
                              boxShadow: hasCases
                                ? `inset 0 0 0 2px ${meta.border}`
                                : "none",
                            }}
                            title={`Threat ${cell.threat} × Vuln ${cell.vulnerability} = ${cell.total_score} (${meta.label})`}
                          >
                            <div className="text-[9px] uppercase tracking-[0.12em] font-bold"
                              style={{ color: meta.ink }}>
                              T{cell.threat}·V{cell.vulnerability}
                            </div>
                            <div
                              className="text-xl sm:text-2xl font-bold leading-none tabular-nums text-right"
                              style={{ color: hasCases ? meta.ink : "#B4ADC7" }}
                              data-testid={`heatmap-cell-count-t${cell.threat}-v${cell.vulnerability}`}
                            >
                              {cell.count}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
                {/* Legend */}
                <div className="flex flex-wrap items-center gap-3 mt-4 text-[11px] text-[#4B4567]">
                  {["low", "medium", "high", "critical"].map((k) => {
                    const m = TIER_META[k];
                    return (
                      <span key={k} className="inline-flex items-center gap-1.5"
                        data-testid={`heatmap-legend-${k}`}>
                        <span
                          className="inline-block w-3 h-3 rounded"
                          style={{ background: m.bg, border: `1px solid ${m.border}` }}
                        />
                        {m.label} · {tierCounts[k] || 0}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Active cases */}
        <section className="mt-8" data-testid="admin-nd-coordinator-cases">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Active cases · High &amp; Critical
          </div>
          {active.length === 0 ? (
            <div className="rounded-2xl border border-[#B5DFC5] bg-[#F1F9F4] p-4 text-sm text-[#1F5C3B]"
              data-testid="admin-nd-coordinator-no-active">
              No high or critical cases right now.
            </div>
          ) : (
            <div className="rounded-3xl border border-[#E5E0EE] bg-white overflow-hidden">
              <ul>
                {active.map((c) => {
                  const meta = TIER_META[c.tier] || TIER_META.low;
                  return (
                    <li
                      key={c.assessment_id}
                      className="border-t border-[#F0EBF7] first:border-t-0 px-4 sm:px-5 py-3 flex flex-wrap items-center gap-3"
                      data-testid={`admin-nd-case-${c.assessment_id}`}
                    >
                      <span
                        className="text-[10px] uppercase tracking-[0.16em] font-bold px-2 py-1 rounded-full"
                        style={{
                          background: meta.bg,
                          color: meta.ink,
                          border: `1px solid ${meta.border}`,
                        }}
                      >
                        {meta.label}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-[#1A1330] truncate">
                          {c.target_name}
                        </div>
                        <div className="text-[11px] text-[#4B4567] truncate">
                          Co-parent: {c.coparent_name || "—"}
                          {" · "}
                          Score {c.total_score} (T{c.threat_score}·V{c.vulnerability_score})
                          {" · "}
                          {formatWhen(c.created_at)}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </section>

        <p className="text-[11px] text-[#4B4567] italic mt-8">
          Read-only overview. This dashboard aggregates the latest
          assessment per parent &mdash; historical assessments are still stored
          per-parent and remain accessible via each parent&rsquo;s account.
        </p>
      </div>
    </div>
  );
}


function Kpi({ testid, icon, label, value, tone = "neutral" }) {
  const toneCls = tone === "danger"
    ? "border-[#EFB4B4] bg-[#FCEDEB] text-[#B02A2A]"
    : "border-[#E5E0EE] bg-white text-[#1A1330]";
  return (
    <div
      data-testid={testid}
      className={`rounded-2xl border p-3 ${toneCls}`}
    >
      <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] inline-flex items-center gap-1.5">
        {icon}
        {label}
      </div>
      <div className="text-2xl font-bold tabular-nums mt-1 leading-tight">
        {value}
      </div>
    </div>
  );
}
