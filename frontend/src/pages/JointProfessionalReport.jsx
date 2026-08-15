/**
 * Joint Co-Parenting Summary for Professional Review.
 *
 * Consent-gated by an active Compare share. Loads the 9-section neutral
 * report from `/api/joint-professional-report/{share_id}` and renders
 * a professional-facing layout with a prominent NOT-A-CUSTODY-EVALUATION
 * disclaimer, Parent A | Parent B | Alignment | Child's Need | Issue
 * strips for every row, and a Download PDF button.
 *
 * The parent reaches this page from three entry points:
 *   1. Dashboard "Your Reports" card (once a Compare share is active)
 *   2. Pathway Report page (dual view)
 *   3. SNC v2 comparison result page
 *
 * Query params:
 *   ?share=<share_id>   Required. The active Compare share the report
 *                       should aggregate. Server-side enforces that
 *                       the caller is a participant.
 */
import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Download, Loader2, ShieldAlert, ScrollText, Users, Info,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api, API } from "../lib/api";
import { logError } from "../lib/logger";

const ALIGNMENT_STYLE = {
  aligned:        { bg: "#EAF7F0", border: "#B5DFC5", text: "#1F5C3B" },
  close:          { bg: "#FFF9EB", border: "#E4D8B8", text: "#8A6B12" },
  divergent:      { bg: "#FCEDEB", border: "#EFB4B4", text: "#B02A2A" },
  one_only:       { bg: "#F1EEF7", border: "#D6CFE8", text: "#4B4567" },
  insufficient:   { bg: "#F1EEF7", border: "#D6CFE8", text: "#4B4567" },
  both_responded: { bg: "#EFE9F9", border: "#D6CFE8", text: "#3D1A78" },
};

const SECTION_ORDER = [
  { key: "shared_priorities",              icon: Users,      colour: "#3D1A78" },
  { key: "medical",                        icon: ShieldAlert, colour: "#B02A2A" },
  { key: "educational",                    icon: ScrollText, colour: "#3D1A78" },
  { key: "psychological",                  icon: ScrollText, colour: "#2DB5B5" },
  { key: "household_consistency",          icon: Info,       colour: "#8A6B12" },
  { key: "communication_concerns",         icon: Info,       colour: "#8A6B12" },
  { key: "areas_of_agreement",             icon: Users,      colour: "#2DB5B5" },
  { key: "areas_where_perceptions_differ", icon: ShieldAlert, colour: "#B02A2A" },
  { key: "issues_for_professional_discussion", icon: Info,   colour: "#8A6B12" },
];

function AlignmentPill({ alignment, label }) {
  const style = ALIGNMENT_STYLE[alignment] || ALIGNMENT_STYLE.insufficient;
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider"
      style={{
        backgroundColor: style.bg,
        border: `1px solid ${style.border}`,
        color: style.text,
      }}
      data-testid={`joint-alignment-${alignment}`}
    >
      {label}
    </span>
  );
}

function ReportRow({ row, parentAName, parentBName }) {
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 space-y-3"
      data-testid="joint-report-row"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="font-serif text-lg text-[#1A1330] leading-snug">
            {row.topic}
          </div>
          {row.pathway_label && (
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#857E9C] mt-0.5">
              {row.pathway_label}
            </div>
          )}
        </div>
        <AlignmentPill alignment={row.alignment} label={row.alignment_label} />
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="rounded-xl bg-[#F7F4FC] p-3">
          <div className="text-[11px] uppercase tracking-wider text-[#3D1A78] font-semibold mb-1">
            {parentAName}
          </div>
          <div className="text-sm text-[#1A1330] whitespace-pre-line">
            {row.parent_a?.summary || "No response"}
          </div>
        </div>
        <div className="rounded-xl bg-[#EAF7F7] p-3">
          <div className="text-[11px] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-1">
            {parentBName}
          </div>
          <div className="text-sm text-[#1A1330] whitespace-pre-line">
            {row.parent_b?.summary || "No response"}
          </div>
        </div>
      </div>

      {row.childs_need && (
        <div className="text-sm">
          <span className="text-[11px] uppercase tracking-wider text-[#3D1A78] font-semibold mr-2">
            Child's need
          </span>
          <span className="text-[#1A1330]">{row.childs_need}</span>
        </div>
      )}
      {row.issue_for_discussion && (
        <div className="text-sm border-l-4 border-[#D6A374] pl-3">
          <div className="text-[11px] uppercase tracking-wider text-[#A26852] font-semibold mb-0.5">
            For discussion
          </div>
          <div className="text-[#1A1330] italic">{row.issue_for_discussion}</div>
        </div>
      )}
    </div>
  );
}

function Section({ meta, section, parentAName, parentBName }) {
  const { icon: Icon, colour } = meta;
  return (
    <section
      className="mt-8"
      data-testid={`joint-report-section-${meta.key}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="w-8 h-8 rounded-full grid place-items-center shrink-0"
          style={{ backgroundColor: `${colour}15`, color: colour }}
        >
          <Icon size={16} />
        </span>
        <h2
          className="font-serif text-2xl text-[#1A1330]"
          data-testid={`joint-report-section-title-${meta.key}`}
        >
          {section.title}
        </h2>
        <span className="text-xs text-[#857E9C]">
          {section.row_count} {section.row_count === 1 ? "item" : "items"}
        </span>
      </div>
      {section.description && (
        <p className="text-sm text-[#4B4567] mb-4 leading-relaxed max-w-3xl">
          {section.description}
        </p>
      )}
      {section.rows && section.rows.length > 0 ? (
        <div className="space-y-3">
          {section.rows.map((row, i) => (
            <ReportRow
              key={`${meta.key}-${i}`}
              row={row}
              parentAName={parentAName}
              parentBName={parentBName}
            />
          ))}
        </div>
      ) : (
        <div
          className="rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] p-4 text-sm text-[#4B4567] italic"
          data-testid={`joint-report-empty-${meta.key}`}
        >
          {section.empty_reason || "No data available for this section."}
        </div>
      )}
    </section>
  );
}

export default function JointProfessionalReport() {
  const [params] = useSearchParams();
  const shareId = params.get("share");
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!shareId) {
      setState({ loading: false, data: null, error: "missing-share" });
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(
          `/joint-professional-report/${encodeURIComponent(shareId)}`,
        );
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("joint report load", err);
        if (!cancelled) {
          setState({
            loading: false,
            data: null,
            error: err?.response?.data?.detail || "load-failed",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [shareId]);

  const downloadPdf = async () => {
    if (!shareId) return;
    setDownloading(true);
    try {
      const res = await fetch(
        `${API}/joint-professional-report/${encodeURIComponent(shareId)}/pdf`,
        { credentials: "include" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `joint-professional-report-${shareId.slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      logError("joint report pdf", err);
      toast.error("Could not download PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (state.loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-8 text-center text-[#4B4567]"
             data-testid="joint-report-loading">
          <Loader2 size={20} className="animate-spin inline-block mr-2" />
          Assembling the joint report...
        </div>
      </AppShell>
    );
  }

  if (state.error === "missing-share") {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto p-8"
             data-testid="joint-report-missing-share">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-4">
            Joint Co-Parenting Summary
          </h1>
          <p className="text-[#4B4567] mb-6 leading-relaxed">
            This report is only available once both parents have completed the
            Special Needs Co-Parenting comparison and consented to share their
            answers. Start (or accept) a Compare invite from your Dashboard,
            then return here through the "Joint Professional Report" button.
          </p>
          <Link to="/dashboard" className="btn-sage inline-flex items-center gap-2"
                data-testid="joint-report-back-dashboard">
            <ArrowLeft size={14} /> Back to dashboard
          </Link>
        </div>
      </AppShell>
    );
  }

  if (state.error || !state.data) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto p-8" data-testid="joint-report-error">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-4">
            Joint Co-Parenting Summary
          </h1>
          <p className="text-[#4B4567] leading-relaxed mb-4">
            {typeof state.error === "string" && state.error.length > 2
              ? state.error
              : "We couldn't load this report. It may not be ready yet — both parents need to complete their assessments and consent to comparison first."}
          </p>
          <Link to="/dashboard" className="btn-soft inline-flex items-center gap-2">
            <ArrowLeft size={14} /> Back to dashboard
          </Link>
        </div>
      </AppShell>
    );
  }

  const d = state.data;
  const parentA = d.parent_a_name || "Parent A";
  const parentB = d.parent_b_name || "Parent B";

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10"
        data-testid="joint-report-root"
      >
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78]"
          >
            <ArrowLeft size={12} /> Back to dashboard
          </Link>
          <button
            type="button"
            onClick={downloadPdf}
            disabled={downloading}
            data-testid="joint-report-download-pdf"
            className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
        </div>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          {d.report_type ? d.report_type.replace(/_/g, " ") : "Joint report"}
        </div>
        <h1
          className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight"
          data-testid="joint-report-title"
        >
          {d.report_title}
        </h1>
        <div className="mt-2 text-sm text-[#4B4567]" data-testid="joint-report-parents">
          {parentA} <span className="text-[#857E9C] mx-1">·</span> {parentB}
        </div>

        {/* NOT-A-CUSTODY-EVALUATION disclaimer — prominent, red. */}
        <div
          className="mt-5 rounded-3xl border-2 border-[#EFB4B4] bg-[#FCEDEB] p-5"
          data-testid="joint-report-disclaimer"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#B02A2A] text-white">
              <ShieldAlert size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B02A2A]">
                This is not a custody evaluation
              </div>
              <p className="mt-1 text-sm text-[#1A1330] leading-relaxed">
                {d.disclaimer}
              </p>
            </div>
          </div>
        </div>

        {/* Neutral-language + safety-privacy caveats. */}
        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <div
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4 text-xs text-[#4B4567] leading-relaxed"
            data-testid="joint-report-neutral-note"
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold mb-1">
              Neutral language
            </div>
            {d.neutral_language_note}
          </div>
          <div
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4 text-xs text-[#4B4567] leading-relaxed"
            data-testid="joint-report-safety-note"
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold mb-1">
              Safety-screen privacy
            </div>
            {d.safety_privacy_note}
          </div>
        </div>

        {SECTION_ORDER.map((meta) => {
          const section = d.sections?.[meta.key];
          if (!section) return null;
          return (
            <Section
              key={meta.key}
              meta={meta}
              section={section}
              parentAName={parentA}
              parentBName={parentB}
            />
          );
        })}

        <div className="mt-12 text-[11px] text-[#857E9C] leading-relaxed border-t border-[#E5E0EE] pt-4">
          Preparation resource · Not a custody evaluation, diagnosis, or
          recommendation to any court. Share ID {d.share_id}.
        </div>
      </div>
    </AppShell>
  );
}
