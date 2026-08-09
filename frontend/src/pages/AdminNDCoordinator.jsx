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
  Loader2, ShieldAlert, Users, AlertTriangle, ArrowLeft, Mail, X,
  ChevronRight, Clock, MailCheck, MailX,
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
  const [drilldown, setDrilldown] = useState({ open: false, targetId: null, targetName: "" });

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
                      className="border-t border-[#F0EBF7] first:border-t-0"
                    >
                      <button
                        type="button"
                        onClick={() => setDrilldown({
                          open: true,
                          targetId: c.target_user_id,
                          targetName: c.target_name,
                        })}
                        data-testid={`admin-nd-case-${c.assessment_id}`}
                        data-target-id={c.target_user_id}
                        className="w-full text-left px-4 sm:px-5 py-3 flex flex-wrap items-center gap-3 hover:bg-[#F8F7FC] transition-colors focus:outline-none focus:bg-[#F5F1FB]"
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
                        <ChevronRight size={16} className="text-[#857E9C]" />
                      </button>
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

      <CaseDrilldown
        open={drilldown.open}
        targetUserId={drilldown.targetId}
        fallbackName={drilldown.targetName}
        onClose={() => setDrilldown({ open: false, targetId: null, targetName: "" })}
      />
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


function CaseDrilldown({ open, targetUserId, fallbackName, onClose }) {
  const [state, setState] = useState({ loading: false, data: null, error: null });

  useEffect(() => {
    if (!open || !targetUserId) return undefined;
    let cancelled = false;
    setState({ loading: true, data: null, error: null });
    (async () => {
      try {
        const res = await api.get(
          `/admin/nd-risk-coordinator/case/${encodeURIComponent(targetUserId)}`
        );
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("admin nd case drilldown", err);
        if (!cancelled) {
          setState({
            loading: false,
            data: null,
            error: err?.response?.data?.detail
              || "Couldn't load this parent's case history.",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [open, targetUserId]);

  // Close on Escape key while the panel is open.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const d = state.data;
  const name = d?.target_name || fallbackName || "Parent";

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      data-testid="admin-nd-drilldown-root"
      role="dialog"
      aria-modal="true"
      aria-label="Case history"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        data-testid="admin-nd-drilldown-overlay"
      />
      <aside
        className="relative bg-white h-full w-full sm:max-w-xl shadow-2xl border-l border-[#E5E0EE] overflow-y-auto"
        data-testid="admin-nd-drilldown-panel"
      >
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-[#F0EBF7] px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Case history
            </div>
            <h2 className="font-serif text-xl text-[#1A1330] leading-snug truncate mt-0.5"
              data-testid="admin-nd-drilldown-name">
              {name}
            </h2>
            {d?.assessment_count > 0 && (
              <p className="text-[11px] text-[#4B4567] mt-0.5"
                data-testid="admin-nd-drilldown-count">
                {d.assessment_count} assessment{d.assessment_count === 1 ? "" : "s"} on file
                {d.alerts?.length > 0 && (
                  <> · {d.alerts.length} coordinator alert{d.alerts.length === 1 ? "" : "s"}</>
                )}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close case history"
            data-testid="admin-nd-drilldown-close"
            className="shrink-0 w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-5">
          {state.loading && (
            <div className="inline-flex items-center gap-2 text-sm text-[#4B4567]"
              data-testid="admin-nd-drilldown-loading">
              <Loader2 size={14} className="animate-spin" /> Loading case history…
            </div>
          )}

          {state.error && (
            <div className="rounded-2xl border border-[#EFB4B4] bg-[#FCEDEB] p-3 text-sm text-[#B02A2A]"
              data-testid="admin-nd-drilldown-error">
              {state.error}
            </div>
          )}

          {d && (
            <>
              {d.alerts?.length > 0 && (
                <section className="mb-6" data-testid="admin-nd-drilldown-alerts">
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                    Coordinator alert audit
                  </div>
                  <ul className="space-y-1.5">
                    {d.alerts.map((a) => {
                      const meta = TIER_META[a.tier] || TIER_META.low;
                      return (
                        <li key={a.assessment_id + a.created_at}
                          className="flex items-center gap-3 text-xs text-[#4B4567]">
                          {a.email_ok
                            ? <MailCheck size={14} className="text-[#1F5C3B]" />
                            : <MailX size={14} className="text-[#B02A2A]" />}
                          <span
                            className="text-[9px] uppercase tracking-[0.16em] font-bold px-1.5 py-0.5 rounded-full"
                            style={{
                              background: meta.bg,
                              color: meta.ink,
                              border: `1px solid ${meta.border}`,
                            }}
                          >
                            {meta.label}
                          </span>
                          <span>
                            {a.email_ok ? "Delivered" : "Send failed"}
                            {" · "}
                            {formatWhen(a.created_at)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}

              <section data-testid="admin-nd-drilldown-history">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                  Assessments · newest first
                </div>
                <ol className="space-y-3">
                  {d.history.map((h, idx) => {
                    const meta = TIER_META[h.tier] || TIER_META.low;
                    const isLatest = idx === 0;
                    return (
                      <li
                        key={h.assessment_id}
                        data-testid={`admin-nd-drilldown-row-${h.assessment_id}`}
                        className="rounded-2xl border p-4"
                        style={{
                          background: isLatest ? meta.bg : "#FFFFFF",
                          borderColor: isLatest ? meta.border : "#E5E0EE",
                        }}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className="text-[10px] uppercase tracking-[0.16em] font-bold px-2 py-1 rounded-full"
                            style={{
                              background: "#fff",
                              color: meta.ink,
                              border: `1px solid ${meta.border}`,
                            }}
                          >
                            {meta.label}
                          </span>
                          {isLatest && (
                            <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                              Latest
                            </span>
                          )}
                          <span className="text-[11px] text-[#4B4567] inline-flex items-center gap-1 ml-auto">
                            <Clock size={11} /> {formatWhen(h.created_at)}
                          </span>
                        </div>
                        <div className="mt-2 text-sm text-[#1A1330]">
                          <span className="font-semibold">Score {h.total_score}</span>
                          {" · "}
                          Threat {h.threat_score} · Vulnerability {h.vulnerability_score}
                        </div>
                        {h.coparent_name && (
                          <div className="text-[11px] text-[#4B4567] mt-0.5">
                            Co-parent: {h.coparent_name}
                          </div>
                        )}
                        {h.sub_scores && (h.sub_scores.threat || h.sub_scores.vulnerability) && (
                          <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-[#4B4567]">
                            {h.sub_scores.threat && (
                              <div>
                                <div className="uppercase tracking-[0.16em] text-[9px] font-bold text-[#3D1A78] mb-1">
                                  Threat sub-scores
                                </div>
                                {Object.entries(h.sub_scores.threat).map(([k, v]) => (
                                  <div key={k} className="flex justify-between">
                                    <span className="truncate mr-2">
                                      {k.replace(/^threat_/, "").replaceAll("_", " ")}
                                    </span>
                                    <span className="tabular-nums font-semibold text-[#1A1330]">{v}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            {h.sub_scores.vulnerability && (
                              <div>
                                <div className="uppercase tracking-[0.16em] text-[9px] font-bold text-[#3D1A78] mb-1">
                                  Vulnerability sub-scores
                                </div>
                                {Object.entries(h.sub_scores.vulnerability).map(([k, v]) => (
                                  <div key={k} className="flex justify-between">
                                    <span className="truncate mr-2">
                                      {k.replace(/^vuln_/, "").replaceAll("_", " ")}
                                    </span>
                                    <span className="tabular-nums font-semibold text-[#1A1330]">{v}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        {h.notes && (
                          <div className="mt-3 rounded-xl bg-white/70 border border-[#E5E0EE] p-2 text-[11px] text-[#4B4567] italic">
                            &ldquo;{h.notes}&rdquo;
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
