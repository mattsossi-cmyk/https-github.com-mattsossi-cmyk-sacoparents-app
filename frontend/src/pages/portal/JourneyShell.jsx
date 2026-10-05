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
    title: "Communication Builder",
    tagline: "Rewrite before you send.",
    body: "Draft a message, see a calmer BIFF rewrite, and build a record of your communication growth over time. Works whether you're here on your own or court-referred.",
    icon: "fa-wand-magic-sparkles",
    tint: "amber",
    // iter253 — tiny "?" explainer surfaced inline so a parent
    // landing fresh understands the term BIFF before expanding.
    info: {
      title: "What's a BIFF rewrite?",
      body: "BIFF stands for Brief, Informative, Friendly, and Firm — a research-backed way to answer a hot message without matching its heat. You keep the facts, drop the drama, and leave less room for a fight.",
      linkKind: "biff_book",
    },
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

function pickCurrentStep({ pathPicked }) {
  // Simplified shell (iter251 — user asked to remove Steps 3, 4, 5).
  // Only two steps remain, so the picker is trivially:
  //   - no door chosen       → Step 1
  //   - any door chosen      → Step 2
  // BIFF, Foundation Statement, and the complete report are still
  // reachable via the bottom-nav drawers (`nav-biff`, `nav-report`).
  return pathPicked ? 2 : 1;
}

export function JourneyShell({
  user,
  safetyAck,
  pathPickedAt,
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
  // Step 2 — Co-parenting assessment / Guided Journey launcher.
  onOpenGuidedJourney = () => {},
  // iter252 — Step 3 Communication Builder. biffAuthoredCount is
  // the number of BIFF rewrites the parent has drafted themselves
  // (seed demo entry subtracted out). biffPairCount is the number
  // filed as `biff_pair` snapshots (parent-explicit saves).
  onOpenBiffCoach = () => {},
  biffAuthoredCount = 0,
  biffPairCount = 0,
  // Intro guide chip (soft, non-blocking).
  onOpenIntroGuide = () => {},
  // Grey-rock chip surface, if applicable.
  safetyFlagged = false,
}) {
  const safetyFlag = safetyFlagged || !!(safetyAck && safetyAck.flagged);
  const current = useMemo(
    () => pickCurrentStep({ pathPicked: !!pathPickedAt }),
    [pathPickedAt]
  );

  const [expanded, setExpanded] = useState(null);
  // iter253 — which step's "?" info card is currently open (0 = none).
  const [infoOpenStep, setInfoOpenStep] = useState(0);

  // iter253 — Bill Eddy's BIFF book link. Env-configurable so the
  // user can swap the direct publisher link for an affiliate link
  // without a code change.
  const biffBookUrl = process.env.REACT_APP_BIFF_BOOK_URL || "";
  const biffBookTitle =
    process.env.REACT_APP_BIFF_BOOK_TITLE || "the BIFF book";
  const biffBookAuthor = process.env.REACT_APP_BIFF_BOOK_AUTHOR || "";

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
              Here's where to begin.
            </h2>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Three short steps. Your Reports and PDF Export stay
              one tap away at the bottom whenever you need them.
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

      {/* iter251 — court-ordered status card. Shown at the top of
          the shell (not inside a step) whenever a court key is
          verified. Replaces the Step-3 inline banner since Step 3
          was deleted. */}
      {courtKey && (
        <div
          data-testid="journey-court-banner"
          className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-[11px] text-emerald-900 leading-snug flex items-start gap-2"
        >
          <i className="fa-solid fa-gavel text-emerald-600 mt-0.5"></i>
          <div>
            <span className="font-semibold">Court access verified:</span>{" "}
            Case {courtKey}
            {verifiedMediator ? ` · ${verifiedMediator}` : ""}. Your
            assessment feeds the mediator's joint report.
          </div>
        </div>
      )}

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
          const isInfoOpen = infoOpenStep === step.n;
          const handleToggle = () => setExpanded(isOpen ? 0 : step.n);
          return (
            <li key={step.n} data-testid={`journey-step-${step.n}`}>
              {/* iter253 — the step card header is a role="button"
                  (not a <button>) so it can contain a nested
                  interactive "?" info button without invalid HTML.
                  Keyboard activation (Space / Enter) is wired by
                  hand to match native button semantics. */}
              <div
                role="button"
                tabIndex={0}
                onClick={handleToggle}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleToggle();
                  }
                }}
                data-testid={`journey-step-${step.n}-toggle`}
                className={`w-full text-left bg-white rounded-2xl border-2 ${
                  isCurrent ? tint.ring : "border-slate-200"
                } p-3 transition hover:shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-400`}
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
                    <div className="flex items-center gap-1.5 mt-1">
                      <h3 className="text-sm font-bold text-slate-900 leading-tight">
                        {step.title}
                      </h3>
                      {step.info && (
                        <button
                          type="button"
                          data-testid={`journey-step-${step.n}-info-btn`}
                          onClick={(e) => {
                            // Stop propagation so clicking "?" doesn't
                            // toggle the step expand/collapse.
                            e.stopPropagation();
                            setInfoOpenStep(isInfoOpen ? 0 : step.n);
                          }}
                          aria-label={step.info.title}
                          aria-expanded={isInfoOpen}
                          className="shrink-0 w-5 h-5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center transition"
                        >
                          ?
                        </button>
                      )}
                    </div>
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
              </div>

              {/* iter253 — inline "What's a BIFF rewrite?" explainer.
                  Renders between the step header and the step panel,
                  only when the parent taps the "?" button. */}
              {isInfoOpen && step.info && (
                <div
                  data-testid={`journey-step-${step.n}-info-card`}
                  className="mt-1 rounded-xl bg-amber-50 border border-amber-200 p-3 text-[12px] text-amber-950 leading-snug space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-bold text-amber-900">
                      {step.info.title}
                    </h4>
                    <button
                      type="button"
                      data-testid={`journey-step-${step.n}-info-close`}
                      onClick={() => setInfoOpenStep(0)}
                      aria-label="Close explainer"
                      className="shrink-0 w-5 h-5 rounded-full bg-white hover:bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center"
                    >
                      <i className="fa-solid fa-xmark"></i>
                    </button>
                  </div>
                  <p>{step.info.body}</p>
                  {biffBookUrl && step.info.linkKind === "biff_book" && (
                    <a
                      href={biffBookUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid={`journey-step-${step.n}-info-book-link`}
                      className="inline-flex items-center gap-1.5 mt-1 px-3 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-[11px] transition"
                    >
                      <i className="fa-solid fa-book"></i>
                      Get {biffBookTitle}
                      {biffBookAuthor ? ` — ${biffBookAuthor}` : ""}
                      <i className="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-80"></i>
                    </a>
                  )}
                </div>
              )}

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
                      {/* iter252 — Communication Builder progress
                          strip. Tracks the parent's authored BIFF
                          rewrites + explicitly filed Draft-to-
                          Snapshot pairs. Always visible so a parent
                          sees their growth record before drafting
                          the next message. */}
                      <div
                        data-testid="journey-step-3-progress"
                        className="rounded-xl bg-white border border-amber-200 p-3 flex items-center gap-3"
                      >
                        <div className="shrink-0 w-10 h-10 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
                          {biffAuthoredCount}
                        </div>
                        <div className="min-w-0 flex-1 leading-snug">
                          <div className="text-[10px] uppercase font-bold tracking-wider text-amber-800">
                            Your growth record
                          </div>
                          <p className="text-[11px] text-slate-700">
                            {biffAuthoredCount === 0 ? (
                              <>
                                No rewrites yet. Your first draft
                                will start the record.
                              </>
                            ) : (
                              <>
                                {biffAuthoredCount} message
                                {biffAuthoredCount === 1 ? "" : "s"}{" "}
                                reworked
                                {biffPairCount > 0
                                  ? ` · ${biffPairCount} filed as snapshot${
                                      biffPairCount === 1 ? "" : "s"
                                    }`
                                  : ""}
                                .
                              </>
                            )}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        data-testid="journey-step-3-cta-biff"
                        onClick={onOpenBiffCoach}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition flex items-center gap-2`}
                      >
                        <i className="fa-solid fa-pen-nib"></i>
                        <span className="text-sm font-bold">
                          {biffAuthoredCount === 0
                            ? "Draft my first BIFF rewrite"
                            : "Draft another message"}
                        </span>
                      </button>
                      <button
                        type="button"
                        data-testid="journey-step-3-cta-history"
                        onClick={onOpenBiffCoach}
                        className="w-full p-2.5 rounded-xl bg-white hover:bg-amber-50 border border-amber-300 text-amber-900 text-left transition text-xs font-semibold flex items-center gap-2"
                      >
                        <i className="fa-solid fa-clock-rotate-left"></i>
                        <span>Review my past rewrites &amp; suggestions</span>
                      </button>
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
