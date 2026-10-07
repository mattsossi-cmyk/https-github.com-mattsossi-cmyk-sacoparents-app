import React from "react";

import { CONTENT, STEPS, scaleLabel } from "./content";
import { CoachBubble, ParentBubble, SectionDivider, TypingBubble } from "./ChatBubbles";

function StepPrompt({ step }) {
  if (step.type === "intro") {
    return (
      <>
        {CONTENT.intro.map((line, i) => (
          <CoachBubble key={i} testid={`sa-chat-intro-${i}`} showAvatar={i === CONTENT.intro.length - 1}>
            {line}
          </CoachBubble>
        ))}
        <CoachBubble testid="sa-chat-safety-note">
          <i className="fa-solid fa-shield-heart text-rose-500 mr-1.5"></i>
          {CONTENT.safety_note}
        </CoachBubble>
      </>
    );
  }
  if (step.type === "goal") {
    return (
      <CoachBubble testid="sa-chat-prompt-goal">
        <span className="font-semibold">{CONTENT.goal.prompt}</span>
        <span className="block text-[11.5px] text-slate-500 mt-1">{CONTENT.goal.helper}</span>
      </CoachBubble>
    );
  }
  return <CoachBubble testid={`sa-chat-prompt-${step.id}`}>{step.prompt}</CoachBubble>;
}

function StepHeader({ step }) {
  if (step.type === "rate" && step.index === 0) {
    return (
      <SectionDivider testid={`sa-chat-section-${step.section.key}`} number={step.section.number} title={step.section.title} />
    );
  }
  if (step.type === "reflect" && step.index === 0) {
    return (
      <>
        <SectionDivider testid="sa-chat-section-reflection" number={CONTENT.reflection.number} title={CONTENT.reflection.title} />
        <CoachBubble>{CONTENT.reflection.intro}</CoachBubble>
      </>
    );
  }
  return null;
}

function StepReply({ step, draft }) {
  if (step.type === "intro") return <ParentBubble>{CONTENT.start_label}</ParentBubble>;
  if (step.type === "rate") {
    const v = draft.answers[step.id];
    return <ParentBubble testid={`sa-chat-reply-${step.id}`}>{`${v} — ${scaleLabel(v)}`}</ParentBubble>;
  }
  const text = step.type === "reflect" ? draft.reflections[step.id] : draft.goal;
  return text ? (
    <ParentBubble testid={`sa-chat-reply-${step.id}`}>{text}</ParentBubble>
  ) : (
    <ParentBubble testid={`sa-chat-reply-${step.id}`} muted>
      Skipped
    </ParentBubble>
  );
}

export function ChatTranscript({ draft, currentIdx, typing, resumeAt }) {
  return STEPS.slice(0, currentIdx + 1).map((step, i) => {
    const isCurrent = i === currentIdx;
    return (
      <React.Fragment key={step.id}>
        <StepHeader step={step} />
        {isCurrent && resumeAt === i && i > 1 && <CoachBubble testid="sa-chat-resume">{CONTENT.resume_message}</CoachBubble>}
        {isCurrent && typing ? <TypingBubble /> : <StepPrompt step={step} />}
        {!isCurrent && <StepReply step={step} draft={draft} />}
      </React.Fragment>
    );
  });
}
