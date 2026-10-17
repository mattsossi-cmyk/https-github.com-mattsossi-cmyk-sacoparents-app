/**
 * SafetyAssessmentPrimitives.jsx — shared UI primitives for the
 * Safety Assessment intake flow.  Extracted from SafetyAssessment.jsx
 * on 2026-03-05 so the main page file can focus on state, scoring,
 * and API orchestration.
 *
 *   - StepHeader:   progress bar + title + subtitle at the top of a step
 *   - YNUButton:    Yes/No/Unsure pill button
 *   - QuestionRow:  one Yes/No/Unsure question with high-concern styling
 *   - ProgressStrip: "N of M answered" bar used inside extension sections
 *   - ExtensionStep: optional depth intake for the trauma-informed lens
 */
import React from "react";
import {
  ShieldAlert,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";

export function StepHeader({ step, total, title, subtitle }) {
  const pct = Math.round(((step + 1) / total) * 100);
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-[#6E6787] mb-2">
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

export function YNUButton({ value, current, label, onClick, testid }) {
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

export function QuestionRow({ idx, question, value, onChange, highConcern, missing }) {
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
            <div className="mt-1.5 inline-flex items-center gap-1 text-[0.625rem] uppercase tracking-[0.18em] text-[#9A3A23] font-bold">
              <ShieldAlert size={11} />
              High safety concern
            </div>
          )}
          {missing && (
            <div
              className="mt-1.5 inline-flex items-center gap-1 text-[0.625rem] uppercase tracking-[0.18em] text-[#9A3A23] font-bold"
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

export function ProgressStrip({ answered, total, testid }) {
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
        className="text-[0.6875rem] uppercase tracking-[0.18em] font-bold text-[#4B4567] shrink-0"
        data-testid={`${testid}-count`}
      >
        {answered} / {total} answered
      </div>
    </div>
  );
}

export function ExtensionStep({
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
        <div className="text-[0.625rem] uppercase tracking-[0.24em] text-[#3D1A78] font-bold mb-1">
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
