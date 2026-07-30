import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Save, RotateCcw, Sparkles,
  AlertTriangle, TrendingUp, MessageCircle, FileText, Download, Share2,
  HelpCircle, HandHeart, XCircle, Users, Copy, RefreshCw,
  ClipboardList, ChevronDown, ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import { api } from "../lib/api";

/**
 * Special Needs Co-Parenting Assessment.
 *
 * Flow: Intake profile (unscored) → 9 scored sections with meta-options →
 * complete → deterministic individual report (identical shape to the
 * Co-Parenting report) → invite co-parent → side-by-side comparison.
 */

// Section chip tones — SAME vocabulary as Co-Parenting.
const RATING_CHIP = {
  Excellent:           "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]",
  Good:                "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]",
  Fair:                "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]",
  "Needs Improvement": "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]",
};

// Overall banner tones — SAME vocabulary as Co-Parenting.
const OVERALL_TONE = {
  "Excellent Progress": { bg: "bg-[#E4F4EC]", text: "text-[#1F5C3B]", border: "border-[#B8DDC6]" },
  "Building Progress":  { bg: "bg-[#EFE9F9]", text: "text-[#3D1A78]", border: "border-[#CFC1EA]" },
  "Early Progress":     { bg: "bg-[#FEF1EC]", text: "text-[#C2481F]", border: "border-[#F0B6A0]" },
};

const META_ICON = {
  na: XCircle,
  need_info: HelpCircle,
  want_help: HandHeart,
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
        return (
          <button
            key={f.key}
            type="button"
            onClick={() => onToggle(f.key)}
            data-testid={`${testidBase}-meta-${f.key}`}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-semibold transition-colors ${
              on
                ? "bg-[#3D1A78] text-white border-[#3D1A78]"
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
            A branded, fictional SA CoParents sample using the same 9-section
            structure. Great to preview before you finish, or to share with your
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
        This intake is unscored. It contextualises the nine section questions and
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
          Continue to section questions <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section step (9 sections × 6 questions)
// ---------------------------------------------------------------------------
function SectionStep({
  schema, section, sectionIdx, answers, meta, onAnswer, onToggleMeta,
  onNext, onPrev, onFinish, saving, completing, isLast, sectionsCount,
  answeredCount, total,
}) {
  const sectionAnswered = section.questions.filter((q) => typeof answers[q.id] === "number").length;
  const sectionComplete = sectionAnswered === section.questions.length;

  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm" data-testid={`snv3-section-${section.id}`}>
      <div className="flex items-start gap-3 mb-4">
        <div className="shrink-0 w-10 h-10 rounded-full grid place-items-center font-bold bg-[#F1EBFA] text-[#3D1A78]">
          {section.number}
        </div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
            Section {section.number} of {sectionsCount} · Step 2 of 2
          </div>
          <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight" data-testid="snv3-section-name">
            {section.name}
          </h2>
          {section.goal && <p className="text-sm text-[#4B4567] mt-1.5">{section.goal}</p>}
        </div>
      </div>

      <div className="mt-2 space-y-6">
        {section.questions.map((q, i) => (
          <div key={q.id} data-testid={`snv3-question-${q.id}`}>
            <div className="flex items-start gap-2 mb-3">
              <span className="text-[11px] font-bold text-[#3D1A78] mt-0.5 shrink-0">
                {section.number}.{i + 1}
              </span>
              <p className="text-[15px] text-[#1A1330] leading-relaxed">
                {q.prompt}
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
          disabled={sectionIdx === 0}
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
            title={!sectionComplete ? "Answer every question in this section to continue" : ""}
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
        {sectionAnswered}/{section.questions.length} answered in this section · Section {sectionIdx + 1} / {sectionsCount}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results view — matches Co-Parenting/Family visual chrome
// ---------------------------------------------------------------------------
function RatingChip({ rating, testid }) {
  if (!rating) return <span className="text-xs italic text-[#857E9C]">Not answered</span>;
  const chipClass = RATING_CHIP[rating] || RATING_CHIP.Fair;
  return (
    <span
      className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${chipClass}`}
      data-testid={testid}
    >
      {rating}
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
  const strengths = report?.strengths || [];
  const growth = report?.growth_areas || [];
  const toolkit = report?.communication_toolkit || [];
  const nextSteps = report?.next_steps || [];
  const sections = report?.sections || report?.domains || [];

  const tone = OVERALL_TONE[overall] || OVERALL_TONE["Building Progress"];

  return (
    <div className="space-y-6" data-testid="snv3-results">
      {/* Overall banner + action buttons */}
      <div className={`rounded-3xl border ${tone.border} ${tone.bg} p-6 sm:p-8`}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
              Your Special Needs Co-Parenting Report · 9 sections
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

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid="snv3-strengths">
          <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <TrendingUp size={14} /> Strengths
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
                  <RatingChip rating={g.rating} testid={`snv3-growth-chip-${g.section_id}`} />
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
            Highlighted because Section 6 (Communication) is currently rated Fair or Needs Improvement.
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

      {/* Section-by-section detail */}
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <h3 className="font-serif text-xl text-[#1A1330] mb-4">Section-by-section detail</h3>
        <div className="space-y-3">
          {sections.map((sec) => (
            <div key={sec.id} className="border border-[#E5E0EE] rounded-2xl p-4" data-testid={`snv3-sec-${sec.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                    Section {sec.number}
                  </div>
                  <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                  {sec.goal && <div className="text-xs text-[#4B4567] mt-0.5">{sec.goal}</div>}
                </div>
                <div className="shrink-0 text-right">
                  <RatingChip rating={sec.rating} testid={`snv3-rating-${sec.id}`} />
                  {typeof sec.avg === "number" && (
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
        <p>They&apos;ll need to accept the invite link and complete their assessment. Come back to this page any time.</p>
      </div>
    );
  }
  const sections = comparison?.sections || comparison?.domains;
  if (!sections) return null;
  const shared = new Set(comparison.shared_priorities || []);
  return (
    <div className="mt-6 rounded-2xl border border-[#CFC1EA] bg-white p-5" data-testid="snv3-comparison-ready">
      <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.2em] mb-3">
        <ClipboardList size={14} /> Side-by-side comparison
      </div>
      {shared.size > 0 && (
        <div className="mb-4 text-xs text-[#4B4567]" data-testid="snv3-comparison-shared">
          <span className="font-semibold text-[#1A1330]">Shared priority focus:</span>{" "}
          {[...shared].join(", ")}
        </div>
      )}
      <div className="space-y-2">
        {sections.map((d) => (
          <div key={d.id} className="border border-[#E5E0EE] rounded-xl p-3" data-testid={`snv3-comparison-${d.id}`}>
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div className="min-w-0 flex-1">
                <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-0.5">
                  Section {d.number}
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
                <RatingChip rating={d.inviter?.rating} />
                {typeof d.inviter?.avg === "number" && (
                  <div className="text-[11px] text-[#857E9C] mt-1">Avg {d.inviter.avg} / 4</div>
                )}
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mb-1">Co-parent</div>
                <RatingChip rating={d.acceptor?.rating} />
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
  const [stage, setStage] = useState("intake");         // 'intake' | 'sections' | 'results'
  const [sectionIdx, setSectionIdx] = useState(0);
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
              const { data: gen } = await api.post("/special-needs-v3/report/generate");
              setReport(gen.report);
              setReportId(gen.report_id);
            }
          } catch { /* ignore */ }
          try {
            const { data: cmp } = await api.get("/special-needs-v3/comparison");
            setComparison(cmp);
          } catch { /* no invite yet */ }
        } else {
          const hasIntake = Object.keys(me.data.intake || {}).length > 0;
          const hasAnswers = Object.keys(me.data.answers || {}).length > 0;
          setStage(hasIntake || hasAnswers ? "sections" : "intake");
        }
      }
    } catch {
      toast.error("Couldn't load the assessment. Please refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sections = schema?.sections || schema?.domains || [];
  const total = schema?.total_questions || 0;
  const answeredCount = Object.keys(answers).length;
  const currentSection = sections[sectionIdx];

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

  const persistSection = async (sec) => {
    if (!sec) return true;
    const payload = {};
    const metaPayload = {};
    for (const q of sec.questions) {
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
      setStage("sections");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const skipIntake = () => {
    setStage("sections");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const goNext = async () => {
    await persistSection(currentSection);
    if (sectionIdx < sections.length - 1) {
      setSectionIdx((i) => i + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const goPrev = async () => {
    await persistSection(currentSection);
    if (sectionIdx === 0) {
      setStage("intake");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setSectionIdx((i) => Math.max(0, i - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const finish = async () => {
    const ok = await persistSection(currentSection);
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
      setSectionIdx(0);
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
          <div className="eyebrow text-[#3D1A78]">Special Needs Assessment · 9 Sections</div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
            data-testid="snv3-title">
            Supporting your special-needs child across two homes
          </h1>
          <p className="mt-2 text-[#4B4567] max-w-2xl text-[15px] leading-relaxed">
            A single-parent assessment across nine sections, using the same 5-point
            scale, rating vocabulary, and report structure as the Co-Parenting
            Assessment. Meta-options let you flag Not applicable, I need more
            information, or I would like professional guidance. Not a diagnosis. Not legal advice.
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

  // Section questionnaire
  return (
    <AppShell>
      <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          {headerBlock}
          <div className="mt-6"><SampleReportCallout /></div>
          <div className="mt-8"><Progress answered={answeredCount} total={total} /></div>
          {currentSection && (
            <SectionStep
              schema={schema}
              section={currentSection}
              sectionIdx={sectionIdx}
              answers={answers}
              meta={meta}
              onAnswer={setAnswer}
              onToggleMeta={toggleMeta}
              onNext={goNext}
              onPrev={goPrev}
              onFinish={finish}
              saving={saving}
              completing={completing}
              isLast={sectionIdx === sections.length - 1}
              sectionsCount={sections.length}
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
