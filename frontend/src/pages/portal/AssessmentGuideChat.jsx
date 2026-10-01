import React, { useMemo, useRef, useEffect, useState } from "react";

/**
 * AssessmentGuideChat — iter232 "SA CoParents Assessment Guide"
 *
 * A separate chatbot from IntroChatBot (which picks a PATH — voluntary
 * vs court-ordered). This one helps a parent who is already inside the
 * Coparenting Journey pick WHICH ASSESSMENT to start with. Copy is
 * authored verbatim by the founder — do not paraphrase.
 *
 * Props:
 *   - open : bool
 *   - onClose : () => void
 *   - onStartAssessment : (targetKey) => void
 *     targetKey ∈ {'coparenting', 'communication', 'safety', 'educational',
 *                  'medical', 'psychological', 'court'}
 *   - safetyFlagged : bool  // grey-rock header hint (parity with IntroChatBot)
 */
const OPTIONS = [
  {
    key: "coparenting",
    icon: "fa-solid fa-people-roof",
    color: "purple",
    number: "1.",
    heading: "Our Overall Co-Parenting Relationship",
    label: "Co-Parenting Assessment",
    ctaLabel: "Start Co-Parenting Assessment",
    why:
      "Choose this if you want to look at how you and the other parent are currently working together, where things are going well, and where you may need more structure or support.",
    topics: [
      "Areas of agreement and disagreement",
      "Co-parenting strengths",
      "Sources of conflict",
      "Areas where clearer expectations may help",
      "Options and resources for moving forward",
    ],
  },
  {
    key: "communication",
    icon: "fa-solid fa-comment-dots",
    color: "purple",
    number: "2.",
    heading: "Communication Between Parents",
    label: "Communication Assessment",
    ctaLabel: "Start Communication Assessment",
    why:
      "Choose this if conversations, texts, emails, or decision-making between parents are difficult, emotional, confusing, or frequently lead to conflict.",
    topics: [
      "Communication patterns",
      "Common triggers",
      "Areas where communication breaks down",
      "Whether more structured communication may help",
      "Communication tools and resources",
    ],
    footnote:
      "You may also be guided to the SA CoParents Communication Coach to help prepare for a specific conversation.",
  },
  {
    key: "safety",
    icon: "fa-solid fa-shield-halved",
    color: "amber",
    number: "3.",
    heading: "Safety or Family Violence Concerns",
    label: "Communication Safety / Family Violence Assessment",
    ctaLabel: "Start Safety Assessment",
    why:
      "Choose this if you have concerns about threats, intimidation, controlling behavior, stalking, physical safety, fear, or whether direct communication with the other parent is appropriate.",
    topics: [
      "Safeguards to consider first",
      "Communication boundaries",
      "Professional resources",
      "Whether direct communication is currently appropriate",
    ],
    footnote:
      "This assessment focuses on safety first and may identify safeguards, communication boundaries, and professional resources that should be considered before proceeding with other co-parenting activities.",
  },
  {
    key: "educational",
    icon: "fa-solid fa-book-open",
    color: "purple",
    number: "4.",
    heading: "My Child\u2019s Educational Needs",
    label: "Educational Assessment",
    ctaLabel: "Start Educational Assessment",
    why:
      "Choose this when parents need to make decisions about school or educational support.",
    topics: [
      "School selection",
      "Academic concerns",
      "ARD/IEP issues",
      "Tutoring",
      "School counseling",
      "Educational evaluations",
      "Parent participation in school decisions",
    ],
  },
  {
    key: "medical",
    icon: "fa-solid fa-briefcase-medical",
    color: "purple",
    number: "5.",
    heading: "My Child\u2019s Medical Needs",
    label: "Medical Assessment",
    ctaLabel: "Start Medical Assessment",
    why:
      "Choose this when parents need help identifying agreements or differences involving their child\u2019s healthcare.",
    topics: [
      "Doctors and specialists",
      "Medical appointments",
      "Prescriptions",
      "Sharing medical information",
      "Treatment decisions",
      "Responsibility for coordinating care",
    ],
  },
  {
    key: "psychological",
    icon: "fa-solid fa-brain",
    color: "purple",
    number: "6.",
    heading: "My Child\u2019s Psychological or Emotional Needs",
    label: "Psychological Assessment",
    ctaLabel: "Start Psychological Assessment",
    why:
      "Choose this when there are questions or differences concerning your child\u2019s emotional, behavioral, or mental-health needs.",
    topics: [
      "Counseling",
      "Psychological evaluations",
      "ADHD or behavioral concerns",
      "Mental-health professionals",
      "Medication and treatment options",
      "Parent participation in treatment decisions",
    ],
  },
  {
    key: "court",
    icon: "fa-solid fa-scale-balanced",
    color: "amber",
    number: "7.",
    heading: "I Was Ordered or Referred to SA CoParents",
    label: "Court-Ordered / Professional Referral Path",
    ctaLabel: "Continue Court-Ordered Path",
    why:
      "Choose this if a court, attorney, mediator, therapist, parent facilitator, or other professional directed you to complete SA CoParents assessments.",
    topics: [
      "I\u2019ll help you identify the assessments requested",
      "I\u2019ll guide you through them in the appropriate order",
    ],
  },
];

const HELP_QUESTIONS = [
  {
    key: "safety_concern",
    prompt:
      "Do you have any concerns about threats, intimidation, controlling behavior, stalking, or physical safety with the other parent?",
  },
  {
    key: "child_area",
    prompt:
      "Is there a specific area of your child\u2019s life you\u2019d like help with right now?",
    options: [
      { value: "educational", label: "School / education" },
      { value: "medical", label: "Medical / health" },
      { value: "psychological", label: "Emotional / mental health" },
      { value: "none", label: "None specifically" },
    ],
  },
  {
    key: "communication_focus",
    prompt:
      "Would you like help with a specific message, text, or conversation between you and your co-parent?",
  },
];

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Not sure" },
];

function recommendFromHelp(answers) {
  if (answers.safety_concern === "yes") return "safety";
  const area = answers.child_area;
  if (area && area !== "none") return area;
  if (answers.communication_focus === "yes") return "communication";
  return "coparenting";
}

/**
 * Internal shared body — renders the chat scroll area + footer CTAs.
 * Used by both the modal-mode <AssessmentGuideChat> and the
 * inline-mode <AssessmentGuideChatInline> so copy + routing stay in
 * exact lockstep between both surfaces.
 */
function AssessmentGuideBody({
  onStartAssessment,
  onClose,
  safetyFlagged,
  inline,
}) {
  // 'list' — 8 selection cards; 'recap' — per-selection card;
  // 'help' — mini triage; 'help-recap' — recap of triage recommendation.
  const [phase, setPhase] = useState("list");
  const [selectedKey, setSelectedKey] = useState(null);
  const [helpStep, setHelpStep] = useState(0);
  const [helpAnswers, setHelpAnswers] = useState({});
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [phase, helpStep, selectedKey]);

  const selected = useMemo(
    () => OPTIONS.find((o) => o.key === selectedKey) || null,
    [selectedKey]
  );

  const helpRecommendationKey = useMemo(
    () => recommendFromHelp(helpAnswers),
    [helpAnswers]
  );
  const helpRecommendation = useMemo(
    () =>
      OPTIONS.find((o) => o.key === helpRecommendationKey) ||
      OPTIONS.find((o) => o.key === "coparenting"),
    [helpRecommendationKey]
  );

  // In inline mode we don't force a viewport-height flex column — the
  // whole card sits in normal document flow. The scroll region gets a
  // max-height so it can't grow to full page and swallow the toolkit.
  const scrollClass = inline
    ? "overflow-y-auto p-3 space-y-2 bg-slate-50 max-h-[520px]"
    : "flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50";
  const afterStart = () => {
    if (inline) {
      // Reset so the inline widget is ready for another triage cycle
      // instead of leaving a stale recap card visible after routing.
      setPhase("list");
      setSelectedKey(null);
      setHelpStep(0);
      setHelpAnswers({});
    } else if (typeof onClose === "function") {
      onClose();
    }
  };

  return (
    <>
      <div
        ref={scrollRef}
        className={scrollClass}
        data-testid="assessment-guide-scroll"
      >
        {phase === "list" && (
          <>
            <div className="flex justify-start">
              <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                Hi! I can help you decide where to start.
              </div>
            </div>
            <div className="flex justify-start">
              <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                You don’t have to complete every assessment. Choose the
                area that best matches what you want help with right
                now.
              </div>
            </div>
            <div className="flex justify-start">
              <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm font-semibold">
                What would you like help with?
              </div>
            </div>

            {OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                data-testid={`assessment-option-${opt.key}`}
                onClick={() => {
                  setSelectedKey(opt.key);
                  setPhase("recap");
                }}
                className={
                  opt.color === "amber"
                    ? "text-left w-full p-2.5 bg-white rounded-2xl border border-amber-300 hover:border-amber-500 hover:bg-amber-50 shadow-sm"
                    : "text-left w-full p-2.5 bg-white rounded-2xl border border-purple-200 hover:border-purple-500 hover:bg-purple-50 shadow-sm"
                }
              >
                <div className="flex items-start gap-2">
                  <div
                    className={
                      opt.color === "amber"
                        ? "w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center shrink-0"
                        : "w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0"
                    }
                  >
                    <i
                      className={
                        opt.color === "amber"
                          ? `${opt.icon} text-amber-700 text-xs`
                          : `${opt.icon} text-purple-800 text-xs`
                      }
                    ></i>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-slate-400 font-mono">
                      {opt.number}
                    </div>
                    <div className="text-xs font-bold text-slate-800 leading-snug">
                      {opt.heading}
                    </div>
                    <div
                      className={
                        opt.color === "amber"
                          ? "text-[10px] text-amber-700 font-semibold uppercase tracking-wider mt-0.5"
                          : "text-[10px] text-purple-700 font-semibold uppercase tracking-wider mt-0.5"
                      }
                    >
                      Choose: {opt.label}
                    </div>
                  </div>
                  <i className="fa-solid fa-chevron-right text-slate-300 text-xs mt-2"></i>
                </div>
              </button>
            ))}

            {/* Option 8 — Help Me Decide */}
            <button
              type="button"
              data-testid="assessment-option-help"
              onClick={() => {
                setPhase("help");
                setHelpStep(0);
                setHelpAnswers({});
              }}
              className="text-left w-full p-2.5 bg-white rounded-2xl border border-dashed border-slate-300 hover:border-slate-500 hover:bg-slate-50 shadow-sm"
            >
              <div className="flex items-start gap-2">
                <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                  <i className="fa-solid fa-circle-question text-slate-500 text-xs"></i>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] text-slate-400 font-mono">
                    8.
                  </div>
                  <div className="text-xs font-bold text-slate-800 leading-snug">
                    I’m Not Sure Where to Start
                  </div>
                  <div className="text-[10px] text-slate-600 mt-0.5">
                    That’s okay. I’ll ask you a few simple questions
                    about what is happening and help you identify
                    which assessment may be most relevant.
                  </div>
                </div>
                <i className="fa-solid fa-chevron-right text-slate-300 text-xs mt-2"></i>
              </div>
            </button>
          </>
        )}

        {phase === "recap" && selected && (
          <>
            <div className="flex justify-start">
              <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                You’ve selected <b>{selected.label}</b>.
              </div>
            </div>
            <div className="p-3 bg-white rounded-2xl border border-purple-200 shadow-sm space-y-2">
              <div>
                <div className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
                  Why parents choose this assessment
                </div>
                <p className="text-[12px] text-slate-700 leading-snug mt-0.5">
                  {selected.why}
                </p>
              </div>
              <div>
                <div className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
                  What you’ll explore
                </div>
                <ul className="text-[11px] text-slate-700 pl-3 list-disc space-y-0.5 mt-0.5">
                  {selected.topics.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
              {selected.footnote && (
                <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg text-[10px] text-slate-600 leading-snug italic">
                  {selected.footnote}
                </div>
              )}
              <div>
                <div className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
                  What happens afterward
                </div>
                <p className="text-[11px] text-slate-700 leading-snug mt-0.5">
                  Your responses can help you identify areas of
                  agreement, areas that may need attention, and
                  possible options or resources for moving forward.
                </p>
              </div>
              {(() => {
                // iter235/iter236/iter238 — "See a sample report"
                // and "Try the preview" links in the recap card.
                // Each key maps to its public sample PDF; co-parenting
                // ALSO maps to a static interactive 30-question
                // preview form the founder dropped in so parents can
                // try the questions themselves before committing.
                const SAMPLE_URL_BY_KEY = {
                  coparenting:   "/api/insights/samples/coparenting-self-assessment.pdf",
                  educational:   "/api/insights/samples/snc-sample-individual-report-educational.pdf",
                  medical:       "/api/insights/samples/snc-sample-individual-report-medical.pdf",
                  psychological: "/api/insights/samples/snc-sample-individual-report-psychological.pdf",
                };
                const samplePath = SAMPLE_URL_BY_KEY[selected.key];
                // iter238 — only the Co-Parenting option has an
                // interactive preview form (the other three are
                // deep-dive assessments without a preview page).
                const previewHref =
                  selected.key === "coparenting"
                    ? "/coparenting-self-assessment-preview.html"
                    : null;
                if (!samplePath && !previewHref) return null;
                return (
                  <div className="flex flex-col gap-1 pt-1">
                    {samplePath && (
                      <a
                        href={`${process.env.REACT_APP_BACKEND_URL || ""}${samplePath}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid={`assessment-guide-sample-link-${selected.key}`}
                        className="inline-flex items-center gap-1.5 text-[11px] font-bold text-purple-800 hover:underline"
                      >
                        <i className="fa-solid fa-file-pdf"></i>
                        See a sample report
                      </a>
                    )}
                    {previewHref && (
                      <a
                        href={previewHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid="assessment-guide-preview-link-coparenting"
                        className="inline-flex items-center gap-1.5 text-[11px] font-bold text-amber-700 hover:underline"
                      >
                        <i className="fa-solid fa-wand-magic-sparkles"></i>
                        Try the preview — 30 quick questions
                      </a>
                    )}
                  </div>
                );
              })()}
            </div>
          </>
        )}

        {phase === "help" && (
          <>
            <div className="flex justify-start">
              <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                A few quick questions and I’ll suggest the best place
                to start.
              </div>
            </div>
            {HELP_QUESTIONS.slice(0, helpStep).map((q) => {
              const chosen = q.options
                ? q.options.find((o) => o.value === helpAnswers[q.key])
                : YES_NO_OPTIONS.find(
                    (o) => o.value === helpAnswers[q.key]
                  );
              return (
                <React.Fragment key={q.key}>
                  <div className="flex justify-start">
                    <div className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm">
                      {q.prompt}
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="max-w-[85%] bg-purple-800 text-white rounded-2xl rounded-tr-sm p-2.5 text-[12px] leading-snug">
                      {chosen?.label}
                    </div>
                  </div>
                </React.Fragment>
              );
            })}
            {helpStep < HELP_QUESTIONS.length && (
              <>
                <div className="flex justify-start">
                  <div
                    className="max-w-[92%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm"
                    data-testid={`assessment-help-q-${helpStep}`}
                  >
                    {HELP_QUESTIONS[helpStep].prompt}
                  </div>
                </div>
                <div
                  className={
                    HELP_QUESTIONS[helpStep].options
                      ? "grid grid-cols-2 gap-2 pt-1"
                      : "grid grid-cols-3 gap-2 pt-1"
                  }
                >
                  {(
                    HELP_QUESTIONS[helpStep].options || YES_NO_OPTIONS
                  ).map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      data-testid={`assessment-help-q-${helpStep}-${opt.value}`}
                      onClick={() => {
                        const nextAnswers = {
                          ...helpAnswers,
                          [HELP_QUESTIONS[helpStep].key]: opt.value,
                        };
                        setHelpAnswers(nextAnswers);
                        if (helpStep + 1 >= HELP_QUESTIONS.length) {
                          setPhase("help-recap");
                        } else {
                          setHelpStep(helpStep + 1);
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
          </>
        )}

        {phase === "help-recap" && helpRecommendation && (
          <>
            <div className="flex justify-start">
              <div
                className="max-w-[92%] bg-white border border-purple-200 rounded-2xl rounded-tl-sm p-2.5 shadow-sm space-y-1"
                data-testid="assessment-help-recommend"
              >
                <div className="flex items-center gap-1.5">
                  <i className="fa-solid fa-lightbulb text-amber-500 text-xs"></i>
                  <span className="text-[9px] font-bold text-purple-800 uppercase tracking-wider">
                    Recommended
                  </span>
                </div>
                <div
                  className="text-[13px] font-bold text-slate-800 leading-snug"
                  data-testid="assessment-help-recommend-label"
                >
                  {helpRecommendation.label}
                </div>
                <p className="text-[11px] text-slate-600 leading-snug">
                  {helpRecommendation.why}
                </p>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="p-3 border-t border-slate-100 bg-white space-y-2">
        {phase === "list" && (
          <p className="text-[10px] text-slate-400 text-center leading-snug">
            Tap any area above to see the details before starting.
          </p>
        )}
        {phase === "recap" && selected && (
          <>
            <button
              type="button"
              data-testid={`assessment-start-${selected.key}`}
              onClick={() => {
                onStartAssessment(selected.key);
                afterStart();
              }}
              className={
                selected.color === "amber"
                  ? "w-full py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-xs"
                  : "w-full py-2.5 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
              }
            >
              <i className="fa-solid fa-arrow-right mr-1"></i>
              {selected.ctaLabel}
            </button>
            <button
              type="button"
              data-testid="assessment-back-to-list"
              onClick={() => {
                setPhase("list");
                setSelectedKey(null);
              }}
              className="w-full py-1.5 text-[11px] text-slate-500 hover:text-slate-700 underline"
            >
              Choose Another Area
            </button>
          </>
        )}
        {phase === "help" && (
          <button
            type="button"
            data-testid="assessment-help-back"
            onClick={() => {
              setPhase("list");
              setHelpStep(0);
              setHelpAnswers({});
            }}
            className="w-full py-1.5 text-[11px] text-slate-500 hover:text-slate-700 underline"
          >
            Back to the list
          </button>
        )}
        {phase === "help-recap" && helpRecommendation && (
          <>
            <button
              type="button"
              data-testid={`assessment-help-start-${helpRecommendation.key}`}
              onClick={() => {
                onStartAssessment(helpRecommendation.key);
                afterStart();
              }}
              className={
                helpRecommendation.color === "amber"
                  ? "w-full py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-xs"
                  : "w-full py-2.5 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
              }
            >
              <i className="fa-solid fa-arrow-right mr-1"></i>
              {helpRecommendation.ctaLabel}
            </button>
            <button
              type="button"
              data-testid="assessment-help-back-from-recap"
              onClick={() => setPhase("list")}
              className="w-full py-1.5 text-[11px] text-slate-500 hover:text-slate-700 underline"
            >
              Show me the full list
            </button>
          </>
        )}
      </div>
    </>
  );
}

/**
 * Inline variant — same chat, mounted on the Alignment & Tools page
 * instead of appearing as a popup. No overlay, no viewport-height,
 * no close button. Chat resets to the list phase after routing.
 */
export function AssessmentGuideChatInline({
  onStartAssessment,
  safetyFlagged = false,
}) {
  return (
    <div
      className="bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden card-box"
      data-testid="assessment-guide-inline"
    >
      <div className="flex items-center gap-2 border-b border-slate-100 p-3">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-700 to-purple-900 flex items-center justify-center shrink-0">
          <i className="fa-solid fa-clipboard-question text-white text-sm"></i>
        </div>
        <div className="min-w-0">
          <div className="text-[9px] font-bold text-purple-800 uppercase tracking-wider">
            {safetyFlagged ? "Grey-rock" : "Assessment Guide"}
          </div>
          <h3 className="font-bold text-slate-800 text-sm truncate">
            SA CoParents Assessment Guide
          </h3>
        </div>
      </div>
      <AssessmentGuideBody
        onStartAssessment={onStartAssessment}
        onClose={undefined}
        safetyFlagged={safetyFlagged}
        inline
      />
    </div>
  );
}

export function AssessmentGuideChat({
  open,
  onClose,
  onStartAssessment,
  safetyFlagged = false,
}) {
  // Force-remount the body every time the modal opens so the phase
  // resets cleanly (list → recap state doesn't carry over between
  // opens). Cheaper + safer than lifting state up.
  const [instanceId, setInstanceId] = useState(0);
  useEffect(() => {
    if (open) setInstanceId((n) => n + 1);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 no-print"
      data-testid="assessment-guide-modal"
    >
      <div className="bg-white w-full max-w-sm sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col h-[92vh] sm:h-[90vh]">
        <div className="flex justify-between items-start border-b border-slate-100 p-3 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-700 to-purple-900 flex items-center justify-center shrink-0">
              <i className="fa-solid fa-clipboard-question text-white text-sm"></i>
            </div>
            <div className="min-w-0">
              <div className="text-[9px] font-bold text-purple-800 uppercase tracking-wider">
                {safetyFlagged ? "Grey-rock" : "Assessment Guide"}
              </div>
              <h3 className="font-bold text-slate-800 text-sm truncate">
                SA CoParents Assessment Guide
              </h3>
            </div>
          </div>
          <button
            type="button"
            data-testid="assessment-guide-close"
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-600 p-1 shrink-0"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        <AssessmentGuideBody
          key={instanceId}
          onStartAssessment={onStartAssessment}
          onClose={onClose}
          safetyFlagged={safetyFlagged}
          inline={false}
        />
      </div>
    </div>
  );
}
