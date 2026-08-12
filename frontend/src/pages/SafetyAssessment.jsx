import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  Shield,
  CheckCircle2,
  Download,
  Mail,
  Phone,
  Home,
  FileText,
  AlertTriangle,
  Lightbulb,
  Send,
  RefreshCw,
  Scale,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";
import { logError } from "../lib/logger";
import { useAuth } from "../context/AuthContext";
import HighConcernOverlay from "../components/HighConcernOverlay";
import WatchFirstVideo from "../components/WatchFirstVideo";
import SectionCoaching from "../components/SectionCoaching";
import MethodologyCard from "../components/MethodologyCard";
import ReportShareControls, { pdfAbs } from "../components/ReportShareControls";
import BriefingEmailDialog from "../components/BriefingEmailDialog";
import DeviceSafetyBanner from "../components/DeviceSafetyBanner";
import ScreenGuardrailPanel from "../components/ScreenGuardrailPanel";
import ReviewerStatusChip from "../components/ReviewerStatusChip";

const TONE_STYLES = {
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


function quickExit() {
  try {
    window.location.replace("https://www.google.com");
  } catch (_e) {
    window.location.href = "https://www.google.com";
  }
}


function StepHeader({ step, total, title, subtitle }) {
  const pct = Math.round(((step + 1) / total) * 100);
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-[#857E9C] mb-2">
        <span>Step {step + 1} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden mb-5">
        <div
          className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <h1 className="font-bold text-2xl sm:text-3xl text-[#1A1330] tracking-tight mb-2">{title}</h1>
      {subtitle && <p className="text-sm text-[#4B4567] leading-relaxed">{subtitle}</p>}
    </div>
  );
}


function YNUButton({ value, current, label, onClick, testid }) {
  const active = current === value;
  const palette = {
    yes: active ? "bg-[#9A3A23] text-white border-[#9A3A23]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#9A3A23]",
    no: active ? "bg-[#3C7858] text-white border-[#3C7858]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3C7858]",
    unsure: active ? "bg-[#857E9C] text-white border-[#857E9C]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#857E9C]",
  };
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      data-testid={testid}
      className={`flex-1 px-3 py-2 rounded-full border text-xs sm:text-sm font-semibold transition-colors ${palette[value]}`}
    >
      {label}
    </button>
  );
}


function QuestionRow({ idx, question, value, onChange, highConcern, missing }) {
  return (
    <div
      className={`rounded-2xl border ${
        missing
          ? "border-[#9A3A23] ring-2 ring-[#9A3A23]/25 bg-[#FDF3F0]"
          : "border-[#E5E0EE] bg-white"
      } p-4 sm:p-5`}
      data-testid={`question-${question.id}`}
      data-missing={missing ? "true" : undefined}
    >
      <div className="flex items-start gap-3 mb-3">
        <div
          className={`shrink-0 w-7 h-7 rounded-full grid place-items-center text-xs font-bold ${
            highConcern ? "bg-[#FCE3DC] text-[#9A3A23]" : "bg-[#EFE9F9] text-[#3D1A78]"
          }`}
        >
          {idx + 1}
        </div>
        <div className="flex-1">
          <p className="text-sm sm:text-base text-[#1A1330] leading-relaxed">{question.text}</p>
          {highConcern && (
            <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] text-[#9A3A23] font-bold">
              <ShieldAlert size={11} />
              High safety concern
            </div>
          )}
          {missing && (
            <div
              className="mt-1.5 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] text-[#9A3A23] font-bold"
              data-testid={`missing-flag-${question.id}`}
            >
              <AlertTriangle size={11} />
              Please answer this one
            </div>
          )}
        </div>
      </div>
      <div className="flex items-stretch gap-2">
        <YNUButton value="yes" current={value} label="Yes" onClick={onChange} testid={`${question.id}-yes`} />
        <YNUButton value="no" current={value} label="No" onClick={onChange} testid={`${question.id}-no`} />
        <YNUButton value="unsure" current={value} label="Unsure" onClick={onChange} testid={`${question.id}-unsure`} />
      </div>
    </div>
  );
}


function ProgressStrip({ answered, total, testid }) {
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
  const complete = answered === total;
  return (
    <div
      className="mb-5 rounded-full border border-[#E5E0EE] bg-white/70 px-4 py-2 flex items-center gap-3"
      data-testid={testid}
    >
      <div className="flex-1 h-2 rounded-full bg-[#EFE9F9] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            complete
              ? "bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5]"
              : "bg-[#3D1A78]/70"
          }`}
          style={{ width: `${pct}%` }}
          data-testid={`${testid}-fill`}
        />
      </div>
      <div
        className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#4B4567] shrink-0"
        data-testid={`${testid}-count`}
      >
        {answered} / {total} answered
      </div>
    </div>
  );
}


function ResultsCard({ assessment, onDownload, onDownloadCourt, onDownloadOnePager, onPrepareCoSign, onEmail, onEmailMediator, onRegenerate, regenerating, downloadingCourt, isAdmin, sending }) {
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
          Trauma-Informed Safety and Functioning Lens · TISFL
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
          </div>          <p className="text-sm text-[#4B4567] leading-relaxed">
            This screen reflects only your responses. The other parent should
            complete this screen separately so each of you has your own private
            result. Forcing or pressuring the other parent to take it is not
            recommended.
          </p>
        </div>

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
            title="TISFL Court Report — one finding per page, interpretation rules on page 1, signature block, safe to file. Does not include your raw Section 1 answers."
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


function MediatorEmailDialog({ open, onClose, onSend, sending }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  if (!open) return null;

  const emailOk = /\S+@\S+\.\S+/.test(email.trim());

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="mediator-email-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mediator-dialog-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              Send to your mediator
            </div>
            <h3
              id="mediator-dialog-title"
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Email your safety pathway
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-close"
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-6 sm:px-7 py-5 space-y-4">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll send your mediator a short summary of your recommended
            pathway with the full PDF attached. They can reply directly to your
            email address.
          </p>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator email <span aria-hidden="true" className="text-[#9A3A23]">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="mediator@example.com"
              data-testid="mediator-email-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator name <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jamie Rivera"
              data-testid="mediator-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Message to your mediator <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Anything you want your mediator to know before our session…"
              rows={3}
              data-testid="mediator-message-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>
        </div>
        <div className="px-6 sm:px-7 pb-6 flex flex-wrap gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-cancel"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() =>
              onSend({
                mediator_email: email.trim(),
                mediator_name: name.trim(),
                parent_message: message.trim(),
              })
            }
            disabled={!emailOk || sending}
            data-testid="mediator-email-send"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
          >
            <Send size={14} />
            {sending ? "Sending…" : "Send to my mediator"}
          </button>
        </div>
      </div>
    </div>
  );
}


function ExtensionStep({
  testid,
  title,
  subtitle,
  leadNote,
  questions,
  answers,
  setAnswers,
  onBack,
  onContinue,
  onContinueLabel = "Continue",
  onSkip,
  submitting = false,
}) {
  const total = (questions || []).length;
  const answered = (questions || []).filter((q) => !!answers[q.id]).length;
  return (
    <div className="fade-up" data-testid={testid}>
      <div className="mb-4">
        <div className="text-[10px] uppercase tracking-[0.24em] text-[#3D1A78] font-bold mb-1">
          Optional depth · Trauma-Informed Lens
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-[#1A1330] mb-1">{title}</h2>
        <p className="text-sm text-[#4B4567] leading-relaxed">{subtitle}</p>
      </div>
      <div className="mb-5 rounded-2xl border border-[#3D1A78]/20 bg-[#F5F1FB] p-3.5 text-xs text-[#3D1A78]">
        <span className="font-semibold uppercase tracking-[0.16em]">Note · </span>
        {leadNote}
      </div>
      <ProgressStrip answered={answered} total={total} testid={`${testid}-progress`} />
      <div className="space-y-3 mb-8">
        {(questions || []).map((q, idx) => (
          <QuestionRow
            key={q.id}
            idx={idx}
            question={q}
            value={answers[q.id]}
            onChange={(v) => setAnswers((prev) => ({ ...prev, [q.id]: v }))}
            highConcern={false}
            missing={false}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3 justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          data-testid={`${testid}-back`}
        >
          <ArrowLeft size={14} /> Back
        </button>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onSkip}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78]/30 text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB] disabled:opacity-50"
            data-testid={`${testid}-skip`}
          >
            Skip this section
          </button>
          <button
            type="button"
            onClick={onContinue}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
            data-testid={`${testid}-continue`}
          >
            {submitting ? "Scoring…" : onContinueLabel}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}


export default function SafetyAssessment() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [questions, setQuestions] = useState(null);
  const [step, setStep] = useState(0); // 0 intro, 1 section 1, 2 section 2, 3 results
  const [answersS1, setAnswersS1] = useState({});
  const [answersS2, setAnswersS2] = useState({});
  const [answersPattern, setAnswersPattern] = useState({});
  const [answersTrauma, setAnswersTrauma] = useState({});
  const [answersChild, setAnswersChild] = useState({});
  const [skippedExt, setSkippedExt] = useState({
    pattern_context: false,
    trauma_impact: false,
    child_experience: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [showHighConcern, setShowHighConcern] = useState(false);
  const [pendingHighId, setPendingHighId] = useState(null);
  const [emailing, setEmailing] = useState(false);
  const [mediatorDialogOpen, setMediatorDialogOpen] = useState(false);
  const [mediatorSending, setMediatorSending] = useState(false);
  const [briefingEmailOpen, setBriefingEmailOpen] = useState(false);
  const [briefingSending, setBriefingSending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [missingIds, setMissingIds] = useState({ section_1: [], section_2: [] });
  const flashedRef = useRef(new Set());

  const isAdmin = Boolean(
    user?.email && user.email.toLowerCase() === "mattsossi@bsossi.com"
  );

  useEffect(() => {
    api
      .get("/safety-assessment/questions")
      .then((r) => setQuestions(r.data))
      .catch((err) => {
        logError("Failed to load questions:", err);
        toast.error("Couldn’t load the assessment. Please refresh.");
      });
  }, []);

  const highConcernIds = useMemo(
    () => new Set(questions?.high_concern_ids || []),
    [questions]
  );

  const onS1Change = (qid) => (value) => {
    setAnswersS1((prev) => ({ ...prev, [qid]: value }));
    setMissingIds((prev) =>
      prev.section_1.includes(qid)
        ? { ...prev, section_1: prev.section_1.filter((id) => id !== qid) }
        : prev
    );
    if (value === "yes" && highConcernIds.has(qid) && !flashedRef.current.has(qid)) {
      flashedRef.current.add(qid);
      setPendingHighId(qid);
      setShowHighConcern(true);
    }
  };
  const onS2Change = (qid) => (value) => {
    setAnswersS2((prev) => ({ ...prev, [qid]: value }));
    setMissingIds((prev) =>
      prev.section_2.includes(qid)
        ? { ...prev, section_2: prev.section_2.filter((id) => id !== qid) }
        : prev
    );
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/safety-assessment", {
        section_1: answersS1,
        section_2: answersS2,
        pattern_context: skippedExt.pattern_context ? {} : answersPattern,
        trauma_impact: skippedExt.trauma_impact ? {} : answersTrauma,
        child_experience: skippedExt.child_experience ? {} : answersChild,
      });
      setResult(r.data);
      setMissingIds({ section_1: [], section_2: [] });
      setStep(6);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      logError("Submit failed:", err);
      const detail = err?.response?.data?.detail;
      // Server-side "all-answered" guard responds with a structured
      // { message, missing: { section_1, section_2 } } payload — flag
      // the missing rows in the UI and jump to the section that has
      // the earliest unanswered item.
      if (
        err?.response?.status === 400 &&
        detail &&
        typeof detail === "object" &&
        detail.missing
      ) {
        const miss = {
          section_1: detail.missing.section_1 || [],
          section_2: detail.missing.section_2 || [],
        };
        setMissingIds(miss);
        if (miss.section_1.length > 0) {
          setStep(1);
        } else if (miss.section_2.length > 0) {
          setStep(2);
        }
        toast.error(
          detail.message ||
            "Please answer every question before submitting.",
        );
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        toast.error("Couldn’t submit your assessment. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const downloadPdf = () => {
    if (!result) return;
    const url = `${API}/safety-assessment/${result.assessment_id}/pdf`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const [downloadingCourt, setDownloadingCourt] = useState(false);
  const downloadCourtReport = () => {
    if (!result) return;
    setDownloadingCourt(true);
    const url = `${API}/safety-assessment/${result.assessment_id}/court-report`;
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setTimeout(() => setDownloadingCourt(false), 1200);
    }
  };

  const downloadOnePager = () => {
    if (!result) return;
    const url = `${API}/safety-assessment/${result.assessment_id}/one-pager`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const [cosignModal, setCosignModal] = useState(null);
  const prepareCoSign = async () => {
    if (!result?.assessment_id) return;
    try {
      const r = await api.post(
        `/safety-assessment/${result.assessment_id}/prepare-cosign`,
      );
      setCosignModal(r.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Couldn't prepare the co-sign QR right now.");
    }
  };
  const copyCoSignLink = async () => {
    if (!cosignModal?.verify_url) return;
    try {
      await navigator.clipboard.writeText(cosignModal.verify_url);
      toast.success("Link copied to clipboard.");
    } catch {
      toast.error("Copy failed — long-press the link to copy manually.");
    }
  };

  const emailMe = async () => {
    if (!result) return;
    setEmailing(true);
    try {
      await api.post(`/safety-assessment/${result.assessment_id}/email`);
      toast.success("Sent! Check your inbox for the PDF.");
    } catch (err) {
      logError("Email failed:", err);
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 400 && /save your work|real email/i.test(detail || "")) {
        toast.error(detail, {
          action: { label: "Save my work", onClick: () => navigate("/claim") },
        });
      } else {
        toast.error(detail || "Couldn’t email the report right now.");
      }
    } finally {
      setEmailing(false);
    }
  };

  const openMediatorDialog = () => {
    if (!result) return;
    setMediatorDialogOpen(true);
  };

  const sendToMediator = async (payload) => {
    if (!result) return;
    setMediatorSending(true);
    try {
      await api.post(
        `/safety-assessment/${result.assessment_id}/email-mediator`,
        payload,
      );
      toast.success("Sent to your mediator.");
      setMediatorDialogOpen(false);
    } catch (err) {
      logError("Mediator email failed:", err);
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 400 && /save your work|real email/i.test(detail || "")) {
        toast.error(detail, {
          action: { label: "Save my work", onClick: () => navigate("/claim") },
        });
      } else {
        toast.error(detail || "Couldn’t send to your mediator right now.");
      }
    } finally {
      setMediatorSending(false);
    }
  };

  const regenerateSummaries = async () => {
    if (!result?.assessment_id) return;
    setRegenerating(true);
    try {
      await api.post(
        `/safety-assessment/${result.assessment_id}/regenerate-summaries`,
      );
      toast.success(
        "AI summaries regenerated. Your next PDF download will include the fresh copy.",
      );
    } catch (err) {
      logError("Regenerate summaries failed:", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 429) {
        toast.error(detail || "Please wait a bit before regenerating again.");
      } else if (status === 503) {
        toast.error(
          detail ||
            "AI summary service is temporarily unavailable. Please try again shortly.",
        );
      } else {
        toast.error(detail || "Couldn't regenerate the summaries right now.");
      }
    } finally {
      setRegenerating(false);
    }
  };

  const allAnsweredS1 = useMemo(() => {
    if (!questions) return false;
    return questions.section_1.every((q) => answersS1[q.id]);
  }, [answersS1, questions]);
  const allAnsweredS2 = useMemo(() => {
    if (!questions) return false;
    return questions.section_2.every((q) => answersS2[q.id]);
  }, [answersS2, questions]);
  const answeredCountS1 = useMemo(() => {
    if (!questions) return 0;
    return questions.section_1.filter((q) => answersS1[q.id]).length;
  }, [answersS1, questions]);
  const answeredCountS2 = useMemo(() => {
    if (!questions) return 0;
    return questions.section_2.filter((q) => answersS2[q.id]).length;
  }, [answersS2, questions]);
  const missingS1Set = useMemo(
    () => new Set(missingIds.section_1 || []),
    [missingIds]
  );
  const missingS2Set = useMemo(
    () => new Set(missingIds.section_2 || []),
    [missingIds]
  );

  if (!questions) {
    return (
      <div className="min-h-screen grid place-items-center text-[#4B4567]">
        <div className="animate-pulse text-sm tracking-[0.2em] uppercase">Loading</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg" data-testid="safety-assessment-page">
      {/* Top safety bar */}
      <div className="sticky top-0 z-40 backdrop-blur-md bg-[#C28771]/10 border-b border-[#C28771]/25">
        <div className="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between gap-3">
          <Link
            to="/safety"
            className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#1A1330]"
            data-testid="assessment-back-link"
          >
            <ArrowLeft size={14} />
            Back to Safety
          </Link>
          <button
            type="button"
            onClick={quickExit}
            className="inline-flex items-center gap-2 rounded-full bg-[#C28771] hover:bg-[#a87560] text-white px-4 py-2 text-sm font-medium shadow-sm"
            data-testid="assessment-quick-exit"
            aria-label="Quick exit"
          >
            <Home size={14} />
            Quick exit
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {step === 0 && (
          <div className="card-soft p-6 sm:p-10 fade-up" data-testid="assessment-intro">
            <DeviceSafetyBanner />

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#C28771]/15 text-[#C28771] grid place-items-center">
                <ShieldAlert size={18} />
              </div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
                SA CoParents
              </div>
            </div>
            <h1 className="font-bold text-3xl sm:text-4xl text-[#1A1330] tracking-tight mb-1">
              Trauma-Informed Safety and Functioning Lens
            </h1>
            <p className="text-sm text-[#4B4567] mb-3">
              Family Violence and Communication Safety Screen
              <span className="text-[#3D1A78] font-semibold"> · TISFL</span>
            </p>
            <div className="mb-4">
              <ReviewerStatusChip />
            </div>

            <MethodologyCard id="safety" defaultOpen={false} />

            <p className="text-[#4B4567] leading-relaxed mb-4">
              This is a <strong className="text-[#1A1330]">reflection screen</strong> — not
              a clinical assessment — to help you notice patterns of family
              violence, coercive control, intimidation, stalking, or safety
              concerns before deciding how (or whether) to communicate with
              your co-parent. Several items are informed by the Danger
              Assessment (Campbell) domains most predictive of severe harm,
              but this tool is <strong className="text-[#1A1330]">not the
              Danger Assessment, MASIC-S, or HITS</strong>, and it has not
              been independently validated in custody or mediation
              populations. A trained professional should be involved in any
              high-risk situation.
            </p>

            <div
              className="rounded-2xl bg-[#F5F1FB] border border-[#3D1A78]/25 text-[#1A1330] p-4 sm:p-5 mb-4"
              data-testid="self-reflection-disclaimer"
            >
              <div className="flex items-center gap-2 mb-2">
                <FileText size={14} className="text-[#3D1A78]" />
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                  What this assessment is (and is not)
                </div>
              </div>
              <p className="text-sm leading-relaxed">
                This assessment is a <strong>guided self-reflection and
                preparation resource</strong>. It is <strong>not a clinical,
                forensic, legal, or professional evaluation</strong>. Its
                results are intended to help you identify concerns, organize
                your thinking, and prepare questions for an appropriate
                professional.
              </p>
            </div>

            <div className="rounded-2xl bg-[#FCE3DC] border border-[#9A3A23]/25 text-[#9A3A23] p-4 sm:p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={14} />
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold">
                  Important safety notice
                </div>
              </div>
              <p className="text-sm leading-relaxed">
                In addition to the disclaimer above: if there is immediate
                danger, call{" "}
                <a href="tel:911" className="underline font-bold">911</a>.
                If communication with the other parent creates fear, danger,
                or retaliation, direct communication may not be appropriate.
              </p>
              <a
                href="tel:18007997233"
                data-testid="intro-call-ndv"
                className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-xs font-bold hover:bg-[#7e2e1c]"
              >
                <Phone size={12} />
                Call 800-799-7233 · National DV Hotline
              </a>
            </div>

            {/* Trauma-Informed Safety and Functioning Lens — procedural safeguards */}
            <div
              className="rounded-2xl border border-[#3D1A78]/20 bg-[#F5F1FB] p-5 sm:p-6 mb-6"
              data-testid="tisfl-safeguards"
            >
              <div className="flex items-center gap-2 mb-3">
                <ShieldAlert size={14} className="text-[#3D1A78]" />
                <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                  Procedural safeguards · Trauma-Informed Lens
                </div>
              </div>
              <ul className="text-sm text-[#1A1330] space-y-2">
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>You complete this <strong>separately</strong> from your co-parent. Your answers are private and are never shared with them unless you choose to.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>You can <strong>pause any time</strong>. If a question raises a strong reaction, step away, breathe, and return when you&rsquo;re ready.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>This tool <strong>does not diagnose</strong> and does not label either parent. It reflects behaviour and safety signals — not personality or worth.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>Safety information stays walled off from the Compare view. Your co-parent only sees the parenting-plan implications, never your pattern or trauma details.</span>
                </li>
              </ul>
              <div className="mt-4 rounded-xl border border-[#3D1A78]/20 bg-white p-3 text-xs text-[#4B4567] leading-relaxed">
                <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1.5">
                  Two interpretation rules
                </div>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Trauma symptoms are not evidence that a parent is unreliable, unfit, or responsible for the violence.</li>
                  <li>A history of trauma does not excuse coercion, intimidation, child maltreatment, or other harmful parenting behavior.</li>
                </ol>
              </div>
            </div>

            {/* 4-dimension clinical model — Safety is one of four separate lenses */}
            <div className="rounded-2xl border border-[#E5E0EE] bg-[#F8F5FF] p-5 sm:p-6 mb-6" data-testid="four-dimension-model">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-full bg-[#3D1A78]/12 grid place-items-center text-[#3D1A78] text-[10px] font-bold">
                  1/4
                </div>
                <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                  Where this assessment sits in the bigger picture
                </div>
              </div>
              <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                We evaluate co-parenting on four separate dimensions, so that a
                communication difference (for example, from autism or ADHD) is
                never confused with a genuine safety concern. This
                assessment focuses on the first one — <strong>Safety</strong>.
              </p>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="rounded-xl border-2 border-[#C28771] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#C28771] mb-1">
                    Dimension 1 · Safety <span className="text-[#857E9C]">(you are here)</span>
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Family violence, coercive control, fear</div>
                  <div className="text-xs text-[#4B4567]">→ Safety recommendations &amp; safer pathways</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 2 · Communication
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Communication profile</div>
                  <div className="text-xs text-[#4B4567]">→ Communication strategies</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 3 · Emotional regulation
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Stress &amp; conflict response</div>
                  <div className="text-xs text-[#4B4567]">→ Regulation tools</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 4 · Executive function
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Organisation, planning, follow-through</div>
                  <div className="text-xs text-[#4B4567]">→ Practical supports</div>
                </div>
              </div>
              <p className="text-xs text-[#4B4567] mt-4">
                Dimensions 2, 3 &amp; 4 can be scored together in a single
                companion assessment once your safety screen clears.
              </p>
            </div>

            <ul className="text-sm text-[#4B4567] space-y-2 mb-7">
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>Takes about 5 minutes.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>Your answers are stored privately on your account.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>You can download or email yourself a PDF copy at the end.</span>
              </li>
            </ul>

            <div className="mb-7">
              <WatchFirstVideo
                videoSrc="/videos/ipv-assessment-intro.mp4"
                posterSrc="/images/ipv-assessment-poster.png"
                label="Watch First · Family Violence and Communication Safety Screen for Co-Parents"
                subtitle="Safety First. Informed Choices. Better Outcomes for Your Children."
                testid="safety-assessment-watch"
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                data-testid="intro-start-button"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                Start the assessment
                <ArrowRight size={14} />
              </button>
              <Link
                to="/safety"
                data-testid="intro-cancel-link"
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-3 text-sm font-semibold hover:bg-[#F8F7FC]"
              >
                Not now
              </Link>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="fade-up" data-testid="assessment-section-1">
            <StepHeader
              step={0}
              total={3}
              title="Section 1 · Immediate Safety Screen"
              subtitle="In the past 12 months, has the other parent…"
            />
            <ProgressStrip
              answered={answeredCountS1}
              total={questions.section_1.length}
              testid="s1-progress"
            />
            <div className="space-y-3 mb-8">
              {questions.section_1.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS1[q.id]}
                  onChange={onS1Change(q.id)}
                  highConcern={highConcernIds.has(q.id)}
                  missing={missingS1Set.has(q.id)}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() => setStep(0)}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="s1-back-button"
              >
                <ArrowLeft size={14} /> Back
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep(2);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                disabled={!allAnsweredS1}
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
                data-testid="s1-next-button"
              >
                Continue to readiness
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="fade-up" data-testid="assessment-section-2">
            <StepHeader
              step={1}
              total={3}
              title="Section 2 · Communication Readiness"
              subtitle="These reflect your own readiness right now. The other parent should complete this separately to get their own private result."
            />
            <ProgressStrip
              answered={answeredCountS2}
              total={questions.section_2.length}
              testid="s2-progress"
            />
            <div className="space-y-3 mb-8">
              {questions.section_2.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS2[q.id]}
                  onChange={onS2Change(q.id)}
                  highConcern={false}
                  missing={missingS2Set.has(q.id)}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() => {
                  setStep(1);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="s2-back-button"
              >
                <ArrowLeft size={14} /> Back
              </button>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setSkippedExt({
                      pattern_context: true,
                      trauma_impact: true,
                      child_experience: true,
                    });
                    submit();
                  }}
                  disabled={!allAnsweredS2 || submitting}
                  className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78]/30 text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB] disabled:opacity-50"
                  data-testid="s2-skip-depth-button"
                >
                  See my pathway now (skip optional depth)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep(3);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  disabled={!allAnsweredS2}
                  className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
                  data-testid="s2-continue-button"
                >
                  {submitting ? "Scoring…" : "Continue to optional depth"}
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <ExtensionStep
            testid="assessment-section-pattern"
            title="Pattern & Context (optional)"
            subtitle="These items help distinguish coercive-control from situational or separation-instigated conflict. This is optional — skip freely if any question is too much."
            leadNote="Trauma-informed pacing: skip any question or the whole section. Nothing is required here."
            questions={questions.pattern_context || []}
            answers={answersPattern}
            setAnswers={setAnswersPattern}
            onBack={() => { setStep(2); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={() => { setStep(4); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, pattern_context: true }));
              setStep(4);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}

        {step === 4 && (
          <ExtensionStep
            testid="assessment-section-trauma"
            title="Trauma Impact (optional, non-diagnostic)"
            subtitle="These items describe common behavioural responses to danger and stress. They do not diagnose anything. They help Finding 2 reflect your reality rather than assume it."
            leadNote="If any question triggers a strong response, step away, breathe, and come back — or skip the whole section."
            questions={questions.trauma_impact || []}
            answers={answersTrauma}
            setAnswers={setAnswersTrauma}
            onBack={() => { setStep(3); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={() => { setStep(5); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, trauma_impact: true }));
              setStep(5);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}

        {step === 5 && (
          <ExtensionStep
            testid="assessment-section-child"
            title="Child Experience — your account (optional)"
            subtitle="Your account of how the children are experiencing all of this. This tool never asks the child directly. A qualified child specialist should conduct any direct assessment of the child."
            leadNote="Skip freely. You know your child better than any form. This section produces Finding 4 when completed."
            questions={questions.child_experience || []}
            answers={answersChild}
            setAnswers={setAnswersChild}
            onBack={() => { setStep(4); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={submit}
            onContinueLabel="See my pathway"
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, child_experience: true }));
              submit();
            }}
            submitting={submitting}
          />
        )}

        {cosignModal && (
          <div
            className="fixed inset-0 bg-black/60 grid place-items-center z-50 p-4"
            data-testid="cosign-modal"
            onClick={() => setCosignModal(null)}
          >
            <div
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-bold mb-2">
                Reviewer co-sign QR
              </div>
              <h3 className="text-xl font-bold text-[#1A1330] mb-3">
                Give this to your professional
              </h3>
              <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                Your mediator, DV advocate, or family counsellor scans this QR (or clicks the link) to add their printed name, role, and optional notes to your court report — no regeneration required on your side.
              </p>
              <div className="grid place-items-center bg-[#FAF9FD] rounded-2xl border border-[#E5E0EE] p-4 mb-4">
                <img
                  src={cosignModal.qr_png_data_url}
                  alt="Reviewer co-sign QR code"
                  className="w-56 h-56"
                  data-testid="cosign-modal-qr"
                />
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#857E9C] font-bold mb-1">Link</div>
              <div className="text-xs break-all text-[#4B4567] mb-3" data-testid="cosign-modal-url">
                {cosignModal.verify_url}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={copyCoSignLink}
                  data-testid="cosign-modal-copy"
                  className="rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs font-semibold hover:bg-[#2a1155]"
                >
                  Copy link
                </button>
                <button
                  type="button"
                  onClick={() => setCosignModal(null)}
                  data-testid="cosign-modal-close"
                  className="rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-4 py-2 text-xs font-semibold hover:bg-[#F8F7FC]"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}


        {step === 6 && result && (
          <div className="fade-up" data-testid="assessment-results">
            <div className="mb-5 text-xs uppercase tracking-[0.2em] text-[#857E9C]">
              Your result · {new Date(result.created_at).toLocaleDateString()}
            </div>
            <ResultsCard
              assessment={result}
              onDownload={downloadPdf}
              onDownloadCourt={downloadCourtReport}
              onDownloadOnePager={downloadOnePager}
              onPrepareCoSign={prepareCoSign}
              downloadingCourt={downloadingCourt}
              onEmail={emailMe}
              onEmailMediator={openMediatorDialog}
              onRegenerate={regenerateSummaries}
              regenerating={regenerating}
              isAdmin={isAdmin}
              sending={emailing}
            />

            {result?.assessment_id && (
              <div className="mt-6">
                <ReportShareControls
                  reportType="safety"
                  pdfUrl={pdfAbs(`/safety-assessment/${result.assessment_id}/pdf`)}
                  shareUrl={`/safety-assessment/${result.assessment_id}/share-link`}
                  visibilityUrl={`/safety-assessment/${result.assessment_id}/visibility`}
                  initialExcluded={result?.visibility?.excluded || []}
                  filename={`safety-assessment-${result.assessment_id}.pdf`}
                  testIdPrefix="safety-share"
                />
              </div>
            )}

            {/* Post-result guardrail — makes explicit what this screen
                does NOT decide, plus an anti-mutualization block for
                Level 1/2 (highest concern) results. */}
            <ScreenGuardrailPanel level={result?.result?.level} />

            {/* AI communication coaching is SUPPRESSED for Level 1 & 2 to
                avoid mutualizing abuse — coaching a survivor to
                communicate "better" with a coercive co-parent shifts
                responsibility onto the person experiencing harm. */}
            {result?.result?.level >= 3 && (
              <div className="mt-6">
                <SectionCoaching
                  section="safety"
                  ready={Boolean(result?.result)}
                  data={{
                    level: result?.result?.level,
                    pathway_tone: result?.result?.pathway_tone,
                    pathway_title: result?.result?.pathway_title,
                    pathway_summary: result?.result?.pathway_summary,
                    recommendations: result?.result?.recommendations || [],
                  }}
                />
              </div>
            )}

            <div className="mt-6 flex justify-center">
              <Link
                to="/next-steps/safety"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#3D1A78] text-white font-semibold hover:bg-[#2D0F63]"
                data-testid="safety-next-steps-cta"
              >
                See your Next Three Steps <ArrowRight size={14} />
              </Link>
            </div>

            {/* Companion 4-dimension CTA — only offered when Safety cleared
                (level 3 or 4). We do not surface this for levels 1/2 so
                parents can prioritise safety planning without being pulled
                into communication/regulation questions that may be
                misinterpreted under coercion. */}
            {result?.result?.level >= 3 && (
              <div
                className="mt-6 rounded-3xl border-2 border-[#3D1A78] bg-gradient-to-br from-[#F8F5FF] to-white p-6 sm:p-8"
                data-testid="safety-companion-cta"
              >
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                  Complete the picture · Dimensions 2, 3 &amp; 4
                </div>
                <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mb-2">
                  Your safety result cleared — want to run the other three
                  dimensions in one sitting?
                </h3>
                <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                  Communication, Emotional Regulation, and Executive Function
                  are the three remaining lenses in the four-dimension model.
                  Because your safety screen cleared, they can now be scored
                  together in a single ~7-minute companion assessment.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link
                    to="/companion-assessment"
                    data-testid="safety-companion-cta-link"
                    className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
                  >
                    Start companion assessment <ArrowRight size={14} />
                  </Link>
                  <button
                    type="button"
                    onClick={() => setBriefingEmailOpen(true)}
                    data-testid="safety-briefing-email-button"
                    className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] px-5 py-3 text-sm font-semibold hover:bg-[#F1EBFA]"
                  >
                    <Mail size={14} /> Email Briefing
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await api.get("/dimension-companion/four-dimension-briefing/pdf", {
                          params: { sign: true },
                          responseType: "blob",
                        });
                        const blob = new Blob([res.data], { type: "application/pdf" });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = "four-dimension-briefing.pdf";
                        a.click();
                        URL.revokeObjectURL(url);
                      } catch (err) {
                        logError("Briefing download failed", err);
                        toast.error("Couldn't download the briefing.");
                      }
                    }}
                    data-testid="safety-briefing-pdf-button"
                    className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] px-5 py-3 text-sm font-semibold hover:bg-[#F1EBFA]"
                  >
                    <Download size={14} /> Download PDF
                  </button>
                </div>
                <p className="text-[11px] text-[#8471B3] mt-3 italic">
                  Briefing includes Safety + whichever companion dimensions you've
                  completed — designed for a mediator, parent facilitator ad litem,
                  or trial court.
                </p>
              </div>
            )}

            {/* Important Advisory — legally-worded post-assessment disclaimer */}
            <div
              className="mt-6 rounded-2xl bg-[#FFF7E6] border-2 border-[#E8A628] p-5 sm:p-7 text-[#1A1330]"
              data-testid="safety-important-advisory"
            >
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] font-bold text-[#B8891C] mb-3">
                <Shield size={13} /> Important Advisory
              </div>
              <p className="leading-relaxed mb-3">
                The SA CoParents Family Violence and Communication Safety
                Screen is designed to help you reflect on your parenting
                and communication situation. It is <strong>not intended to
                diagnose domestic violence, determine legal rights, predict
                future behavior, or replace professional advice</strong>.
              </p>
              <p className="leading-relaxed mb-3">
                Your responses are based solely on the information you provide
                and may not reflect the complete circumstances of your family.
              </p>
              <p className="leading-relaxed mb-4">
                If your assessment suggests concerns about intimidation,
                coercive control, threats, stalking, harassment, or violence,
                we strongly encourage you to seek additional guidance before
                making parenting or communication decisions.
              </p>
              <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
                Consider consulting with
              </div>
              <ul className="space-y-2 text-sm mb-4">
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  A qualified <strong>family law attorney</strong> to
                  understand your legal rights and available protections.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  A licensed <strong>therapist or domestic violence
                  professional</strong> experienced in intimate partner
                  violence.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  Your local <strong>domestic violence advocacy
                  organization</strong> or victim assistance program.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  <strong>Law enforcement or emergency services immediately</strong>{" "}
                  if you believe you or your child are in immediate danger.
                </li>
              </ul>
              <p className="text-sm font-semibold text-[#1A1330] mb-2">
                The safety of you and your child should always come before
                attempts to improve communication or co-parenting.
              </p>
              <p className="text-xs text-[#6B6580] italic leading-relaxed">
                This assessment is intended to support informed decision-making
                — not to replace professional legal, therapeutic, or safety
                planning services.
              </p>
            </div>

            <div className="mt-6 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 sm:p-5 text-sm text-[#4B4567] leading-relaxed">
              <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
                Texas resources
              </div>
              <p>
                National Domestic Violence Hotline:{" "}
                <a href="tel:18007997233" className="underline font-bold text-[#1A1330]">800-799-7233</a>{" "}
                · text <strong>START</strong> to <strong>88788</strong>. Trained
                advocates provide crisis intervention, safety planning,
                education, advocacy, and referrals to shelters and local
                resources. If there is immediate danger, call{" "}
                <a href="tel:911" className="underline font-bold text-[#1A1330]">911</a>.
              </p>
            </div>

            <div className="mt-6 flex flex-wrap gap-3 justify-between">
              <Link
                to="/safety"
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="results-back-to-safety"
              >
                <ArrowLeft size={14} /> Back to Safety
              </Link>
              <button
                type="button"
                onClick={() => {
                  setAnswersS1({});
                  setAnswersS2({});
                  setAnswersPattern({});
                  setAnswersTrauma({});
                  setAnswersChild({});
                  setSkippedExt({
                    pattern_context: false,
                    trauma_impact: false,
                    child_experience: false,
                  });
                  setResult(null);
                  flashedRef.current = new Set();
                  setStep(0);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="results-retake-button"
              >
                Retake assessment
              </button>
            </div>
          </div>
        )}
      </div>

      <HighConcernOverlay
        open={showHighConcern}
        onContinue={() => {
          setShowHighConcern(false);
          setPendingHighId(null);
        }}
        onClose={() => {
          if (pendingHighId) {
            setAnswersS1((prev) => {
              const next = { ...prev };
              delete next[pendingHighId];
              return next;
            });
            flashedRef.current.delete(pendingHighId);
          }
          setShowHighConcern(false);
          setPendingHighId(null);
        }}
      />

      <MediatorEmailDialog
        open={mediatorDialogOpen}
        onClose={() => {
          if (!mediatorSending) setMediatorDialogOpen(false);
        }}
        onSend={sendToMediator}
        sending={mediatorSending}
      />

      <BriefingEmailDialog
        open={briefingEmailOpen}
        onClose={() => { if (!briefingSending) setBriefingEmailOpen(false); }}
        onSend={async (payload) => {
          setBriefingSending(true);
          try {
            const r = await api.post("/dimension-companion/four-dimension-briefing/email", payload);
            toast.success(`Briefing sent to ${r.data.emailed_to}.`);
            setBriefingEmailOpen(false);
          } catch (err) {
            logError("Briefing email failed", err);
            const detail = err?.response?.data?.detail;
            const status = err?.response?.status;
            if (status === 400 && /save your work|real email/i.test(detail || "")) {
              toast.error(detail, {
                action: { label: "Save my work", onClick: () => navigate("/claim") },
              });
            } else if (status === 503) {
              toast.error(detail || "Email service isn't available right now.");
            } else {
              toast.error(detail || "Couldn't send the briefing. Please try again.");
            }
          } finally {
            setBriefingSending(false);
          }
        }}
        sending={briefingSending}
      />
    </div>
  );
}
