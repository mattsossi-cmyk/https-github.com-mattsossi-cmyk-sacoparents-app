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
import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Download, Loader2, ShieldAlert, ScrollText, Users, Info, Mail,
  Link2, Copy, Check, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import JointReportEmailDialog from "../components/JointReportEmailDialog";
import JointReportParentView from "../components/joint/JointReportParentView";
import RecentlySharedWith from "../components/joint/RecentlySharedWith";
import { requestPreShareConsent } from "../components/PreShareConsentDialog";
import { api, API } from "../lib/api";
import { downloadPdf as fetchPdfWithGracefulFailure } from "../lib/pdf";
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
  const [params, setParams] = useSearchParams();
  const shareId = params.get("share");
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [shareLinkOpen, setShareLinkOpen] = useState(false);
  const [shareLinkExpireDays, setShareLinkExpireDays] = useState(7);
  const [shareLinkNote, setShareLinkNote] = useState("");
  const [shareLinkMinting, setShareLinkMinting] = useState(false);
  const [shareLinkResult, setShareLinkResult] = useState(null);
  const [shareLinkCopied, setShareLinkCopied] = useState(false);
  const [shareLinkRevoking, setShareLinkRevoking] = useState(false);
  const shareLinkInputRef = useRef(null);

  useEffect(() => {
    if (shareLinkResult && shareLinkInputRef.current) {
      const el = shareLinkInputRef.current;
      const t = window.setTimeout(() => {
        try { el.focus(); el.select(); }
        catch (e) { logError("report share-link focus failed", e); }
      }, 60);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [shareLinkResult]);

  const openShareLink = async () => {
    const ok = await requestPreShareConsent("Joint Report link");
    if (!ok) return;
    setShareLinkResult(null);
    setShareLinkCopied(false);
    setShareLinkExpireDays(7);
    setShareLinkNote("");
    setShareLinkOpen(true);
  };

  const mintShareLink = async () => {
    if (!shareId) return;
    setShareLinkMinting(true);
    try {
      const res = await api.post(
        `/joint-professional-report/${encodeURIComponent(shareId)}/share-link`,
        {
          consent_acknowledged: true,
          expire_days: shareLinkExpireDays,
          note: (shareLinkNote || "").trim() || undefined,
        },
      );
      setShareLinkResult(res.data || null);
      toast.success("Shareable link created. Copy it below.");
    } catch (err) {
      logError("joint report share-link mint", err);
      const msg = err?.response?.data?.detail
        || "Could not create a shareable link right now. Please try again in a moment.";
      toast.error(msg);
    } finally {
      setShareLinkMinting(false);
    }
  };

  const copyShareLink = async () => {
    if (!shareLinkResult) return;
    const rel = shareLinkResult.preview_path || shareLinkResult.path;
    const fullUrl = `${window.location.origin}${rel}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setShareLinkCopied(true);
      toast.success("Link copied to clipboard.");
      window.setTimeout(() => setShareLinkCopied(false), 2200);
    } catch {
      try {
        shareLinkInputRef.current?.focus();
        shareLinkInputRef.current?.select();
      } catch (e) { logError("report share-link fallback focus", e); }
      toast.info("Press ⌘/Ctrl-C to copy — the link is already selected.");
    }
  };

  const revokeShareLink = async () => {
    if (!shareLinkResult?.jti) return;
    setShareLinkRevoking(true);
    try {
      await api.post(`/share/revoke`, { jti: shareLinkResult.jti });
      toast.success("Link revoked. Anyone with the old link will now see an expired message.");
      setShareLinkResult(null);
    } catch (err) {
      logError("joint report share-link revoke", err);
      toast.error("Could not revoke the link right now. Please try again in a moment.");
    } finally {
      setShareLinkRevoking(false);
    }
  };
  const [emailSending, setEmailSending] = useState(false);

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

  // Auto-open the mint dialog when the parent arrives with ?mint=1
  // (the Dashboard hero "Share a report" quick action). Fires once the
  // report has finished loading so the consent-gate + form dropdown
  // aren't racing the API call. We also strip the `mint` param from the
  // URL after firing so a refresh, browser-back, or PWA relaunch doesn't
  // re-open the dialog — that was the "I can't get out of the report"
  // trap reported by parents.
  const autoMintTriggered = useRef(false);
  useEffect(() => {
    if (autoMintTriggered.current) return;
    if (params.get("mint") !== "1") return;
    if (state.loading || state.error || !state.data) return;
    autoMintTriggered.current = true;
    openShareLink();
    // Remove ?mint=1 from the URL without adding a history entry.
    const next = new URLSearchParams(params);
    next.delete("mint");
    setParams(next, { replace: true });
    // openShareLink / setParams are stable — safe to omit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.loading, state.error, state.data, params]);

  const downloadPdf = async () => {
    if (!shareId) return;
    setDownloading(true);
    try {
      await fetchPdfWithGracefulFailure(
        `/joint-professional-report/${encodeURIComponent(shareId)}/pdf`,
        {
          filename: `joint-professional-report-${shareId.slice(0, 10)}.pdf`,
          testid: "joint-report-download",
        },
      );
    } finally {
      setDownloading(false);
    }
  };

  const sendEmail = async (payload) => {
    if (!shareId) return;
    setEmailSending(true);
    try {
      const res = await api.post(
        `/joint-professional-report/${encodeURIComponent(shareId)}/email`,
        payload,
      );
      const emailed = res.data?.emailed_to || payload.recipient_email;
      toast.success(`Joint report emailed to ${emailed}.`);
      setEmailOpen(false);
    } catch (err) {
      logError("joint report email", err);
      const msg = err?.response?.data?.detail
        || "Could not send the joint report right now. Please try again in a moment.";
      toast.error(msg);
    } finally {
      setEmailSending(false);
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
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={`${API}/joint-professional-report/professional-intro.pdf`}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="joint-report-download-intro"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#857E9C] text-[#4B4567] px-4 py-2 text-sm font-semibold hover:bg-[#F8F7FC] transition-colors"
              title="Download the 3-minute Introduction to SA CoParents for professionals."
            >
              <Info size={14} /> 3-min professional intro
            </a>
            <Link
              to={`/joint-agreement?share=${encodeURIComponent(shareId)}`}
              data-testid="joint-report-open-agreement"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#2DB5B5] text-[#2DB5B5] px-4 py-2 text-sm font-semibold hover:bg-[#EAF7F7] transition-colors"
              title="Open the Joint Alignment Agreement — merged from both parents' individual drafts."
            >
              <ScrollText size={14} /> Joint Alignment Agreement
            </Link>
            <button
              type="button"
              onClick={openShareLink}
              data-testid="joint-report-share-link-open"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5F1FB] transition-colors"
              title="Create a link a mediator or attorney can open in-browser to view this Joint Alignment Report — no login required."
            >
              <Link2 size={14} /> Get shareable link
            </button>
            <button
              type="button"
              onClick={() => setEmailOpen(true)}
              data-testid="joint-report-email-open"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5F1FB] transition-colors"
              title="Email this Joint Alignment Report to a mediator, attorney, court, or therapist."
            >
              <Mail size={14} /> Email to professional
            </button>
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
        </div>

        <div className="mt-4">
          <RecentlySharedWith
            shareId={shareId}
            artefactBase="joint-professional-report"
            artefactLabel="Joint Report"
          />
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
        <p
          className="mt-2 text-xs text-[#4B4567] max-w-2xl leading-relaxed"
          data-testid="joint-report-parent-facing-subline"
        >
          This is your <strong>Joint Alignment Report</strong> — send it to
          your mediator or attorney. Your co-parent sees the same version.
        </p>
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

        {/* Primary presentation — parent-friendly 5-bucket view.
            Replaces the row-strip sections as the default layout for
            everyone (parents AND professionals). The row-strip lives
            below as a collapsible "Detailed Comparison" appendix. */}
        <div className="mt-6">
          <JointReportParentView parentView={d.parent_view} />
        </div>

        <details
          className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white/60 overflow-hidden"
          data-testid="joint-report-detailed-comparison"
        >
          <summary className="cursor-pointer px-5 py-4 flex items-center justify-between gap-3 hover:bg-white/80 transition-colors">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                For attorneys, mediators &amp; therapists
              </div>
              <div className="font-serif text-lg text-[#1A1330] mt-0.5">
                Detailed Comparison
              </div>
            </div>
            <span className="text-xs text-[#857E9C] font-semibold">
              Click to expand
            </span>
          </summary>
          <div className="px-5 pb-6 pt-2 border-t border-[#E5E0EE]">
            <p className="text-xs text-[#4B4567] leading-relaxed mb-4 mt-3 max-w-3xl">
              The row-strip layout below is written in clinical, non-adjudicative
              language for professional review. Each row shows Parent A · Parent B
              · Alignment · Child&rsquo;s need · Issue for the same underlying data
              summarised in the buckets above.
            </p>
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
          </div>
        </details>

        <div className="mt-12 text-[11px] text-[#857E9C] leading-relaxed border-t border-[#E5E0EE] pt-4">
          Preparation resource · Not a custody evaluation, diagnosis, or
          recommendation to any court. Share ID {d.share_id}.
        </div>

        <JointReportEmailDialog
          open={emailOpen}
          onClose={() => setEmailOpen(false)}
          onSend={sendEmail}
          sending={emailSending}
          parentAName={parentA}
          parentBName={parentB}
        />

        {shareLinkOpen && (
          <div
            className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
            data-testid="joint-report-share-link-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="joint-report-share-link-title"
            onClick={() => !shareLinkMinting && !shareLinkRevoking && setShareLinkOpen(false)}
          >
            <div
              className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="px-6 pt-6">
                <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
                  Shareable link
                </div>
                <h3
                  id="joint-report-share-link-title"
                  className="font-bold text-xl text-[#1A1330] leading-tight"
                >
                  Give your mediator or attorney direct access
                </h3>
              </div>

              {!shareLinkResult && (
                <div className="px-6 py-5 space-y-4">
                  <p className="text-sm text-[#4B4567] leading-relaxed">
                    We&rsquo;ll generate a signed link they can open in any
                    browser — no login required. The link renders the same
                    joint report you see here and lets them download the PDF.
                    You can revoke it at any time.
                  </p>
                  <div>
                    <label
                      htmlFor="joint-report-share-link-expiry"
                      className="block text-[10px] uppercase tracking-[0.18em] text-[#3D1A78] font-semibold mb-1.5"
                    >
                      Link expires in
                    </label>
                    <select
                      id="joint-report-share-link-expiry"
                      value={shareLinkExpireDays}
                      onChange={(e) => setShareLinkExpireDays(parseInt(e.target.value, 10))}
                      disabled={shareLinkMinting}
                      data-testid="joint-report-share-link-expiry-select"
                      className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 disabled:opacity-60"
                    >
                      <option value={1}>1 day</option>
                      <option value={7}>7 days</option>
                      <option value={14}>14 days</option>
                      <option value={30}>30 days</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="joint-report-share-link-note"
                      className="block text-[10px] uppercase tracking-[0.18em] text-[#3D1A78] font-semibold mb-1.5"
                    >
                      Optional note for the recipient
                    </label>
                    <textarea
                      id="joint-report-share-link-note"
                      value={shareLinkNote}
                      onChange={(e) => setShareLinkNote(e.target.value.slice(0, 500))}
                      disabled={shareLinkMinting}
                      rows={3}
                      maxLength={500}
                      placeholder="e.g. Hi Sam — this is the SNC v2 summary I mentioned. Happy to review on Tuesday."
                      data-testid="joint-report-share-link-note-input"
                      className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 disabled:opacity-60 resize-none"
                    />
                    <div className="mt-1 text-[11px] text-[#857E9C] text-right">
                      {shareLinkNote.length}/500
                    </div>
                  </div>
                </div>
              )}

              {shareLinkResult && (
                <div className="px-6 py-5 space-y-4">
                  <p className="text-sm text-[#4B4567] leading-relaxed">
                    Copy the link below and send it however you like —
                    email, secure message, or paste it into your case
                    system. Anyone with the link can view and download
                    until you revoke it or it expires.
                  </p>
                  <div className="rounded-xl border border-[#D6CFE8] bg-[#F5F1FB] p-3">
                    <input
                      ref={shareLinkInputRef}
                      type="text"
                      readOnly
                      value={`${window.location.origin}${shareLinkResult.preview_path || shareLinkResult.path}`}
                      onFocus={(e) => e.target.select()}
                      data-testid="joint-report-share-link-url"
                      className="w-full bg-transparent text-sm text-[#1A1330] font-mono outline-none"
                    />
                  </div>
                  {shareLinkResult.expires_at && (
                    <div
                      className="text-xs text-[#4B4567]"
                      data-testid="joint-report-share-link-expiry-info"
                    >
                      Expires{" "}
                      {new Date(shareLinkResult.expires_at).toLocaleString(undefined, {
                        year: "numeric", month: "short", day: "numeric",
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between gap-2 px-6 pb-6 pt-2 flex-wrap">
                <button
                  type="button"
                  onClick={() => setShareLinkOpen(false)}
                  disabled={shareLinkMinting || shareLinkRevoking}
                  data-testid="joint-report-share-link-close"
                  className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
                >
                  {shareLinkResult ? "Done" : "Cancel"}
                </button>
                {!shareLinkResult ? (
                  <button
                    type="button"
                    onClick={mintShareLink}
                    disabled={shareLinkMinting}
                    data-testid="joint-report-share-link-create-btn"
                    className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
                  >
                    {shareLinkMinting ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />}
                    {shareLinkMinting ? "Creating…" : "Create link"}
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={revokeShareLink}
                      disabled={shareLinkRevoking}
                      data-testid="joint-report-share-link-revoke-btn"
                      className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#B02A2A] text-[#B02A2A] px-4 py-2.5 text-sm font-semibold hover:bg-[#FBEBEB] disabled:opacity-60"
                    >
                      {shareLinkRevoking ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                      Revoke
                    </button>
                    <button
                      type="button"
                      onClick={copyShareLink}
                      data-testid="joint-report-share-link-copy-btn"
                      className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold"
                    >
                      {shareLinkCopied ? <Check size={14} /> : <Copy size={14} />}
                      {shareLinkCopied ? "Copied" : "Copy link"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
