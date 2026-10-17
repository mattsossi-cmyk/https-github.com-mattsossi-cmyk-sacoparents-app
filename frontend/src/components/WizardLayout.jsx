import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";

const STEPS = [
  { key: "child-goals", label: "Child Goals", path: "/prep/child-goals" },
  { key: "issues", label: "Issues", path: "/prep/issues" },
  { key: "priority", label: "Priority", path: "/prep/priority" },
  { key: "communication", label: "Communication", path: "/prep/communication" },
  { key: "readiness", label: "Readiness", path: "/prep/readiness" },
];

const SEGMENT_ACTIVE = "bg-[#3D1A78]";
const SEGMENT_DONE = "bg-[#3D1A78]/70";
const SEGMENT_IDLE = "bg-[#E5E0EE]";

function segmentClass(isActive, isDone) {
  if (isActive) return SEGMENT_ACTIVE;
  if (isDone) return SEGMENT_DONE;
  return SEGMENT_IDLE;
}

export default function WizardLayout({
  currentKey,
  title,
  eyebrow,
  description,
  completed = {},
  onNext,
  saving = false,
  children,
  nextLabel,
}) {
  const navigate = useNavigate();
  const idx = STEPS.findIndex((s) => s.key === currentKey);
  const prev = STEPS[idx - 1];
  const next = STEPS[idx + 1];

  return (
    <div className="max-w-3xl mx-auto fade-up">
      {/* Step indicator */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-3">
          {STEPS.map((s, i) => {
            const isDone = !!completed[s.key.replace("-", "_")] && i !== idx;
            const isActive = i === idx;
            return (
              <div key={s.key} className="flex-1">
                <div
                  className={`h-1.5 rounded-full progress-fill ${segmentClass(isActive, isDone)}`}
                />
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[0.625rem] uppercase tracking-[0.2em] text-[#6E6787]">
          {STEPS.map((s, i) => (
            <div
              key={s.key}
              className={`flex-1 text-center ${i === idx ? "text-[#1A1330]" : ""}`}
            >
              {s.label}
            </div>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="mb-8">
        {eyebrow && <div className="eyebrow mb-3">{eyebrow}</div>}
        <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight">
          {title}
        </h1>
        {description && (
          <p className="text-[#4B4567] mt-4 leading-relaxed max-w-2xl">
            {description}
          </p>
        )}
      </div>

      {/* Body */}
      <div className="card-soft p-8 sm:p-10 mb-8" data-testid={`wizard-card-${currentKey}`}>
        {children}
      </div>

      {/* Footer nav */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => (prev ? navigate(prev.path) : navigate("/dashboard"))}
          className="btn-soft flex items-center gap-2"
          data-testid="wizard-back-button"
        >
          <ArrowLeft size={16} /> {prev ? prev.label : "Dashboard"}
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={saving}
          className="btn-sage flex items-center gap-2"
          data-testid="wizard-next-button"
        >
          {saving ? "Saving…" : nextLabel || (next ? `Continue: ${next.label}` : "Finish")}
          {!saving && (next ? <ArrowRight size={16} /> : <Check size={16} />)}
        </button>
      </div>
    </div>
  );
}

export { STEPS };
