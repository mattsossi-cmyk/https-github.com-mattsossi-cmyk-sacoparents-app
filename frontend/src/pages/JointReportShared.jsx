/**
 * Public Joint Co-Parenting Summary for Professional Review — shared view.
 *
 * Anyone with the signed share link opens this page — no login. Mirrors
 * `JointAgreementShared.jsx`: renders the provenance banner + optional
 * sender note + not-a-custody-evaluation disclaimer + summary + a
 * prominent Download PDF button. Full section detail is intentionally
 * delivered via the PDF (that's the artefact mediators file); this
 * page is an at-a-glance orientation plus the download hand-off.
 *
 * URL: `/joint-report/shared/:token`
 */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Download, Loader2, ShieldAlert, Users, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { API } from "../lib/api";
import { logError } from "../lib/logger";


export default function JointReportShared() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!token) {
      setState({ loading: false, data: null, error: "missing-token" });
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API}/joint-professional-report/shared/${encodeURIComponent(token)}`,
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) setState({ loading: false, data, error: null });
      } catch (err) {
        logError("shared joint report load", err);
        if (!cancelled) {
          setState({
            loading: false, data: null,
            error: err?.message || "load-failed",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const downloadPdf = async () => {
    if (!token) return;
    setDownloading(true);
    try {
      const res = await fetch(
        `${API}/joint-professional-report/shared/${encodeURIComponent(token)}/pdf`,
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "joint-professional-report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      logError("shared joint report pdf", err);
      toast.error("Could not download PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (state.loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8F7FC] text-[#4B4567]"
        data-testid="joint-report-shared-loading"
      >
        <div className="text-center">
          <Loader2 size={22} className="animate-spin inline-block mr-2" />
          Loading the joint report…
        </div>
      </div>
    );
  }

  if (state.error || !state.data) {
    const msg = state.error === "missing-token"
      ? "This link is missing a token."
      : (typeof state.error === "string" && state.error.length > 2
          ? state.error
          : "We couldn't open this shared link.");
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8F7FC] px-6 py-10"
        data-testid="joint-report-shared-error"
      >
        <div className="max-w-lg w-full rounded-3xl border border-[#E5E0EE] bg-white p-8 text-center shadow-sm">
          <h1 className="font-serif text-2xl text-[#1A1330] mb-3">
            Joint Co-Parenting Summary
          </h1>
          <p className="text-[#4B4567] leading-relaxed mb-5">{msg}</p>
          <p className="text-xs text-[#857E9C]">
            If you were sent this link, please ask the parent who shared
            it to generate a fresh link from their SA CoParents account.
          </p>
        </div>
      </div>
    );
  }

  const d = state.data;
  const parentA = d.parent_a_name || "Parent A";
  const parentB = d.parent_b_name || "Parent B";
  const sharedBy = d.shared_by_name || parentA;
  const comparison = d.comparison_summary || d.comparison || {};
  const alignedPct = comparison.aligned_pct ?? comparison.summary?.aligned_pct ?? 0;
  const totalItems = comparison.total_items ?? comparison.summary?.total_items ?? 0;

  return (
    <div
      className="min-h-screen bg-[#F8F7FC]"
      data-testid="joint-report-shared-root"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Provenance */}
        <div
          className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-5 sm:p-6"
          data-testid="joint-report-shared-provenance"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-10 w-10 rounded-full grid place-items-center bg-[#3D1A78] text-white">
              <ExternalLink size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                Shared with you
              </div>
              <p className="mt-1 text-sm text-[#1A1330] leading-relaxed">
                <strong>{sharedBy}</strong> shared this Joint Co-Parenting
                Summary with you through SA CoParents. It is a preparation
                resource — not a custody evaluation, diagnosis, or a
                recommendation to any court.
              </p>
            </div>
          </div>
        </div>

        {/* Optional sender note */}
        {d.sender_note && (
          <div
            className="mt-4 rounded-3xl border-2 border-[#CFC1EA] bg-white p-5 sm:p-6 shadow-sm"
            data-testid="joint-report-shared-sender-note"
          >
            <div className="flex items-start gap-3">
              <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-white border-2 border-[#3D1A78] text-[#3D1A78] font-serif text-sm font-bold">
                &ldquo;
              </div>
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                  A note from {sharedBy}
                </div>
                <p className="text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap">
                  {d.sender_note}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              {d.report_type ? d.report_type.replace(/_/g, " ") : "Joint report"}
            </div>
            <h1
              className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight"
              data-testid="joint-report-shared-title"
            >
              {d.report_title}
            </h1>
            <div
              className="mt-2 text-sm text-[#4B4567]"
              data-testid="joint-report-shared-parents"
            >
              {parentA} <span className="text-[#857E9C] mx-1">·</span> {parentB}
            </div>
          </div>
          <button
            type="button"
            onClick={downloadPdf}
            disabled={downloading}
            data-testid="joint-report-shared-download-pdf"
            className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
        </div>

        {/* Not-a-custody-evaluation disclaimer */}
        <div
          className="mt-5 rounded-3xl border-2 border-[#EFB4B4] bg-[#FCEDEB] p-5"
          data-testid="joint-report-shared-disclaimer"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#B02A2A] text-white">
              <ShieldAlert size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B02A2A]">
                Not a custody evaluation
              </div>
              <p className="mt-1 text-sm text-[#1A1330] leading-relaxed">
                {d.disclaimer}
              </p>
            </div>
          </div>
        </div>

        {/* At-a-glance */}
        <div
          className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-4"
          data-testid="joint-report-shared-summary"
        >
          <div className="flex items-center gap-2 mb-2">
            <Users size={14} className="text-[#3D1A78]" />
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold">
              At a glance
            </div>
          </div>
          <div className="text-sm text-[#1A1330] leading-relaxed">
            <div>
              <strong>{totalItems}</strong> items compared across both parents
            </div>
            <div className="mt-1 text-[#1F5C3B] font-semibold">
              Alignment: {alignedPct}%
            </div>
          </div>
        </div>

        {/* Section titles — full narrative is in the PDF */}
        {Array.isArray(d.section_order) && d.section_order.length > 0 && (
          <div
            className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-5"
            data-testid="joint-report-shared-sections-outline"
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold mb-3">
              Sections in the full report
            </div>
            <ul className="space-y-1.5 text-sm text-[#1A1330]">
              {d.section_order.map((s) => (
                <li key={s.key || s.title} className="flex items-start gap-2">
                  <span className="text-[#3D1A78]">•</span>
                  <span>{s.title || s.key}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-[#4B4567] leading-relaxed">
              This shared view is an at-a-glance orientation. Download the PDF
              above for the full section-by-section narrative, row strips
              (Parent A · Parent B · Alignment · Child&rsquo;s need · Issue),
              and any TISFL Parenting-Plan Implications.
            </p>
          </div>
        )}

        <div className="mt-10 text-[11px] text-[#857E9C] leading-relaxed border-t border-[#E5E0EE] pt-4">
          Preparation resource · Not a custody evaluation, diagnosis, or
          recommendation to any court. Rendered via a signed link the
          sending parent created; the link can be revoked at any time
          from their account. Share ID {d.share_id}.
        </div>
      </div>
    </div>
  );
}
