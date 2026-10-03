import React, { useMemo, useState } from "react";

import { GreyRockToggleChip } from "./AlignmentHub";

/**
 * JourneyShell — iter244 Phase A.
 *
 * The five-step parent-facing scaffold. The ONE rule set in
 * NORTH_STAR.md: parents should see the five steps and nothing
 * else. Every current tool/assessment/report lives behind one of
 * these steps.
 *
 * Phase A deliberately keeps old components intact. Steps 2–5 for
 * now route into the existing parent-journey screen (which still
 * renders the AlignmentHub + BiffTab + guided journey). Phase B
 * (iter245) will absorb those surfaces INTO the step cards
 * themselves, deleting the toolkit tile grid and hub-section tabs.
 *
 * Testids: `journey-shell`, `journey-step-{n}`, `journey-step-{n}-cta`.
 * Old testids on existing components stay untouched.
 */
const STEPS = [
  {
    n: 1,
    title: "Start My Journey",
    tagline: "Tell us how you got here.",
    body: "Two short questions and we'll pick the right starting point — whether you're here on your own or because a court, mediator, or attorney referred you.",
    icon: "fa-door-open",
    tint: "purple",
  },
  {
    n: 2,
    title: "Understand My Situation",
    tagline: "A quiet check on where things stand.",
    body: "Private safety check, a quick 40-question profile, and a progress snapshot. Nothing you do here is shared with anyone unless you decide to.",
    icon: "fa-compass",
    tint: "indigo",
  },
  {
    n: 3,
    title: "Focus on My Child",
    tagline: "What does your child actually need?",
    body: "The full co-parenting assessment plus optional deep-dives for Educational, Medical, or Psychological needs. Choose what fits — skip what doesn't.",
    icon: "fa-child-reaching",
    tint: "emerald",
  },
  {
    n: 4,
    title: "Explore Options",
    tagline: "Try something before you commit to it.",
    body: "Rewrite a message the BIFF way, review conflict-resolution ideas, or walk through a mediation-prep script. Low-stakes, high-insight.",
    icon: "fa-wand-magic-sparkles",
    tint: "amber",
  },
  {
    n: 5,
    title: "Create My Plan",
    tagline: "Build something you can share.",
    body: "Draft your Foundation Statement, generate a fridge-size parenting card, request a Joint Report, or send a Progress Snapshot to your mediator.",
    icon: "fa-clipboard-check",
    tint: "rose",
  },
];

const TINT_CLASSES = {
  purple: {
    ring: "border-purple-300",
    chip: "bg-purple-100 text-purple-800",
    icon: "bg-purple-100 text-purple-700",
    cta: "bg-purple-600 hover:bg-purple-700 text-white",
    accent: "text-purple-700",
  },
  indigo: {
    ring: "border-indigo-300",
    chip: "bg-indigo-100 text-indigo-800",
    icon: "bg-indigo-100 text-indigo-700",
    cta: "bg-indigo-600 hover:bg-indigo-700 text-white",
    accent: "text-indigo-700",
  },
  emerald: {
    ring: "border-emerald-300",
    chip: "bg-emerald-100 text-emerald-800",
    icon: "bg-emerald-100 text-emerald-700",
    cta: "bg-emerald-600 hover:bg-emerald-700 text-white",
    accent: "text-emerald-700",
  },
  amber: {
    ring: "border-amber-300",
    chip: "bg-amber-100 text-amber-800",
    icon: "bg-amber-100 text-amber-700",
    cta: "bg-amber-600 hover:bg-amber-700 text-white",
    accent: "text-amber-700",
  },
  rose: {
    ring: "border-rose-300",
    chip: "bg-rose-100 text-rose-800",
    icon: "bg-rose-100 text-rose-700",
    cta: "bg-rose-600 hover:bg-rose-700 text-white",
    accent: "text-rose-700",
  },
};

/**
 * ProgressDots — iter249. 5-dot strip at the top of the shell
 * showing which steps the parent has "touched" so far. Dot
 * fills are driven by completion signals, not by current-step
 * cursor position — so a parent iterating back from Step 5 to
 * Step 2 still sees their earlier progress preserved.
 *
 * Fill signals (one per step):
 *   1. Start My Journey        pathPickedAt (any door chosen)
 *   2. Understand My Situation safetyAck (any — flagged or cleared)
 *   3. Focus on My Child       firstEngagementAt (any assessment opened)
 *   4. Explore Options         biffUsedAt (any BIFF draft logged)
 *   5. Create My Plan          hasSnapshots (any snapshot saved)
 */
function ProgressDots({
  pathPickedAt,
  safetyAck,
  firstEngagementAt,
  biffUsedAt,
  hasSnapshots,
}) {
  const states = [
    { n: 1, filled: !!pathPickedAt, label: "Started" },
    { n: 2, filled: !!safetyAck, label: "Checked" },
    { n: 3, filled: !!firstEngagementAt, label: "Assessed" },
    { n: 4, filled: !!biffUsedAt, label: "Explored" },
    { n: 5, filled: !!hasSnapshots, label: "Planned" },
  ];
  const filledCount = states.filter((s) => s.filled).length;

  return (
    <div
      data-testid="journey-progress-dots"
      className="bg-white rounded-xl border border-slate-200 px-3 py-2.5 flex items-center justify-between gap-2"
    >
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        {states.map((s, idx) => (
          <React.Fragment key={s.n}>
            <div
              data-testid={`journey-progress-dot-${s.n}`}
              data-filled={s.filled ? "true" : "false"}
              className={
                s.filled
                  ? "w-6 h-6 rounded-full bg-purple-700 text-white text-[10px] font-bold flex items-center justify-center shrink-0"
                  : "w-6 h-6 rounded-full bg-slate-100 text-slate-400 text-[10px] font-bold flex items-center justify-center border border-slate-200 shrink-0"
              }
              title={`Step ${s.n} — ${s.label}`}
            >
              {s.filled ? (
                <i className="fa-solid fa-check text-[9px]"></i>
              ) : (
                s.n
              )}
            </div>
            {idx < states.length - 1 && (
              <div
                className={
                  states[idx + 1].filled
                    ? "h-0.5 flex-1 bg-purple-700/60 rounded"
                    : "h-0.5 flex-1 bg-slate-200 rounded"
                }
              />
            )}
          </React.Fragment>
        ))}
      </div>
      <span
        data-testid="journey-progress-count"
        className="shrink-0 text-[10px] font-bold text-purple-800 bg-purple-100 px-2 py-0.5 rounded-full"
      >
        {filledCount}/5
      </span>
    </div>
  );
}

function pickCurrentStep({ safetyAck, pathPicked, firstEngagement, hasSnapshots, courtKey }) {
  // The system picks the "current" step for the parent. Rules:
  // iters (Phase B+) will replace this with signal from the
  // assessment & plan progress. For now:
  //  - court key verified → Step 3 (iter246 Phase C: a referred
  //    parent walks in holding a professional artefact; the next
  //    step for them is Focus on My Child, not Start)
  //  - no path picked → Step 1
  //  - path picked but no safety ack cleared/flagged → Step 2
  //  - safety ack present but no engagement → Step 2
  //  - engagement but no snapshots → Step 3
  //  - snapshots exist → Step 4 (parent is iterating)
  if (courtKey) return 3;
  if (!pathPicked) return 1;
  if (!safetyAck) return 2;
  if (!firstEngagement) return 2;
  if (!hasSnapshots) return 3;
  return 4;
}

export function JourneyShell({
  user,
  safetyAck,
  pathPickedAt,
  firstEngagementAt,
  snapshotCount,
  // iter249 — Step Progress Dots signals. biffUsedAt is derived
  // from the parent's BIFF log history (first time they drafted a
  // BIFF rewrite); it fills Dot 4 "Explore Options".
  biffUsedAt = null,
  courtKey = null,
  verifiedMediator = null,
  // Step 1 door CTAs — same handlers the old Gateway used, so the
  // Safety-First gate still fires before either door.
  onEnterParent = () => {},
  onEnterCourt = () => {},
  // Step 2 — safety check launcher + grey-rock controls.
  onOpenSafety = () => {},
  onClearGreyRock = () => {},
  onOpenSafetyRetake = () => {},
  // Step 2 — self-assessment preview URL (static HTML in /public).
  selfAssessmentUrl = "/coparenting-self-assessment-preview.html",
  // Step 3 — assessment topic handlers (openGuidedJourney in parent).
  onOpenGuidedJourney = () => {},
  onOpenAssessmentFolder = () => {},
  // Step 4 — BIFF Coach + Mediation Prep + Communication reflections.
  onOpenBiffCoach = () => {},
  // Step 5 — Foundation Statement + Share-complete-report + Email coparent.
  onOpenFoundationStatement = () => {},
  onDownloadCompleteReport = () => {},
  onShareCompleteReport = () => {},
  // Intro guide chip (soft, non-blocking).
  onOpenIntroGuide = () => {},
  // Grey-rock chip surface, if applicable.
  safetyFlagged = false,
}) {
  const safetyFlag = safetyFlagged || !!(safetyAck && safetyAck.flagged);
  const current = useMemo(
    () =>
      pickCurrentStep({
        safetyAck,
        pathPicked: !!pathPickedAt,
        firstEngagement: !!firstEngagementAt,
        hasSnapshots: snapshotCount > 0,
        courtKey: !!courtKey,
      }),
    [safetyAck, pathPickedAt, firstEngagementAt, snapshotCount, courtKey]
  );

  const [expanded, setExpanded] = useState(null);

  // If the parent hasn't explicitly toggled a step (expanded === null),
  // the shell follows whichever step `pickCurrentStep` says is current.
  // Once the parent manually toggles, we respect their choice. This
  // handles the case where courtKey or safetyAck hydrates from
  // localStorage AFTER mount — the shell re-targets the newly current
  // step instead of staying on whichever step was current on first
  // render.
  const activeStep = expanded ?? current;

  const greetingName = user?.name ? user.name.split(" ")[0] : null;

  return (
    <div
      data-testid="journey-shell"
      className="space-y-4"
    >
      {/* Soft welcome. Not a modal, not a door — just a line of
          text so the parent knows the five cards are a map, not a
          choice to make. */}
      <section className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-10 h-10 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center">
            <i className="fa-solid fa-hand-holding-heart"></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase font-bold tracking-wider text-purple-700">
              Welcome{greetingName ? `, ${greetingName}` : ""}
            </div>
            <h2 className="text-base font-bold text-slate-900 leading-tight">
              Here's your journey, five steps at a time.
            </h2>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Everything SA CoParents can do — assessments, plans,
              reports, mediator-ready documents — lives behind
              these five steps. We'll put you on the right one.
              You can wander backward and forward any time.
            </p>
          </div>
        </div>

        <button
          type="button"
          data-testid="journey-open-intro-guide"
          onClick={onOpenIntroGuide}
          className="mt-3 w-full py-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-xs transition"
        >
          <i className="fa-solid fa-comment-dots mr-1.5"></i>
          Not sure where to start? Chat with the Guide
        </button>
      </section>

      {/* iter249 — 5-dot progress strip. Driven by completion
          signals, not current-step cursor, so a parent sees
          their actual journey progress at a glance. */}
      <ProgressDots
        pathPickedAt={pathPickedAt}
        safetyAck={safetyAck}
        firstEngagementAt={firstEngagementAt}
        biffUsedAt={biffUsedAt}
        hasSnapshots={snapshotCount > 0}
      />

      {/* Grey-rock soft indicator — if the parent is in grey-rock
          mode they already see the chip inside AlignmentHub when
          they tap Step 2–5. The shell adds a tiny banner above
          the step list so it's visible BEFORE they tap anything. */}
      {safetyFlag && (
        <div
          data-testid="journey-grey-rock-banner"
          className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-900 flex items-start gap-2"
        >
          <i className="fa-solid fa-shield-halved text-amber-600 mt-0.5"></i>
          <div className="leading-snug">
            <span className="font-semibold">Grey-rock mode is on.</span>{" "}
            <span className="text-amber-800">
              Tools and language are quietly adapted. You can turn it
              off inside Step 2.
            </span>
          </div>
        </div>
      )}

      {/* The five steps. Vertical card list. Current step is
          highlighted + auto-expanded. */}
      <ol className="space-y-3 list-none">
        {STEPS.map((step) => {
          const tint = TINT_CLASSES[step.tint];
          const isCurrent = step.n === current;
          const isOpen = activeStep === step.n;
          return (
            <li key={step.n} data-testid={`journey-step-${step.n}`}>
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? 0 : step.n)}
                data-testid={`journey-step-${step.n}-toggle`}
                className={`w-full text-left bg-white rounded-2xl border-2 ${
                  isCurrent ? tint.ring : "border-slate-200"
                } p-3 transition hover:shadow-sm`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`shrink-0 w-10 h-10 rounded-xl ${tint.icon} flex items-center justify-center`}
                  >
                    <i className={`fa-solid ${step.icon}`}></i>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${tint.chip}`}
                      >
                        Step {step.n}
                      </span>
                      {isCurrent && (
                        <span
                          className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-900 text-white"
                          data-testid={`journey-step-${step.n}-current`}
                        >
                          You're here
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 mt-1 leading-tight">
                      {step.title}
                    </h3>
                    <p className={`text-[11px] mt-0.5 leading-snug ${tint.accent}`}>
                      {step.tagline}
                    </p>
                  </div>
                  <i
                    className={`fa-solid ${
                      isOpen ? "fa-chevron-down" : "fa-chevron-right"
                    } text-slate-400 mt-3`}
                  ></i>
                </div>
              </button>

              {isOpen && (
                <div
                  data-testid={`journey-step-${step.n}-panel`}
                  className="bg-slate-50 rounded-b-2xl border-2 border-t-0 border-slate-200 -mt-1 p-3 pt-4 text-[12px] text-slate-700 leading-snug space-y-3"
                >
                  <p>{step.body}</p>

                  {step.n === 1 && (
                    <div className="grid grid-cols-1 gap-2 pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-1-cta-voluntary"
                        onClick={onEnterParent}
                        className={`w-full p-3 rounded-xl text-left ${tint.cta} transition`}
                      >
                        <div className="text-[10px] font-bold uppercase tracking-wider opacity-90">
                          I'm here on my own
                        </div>
                        <div className="text-sm font-bold leading-tight mt-0.5">
                          Start My Co-Parenting Journey
                        </div>
                        <div className="text-[11px] opacity-90 leading-snug mt-0.5">
                          Voluntary. You pick the pace.
                        </div>
                      </button>
                      <button
                        type="button"
                        data-testid="journey-step-1-cta-court"
                        onClick={onEnterCourt}
                        className="w-full p-3 rounded-xl text-left bg-amber-600 hover:bg-amber-700 text-white transition"
                      >
                        <div className="text-[10px] font-bold uppercase tracking-wider opacity-90">
                          I was sent here
                        </div>
                        <div className="text-sm font-bold leading-tight mt-0.5">
                          I have a court order or professional referral
                        </div>
                        <div className="text-[11px] opacity-90 leading-snug mt-0.5">
                          Enter your access key — we'll fast-forward
                          you to the right assessment.
                        </div>
                      </button>
                    </div>
                  )}

                  {step.n === 2 && (
                    <div className="space-y-2 pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-2-cta-safety"
                        onClick={onOpenSafety}
                        className="w-full p-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-left transition flex items-center gap-2"
                      >
                        <i className="fa-solid fa-shield-heart"></i>
                        <span className="text-sm font-bold">
                          Private Safety Check
                        </span>
                      </button>
                      {safetyFlag && (
                        <GreyRockToggleChip
                          onClear={onClearGreyRock}
                          onRetake={onOpenSafetyRetake}
                        />
                      )}
                      <button
                        type="button"
                        data-testid="journey-step-2-cta-progress"
                        onClick={() => onOpenGuidedJourney("coparenting")}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition flex items-center gap-2`}
                      >
                        <i className="fa-solid fa-chart-line"></i>
                        <span className="text-sm font-bold">
                          Track my progress (take or re-take the
                          40-Q check)
                        </span>
                      </button>
                      <a
                        href={selfAssessmentUrl}
                        target="_blank"
                        rel="noreferrer"
                        data-testid="journey-step-2-cta-preview"
                        className="block w-full p-2.5 rounded-xl bg-white hover:bg-indigo-50 border border-indigo-300 text-indigo-800 text-left transition text-sm font-bold"
                      >
                        <i className="fa-solid fa-wand-magic-sparkles mr-1.5"></i>
                        Try the 40-question interactive preview
                      </a>
                    </div>
                  )}

                  {step.n === 3 && (
                    <div className="space-y-2 pt-1">
                      {courtKey && (
                        <div
                          data-testid="journey-step-3-court-banner"
                          className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-[11px] text-emerald-900 leading-snug"
                        >
                          <i className="fa-solid fa-gavel text-emerald-600 mr-1.5"></i>
                          <span className="font-semibold">
                            Court access verified:
                          </span>{" "}
                          Case {courtKey}
                          {verifiedMediator
                            ? ` · ${verifiedMediator}`
                            : ""}
                          . Your assessment feeds the mediator's
                          joint report.
                        </div>
                      )}
                      <button
                        type="button"
                        data-testid="journey-step-3-cta-coparenting"
                        onClick={() => onOpenGuidedJourney("coparenting")}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        <i className="fa-solid fa-child-reaching mr-1.5"></i>
                        Co-Parenting Assessment
                      </button>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <button
                          type="button"
                          data-testid="journey-step-3-cta-educational"
                          onClick={() => onOpenGuidedJourney("educational")}
                          className="p-2 rounded-xl bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-900 text-[11px] font-bold transition"
                        >
                          <i className="fa-solid fa-graduation-cap block mb-0.5"></i>
                          Educational
                        </button>
                        <button
                          type="button"
                          data-testid="journey-step-3-cta-medical"
                          onClick={() => onOpenGuidedJourney("medical")}
                          className="p-2 rounded-xl bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-900 text-[11px] font-bold transition"
                        >
                          <i className="fa-solid fa-stethoscope block mb-0.5"></i>
                          Medical
                        </button>
                        <button
                          type="button"
                          data-testid="journey-step-3-cta-psychological"
                          onClick={() => onOpenGuidedJourney("psychological")}
                          className="p-2 rounded-xl bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-900 text-[11px] font-bold transition"
                        >
                          <i className="fa-solid fa-brain block mb-0.5"></i>
                          Psychological
                        </button>
                      </div>
                      <button
                        type="button"
                        data-testid="journey-step-3-cta-records"
                        onClick={() => onOpenAssessmentFolder("All")}
                        className="w-full p-2 rounded-xl bg-white hover:bg-emerald-50 border border-emerald-200 text-emerald-800 text-left transition text-xs font-semibold"
                      >
                        <i className="fa-solid fa-folder-open mr-1.5"></i>
                        Open my Alignment Records folder
                      </button>
                    </div>
                  )}

                  {step.n === 4 && (
                    <div className="space-y-2 pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-4-cta-biff"
                        onClick={onOpenBiffCoach}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        <i className="fa-solid fa-wand-magic-sparkles mr-1.5"></i>
                        Rewrite a message the BIFF way
                      </button>
                      <button
                        type="button"
                        data-testid="journey-step-4-cta-mediation"
                        onClick={() => onOpenGuidedJourney("foundation")}
                        className="w-full p-2.5 rounded-xl bg-white hover:bg-amber-50 border border-amber-300 text-amber-900 text-left transition text-xs font-semibold"
                      >
                        <i className="fa-solid fa-handshake-angle mr-1.5"></i>
                        Walk through a mediation-prep script
                      </button>
                    </div>
                  )}

                  {step.n === 5 && (
                    <div className="space-y-2 pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-5-cta-foundation"
                        onClick={onOpenFoundationStatement}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        <i className="fa-solid fa-feather-pointed mr-1.5"></i>
                        Draft my Foundation Statement
                      </button>
                      <button
                        type="button"
                        data-testid="journey-step-5-cta-download-complete"
                        onClick={onDownloadCompleteReport}
                        className="w-full p-2.5 rounded-xl bg-white hover:bg-rose-50 border border-rose-300 text-rose-800 text-left transition text-xs font-semibold"
                      >
                        <i className="fa-solid fa-file-pdf mr-1.5"></i>
                        Download my complete report PDF
                      </button>
                      <button
                        type="button"
                        data-testid="journey-step-5-cta-share-complete"
                        onClick={onShareCompleteReport}
                        className="w-full p-2.5 rounded-xl bg-white hover:bg-rose-50 border border-rose-300 text-rose-800 text-left transition text-xs font-semibold"
                      >
                        <i className="fa-solid fa-envelope-circle-check mr-1.5"></i>
                        Email my progress to my mediator
                      </button>
                      {snapshotCount > 0 && (
                        <p
                          data-testid="journey-step-5-snapshot-count"
                          className="text-[11px] text-rose-700 pt-1"
                        >
                          <i className="fa-solid fa-camera-retro mr-1"></i>
                          You have {snapshotCount} saved snapshot
                          {snapshotCount === 1 ? "" : "s"} available
                          below.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
