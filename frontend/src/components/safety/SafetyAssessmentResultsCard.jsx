/**
 * SafetyAssessmentResultsCard.jsx — the trauma-informed lens result
 * card shown after a parent completes the Safety Assessment.
 *
 * Extracted from SafetyAssessment.jsx on 2026-03-05.  This component is
 * purely presentational — every button is a callback prop wired up by
 * the page.  Keep it that way: no fetch / navigate calls here.
 *
 * Renders:
 *   - Level badge + pathway title + self-reflection disclaimer
 *   - Two interpretation rules (if returned by the lens)
 *   - Three (or four) findings with typology / signals / feasibility
 *     tier / arrangement spectrum embeds
 *   - Recommended pathway checklist
 *   - Cross-link to the ND Risk Assessment
 *   - Toolbar: download PDF, court report, one-pager, co-sign QR,
 *     email-me, email-mediator, problem-solving worksheet link,
 *     regenerate AI summaries.
 */
import React from "react";
import { ProSeeLink } from "../privacy/ProSeeLink";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  Download,
  FileText,
  Lightbulb,
  Mail,
  RefreshCw,
  Scale,
  Send,
} from "lucide-react";

import CourtReportDisclaimer from "../CourtReportDisclaimer";

export const TONE_STYLES = {
  danger: {
    chip: "bg-[#FCE3DC] text-[#9A3A23] border-[#9A3A23]/25",
    badge: "bg-[#9A3A23] text-white",
    card: "border-[#9A3A23]/30",
  },
  warning: {
    chip: "bg-[#FFF1D6] text-[#7A4A05] border-[#7A4A05]/25",
    badge: "bg-[#A05C1E] text-white",
    card: "border-[#A05C1E]/30",
  },
  info: {
    chip: "bg-[#E5EAF7] text-[#1B3D8F] border-[#1B3D8F]/25",
    badge: "bg-[#3C598A] text-white",
    card: "border-[#3C598A]/30",
  },
  ok: {
    chip: "bg-[#DCEEDF] text-[#1F5C3B] border-[#1F5C3B]/25",
    badge: "bg-[#3C7858] text-white",
    card: "border-[#3C7858]/30",
  },
};

export default function SafetyAssessmentResultsCard({
  assessment,
  authorName = null,
  onDownload,
  onDownloadCourt,
  onDownloadOnePager,
  onPrepareCoSign,
  onEmail,
  onEmailMediator,
  onRegenerate,
  regenerating,
  downloadingCourt,
  isAdmin,
  sending,
}) {
  const result = assessment?.result || {};
  const tone = TONE_STYLES[result.pathway_tone] || TONE_STYLES.info;
  const level = result.level || 4;
  const lens = result.lens || null;
  const findings = lens?.findings || null;
  const rules = lens?.interpretation_rules || [];
  return (
    <div
      className={`rounded-3xl border-2 ${tone.card} bg-white shadow-sm overflow-hidden`}
      data-testid="results-card"
    >
      <div className={`${tone.badge} px-6 sm:px-8 py-3 flex items-center justify-between gap-3`}>
        <div className="text-[11px] uppercase tracking-[0.22em] font-bold">Level {level} pathway</div>
        <div className="text-[11px] uppercase tracking-[0.18em] opacity-90">{result.pathway_tone}</div>
      </div>
      <div className="p-6 sm:p-8">
        <div className="text-[10px] uppercase tracking-[0.24em] text-[#3D1A78] font-bold mb-1.5">
          Family Safety and Functioning Reflection
        </div>
        <h2 className="font-bold text-2xl sm:text-3xl text-[#1A1330] mb-3" data-testid="results-pathway-title">
          {result.pathway_title}
        </h2>
        <div
          className="rounded-2xl bg-[#F5F1FB] border border-[#3D1A78]/20 p-3.5 mb-4 text-xs text-[#1A1330] leading-relaxed"
          data-testid="results-self-reflection-disclaimer"
        >
          <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mr-1">
            Read this first ·
          </span>
          This assessment is a guided self-reflection and preparation
          resource. It is not a clinical, forensic, legal, or professional
          evaluation. Its results are intended to help you identify
          concerns, organize your thinking, and prepare questions for an
          appropriate professional.
        </div>
        <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mb-6">{result.pathway_summary}</p>

        {rules.length > 0 && (
          <div
            className="mb-6 rounded-2xl border border-[#3D1A78]/20 bg-[#F5F1FB] p-4 sm:p-5"
            data-testid="results-interpretation-rules"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
              Two interpretation rules
            </div>
            <ol className="list-decimal list-inside text-sm text-[#1A1330] space-y-1.5">
              {rules.map((r, i) => (
                <li key={`lens-rule-${i}`}>{r}</li>
              ))}
            </ol>
          </div>
        )}

        {findings && (
          <div className="mb-6 space-y-3" data-testid="results-three-findings">
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#857E9C] font-bold">
              Three findings
            </div>
            {[
              { key: "family_violence_pattern", accent: "border-l-[#9A3A23]", label: "text-[#9A3A23]" },
              { key: "trauma_impact", accent: "border-l-[#B7791F]", label: "text-[#B7791F]" },
              { key: "parenting_plan_implications", accent: "border-l-[#3D1A78]", label: "text-[#3D1A78]" },
              { key: "child_experience", accent: "border-l-[#9A3A23]", label: "text-[#9A3A23]" },
            ].map(({ key, accent, label }) => {
              const f = findings[key];
              if (!f) return null;
              return (
                <div
                  key={key}
                  className={`rounded-2xl bg-white border border-[#E5E0EE] border-l-4 ${accent} p-4 sm:p-5`}
                  data-testid={`finding-${key.replace(/_/g, "-")}`}
                >
                  <div className={`text-[10px] uppercase tracking-[0.22em] font-bold ${label} mb-1`}>
                    {f.title}
                  </div>
                  <div className="text-xs italic text-[#857E9C] mb-2">
                    {f.core_question}
                  </div>
                  <div className="text-sm font-semibold text-[#1A1330] mb-1.5">{f.headline}</div>
                  <p className="text-sm text-[#4B4567] leading-relaxed">{f.summary}</p>
                  {f.pattern_typology && (
                    <div className="mt-3 rounded-xl bg-[#FDF3F0] border border-[#9A3A23]/20 p-3">
                      <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#9A3A23] mb-1">
                        Pattern typology · {f.pattern_typology.label}
                      </div>
                      <p className="text-xs text-[#1A1330] leading-relaxed">{f.pattern_typology.framing}</p>
                    </div>
                  )}
                  {f.domain_signals && (
                    <div className="mt-3 rounded-xl bg-[#FEF5EA] border border-[#B7791F]/20 p-3">
                      <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#B7791F] mb-2">
                        Behavioural signals · overall {f.domain_signals.overall_intensity}
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {Object.entries(f.domain_signals.domains || {}).map(([k, d]) => (
                          <div key={k} className="flex items-center justify-between text-xs">
                            <span className="text-[#4B4567]">{d.label}</span>
                            <span
                              className={`text-[10px] uppercase tracking-[0.14em] font-bold px-2 py-0.5 rounded-full ${
                                d.intensity === "high"
                                  ? "bg-[#9A3A23]/15 text-[#9A3A23]"
                                  : d.intensity === "moderate"
                                  ? "bg-[#B7791F]/15 text-[#B7791F]"
                                  : "bg-[#EFE9F9] text-[#4B4567]"
                              }`}
                            >
                              {d.intensity}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {f.concern_domains && f.concern_domains.length > 0 && (
                    <div className="mt-3 rounded-xl bg-[#FDF3F0] border border-[#9A3A23]/20 p-3">
                      <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#9A3A23] mb-1">
                        Reported concern areas
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {f.concern_domains.map((d) => (
                          <span key={d} className="text-[11px] font-semibold text-[#9A3A23] bg-white border border-[#9A3A23]/20 rounded-full px-2 py-0.5">
                            {d}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {f.protective_relationship_present && (
                    <div className="mt-3 rounded-xl bg-[#E9F5EE] border border-[#2E7D5E]/25 p-3 text-xs text-[#1F5540]">
                      <span className="font-bold uppercase tracking-[0.16em]">Resilience · </span>
                      A safe, consistent protective adult was reported. Build this into the parenting plan.
                    </div>
                  )}
                  {f.non_diagnostic_note && (
                    <p className="mt-2 text-xs italic text-[#857E9C]">{f.non_diagnostic_note}</p>
                  )}
                  {f.feasibility_tier && (
                    <div
                      className="mt-3 rounded-xl bg-white border border-[#3D1A78]/25 p-3"
                      data-testid={`finding-feasibility-tier-${f.feasibility_tier.tier}`}
                    >
                      <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-1">
                        Coparenting Feasibility Spectrum · Tier {f.feasibility_tier.order} of 6
                      </div>
                      <div className="text-sm font-semibold text-[#1A1330]">
                        {f.feasibility_tier.label}
                      </div>
                      <p className="text-xs text-[#4B4567] leading-relaxed mt-1">
                        {f.feasibility_tier.narrative}
                      </p>
                      <div className="mt-2 text-[11px] uppercase tracking-[0.14em] text-[#857E9C]">
                        Review point in {f.feasibility_tier.review_point_days} days
                      </div>
                      {Array.isArray(f.feasibility_tier.triggers) && f.feasibility_tier.triggers.length > 0 && (
                        <div className="mt-2 text-[11px] text-[#4B4567]">
                          <span className="font-bold uppercase tracking-[0.12em] text-[#9A3A23]">
                            Escalated by:
                          </span>{" "}
                          {f.feasibility_tier.triggers.join(", ")}
                        </div>
                      )}
                      {Array.isArray(f.feasibility_tier.caveats) && f.feasibility_tier.caveats.map((c, i) => (
                        <p key={`tier-cav-${i}`} className="mt-2 text-xs italic text-[#4B4567]">
                          {c}
                        </p>
                      ))}
                    </div>
                  )}
                  {f.arrangement_spectrum && !f.feasibility_tier && (
                    <div className="mt-2 text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                      Recommended structure: <span className="normal-case">{f.arrangement_spectrum}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mb-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#857E9C] font-bold mb-3">
            Recommended pathway
          </div>
          <ul className="space-y-2">
            {(result.recommendations || []).map((r, i) => (
              <li key={`safety-rec-${i}-${(r || "").slice(0, 30)}`} className="flex items-start gap-2 text-sm text-[#1A1330]">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Cross-link to the ND Risk Assessment — iter84. Sits above
            the co-parent note so a target parent finishing this
            assessment sees it as the recommended next action. */}
        <a
          href="/nd-risk-assessment"
          className="mb-6 flex items-start gap-3 rounded-2xl border-2 border-[#3D1A78]/25 bg-[#F5F1FB] p-4 sm:p-5 hover:bg-[#EEE9F7] transition-colors"
          data-testid="safety-recommend-nd-risk"
        >
          <div className="shrink-0 w-10 h-10 rounded-full bg-[#3D1A78] text-white flex items-center justify-center">
            <CheckCircle2 size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Recommended next
            </div>
            <div className="text-sm sm:text-base font-serif text-[#1A1330] mt-0.5">
              Neurodivergent Coparenting Risk Assessment
            </div>
            <div className="text-xs text-[#4B4567] mt-1">
              A shorter, matrix-based screen that filters coparenting risk
              through an ADHD / autism vulnerability lens. Produces a
              professionally formatted informational summary PDF with a
              tier + suggested interventions plan.
            </div>
          </div>
        </a>

        <div className="rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 sm:p-5 mb-6">
          <div className="flex items-center gap-2 text-[#3D1A78] mb-2">
            <Lightbulb size={14} />
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold">Note about your co-parent</div>
          </div>
          <p className="text-sm text-[#4B4567] leading-relaxed">
            This screen reflects only your responses. The other parent should
            complete this screen separately so each of you has your own private
            result. Forcing or pressuring the other parent to take it is not
            recommended.
          </p>
        </div>

        <CourtReportDisclaimer
          className="mb-4"
          authorName={authorName || null}
          bothParents={false}
          testId="safety-results-court-disclaimer"
        />
        <p className="mb-4 text-[13px] text-[#4B4567]">
          When you email your mediator, your answers are left out unless you choose to include them. The court report includes summary findings only.{" "}
          <ProSeeLink testid="safety-results-pros-see-link" area="safety-check" />
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onDownload}
            data-testid="results-download-pdf"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
          >
            <Download size={14} />
            Download PDF
          </button>
          <button
            type="button"
            onClick={onDownloadCourt}
            disabled={downloadingCourt}
            data-testid="results-download-court-report"
            title="Family Safety and Functioning Reflection · Court-facing report — one finding per page, interpretation rules on page 1, signature block, safe to file. Does not include your raw Section 1 answers."
            className="inline-flex items-center gap-2 rounded-full bg-[#1A1330] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:bg-[#3D1A78] transition-colors disabled:opacity-60"
          >
            <Scale size={14} />
            {downloadingCourt ? "Preparing…" : "Download court report"}
          </button>
          <button
            type="button"
            onClick={onDownloadOnePager}
            data-testid="results-download-one-pager"
            title="A one-page handoff you can give to your lawyer, DV advocate, or family counsellor. Says what this tool is/is-not and lists the questions they should explore with you."
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#1A1330]/30 text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            <FileText size={14} />
            For your professional (1 page)
          </button>
          <button
            type="button"
            onClick={onPrepareCoSign}
            data-testid="results-prepare-cosign"
            title="Generate a QR link a mediator or DV practitioner can scan to co-sign your court report. They add their name, role, and notes without you having to regenerate the file."
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78]/30 text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB]"
          >
            <RefreshCw size={14} />
            Get reviewer co-sign QR
          </button>
          <button
            type="button"
            onClick={onEmail}
            disabled={sending}
            data-testid="results-email-button"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            <Mail size={14} />
            {sending ? "Sending…" : "Email me a copy"}
          </button>
          <button
            type="button"
            onClick={onEmailMediator}
            data-testid="results-email-mediator-button"
            className="inline-flex items-center gap-2 rounded-full bg-[#1A1330] hover:bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold shadow-md transition-colors"
          >
            <Send size={14} />
            Email my pathway to my mediator
          </button>
          <Link
            to="/problem-solving"
            data-testid="results-problem-solving-link"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            <FileText size={14} />
            Open the Problem-Solving Worksheet
          </Link>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={regenerating}
            data-testid="results-regenerate-summaries"
            title={
              isAdmin
                ? "Force-regenerate the four AI summaries (admin — no cooldown)"
                : "Regenerate the four AI summaries if the copy no longer fits your situation. Limited to once every 10 minutes."
            }
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78]/30 text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB] disabled:opacity-60"
          >
            <RefreshCw size={14} className={regenerating ? "animate-spin" : ""} />
            {regenerating
              ? "Regenerating…"
              : isAdmin
              ? "Regenerate AI summaries (admin)"
              : "Regenerate AI summaries"}
          </button>
        </div>
      </div>
    </div>
  );
}
