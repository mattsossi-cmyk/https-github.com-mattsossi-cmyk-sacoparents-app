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
  ChevronRight, Clock, MailCheck, MailX, Download,
} from "lucide-react";
import { toast } from "sonner";
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
  const [windowDays, setWindowDays] = useState(null);  // null = "All history"

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true }));
    (async () => {
      try {
        const path = windowDays
          ? `/admin/nd-risk-coordinator?window_days=${windowDays}`
          : "/admin/nd-risk-coordinator";
        const res = await api.get(path);
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
  }, [windowDays]);

  if (state.loading && !state.data) {
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
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
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

        <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
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

        {/* Trailing-days filter — hides stale risk without archiving data */}
        <div className="mt-5" data-testid="admin-nd-coordinator-window-filter">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2 inline-flex items-center gap-1.5">
            <Clock size={12} />
            Time window
            {state.loading && (
              <Loader2 size={11} className="animate-spin ml-1" />
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {[
              { key: null, label: "All history" },
              { key: 30,   label: "Last 30 days" },
              { key: 60,   label: "Last 60 days" },
              { key: 90,   label: "Last 90 days" },
              { key: 180,  label: "Last 6 months" },
            ].map((opt) => {
              const active = windowDays === opt.key;
              return (
                <button
                  key={String(opt.key)}
                  type="button"
                  onClick={() => setWindowDays(opt.key)}
                  disabled={state.loading}
                  data-testid={`admin-nd-window-${opt.key ?? "all"}`}
                  aria-pressed={active}
                  className={`text-[0.75rem] px-3 py-1.5 rounded-full border transition ${
                    active
                      ? "bg-[#3D1A78] text-white border-[#3D1A78] font-semibold shadow-sm"
                      : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78] hover:text-[#3D1A78]"
                  } disabled:opacity-60`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

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
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Threat × Vulnerability heat map
          </div>
          {totalParents === 0 ? (
            <div className="rounded-2xl border border-[#E5E0EE] bg-white p-6 text-sm text-[#4B4567]"
              data-testid="admin-nd-coordinator-empty">
              {windowDays
                ? `No parents completed an ND Risk Assessment in the last ${windowDays} days. Widen the time window or clear the filter to see older data.`
                : "No parents have completed an ND Risk Assessment yet. When they do, their latest assessment will appear here."}
            </div>
          ) : (
            <div tabIndex={0} role="region" aria-label="Scrollable table" className="rounded-3xl border border-[#E5E0EE] bg-white p-4 sm:p-6 overflow-x-auto">
              <div className="min-w-[420px]">
                <div className="flex items-end gap-1 mb-1">
                  <div className="w-12" />
                  <div className="text-[0.625rem] uppercase tracking-[0.18em] text-[#4B4567] flex-1 text-center">
                    Threat score →
                  </div>
                </div>
                <div className="flex gap-1">
                  <div className="w-12 flex flex-col justify-between text-[0.625rem] uppercase tracking-[0.14em] text-[#4B4567] py-1">
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
                            <div className="text-[0.5625rem] uppercase tracking-[0.12em] font-bold"
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
                <div className="flex flex-wrap items-center gap-3 mt-4 text-[0.6875rem] text-[#4B4567]">
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
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Active cases · High &amp; Critical
          </div>
          {active.length === 0 ? (
            <div className="rounded-2xl border border-[#B5DFC5] bg-[#F1F9F4] p-4 text-sm text-[#1F5C3B]"
              data-testid="admin-nd-coordinator-no-active">
              {windowDays
                ? `No high or critical cases in the last ${windowDays} days.`
                : "No high or critical cases right now."}
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
                          className="text-[0.625rem] uppercase tracking-[0.16em] font-bold px-2 py-1 rounded-full"
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
                          <div className="text-[0.6875rem] text-[#4B4567] truncate">
                            Co-parent: {c.coparent_name || "—"}
                            {" · "}
                            Score {c.total_score} (T{c.threat_score}·V{c.vulnerability_score})
                            {" · "}
                            {formatWhen(c.created_at)}
                          </div>
                        </div>
                        <ChevronRight size={16} className="text-[#6E6787]" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </section>

        <p className="text-[0.6875rem] text-[#4B4567] italic mt-8">
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
      <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] inline-flex items-center gap-1.5">
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
  const [pdfBusy, setPdfBusy] = useState(false);

  const downloadPdf = async () => {
    if (!targetUserId || pdfBusy) return;
    setPdfBusy(true);
    try {
      const res = await api.get(
        `/admin/nd-risk-coordinator/case/${encodeURIComponent(targetUserId)}/pdf`,
        { responseType: "blob" },
      );
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nd-case-history-${targetUserId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Case history PDF downloaded.");
    } catch (err) {
      logError("admin nd case pdf", err);
      toast.error(err?.response?.data?.detail || "Couldn't build the case PDF right now.");
    } finally {
      setPdfBusy(false);
    }
  };

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
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Case history
            </div>
            <h2 className="font-serif text-xl text-[#1A1330] leading-snug truncate mt-0.5"
              data-testid="admin-nd-drilldown-name">
              {name}
            </h2>
            {d?.assessment_count > 0 && (
              <p className="text-[0.6875rem] text-[#4B4567] mt-0.5"
                data-testid="admin-nd-drilldown-count">
                {d.assessment_count} assessment{d.assessment_count === 1 ? "" : "s"} on file
                {d.alerts?.length > 0 && (
                  <> · {d.alerts.length} coordinator alert{d.alerts.length === 1 ? "" : "s"}</>
                )}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {d && d.assessment_count > 0 && (
              <button
                type="button"
                onClick={downloadPdf}
                disabled={pdfBusy}
                data-testid="admin-nd-drilldown-pdf"
                aria-label="Download case history PDF"
                className="inline-flex items-center gap-1.5 h-9 px-3 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white text-xs font-semibold disabled:opacity-60"
              >
                {pdfBusy
                  ? <Loader2 size={12} className="animate-spin" />
                  : <Download size={12} />}
                <span className="hidden sm:inline">
                  {pdfBusy ? "Building…" : "Court-ready PDF"}
                </span>
              </button>
            )}
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
                  <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
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
                            className="text-[0.5625rem] uppercase tracking-[0.16em] font-bold px-1.5 py-0.5 rounded-full"
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

              {d.history.length >= 2 && (
                <TierSparkline history={d.history} />
              )}

              <section data-testid="admin-nd-drilldown-history">
                <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
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
                            className="text-[0.625rem] uppercase tracking-[0.16em] font-bold px-2 py-1 rounded-full"
                            style={{
                              background: "#fff",
                              color: meta.ink,
                              border: `1px solid ${meta.border}`,
                            }}
                          >
                            {meta.label}
                          </span>
                          {isLatest && (
                            <span className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                              Latest
                            </span>
                          )}
                          <span className="text-[0.6875rem] text-[#4B4567] inline-flex items-center gap-1 ml-auto">
                            <Clock size={11} /> {formatWhen(h.created_at)}
                          </span>
                        </div>
                        <div className="mt-2 text-sm text-[#1A1330]">
                          <span className="font-semibold">Score {h.total_score}</span>
                          {" · "}
                          Threat {h.threat_score} · Vulnerability {h.vulnerability_score}
                        </div>
                        {h.coparent_name && (
                          <div className="text-[0.6875rem] text-[#4B4567] mt-0.5">
                            Co-parent: {h.coparent_name}
                          </div>
                        )}
                        {h.sub_scores && (h.sub_scores.threat || h.sub_scores.vulnerability) && (
                          <div className="mt-3 grid grid-cols-2 gap-2 text-[0.6875rem] text-[#4B4567]">
                            {h.sub_scores.threat && (
                              <div>
                                <div className="uppercase tracking-[0.16em] text-[0.5625rem] font-bold text-[#3D1A78] mb-1">
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
                                <div className="uppercase tracking-[0.16em] text-[0.5625rem] font-bold text-[#3D1A78] mb-1">
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
                          <div className="mt-3 rounded-xl bg-white/70 border border-[#E5E0EE] p-2 text-[0.6875rem] text-[#4B4567] italic">
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



/**
 * TierSparkline — inline SVG showing total_score (0..16) over time for
 * every assessment in the parent's history. Renders chronologically
 * (oldest → newest) even though the API returns newest-first. Points
 * are coloured by tier; the connecting line uses the app's neutral
 * indigo so a viewer instinctively focuses on the coloured dots. Only
 * rendered when the parent has ≥2 assessments — a single point on a
 * chart says nothing about escalation.
 *
 * Deliberately pure SVG (no chart lib) — the drawer must stay light so
 * an admin scanning through active cases doesn't wait on chart bundle
 * chunks between clicks.
 */
function TierSparkline({ history }) {
  const rows = [...history].reverse();
  const total = rows.length;
  const w = 320;
  const h = 90;
  const padX = 8;
  const padY = 10;
  const maxScore = 16;

  const xs = rows.map((_, i) =>
    total > 1
      ? padX + ((w - 2 * padX) * i) / (total - 1)
      : w / 2,
  );
  const ys = rows.map((r) => {
    const s = Number(r.total_score ?? 0);
    const clamped = Math.max(0, Math.min(maxScore, s));
    return padY + (h - 2 * padY) * (1 - clamped / maxScore);
  });
  const linePath = xs
    .map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`)
    .join(" ");

  const latest = rows[rows.length - 1] || {};
  const first  = rows[0] || {};
  const scoreDelta = (Number(latest.total_score ?? 0)) - (Number(first.total_score ?? 0));
  const deltaTone =
    scoreDelta > 0 ? { arrow: "\u2191", color: "#B02A2A", verb: "up" } :
    scoreDelta < 0 ? { arrow: "\u2193", color: "#1F5C3B", verb: "down" } :
                     { arrow: "\u2192", color: "#4B4567", verb: "unchanged" };

  return (
    <section
      className="mb-6 rounded-2xl border border-[#E5E0EE] bg-white p-4"
      data-testid="admin-nd-drilldown-sparkline"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Escalation arc
          </div>
          <div className="text-[0.6875rem] text-[#4B4567] mt-0.5">
            Total score (0-16) across {total} assessment{total === 1 ? "" : "s"}
            {total > 1 && (
              <>
                {" · "}
                <span
                  className="font-semibold"
                  style={{ color: deltaTone.color }}
                  data-testid="admin-nd-drilldown-sparkline-delta"
                >
                  {deltaTone.arrow}
                  {" "}
                  {deltaTone.verb === "unchanged"
                    ? "no change"
                    : `${deltaTone.verb} ${Math.abs(scoreDelta)}`}
                  {" since first"}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label="Assessment score history"
        className="w-full h-auto"
        data-testid="admin-nd-drilldown-sparkline-svg"
      >
        {[
          { key: "critical", min: 13, color: TIER_META.critical.bg },
          { key: "high",     min: 9,  color: TIER_META.high.bg },
          { key: "medium",   min: 4,  color: TIER_META.medium.bg },
          { key: "low",      min: 0,  color: TIER_META.low.bg },
        ].map((band, i, arr) => {
          const topY   = padY + (h - 2 * padY) * (1 - band.min / maxScore);
          const nextMax = i === 0 ? maxScore : arr[i - 1].min;
          const bottomY = padY + (h - 2 * padY) * (1 - nextMax / maxScore);
          return (
            <rect
              key={band.key}
              x={0}
              y={Math.min(topY, bottomY)}
              width={w}
              height={Math.abs(bottomY - topY)}
              fill={band.color}
              opacity="0.35"
            />
          );
        })}

        <path
          d={linePath}
          fill="none"
          stroke="#3D1A78"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {rows.map((r, i) => {
          const meta = TIER_META[r.tier] || TIER_META.low;
          return (
            <g key={r.assessment_id || i}>
              <circle
                cx={xs[i]}
                cy={ys[i]}
                r={3.5}
                fill={meta.ink}
                stroke="#FFFFFF"
                strokeWidth="1.5"
              />
              <title>
                {`${r.tier_label || r.tier || "?"} · Score ${r.total_score ?? "\u2014"} · ${r.created_at || ""}`.trim()}
              </title>
            </g>
          );
        })}
      </svg>

      <div className="flex items-center justify-between text-[0.625rem] uppercase tracking-[0.14em] text-[#4B4567] mt-1">
        <span data-testid="admin-nd-drilldown-sparkline-first">
          {(first.created_at || "").slice(0, 10) || "oldest"}
        </span>
        <span data-testid="admin-nd-drilldown-sparkline-latest">
          {(latest.created_at || "").slice(0, 10) || "newest"}
        </span>
      </div>
    </section>
  );
}
