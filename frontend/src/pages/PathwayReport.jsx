/**
 * PathwayReport — Dispute Resolution Pathway Report page.
 *
 * Loads the single-parent preview from `/pathway-report/preview`. If the
 * parent has an active Compare share, they can pass its share_id via
 * `?share=...` to load the full dual-party report instead. The endpoint
 * enforces both parents' consent server-side.
 *
 * Language guardrails (mirror server-side commitment):
 *   - "Primary pathway for professional consideration" (never "you should")
 *   - Every pathway comes with rated suitability + reasoning
 *   - If a safety hard-lock fired we surface the reasons prominently
 *     and hide the mediation pathway suitability chip badge.
 */
import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2, Scale, ShieldAlert, ArrowLeft, FileText, Download, Mail, Handshake, ScrollText } from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import PathwayEmailDialog from "../components/PathwayEmailDialog";
import { api } from "../lib/api";
import { downloadPdf as fetchPdfWithGracefulFailure } from "../lib/pdf";
import { logError } from "../lib/logger";

const LEVEL_META = {
  high:          { label: "High suitability",       color: "#1F5C3B", bg: "#F1F9F4", border: "#B5DFC5" },
  moderate:      { label: "Moderate suitability",   color: "#8A6B12", bg: "#FFF9EB", border: "#E4D8B8" },
  low:           { label: "Low suitability",        color: "#B02A2A", bg: "#FCEDEB", border: "#EFB4B4" },
  not_indicated: { label: "Not indicated at this time", color: "#4B4567", bg: "#F1EEF7", border: "#D6CFE8" },
};

export default function PathwayReport() {
  const [params] = useSearchParams();
  const shareId = params.get("share");
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailSending, setEmailSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const path = shareId
          ? `/pathway-report/dual/${encodeURIComponent(shareId)}`
          : "/pathway-report/preview";
        const res = await api.get(path);
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("pathway report load", err);
        if (!cancelled) {
          setState({
            loading: false, data: null,
            error: err?.response?.data?.detail || "Could not load the report right now.",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [shareId]);

  if (state.loading) {
    return (
      <AppShell>
        <div className="p-10 inline-flex items-center gap-2 text-sm text-[#4B4567]"
          data-testid="pathway-report-loading">
          <Loader2 size={14} className="animate-spin" /> Building the pathway report…
        </div>
      </AppShell>
    );
  }
  if (state.error) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto p-8" data-testid="pathway-report-error">
          <div className="rounded-2xl border border-[#EFB4B4] bg-[#FCEDEB] p-4 text-sm text-[#B02A2A]">
            {state.error}
          </div>
        </div>
      </AppShell>
    );
  }

  const d = state.data;
  const hardLocked = (d.hard_locked_by || []).length > 0;

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const path = shareId
        ? `/pathway-report/dual/${encodeURIComponent(shareId)}/pdf`
        : "/pathway-report/preview/pdf";
      const ok = await fetchPdfWithGracefulFailure(path, {
        filename: shareId ? `pathway-report-${shareId}.pdf` : "pathway-report-preview.pdf",
        testid: "pathway-report-download",
      });
      if (ok) toast.success("Pathway report downloaded.");
    } finally {
      setDownloading(false);
    }
  };

  const sendPathwayEmail = async (payload) => {
    setEmailSending(true);
    try {
      const body = { ...payload };
      if (shareId) body.share_id = shareId;
      const res = await api.post("/pathway-report/email", body);
      toast.success(`Pathway report emailed to ${res.data?.emailed_to || "recipient"}.`);
      setEmailOpen(false);
    } catch (err) {
      logError("pathway report email", err);
      toast.error(err?.response?.data?.detail || "Couldn't send the pathway report right now.");
    } finally {
      setEmailSending(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10"
        data-testid="pathway-report-root">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <Link to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78]">
            <ArrowLeft size={12} /> Back to dashboard
          </Link>
          <div className="flex items-center gap-2 flex-wrap">
            {shareId && (
              <Link
                to={`/joint-professional-report?share=${encodeURIComponent(shareId)}`}
                data-testid="pathway-report-joint-report"
                className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5F1FB] transition-colors"
                title="Open the Co-Parenting Agreement — side-by-side, for attorneys and mediators."
              >
                <ScrollText size={14} />
                Co-Parenting Agreement
              </Link>
            )}
            <Link
              to="/summary?tab=agreement"
              data-testid="pathway-report-draft-agreement"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#2DB5B5] text-[#2DB5B5] px-4 py-2 text-sm font-semibold hover:bg-[#EAF7F7] transition-colors"
              title="Start a Co-Parenting Agreement Draft you can share with the other parent."
            >
              <Handshake size={14} />
              Draft Co-Parenting Agreement
            </Link>
            <button
              type="button"
              onClick={() => setEmailOpen(true)}
              data-testid="pathway-report-email-open"
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5F1FB] transition-colors"
            >
              <Mail size={14} />
              Email to mediator
            </button>
            <button
              type="button"
              onClick={downloadPdf}
              disabled={downloading}
              data-testid="pathway-report-download-pdf"
              className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
            >
              {downloading
                ? <Loader2 size={14} className="animate-spin" />
                : <Download size={14} />}
              Download PDF
            </button>
          </div>
        </div>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          Dispute Resolution Pathway Report
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight">
          Primary pathway for professional consideration
        </h1>

        {!d.is_dual_party && (
          <div className="mt-4 rounded-2xl border border-[#E5E0EE] bg-[#F5F1FB] p-4 text-sm text-[#3D1A78]"
            data-testid="pathway-report-preview-banner">
            <strong>This is a single-parent preview.</strong> The full
            professional report requires your co-parent's data as well.
            Invite them through Compare Share to unlock the two-parent
            version.
          </div>
        )}

        {/* Primary pathway card */}
        <div
          className={
            "mt-5 rounded-3xl border-2 p-6 sm:p-7 " +
            (hardLocked
              ? "border-[#EFB4B4] bg-[#FCEDEB]"
              : "border-[#D6CFE8] bg-white")
          }
          data-testid="pathway-report-primary"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center"
              style={{ background: hardLocked ? "#B02A2A" : "#3D1A78", color: "#fff" }}>
              {hardLocked ? <ShieldAlert size={16} /> : <Scale size={16} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold"
                style={{ color: hardLocked ? "#B02A2A" : "#3D1A78" }}>
                Primary pathway
              </div>
              <div className="font-serif text-2xl text-[#1A1330] leading-snug"
                data-testid="pathway-report-primary-label">
                {d.primary_pathway_label}
              </div>
              <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
                {d.primary_pathway_summary}
              </p>
            </div>
          </div>

          {hardLocked && (
            <div className="mt-4 rounded-2xl bg-white border border-[#EFB4B4] p-4"
              data-testid="pathway-report-hard-lock">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B02A2A]">
                Safety trigger applied
              </div>
              <ul className="mt-1 text-sm text-[#B02A2A] list-disc pl-5 space-y-1">
                {d.hard_locked_by.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <p className="text-xs text-[#4B4567] mt-2 italic">
                This app never recommends mediation or a consensual process
                when the assessment data shows a safety trigger. A
                qualified family-violence advocate, forensic psychologist,
                or family-law attorney should be consulted before any
                further step is taken.
              </p>
            </div>
          )}
        </div>

        {/* Factors supporting */}
        <Section title="Factors supporting this pathway" testid="pathway-report-factors">
          <ul className="list-disc pl-5 space-y-1.5 text-sm text-[#1A1330]">
            {(d.factors_supporting_primary || []).map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </Section>

        {/* Goals */}
        <Section title="Goals before or during this process" testid="pathway-report-goals">
          <ul className="list-disc pl-5 space-y-1.5 text-sm text-[#1A1330]">
            {(d.goals_before_or_during || []).map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </Section>

        {/* Suitability profile */}
        <Section title="Process suitability profile" testid="pathway-report-suitability">
          <ul className="space-y-2">
            {(d.suitability_profile || []).map((row) => {
              const meta = LEVEL_META[row.suitability] || LEVEL_META.not_indicated;
              return (
                <li
                  key={row.key}
                  className="flex items-center justify-between gap-3 rounded-xl border p-3 bg-white"
                  style={{ borderColor: meta.border }}
                  data-testid={`pathway-suitability-${row.key}`}
                >
                  <div className="text-sm font-semibold text-[#1A1330]">{row.label}</div>
                  <span
                    className="text-[10px] uppercase tracking-[0.16em] font-bold px-2.5 py-1 rounded-full"
                    style={{ background: meta.bg, color: meta.color, border: `1px solid ${meta.border}` }}
                  >
                    {meta.label}
                  </span>
                </li>
              );
            })}
          </ul>
        </Section>

        {/* Considerations / disclaimer */}
        <Section title="Considerations" testid="pathway-report-considerations">
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-[#4B4567] italic">
            {(d.considerations || []).map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </Section>

        <div className="mt-8 rounded-2xl border border-[#E5E0EE] bg-white p-4 flex items-start gap-3">
          <FileText size={18} className="text-[#3D1A78] shrink-0 mt-0.5" />
          <div className="text-xs text-[#4B4567] leading-relaxed">
            <strong>Not legal advice.</strong> This report is a summary of
            self-reported data intended to help a qualified professional
            (mediator, family-law attorney, therapist, or advocate)
            frame their own assessment. It is not a psychological
            determination, a legal opinion, or a substitute for a
            mediator's own screening.
          </div>
        </div>
      </div>
      <PathwayEmailDialog
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        onSend={sendPathwayEmail}
        sending={emailSending}
        isDual={!!(state.data && state.data.is_dual_party)}
        pathwayLabel={state.data?.primary_pathway_label || ""}
      />
    </AppShell>
  );
}

function Section({ title, testid, children }) {
  return (
    <section className="mt-6" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
        {title}
      </div>
      {children}
    </section>
  );
}
