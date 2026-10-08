import React, { useEffect, useState } from "react";

import { CONTENT, REFLECTIONS, SCALE } from "./content";
import { BackLink, TextReply } from "./ChatComposer";

const STATUS_COPY = {
  idle: "Your answers save to your account automatically",
  pending: "Saving…",
  saving: "Saving…",
  saved: "Saved to your account",
  local: "Saved on this device",
  error: "Saved on this device — we'll retry your account on your next answer",
};

const Shell = ({ title, children, status }) => (
  <div data-testid="sa-question-panel" className="bg-white rounded-2xl p-6 shadow-md border border-purple-100 mt-6">
    <h4 data-testid="sa-question-title" className="text-base font-bold text-[#3B1C6B] mb-2">
      {title}
    </h4>
    {children}
    {status && (
      <p data-testid="self-assessment-save-status" data-status={status} className="text-[10px] text-slate-400 text-center mt-4">
        {STATUS_COPY[status] || STATUS_COPY.idle}
      </p>
    )}
  </div>
);

function IntroPanel() {
  return (
    <Shell title="Before you begin">
      <div className="space-y-2 text-sm text-slate-600 leading-relaxed">
        {CONTENT.intro.map((line, i) => (
          <p key={i} data-testid={`sa-intro-${i}`} className="whitespace-pre-line">
            {line}
          </p>
        ))}
        <p data-testid="sa-intro-safety" className="rounded-xl bg-rose-50 border border-rose-100 px-3 py-2 text-[13px] text-rose-900">
          <i className="fa-solid fa-shield-heart text-rose-500 mr-1.5"></i>
          {CONTENT.safety_note}
        </p>
      </div>
    </Shell>
  );
}

function RatePanel({ step, onAnswer, onBack, status }) {
  const [picked, setPicked] = useState(null);
  useEffect(() => setPicked(null), [step.id]);
  const pick = (v) => {
    if (picked != null) return;
    setPicked(v);
    setTimeout(() => onAnswer(v), 280);
  };
  const { section } = step;
  return (
    <Shell
      status={status}
      title={`Question ${step.index + 1} of ${section.questions.length} · Step ${section.number}: ${section.title}`}
    >
      <p data-testid="sa-question-prompt" className="text-sm text-slate-600 mb-4">
        {step.prompt}
      </p>
      <div role="radiogroup" aria-label={step.prompt} className="space-y-2 text-xs md:text-sm">
        {SCALE.map((s) => (
          <label
            key={s.value}
            data-testid={`sa-option-${s.value}`}
            className={`flex items-center p-3 rounded-xl border cursor-pointer transition-colors ${
              picked === s.value
                ? "border-purple-500 bg-purple-50"
                : "border-slate-200 hover:border-purple-400 hover:bg-purple-50/50"
            }`}
          >
            <input
              type="radio"
              name={step.id}
              checked={picked === s.value}
              onChange={() => pick(s.value)}
              className="accent-purple-600 w-4 h-4"
            />
            <span className="ml-3 font-medium text-slate-700">
              <span className="font-extrabold text-[#3B1C6B] mr-1.5">{s.value}</span>
              {s.label}
            </span>
          </label>
        ))}
      </div>
      <div className="mt-3">
        <BackLink onBack={onBack} />
      </div>
    </Shell>
  );
}

function ReflectPanel({ step, onSave, onBack, status }) {
  return (
    <Shell status={status} title={`Reflection ${step.index + 1} of ${REFLECTIONS.length} · Step 5: ${CONTENT.reflection.title}`}>
      {step.index === 0 && <p className="text-xs text-slate-500 mb-2">{CONTENT.reflection.intro}</p>}
      <p data-testid="sa-question-prompt" className="text-sm text-slate-700 font-medium mb-3">
        {step.prompt}
      </p>
      <TextReply
        key={step.id}
        testidPrefix="sa-reflect"
        placeholder="Type your reflection…"
        sendLabel="Next"
        skipLabel="Skip"
        onSend={onSave}
        onSkip={() => onSave("")}
        onBack={onBack}
      />
    </Shell>
  );
}

function GoalPanel({ draft, onFinish, onBack, busy, status }) {
  return (
    <Shell status={status} title="Step 6: Set Your Personal Goal">
      <p data-testid="sa-question-prompt" className="text-sm text-slate-700 font-medium">
        {CONTENT.goal.prompt}
      </p>
      <p className="text-xs text-slate-500 mt-1 mb-3">{CONTENT.goal.helper}</p>
      <TextReply
        testidPrefix="sa-goal"
        initial={draft.reflections.goal_before_next || ""}
        placeholder="e.g. Pause and wait an hour before replying to a difficult message"
        sendLabel="Set my goal & see results"
        skipLabel="Skip for now"
        busy={busy}
        onSend={onFinish}
        onSkip={() => onFinish("")}
        onBack={onBack}
      />
    </Shell>
  );
}

export function QuestionPanel({ step, draft, update, onFinish, onBack, busy, status }) {
  if (!step || step.type === "intro") return <IntroPanel />;
  if (step.type === "rate") {
    const onAnswer = (v) => update((d) => ({ ...d, answers: { ...d.answers, [step.id]: v } }));
    return <RatePanel step={step} onAnswer={onAnswer} onBack={onBack} status={status} />;
  }
  if (step.type === "reflect") {
    const onSave = (text) => update((d) => ({ ...d, reflections: { ...d.reflections, [step.id]: text } }));
    return <ReflectPanel step={step} onSave={onSave} onBack={onBack} status={status} />;
  }
  return <GoalPanel draft={draft} onFinish={onFinish} onBack={onBack} busy={busy} status={status} />;
}
