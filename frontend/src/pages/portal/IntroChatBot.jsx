import React, { useEffect, useMemo, useRef, useState } from "react";

const INTRO_SEEN_KEY = "sacoparents_intro_chat_seen_v1";

export function hasIntroBeenSeen() {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(INTRO_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

export function markIntroSeen() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(INTRO_SEEN_KEY, "1");
  } catch {
    /* noop */
  }
}

/**
 * IntroChatBot — friendly "SA CoParents Guide" onboarding modal.
 *
 * Chat-style intro that greets first-time visitors, explains the two
 * paths (Coparenting Journey vs Court-Ordered), and offers a "Help
 * Me Choose" mini-triage that recommends a path from three yes/no
 * answers.
 *
 * Copy is authored by the founder and must remain in exact lockstep
 * with the marketing site — do NOT rephrase for LLM taste.
 *
 * Props:
 *   - open: bool
 *   - onClose: () => void
 *   - onEnterParent: () => void  // routes to Coparenting Journey door
 *   - onEnterCourt: () => void   // routes to Court-Ordered / Court-Key door
 */
const INTRO_MESSAGES = [
  "Hi. I\u2019m your SA CoParents Guide.",
  "Every family\u2019s situation is different. I\u2019m here to help you get started and guide you through the next steps.",
  "SA CoParents is designed to help you understand your situation, focus on your child\u2019s needs, and prepare for better decisions and agreements.",
  "Before we begin, tell me how you arrived here:",
];

const PARENT_BENEFITS = [
  "Understand your current co-parenting situation",
  "Identify your child\u2019s needs",
  "Recognize areas where you and the other parent may agree or see things differently",
  "Build your Foundation Statement",
  "Explore communication, co-parenting, and conflict-resolution options",
  "Prepare for a possible Co-Parenting Agreement, Joint Report, or mediation",
];

const COURT_BENEFITS = [
  "Areas of agreement and disagreement",
  "Your child\u2019s needs",
  "Co-parenting and communication concerns",
  "Options and resources that may help",
  "Issues that may need professional assistance or conflict resolution",
];

const HELP_QUESTIONS = [
  {
    key: "court_directed",
    prompt:
      "Has a court, judge, attorney, mediator, parent facilitator, therapist, or any other professional directed you to SA CoParents?",
  },
  {
    key: "active_case",
    prompt:
      "Are you currently in an active custody case, mediation, or parent-facilitation process?",
  },
  {
    key: "voluntary",
    prompt:
      "Are you here voluntarily to work on your co-parenting on your own?",
  },
];

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Not sure" },
];

function recommendFrom(answers) {
  if (answers.court_directed === "yes" || answers.active_case === "yes") {
    return "court";
  }
  if (answers.voluntary === "yes") return "parent";
  // If everything is No / Not sure, the safer default is the voluntary
  // path — parents can switch to the Court-Ordered door anytime.
  return "parent";
}

const RECOMMEND_COPY = {
  parent: {
    title: "The Co-Parenting Journey looks like the right starting point.",
    body:
      "You can move through it at your own pace. If a professional later directs you to a specific assessment, you can switch to the Court-Ordered path anytime.",
    cta: "Start My Co-Parenting Journey",
    testid: "intro-recommend-start-parent",
    action: "parent",
  },
  court: {
    title: "The Court-Ordered path is the right starting point.",
    body:
      "I\u2019ll walk you through the assessments or activities you\u2019ve been asked to complete. If you\u2019d also like to work on your co-parenting on your own, you can visit the Co-Parenting Journey anytime.",
    cta: "Start My Court-Ordered Journey",
    testid: "intro-recommend-start-court",
    action: "court",
  },
};

export function IntroChatBot({
  open,
  onClose,
  onEnterParent,
  onEnterCourt,
}) {
  // 'paths' — initial 2-CTA screen. 'help' — three-question triage.
  // 'recommend' — recap with the recommended path.
  const [phase, setPhase] = useState("paths");
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    // Reset every time the modal is (re-)opened so a returning user
    // doesn't see stale answers.
    setPhase("paths");
    setStep(0);
    setAnswers({});
  }, [open]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [phase, step]);

  const closeAndMark = (fn) => () => {
    markIntroSeen();
    if (typeof fn === "function") fn();
    onClose();
  };

  const recommended = useMemo(() => recommendFrom(answers), [answers]);

  if (!open) return null;

  const rec = RECOMMEND_COPY[recommended];

  return (
    <div
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 no-print"
      data-testid="intro-chat-modal"
    >
      <div className="bg-white w-full max-w-sm sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col h-[92vh] sm:h-[90vh]">
        {/* Header */}
        <div className="flex justify-between items-start border-b border-slate-100 p-3 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-700 to-purple-900 flex items-center justify-center shrink-0">
              <i className="fa-solid fa-hands-holding-child text-white text-sm"></i>
            </div>
            <div className="min-w-0">
              <div className="text-[9px] font-bold text-purple-800 uppercase tracking-wider">
                Welcome
              </div>
              <h3 className="font-bold text-slate-800 text-sm truncate">
                SA CoParents Guide
              </h3>
            </div>
          </div>
          <button
            type="button"
            data-testid="intro-chat-close"
            onClick={() => {
              markIntroSeen();
              onClose();
            }}
            className="text-slate-400 hover:text-slate-600 p-1 shrink-0"
            aria-label="Close welcome"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        {/* Chat scroll */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50"
          data-testid="intro-chat-scroll"
        >
          {phase === "paths" && (
            <>
              {INTRO_MESSAGES.map((m, i) => (
                <div className="flex justify-start" key={`intro-${i}`}>
                  <div
                    className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm"
                    data-testid={`intro-msg-${i}`}
                  >
                    {m}
                  </div>
                </div>
              ))}

              {/* Path A card */}
              <div
                className="p-3 bg-white rounded-2xl border border-purple-200 shadow-sm space-y-2"
                data-testid="intro-path-parent-card"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-purple-800 text-base leading-none">
                    <i className="fa-solid fa-circle-user"></i>
                  </span>
                  <h4 className="text-xs font-bold text-slate-800">
                    I’m Here to Work on Co-Parenting
                  </h4>
                </div>
                <p className="text-[11px] text-slate-600 leading-snug">
                  Choose this path if you are starting on your own or
                  voluntarily working on your co-parenting relationship.
                </p>
                <ul className="text-[10px] text-slate-600 space-y-0.5 pl-3 list-disc">
                  {PARENT_BENEFITS.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  data-testid="intro-start-parent-journey"
                  onClick={closeAndMark(onEnterParent)}
                  className="w-full py-2 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-arrow-right mr-1"></i>
                  Start My Co-Parenting Journey
                </button>
              </div>

              {/* Path B card */}
              <div
                className="p-3 bg-white rounded-2xl border border-amber-300 shadow-sm space-y-2"
                data-testid="intro-path-court-card"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-amber-700 text-base leading-none">
                    <i className="fa-solid fa-scale-balanced"></i>
                  </span>
                  <h4 className="text-xs font-bold text-slate-800">
                    I’m Here Because of a Court Order
                  </h4>
                </div>
                <p className="text-[11px] text-slate-600 leading-snug">
                  Choose this path if a court, attorney, mediator, parent
                  facilitator, therapist, or other professional directed
                  you to SA CoParents.
                </p>
                <p className="text-[11px] text-slate-600 leading-snug">
                  I’ll guide you through the assessments or activities
                  you have been asked to complete. Your responses can then
                  be used to help identify:
                </p>
                <ul className="text-[10px] text-slate-600 space-y-0.5 pl-3 list-disc">
                  {COURT_BENEFITS.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  data-testid="intro-start-court-journey"
                  onClick={closeAndMark(onEnterCourt)}
                  className="w-full py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-arrow-right mr-1"></i>
                  Start My Court-Ordered Journey
                </button>
              </div>

              {/* Help Me Choose */}
              <div
                className="p-3 bg-white rounded-2xl border border-dashed border-slate-300 shadow-sm space-y-2"
                data-testid="intro-help-choose-card"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500 text-sm leading-none">
                    <i className="fa-solid fa-circle-question"></i>
                  </span>
                  <h4 className="text-xs font-bold text-slate-800">
                    Not Sure Which Path to Choose?
                  </h4>
                </div>
                <p className="text-[11px] text-slate-600 leading-snug">
                  That’s okay. I can ask you a few simple questions
                  and help you identify the appropriate starting point.
                </p>
                <button
                  type="button"
                  data-testid="intro-help-me-choose"
                  onClick={() => {
                    setPhase("help");
                    setStep(0);
                  }}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-comment-dots mr-1"></i>
                  Help Me Choose
                </button>
              </div>

              {/* Footer aphorism */}
              <div className="pt-2 pb-3 text-center space-y-1">
                <p className="text-[10px] text-slate-500 italic">
                  You can move through SA CoParents at your own pace. The
                  goal isn’t to decide which parent is right or wrong.
                  The goal is to better understand your parenting situation
                  and keep your child’s needs at the center of what
                  happens next.
                </p>
                <p className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
                  Start with Alignment. Move Toward Agreement.
                </p>
              </div>
            </>
          )}

          {phase === "help" && (
            <>
              <div className="flex justify-start">
                <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                  Great — a few quick questions and I’ll point
                  you to the best starting place.
                </div>
              </div>
              {/* Prior answers echoed as chat bubbles */}
              {HELP_QUESTIONS.slice(0, step).map((q) => (
                <React.Fragment key={q.key}>
                  <div className="flex justify-start">
                    <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                      {q.prompt}
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="max-w-[85%] bg-purple-800 text-white rounded-2xl rounded-tr-sm p-2.5 text-[12px] leading-snug">
                      {
                        YES_NO_OPTIONS.find((o) => o.value === answers[q.key])
                          ?.label
                      }
                    </div>
                  </div>
                </React.Fragment>
              ))}
              {/* Current question */}
              {step < HELP_QUESTIONS.length && (
                <>
                  <div className="flex justify-start">
                    <div
                      className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm"
                      data-testid={`intro-help-q-${step}`}
                    >
                      {HELP_QUESTIONS[step].prompt}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    {YES_NO_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        data-testid={`intro-help-q-${step}-${opt.value}`}
                        onClick={() => {
                          const nextAnswers = {
                            ...answers,
                            [HELP_QUESTIONS[step].key]: opt.value,
                          };
                          setAnswers(nextAnswers);
                          if (step + 1 >= HELP_QUESTIONS.length) {
                            setPhase("recommend");
                          } else {
                            setStep(step + 1);
                          }
                        }}
                        className="py-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-xs"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
              <button
                type="button"
                data-testid="intro-help-back"
                onClick={() => {
                  setPhase("paths");
                  setStep(0);
                  setAnswers({});
                }}
                className="w-full mt-2 py-1.5 text-[10px] text-slate-400 hover:text-slate-600 underline"
              >
                Back to the paths
              </button>
            </>
          )}

          {phase === "recommend" && (
            <>
              <div className="flex justify-start">
                <div
                  className="max-w-[92%] bg-white border border-purple-200 rounded-2xl rounded-tl-sm p-2.5 shadow-sm space-y-1"
                  data-testid="intro-recommend-card"
                >
                  <div className="flex items-center gap-1.5">
                    <i className="fa-solid fa-lightbulb text-amber-500 text-xs"></i>
                    <span className="text-[9px] font-bold text-purple-800 uppercase tracking-wider">
                      Recommended
                    </span>
                  </div>
                  <div
                    className="text-[13px] font-bold text-slate-800 leading-snug"
                    data-testid="intro-recommend-title"
                  >
                    {rec.title}
                  </div>
                  <p className="text-[11px] text-slate-600 leading-snug">
                    {rec.body}
                  </p>
                </div>
              </div>
              <div className="pt-2 space-y-2">
                <button
                  type="button"
                  data-testid={rec.testid}
                  onClick={closeAndMark(
                    rec.action === "court" ? onEnterCourt : onEnterParent
                  )}
                  className={
                    rec.action === "court"
                      ? "w-full py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-xs"
                      : "w-full py-2.5 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
                  }
                >
                  <i className="fa-solid fa-arrow-right mr-1"></i>
                  {rec.cta}
                </button>
                <button
                  type="button"
                  data-testid="intro-recommend-back"
                  onClick={() => setPhase("paths")}
                  className="w-full py-1.5 text-[10px] text-slate-400 hover:text-slate-600 underline"
                >
                  Show me both paths again
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
