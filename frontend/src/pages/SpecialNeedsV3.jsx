import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Save, RotateCcw, Sparkles,
  AlertTriangle, TrendingUp, MessageCircle, FileText, Download, Share2,
  ShieldAlert, HelpCircle, HandHeart, XCircle, Users, Copy, RefreshCw,
  ClipboardList, ChevronDown, ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import { api } from "../lib/api";

/**
 * Special Needs Co-Parenting Assessment (2026 framework).
 *
 * Flow: Intake profile (unscored) → 10 scored domains with meta-options →
 * complete → deterministic individual report → invite co-parent → comparison.
 */

// Per-domain / per-report category chip tones.
const CATEGORY_TONE = {
  "Existing strength":                  { chip: "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]" },
  "Developing area":                    { chip: "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]" },
  "Priority for planning":              { chip: "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]" },
  "Professional guidance recommended":  { chip: "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]" },
  "Safety-sensitive concern":           { chip: "text-white bg-[#B02A2A] border-[#B02A2A]" },
};

// Overall banner tones.
const OVERALL_TONE = {
  "Existing Strength Overall":            { bg: "bg-[#E4F4EC]", text: "text-[#1F5C3B]", border: "border-[#B8DDC6]" },
  "Developing Overall":                   { bg: "bg-[#EFE9F9]", text: "text-[#3D1A78]", border: "border-[#CFC1EA]" },
  "Priority Focus Overall":               { bg: "bg-[#FEF1EC]", text: "text-[#C2481F]", border: "border-[#F0B6A0]" },
  "Safety-Sensitive Review Recommended":  { bg: "bg-[#FCE9E9]", text: "text-[#8B1E1E]", border: "border-[#F2B4B4]" },
};

const META_ICON = {
  na: XCircle,
  need_info: HelpCircle,
  want_help: HandHeart,
  safety: ShieldAlert,
};

const SAMPLE_HTML_URL = "/special-needs-report.html";
const SAMPLE_PDF_URL = "/api/insights/special-needs-dynamic-sample.pdf";

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------
function Progress({ answered, total }) {
  const pct = total ? Math.min(100, Math.round((answered / total) * 100)) : 0;
  return (
    <div className="mb-6" data-testid="snv3-progress">
      <div className="flex items-center justify-between text-xs text-[#857E9C] mb-2">
        <span data-testid="snv3-progress-label">{answered} of {total} answered</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden">
        <div className="h-full bg-[#3D1A78] transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function LikertRow({ scale, value, onChange, testidBase }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
      {scale.map((opt) => {
        const on = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            data-testid={`${testidBase}-${opt.value}`}
            className={`text-xs sm:text-sm font-medium px-3 py-2.5 rounded-xl border-2 transition-colors leading-tight ${
              on
                ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function MetaChips({ flags, values, onToggle, testidBase }) {
  return (
    <div className="mt-2.5 flex flex-wrap gap-1.5">
      {flags.map((f) => {
        const on = !!values?.[f.key];
        const Icon = META_ICON[f.key] || HelpCircle;
        const isSafety = f.key === "safety";
        return (
          <button
            key={f.key}
            type="button"
            onClick={() => onToggle(f.key)}
            data-testid={`${testidBase}-meta-${f.key}`}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-semibold transition-colors ${
              on
                ? isSafety
                  ? "bg-[#B02A2A] text-white border-[#B02A2A]"
                  : "bg-[#3D1A78] text-white border-[#3D1A78]"
                : isSafety
                  ? "bg-white text-[#8B1E1E] border-[#F2B4B4] hover:border-[#B02A2A]"
                  : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78]"
            }`}
          >
            <Icon size={11} /> {f.label}
          </button>
        );
      })}
    </div>
  );
}

function SampleReportCallout({ variant = "default" }) {
  const isCompact = variant === "compact";
  return (
    <div
      className={`rounded-2xl border border-[#CFC1EA] bg-[#F5F0FE] ${isCompact ? "p-4" : "p-5"}`}
      data-testid="snv3-sample-report-callout"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-9 h-9 rounded-full bg-white grid place-items-center text-[#3D1A78] border border-[#CFC1EA]">
          <FileText size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-0.5">Sample report</div>
          <div className="font-semibold text-[#1A1330]">See what a completed Special Needs report looks like</div>
          <p className="text-xs sm:text-sm text-[#4B4567] mt-1 leading-relaxed">
            A branded, fictional SA CoParents sample using the 2026 10-domain
            framework. Great to preview before you finish, or to share with your
            co-parent, mediator, or Parenting Facilitator.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a href={SAMPLE_HTML_URL} target="_blank" rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] bg-white border border-[#CFC1EA] hover:border-[#3D1A78] rounded-full px-3 py-1.5"
              data-testid="snv3-sample-view-btn">
              <FileText size={12} /> View sample (HTML)
            </a>
            <a href={SAMPLE_PDF_URL} target="_blank" rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5"
              data-testid="snv3-sample-pdf-btn">
              <Download size={12} /> Download sample PDF
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Intake Profile step (unscored)
// ---------------------------------------------------------------------------
function IntakeStep({ schema, intake, onChange, onSave, onSkip, saving }) {
  const groups = schema?.intake_profile || [];
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm" data-testid="snv3-intake">
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
        Step 1 of 2 · Child &amp; Family Profile
      </div>
      <h2 className="font-serif text-2xl text-[#1A1330] leading-tight mb-2" data-testid="snv3-intake-title">
        Tell us about your child and family
      </h2>
      <p className="text-sm text-[#4B4567] leading-relaxed">
        This intake is unscored. It contextualises the 10 domain questions and
        appears in your final report so mediators and professionals understand
        the picture. You can skip any question and update it later.
      </p>

      <div className="mt-6 space-y-8">
        {groups.map((group) => (
          <div key={group.group} data-testid={`snv3-intake-group-${group.group}`}>
            <div className="eyebrow text-[#3D1A78] mb-3">{group.label}</div>
            <div className="grid gap-4 sm:grid-cols-2">
              {group.fields.map((f) => {
                const val = intake?.[f.id] ?? "";
                const testid = `snv3-intake-field-${f.id}`;
                if (f.type === "textarea") {
                  return (
                    <label key={f.id} className={`text-sm text-[#4B4567] ${f.type === "textarea" ? "sm:col-span-2" : ""}`}>
                      <div className="font-semibold text-[#1A1330] mb-1">{f.label}</div>
                      <textarea
                        rows={3}
                        value={val}
                        onChange={(e) => onChange(f.id, e.target.value)}
                        data-testid={testid}
                        className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330] focus:border-[#3D1A78] focus:outline-none"
                      />
                    </label>
                  );
                }
                return (
                  <label key={f.id} className="text-sm text-[#4B4567]">
                    <div className="font-semibold text-[#1A1330] mb-1">{f.label}</div>
                    <input
                      type={f.type === "number" ? "number" : "text"}
                      value={val}
                      onChange={(e) => onChange(f.id, e.target.value)}
                      data-testid={testid}
                      className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330] focus:border-[#3D1A78] focus:outline-none"
                    />
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={onSkip}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[#E5E0EE] text-[#3D1A78] text-sm hover:bg-[#F5F2FA]"
          data-testid="snv3-intake-skip-btn"
        >
          Skip for now
        </button>
        <div className="flex items-center gap-2 text-xs text-[#857E9C]">
          {saving ? <><Loader2 size={12} className="animate-spin" /> Saving…</> : <><Save size={12} /> Autosaves as you go</>}
        </div>
        <button
          onClick={onSave}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
          data-testid="snv3-intake-continue-btn"
        >
          Continue to domain questions <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Domain step (10 domains × 6 questions)
// ---------------------------------------------------------------------------
function DomainStep({
  schema, domain, domainIdx, answers, meta, onAnswer, onToggleMeta,
  onNext, onPrev, onFinish, saving, completing, isLast, sectionsCount,
  totalDomains, answeredCount, total,
}) {
  const isSafety = !!domain.safety_sensitive;
  const sectionAnswered = domain.questions.filter((q) => typeof answers[q.id] === "number").length;
  const sectionComplete = sectionAnswered === domain.questions.length;

  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm" data-testid={`snv3-section-${domain.id}`}>
      <div className="flex items-start gap-3 mb-4">
        <div className={`shrink-0 w-10 h-10 rounded-full grid place-items-center font-bold ${
          isSafety ? "bg-[#FCE9E9] text-[#8B1E1E]" : "bg-[#F1EBFA] text-[#3D1A78]"
        }`}>
          {domain.number}
        </div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
            Domain {domain.number} of {sectionsCount} · Step 2 of 2
          </div>
          <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight" data-testid="snv3-section-name">
            {domain.name}
          </h2>
          {domain.goal && <p className="text-sm text-[#4B4567] mt-1.5">{domain.goal}</p>}
        </div>
      </div>

      {isSafety && (
        <div className="rounded-2xl border border-[#F2B4B4] bg-[#FCE9E9] p-4 mb-4 flex items-start gap-2" data-testid="snv3-safety-notice">
          <ShieldAlert size={16} className="text-[#8B1E1E] shrink-0 mt-0.5" />
          <div className="text-xs text-[#8B1E1E] leading-relaxed">
            <span className="font-bold">Safety-sensitive domain.</span> These items screen for
            coercive control, harassment, and protective-order concerns. Your answers here are
            <span className="font-bold"> never averaged into an overall strength score</span> — if
            any are true, we surface a safety-sensitive concern and adjust recommendations. You can
            also flag any question with a safety concern.
          </div>
        </div>
      )}

      <div className="mt-2 space-y-6">
        {domain.questions.map((q, i) => (
          <div key={q.id} data-testid={`snv3-question-${q.id}`}>
            <div className="flex items-start gap-2 mb-3">
              <span className="text-[11px] font-bold text-[#3D1A78] mt-0.5 shrink-0">
                {domain.number}.{i + 1}
              </span>
              <p className="text-[15px] text-[#1A1330] leading-relaxed">
                {q.prompt}
                {q.reverse && (
                  <span className="ml-2 text-[10px] uppercase tracking-[0.14em] text-[#857E9C]">
                    (safety-sensitive item)
                  </span>
                )}
              </p>
            </div>
            <LikertRow
              scale={schema.response_scale}
              value={answers[q.id]}
              onChange={(v) => onAnswer(q.id, v)}
              testidBase={`snv3-scale-${q.id}`}
            />
            <MetaChips
              flags={schema.meta_flags}
              values={meta[q.id]}
              onToggle={(k) => onToggleMeta(q.id, k)}
              testidBase={`snv3-${q.id}`}
            />
          </div>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={onPrev}
          disabled={domainIdx === 0}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[#E5E0EE] text-[#3D1A78] text-sm hover:bg-[#F5F2FA] disabled:opacity-40"
          data-testid="snv3-prev-btn"
        >
          <ArrowLeft size={14} /> Back
        </button>

        <div className="flex items-center gap-2 text-xs text-[#857E9C]">
          {saving || completing ? (
            <><Loader2 size={12} className="animate-spin" /> {completing ? "Scoring…" : "Saving…"}</>
          ) : (
            <><Save size={12} /> Autosaves as you go</>
          )}
        </div>

        {!isLast ? (
          <button
            onClick={onNext}
            disabled={!sectionComplete}
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
            data-testid="snv3-next-btn"
            title={!sectionComplete ? "Answer every question in this domain to continue" : ""}
          >
            Next <ArrowRight size={14} />
          </button>
        ) : (
          <button
            onClick={onFinish}
            disabled={completing || answeredCount < total}
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
            data-testid="snv3-finish-btn"
          >
            {completing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
            Finish &amp; see results
          </button>
        )}
      </div>

      <div className="mt-4 text-[11px] text-[#857E9C]">
        {sectionAnswered}/{domain.questions.length} answered in this domain · Domain {domainIdx + 1} / {totalDomains}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results view — matches Co-Parenting/Family visual chrome
// ---------------------------------------------------------------------------
function CategoryChip({ category, testid }) {
  if (!category) return <span className="text-xs italic text-[#857E9C]">Not answered</span>;
  const tone = CATEGORY_TONE[category] || CATEGORY_TONE["Developing area"];
  return (
    <span
      className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${tone.chip}`}
      data-testid={testid}
    >
      {category}
    </span>
  );
}

function IntakeSummary({ intake }) {
  const entries = Object.entries(intake || {}).filter(([, v]) => (v ?? "").toString().trim());
  const [open, setOpen] = useState(false);
  if (entries.length === 0) return null;
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="snv3-intake-summary">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between text-left"
        data-testid="snv3-intake-summary-toggle"
      >
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
            Child &amp; family profile
          </div>
          <div className="font-serif text-lg text-[#1A1330]">
            {entries.length} field{entries.length === 1 ? "" : "s"} captured
          </div>
        </div>
        {open ? <ChevronUp size={18} className="text-[#3D1A78]" /> : <ChevronDown size={18} className="text-[#3D1A78]" />}
      </button>
      {open && (
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          {entries.map(([k, v]) => (
            <div key={k} className="text-sm">
              <dt className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mb-0.5">{k.replace(/_/g, " ")}</dt>
              <dd className="text-[#1A1330] whitespace-pre-wrap">{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function ResultsView({
  report, scores, onRestart, onDownloadPdf, onShare, downloading, sharing,
}) {
  const overall = report?.overall_rating || scores?.overall_rating || "—";
  const overallSummary = report?.overall_summary || "";
  const safetyTriggered = !!(report?.safety_triggered || scores?.safety_triggered);
  const strengths = report?.strengths || [];
  const growth = report?.growth_areas || [];
  const toolkit = report?.communication_toolkit || [];
  const nextSteps = report?.next_steps || [];
  const domains = report?.domains || report?.sections || [];

  const tone = OVERALL_TONE[overall] || OVERALL_TONE["Developing Overall"];

  return (
    <div className="space-y-6" data-testid="snv3-results">
      {/* Overall banner + action buttons */}
      <div className={`rounded-3xl border ${tone.border} ${tone.bg} p-6 sm:p-8`}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
              Your Special Needs Co-Parenting Report · 2026 framework · 10 domains
            </div>
            <h2 className={`font-serif text-2xl sm:text-3xl leading-tight ${tone.text}`} data-testid="snv3-overall">
              {overall}
            </h2>
            {overallSummary && (
              <p className="text-sm text-[#1A1330] mt-2 max-w-2xl leading-relaxed">{overallSummary}</p>
            )}
            <p className="text-xs text-[#4B4567] italic mt-2">
              Findings are based on this parent&apos;s responses. This is not a diagnostic, legal, or custody evaluation.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onDownloadPdf}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] disabled:opacity-50 rounded-full px-4 py-2"
              data-testid="snv3-download-pdf-btn"
            >
              {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} PDF
            </button>
            <button
              onClick={onShare}
              disabled={sharing}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] disabled:opacity-50 rounded-full px-4 py-2"
              data-testid="snv3-share-btn"
            >
              {sharing ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />} Share
            </button>
            <button
              onClick={onRestart}
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-4 py-2"
              data-testid="snv3-restart-btn"
            >
              <RotateCcw size={14} /> Retake
            </button>
          </div>
        </div>
      </div>

      {/* Safety-sensitive alert */}
      {safetyTriggered && (
        <div className="rounded-3xl border-2 border-[#B02A2A] bg-[#FCE9E9] p-6" data-testid="snv3-safety-alert">
          <div className="flex items-start gap-3">
            <ShieldAlert size={22} className="text-[#8B1E1E] shrink-0 mt-0.5" />
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#8B1E1E] mb-1">
                Safety-sensitive concern
              </div>
              <div className="font-serif text-xl text-[#8B1E1E] leading-tight">
                Ordinary co-parenting recommendations may not be appropriate right now.
              </div>
              <p className="text-sm text-[#1A1330] mt-2 leading-relaxed">
                Your responses flagged one or more safety items. This report intentionally does
                <span className="font-semibold"> not </span> recommend direct joint meetings or
                shared decision sessions until a qualified professional has assessed the situation
                with you. Please prioritise your safety and your child&apos;s safety.
              </p>
              <div className="mt-3">
                <Link to="/safety-assessment" data-testid="snv3-safety-link"
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-[#8B1E1E] hover:bg-[#6E1616] rounded-full px-4 py-2">
                  Take the Safety Assessment <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid="snv3-strengths">
          <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <TrendingUp size={14} /> Existing strengths
          </div>
          <ul className="space-y-2.5">
            {strengths.map((s) => (
              <li key={s.section_id} className="text-[#1A1330]" data-testid={`snv3-strength-${s.section_id}`}>
                <div className="font-semibold">{s.title}</div>
                {s.detail && <div className="text-sm text-[#4B4567]">{s.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Priority focus */}
      {growth.length > 0 && (
        <div className="rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6" data-testid="snv3-priority">
          <div className="flex items-center gap-2 text-[#C2481F] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <AlertTriangle size={14} /> Priority focus areas
          </div>
          <ul className="space-y-3">
            {growth.map((g) => (
              <li key={g.section_id} data-testid={`snv3-growth-${g.section_id}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-[#1A1330]">{g.title}</span>
                  <CategoryChip category={g.rating} testid={`snv3-growth-chip-${g.section_id}`} />
                </div>
                {g.why_it_matters && (
                  <div className="text-sm text-[#4B4567] mt-1">
                    <span className="font-semibold text-[#1A1330]">Why:</span> {g.why_it_matters}
                  </div>
                )}
                {g.first_step && (
                  <div className="text-sm text-[#4B4567] mt-0.5">
                    <span className="font-semibold text-[#1A1330]">First step:</span> {g.first_step}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Communication toolkit */}
      {toolkit.length > 0 && (
        <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6" data-testid="snv3-toolkit">
          <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <MessageCircle size={14} /> Communication toolkit
          </div>
          <p className="text-sm text-[#4B4567] mb-3">
            Highlighted because Domain 6 (Communication) is a Priority for planning or Professional
            guidance recommended.
          </p>
          <ul className="space-y-2.5">
            {toolkit.map((tip, i) => (
              <li key={i} className="text-[#1A1330]" data-testid={`snv3-tip-${i}`}>
                <div className="font-semibold">{tip.title}</div>
                {tip.detail && <div className="text-sm text-[#4B4567]">{tip.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Domain-by-domain detail */}
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <h3 className="font-serif text-xl text-[#1A1330] mb-4">Domain-by-domain detail</h3>
        <div className="space-y-3">
          {domains.map((sec) => (
            <div key={sec.id} className="border border-[#E5E0EE] rounded-2xl p-4" data-testid={`snv3-sec-${sec.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                    Domain {sec.number}
                  </div>
                  <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                  {sec.goal && <div className="text-xs text-[#4B4567] mt-0.5">{sec.goal}</div>}
                </div>
                <div className="shrink-0 text-right">
                  <CategoryChip category={sec.category || sec.rating} testid={`snv3-rating-${sec.id}`} />
                  {typeof sec.avg === "number" && sec.id !== "d10" && (
                    <div className="text-[11px] text-[#857E9C] mt-1">Avg {sec.avg} / 4</div>
                  )}
                </div>
              </div>
              {(sec.findings || []).length > 0 && (
                <div className="mt-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Findings</div>
                  <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                    {sec.findings.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
              {(sec.recommendations || []).length > 0 && (
                <div className="mt-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
                  <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                    {sec.recommendations.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Next steps */}
      {nextSteps.length > 0 && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="snv3-next-steps">
          <h3 className="font-serif text-xl text-[#1A1330] mb-3">Recommended next steps</h3>
          <ol className="list-decimal pl-5 space-y-1.5 text-[#1A1330]">
            {nextSteps.map((s, i) => <li key={i} data-testid={`snv3-step-${i}`}>{s}</li>)}
          </ol>
        </div>
      )}

      {/* Intake summary at the bottom */}
      <IntakeSummary intake={report?.intake} />

      <p className="text-xs text-[#857E9C] italic text-center px-6">
        {report?.disclaimer || "Educational reflection tool. Not a diagnostic evaluation, custody evaluation, or legal advice."}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invite + Comparison block
// ---------------------------------------------------------------------------
function InviteAndComparison({ invite, onCreate, onLoadComparison, creating, loadingCmp, comparison }) {
  const inviteUrl = invite?.viewer_path
    ? `${window.location.origin}${invite.viewer_path}`
    : null;

  const copy = async () => {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      toast.success("Invite link copied");
    } catch {
      toast.info(inviteUrl);
    }
  };

  return (
    <div className="rounded-3xl border border-[#CFC1EA] bg-[#F5F0FE] p-6 sm:p-8" data-testid="snv3-invite-block">
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-10 h-10 rounded-full bg-white grid place-items-center text-[#3D1A78] border border-[#CFC1EA]">
          <Users size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
            Compare with your co-parent
          </div>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight">
            Invite the other parent to complete their assessment
          </h3>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            Each parent completes separately. The comparison highlights where you
            <span className="font-semibold"> align</span>, where you have
            <span className="font-semibold"> different observations</span>, and where
            <span className="font-semibold"> professional clarification</span> may help. Neither
            parent is labelled correct.
          </p>

          {!invite ? (
            <button
              onClick={onCreate}
              disabled={creating}
              className="mt-4 inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
              data-testid="snv3-invite-create-btn"
            >
              {creating ? <Loader2 size={14} className="animate-spin" /> : <Users size={14} />}
              Generate co-parent invite link
            </button>
          ) : (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  readOnly
                  value={inviteUrl || ""}
                  className="flex-1 min-w-[220px] rounded-full border border-[#E5E0EE] bg-white px-4 py-2 text-xs text-[#1A1330]"
                  data-testid="snv3-invite-link"
                />
                <button
                  onClick={copy}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-2"
                  data-testid="snv3-invite-copy-btn"
                >
                  <Copy size={12} /> Copy link
                </button>
              </div>
              <button
                onClick={onLoadComparison}
                disabled={loadingCmp}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] border border-[#CFC1EA] hover:border-[#3D1A78] rounded-full px-3 py-2"
                data-testid="snv3-comparison-refresh-btn"
              >
                {loadingCmp ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                Check comparison status
              </button>
            </div>
          )}

          {comparison && <ComparisonBlock comparison={comparison} />}
        </div>
      </div>
    </div>
  );
}

function ComparisonBlock({ comparison }) {
  if (comparison?.status === "waiting") {
    return (
      <div className="mt-4 rounded-2xl border border-[#CFC1EA] bg-white p-4 text-sm text-[#4B4567]" data-testid="snv3-comparison-waiting">
        <div className="flex items-center gap-2 text-[#3D1A78] font-semibold mb-1">
          <Loader2 size={14} className="animate-spin" /> Waiting for your co-parent
        </div>
        <p>They&apos;ll need to accept the invite link and complete the 10-domain assessment. Come back to this page any time.</p>
      </div>
    );
  }
  if (!comparison?.domains) return null;
  const shared = new Set(comparison.shared_priorities || []);
  return (
    <div className="mt-6 rounded-2xl border border-[#CFC1EA] bg-white p-5" data-testid="snv3-comparison-ready">
      <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.2em] mb-3">
        <ClipboardList size={14} /> Side-by-side comparison
      </div>
      {comparison.safety_flag && (
        <div className="mb-4 rounded-xl border border-[#F2B4B4] bg-[#FCE9E9] p-3 text-xs text-[#8B1E1E] flex items-start gap-2" data-testid="snv3-comparison-safety">
          <ShieldAlert size={14} className="shrink-0 mt-0.5" />
          <span>
            One or both parents flagged a safety-sensitive concern. Please review each individual
            report privately and prioritise safety before any joint session.
          </span>
        </div>
      )}
      {shared.size > 0 && (
        <div className="mb-4 text-xs text-[#4B4567]" data-testid="snv3-comparison-shared">
          <span className="font-semibold text-[#1A1330]">Shared priority focus:</span>{" "}
          {[...shared].join(", ")}
        </div>
      )}
      <div className="space-y-2">
        {comparison.domains.map((d) => (
          <div key={d.id} className="border border-[#E5E0EE] rounded-xl p-3" data-testid={`snv3-comparison-${d.id}`}>
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div className="min-w-0 flex-1">
                <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-0.5">
                  Domain {d.number}
                </div>
                <div className="font-semibold text-[#1A1330] text-sm">{d.name}</div>
              </div>
              <div className="shrink-0 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em]">
                {d.aligned ? (
                  <span className="text-[#1F5C3B] bg-[#E4F4EC] border border-[#B8DDC6] rounded-full px-2 py-0.5">Aligned</span>
                ) : (
                  <span className="text-[#8C5A2C] bg-[#FFF7E3] border border-[#F5C147] rounded-full px-2 py-0.5">Different observations</span>
                )}
              </div>
            </div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mb-1">You (inviter)</div>
                <CategoryChip category={d.inviter?.category} />
                {typeof d.inviter?.avg === "number" && (
                  <div className="text-[11px] text-[#857E9C] mt-1">Avg {d.inviter.avg} / 4</div>
                )}
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mb-1">Co-parent</div>
                <CategoryChip category={d.acceptor?.category} />
                {typeof d.acceptor?.avg === "number" && (
                  <div className="text-[11px] text-[#857E9C] mt-1">Avg {d.acceptor.avg} / 4</div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] italic text-[#857E9C] mt-4">
        A difference between parents does not mean one is right and one is wrong. Different homes
        see different sides of the same child — treat differences as information, not blame.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------
export default function SpecialNeedsV3() {
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [meta, setMeta] = useState({});
  const [intake, setIntake] = useState({});
  const [scores, setScores] = useState(null);
  const [report, setReport] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [stage, setStage] = useState("intake");         // 'intake' | 'domains' | 'results'
  const [domainIdx, setDomainIdx] = useState(0);
  const [invite, setInvite] = useState(null);
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [loadingCmp, setLoadingCmp] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, me] = await Promise.all([
        api.get("/special-needs-v3/schema"),
        api.get("/special-needs-v3/me"),
      ]);
      setSchema(s.data);
      if (me.data?.exists) {
        setAnswers(me.data.answers || {});
        setMeta(me.data.meta || {});
        setIntake(me.data.intake || {});
        if (me.data.completed && me.data.scores) {
          setScores(me.data.scores);
          setCompleted(true);
          setStage("results");
          try {
            const { data: rep } = await api.get("/special-needs-v3/report");
            if (rep && rep.report_id) {
              setReport(rep.report);
              setReportId(rep.report_id);
            } else {
              // Generate on-demand if not already stored
              const { data: gen } = await api.post("/special-needs-v3/report/generate");
              setReport(gen.report);
              setReportId(gen.report_id);
            }
          } catch { /* ignore */ }
          // Attempt to load a comparison silently (no toast if none)
          try {
            const { data: cmp } = await api.get("/special-needs-v3/comparison");
            setComparison(cmp);
          } catch { /* no invite yet */ }
        } else {
          // Determine starting stage: if intake has any keys, go to domains
          const hasIntake = Object.keys(me.data.intake || {}).length > 0;
          const hasAnswers = Object.keys(me.data.answers || {}).length > 0;
          setStage(hasIntake || hasAnswers ? "domains" : "intake");
        }
      }
    } catch {
      toast.error("Couldn't load the assessment. Please refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const domains = schema?.domains || schema?.sections || [];
  const total = schema?.total_questions || 0;
  const answeredCount = Object.keys(answers).length;
  const currentDomain = domains[domainIdx];

  const setAnswer = (qid, v) => setAnswers((a) => ({ ...a, [qid]: v }));

  const toggleMeta = (qid, key) => {
    setMeta((m) => {
      const cur = m[qid] || {};
      return { ...m, [qid]: { ...cur, [key]: !cur[key] } };
    });
  };

  const setIntakeField = (fid, value) =>
    setIntake((it) => ({ ...it, [fid]: value }));

  const persistIntake = async () => {
    setSaving(true);
    try {
      await api.post("/special-needs-v3/intake", { intake });
      return true;
    } catch {
      toast.error("Couldn't save intake — trying again shortly.");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const persistDomain = async (dom) => {
    if (!dom) return true;
    const payload = {};
    const metaPayload = {};
    for (const q of dom.questions) {
      if (typeof answers[q.id] === "number") payload[q.id] = answers[q.id];
      if (meta[q.id]) metaPayload[q.id] = meta[q.id];
    }
    if (Object.keys(payload).length === 0 && Object.keys(metaPayload).length === 0) return true;
    setSaving(true);
    try {
      await api.post("/special-needs-v3/answers/bulk", {
        answers: payload,
        meta: metaPayload,
      });
      return true;
    } catch {
      toast.error("Save failed. Your answers are kept locally — we'll retry.");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const continueFromIntake = async () => {
    const ok = await persistIntake();
    if (ok) {
      setStage("domains");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const skipIntake = () => {
    setStage("domains");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const goNext = async () => {
    await persistDomain(currentDomain);
    if (domainIdx < domains.length - 1) {
      setDomainIdx((i) => i + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const goPrev = async () => {
    await persistDomain(currentDomain);
    if (domainIdx === 0) {
      setStage("intake");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setDomainIdx((i) => Math.max(0, i - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const finish = async () => {
    const ok = await persistDomain(currentDomain);
    if (!ok) return;
    if (answeredCount < total) {
      toast.error(`Please answer all ${total} questions before finishing. (${answeredCount}/${total})`);
      return;
    }
    setCompleting(true);
    try {
      const { data } = await api.post("/special-needs-v3/complete", {});
      setScores(data.scores);
      setCompleted(true);
      try {
        const { data: rep } = await api.post("/special-needs-v3/report/generate");
        setReport(rep.report);
        setReportId(rep.report_id);
      } catch {
        toast.error("Scored, but couldn't build the report right now.");
      }
      setStage("results");
      toast.success("Assessment complete — here are your results.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't finalize the assessment.");
    } finally {
      setCompleting(false);
    }
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get("/special-needs-v3/report/pdf", { responseType: "blob" });
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Special_Needs_Report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Couldn't download the PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const share = async () => {
    if (!reportId) return;
    setSharing(true);
    try {
      const { data } = await api.post(`/special-needs-v3/report/${reportId}/share-link`, {});
      const url = `${window.location.origin}${data.viewer_path}`;
      try {
        await navigator.clipboard.writeText(url);
        toast.success("Share link copied to clipboard");
      } catch {
        toast.info(url);
      }
    } catch {
      toast.error("Couldn't create a share link.");
    } finally {
      setSharing(false);
    }
  };

  const restart = async () => {
    if (!window.confirm("Retake the assessment? Your current answers will be cleared.")) return;
    try {
      await api.delete("/special-needs-v3/me");
      setAnswers({});
      setMeta({});
      setIntake({});
      setScores(null);
      setReport(null);
      setReportId(null);
      setCompleted(false);
      setDomainIdx(0);
      setStage("intake");
      setInvite(null);
      setComparison(null);
      toast.success("Ready when you are.");
    } catch {
      toast.error("Couldn't reset. Please try again.");
    }
  };

  const createInvite = async () => {
    setCreatingInvite(true);
    try {
      const { data } = await api.post("/special-needs-v3/invite", {});
      setInvite(data);
      toast.success("Invite link ready — send it to your co-parent.");
      // Try loading comparison right away (will most likely say 'waiting')
      try {
        const { data: cmp } = await api.get("/special-needs-v3/comparison");
        setComparison(cmp);
      } catch { /* ignore */ }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't create the invite.");
    } finally {
      setCreatingInvite(false);
    }
  };

  const refreshComparison = async () => {
    setLoadingCmp(true);
    try {
      const { data } = await api.get("/special-needs-v3/comparison");
      setComparison(data);
      if (data?.status === "ready") toast.success("Comparison is ready.");
    } catch (err) {
      toast.info(err?.response?.data?.detail || "No comparison available yet.");
    } finally {
      setLoadingCmp(false);
    }
  };

  const headerBlock = useMemo(() => (
    <>
      <Link to="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
        data-testid="snv3-back-to-dashboard">
        <ArrowLeft size={14} /> Back to Dashboard
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="eyebrow text-[#3D1A78]">Special Needs Assessment · 2026 · 10 Domains</div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
            data-testid="snv3-title">
            Supporting your special-needs child across two homes
          </h1>
          <p className="mt-2 text-[#4B4567] max-w-2xl text-[15px] leading-relaxed">
            A single-parent assessment across 10 domains. Answers use a 5-point scale with meta-options
            for &quot;not applicable&quot;, &quot;need more information&quot;, &quot;want professional guidance&quot;, or
            &quot;safety concern&quot;. Safety is handled separately. Not a diagnosis. Not legal advice.
          </p>
        </div>
      </div>
      <div className="mt-6"><DemoModeBanner /></div>
    </>
  ), []);

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[#857E9C]" data-testid="snv3-loading">
          Loading your space…
        </div>
      </AppShell>
    );
  }

  // Results view (post-completion)
  if (completed && scores && stage === "results") {
    return (
      <AppShell>
        <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
            <Link to="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
              data-testid="snv3-back-to-dashboard">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
            <ResultsView
              report={report}
              scores={scores}
              onRestart={restart}
              onDownloadPdf={downloadPdf}
              onShare={share}
              downloading={downloading}
              sharing={sharing}
            />
            <div className="mt-6">
              <InviteAndComparison
                invite={invite}
                onCreate={createInvite}
                onLoadComparison={refreshComparison}
                creating={creatingInvite}
                loadingCmp={loadingCmp}
                comparison={comparison}
              />
            </div>
            <div className="mt-6">
              <SampleReportCallout variant="compact" />
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  // Intake step
  if (stage === "intake") {
    return (
      <AppShell>
        <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
            {headerBlock}
            <div className="mt-6"><SampleReportCallout /></div>
            <div className="mt-8">
              <Progress answered={answeredCount} total={total} />
            </div>
            <IntakeStep
              schema={schema}
              intake={intake}
              onChange={setIntakeField}
              onSave={continueFromIntake}
              onSkip={skipIntake}
              saving={saving}
            />
            <div className="mt-6 rounded-2xl bg-[#F8F5FF] border border-[#E5E0EE] p-4">
              <div className="flex items-start gap-2 text-xs text-[#4B4567]">
                <Sparkles size={14} className="text-[#3D1A78] shrink-0 mt-0.5" />
                <span>
                  This is a reflective tool. It doesn&apos;t diagnose, grade, or recommend legal
                  action. It gives you a clear starting point for conversations with your co-parent,
                  mediator, or Parenting Facilitator.
                </span>
              </div>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  // Domain questionnaire
  return (
    <AppShell>
      <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          {headerBlock}
          <div className="mt-6"><SampleReportCallout /></div>
          <div className="mt-8"><Progress answered={answeredCount} total={total} /></div>
          {currentDomain && (
            <DomainStep
              schema={schema}
              domain={currentDomain}
              domainIdx={domainIdx}
              answers={answers}
              meta={meta}
              onAnswer={setAnswer}
              onToggleMeta={toggleMeta}
              onNext={goNext}
              onPrev={goPrev}
              onFinish={finish}
              saving={saving}
              completing={completing}
              isLast={domainIdx === domains.length - 1}
              sectionsCount={domains.length}
              totalDomains={domains.length}
              answeredCount={answeredCount}
              total={total}
            />
          )}
          <div className="mt-6 rounded-2xl bg-[#F8F5FF] border border-[#E5E0EE] p-4">
            <div className="flex items-start gap-2 text-xs text-[#4B4567]">
              <Sparkles size={14} className="text-[#3D1A78] shrink-0 mt-0.5" />
              <span>
                This assessment is a reflective tool. It doesn&apos;t diagnose, grade, or recommend
                legal action. It gives you a clear starting point for conversations with your
                co-parent, mediator, or Parenting Facilitator.
              </span>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
