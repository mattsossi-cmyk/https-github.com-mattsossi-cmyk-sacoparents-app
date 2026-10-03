import React, { useMemo, useState } from "react";

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

function pickCurrentStep({ safetyAck, pathPicked, firstEngagement, hasSnapshots }) {
  // The system picks the "current" step for the parent. Future
  // iters (Phase B+) will replace this with signal from the
  // assessment & plan progress. For now:
  //  - no path picked → Step 1
  //  - path picked but no safety ack cleared/flagged → Step 2
  //  - safety ack present but no engagement → Step 2
  //  - engagement but no snapshots → Step 3
  //  - snapshots exist → Step 4 (parent is iterating)
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
  // Step 1 door CTAs — same handlers the old Gateway used, so the
  // Safety-First gate still fires before either door.
  onEnterParent = () => {},
  onEnterCourt = () => {},
  // Step 2 — safety check launcher. Opens the SafetyScreen modal
  // via the container's existing state.
  onOpenSafety = () => {},
  // Step 2 → 5 — route into the existing parent-journey screen and
  // scroll to the right surface. Phase B will inline these.
  onEnterStep2 = () => {},
  onEnterStep3 = () => {},
  onEnterStep4 = () => {},
  onEnterStep5 = () => {},
  // Intro guide chip (soft, non-blocking) — same handler as the
  // old gateway's "Talk to the SA CoParents Guide" button.
  onOpenIntroGuide = () => {},
  // Grey-rock chip surface, if applicable — reuses the Alignment
  // hub chip when a parent in grey-rock mode lands on the shell.
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
      }),
    [safetyAck, pathPickedAt, firstEngagementAt, snapshotCount]
  );

  const [expanded, setExpanded] = useState(current);

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
          const isOpen = expanded === step.n;
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
                      <button
                        type="button"
                        data-testid="journey-step-2-cta-open"
                        onClick={onEnterStep2}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        Open my Understand My Situation workspace
                      </button>
                    </div>
                  )}

                  {step.n === 3 && (
                    <div className="pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-3-cta-open"
                        onClick={onEnterStep3}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        Open Focus on My Child
                      </button>
                    </div>
                  )}

                  {step.n === 4 && (
                    <div className="pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-4-cta-open"
                        onClick={onEnterStep4}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        Open Explore Options
                      </button>
                    </div>
                  )}

                  {step.n === 5 && (
                    <div className="pt-1">
                      <button
                        type="button"
                        data-testid="journey-step-5-cta-open"
                        onClick={onEnterStep5}
                        className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition text-sm font-bold`}
                      >
                        Open Create My Plan
                      </button>
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {/* Advanced-view escape hatch. Will be deleted in Phase D
          (iter247) once the shell has settled across all surfaces. */}
      <div className="pt-2 text-center">
        <a
          href="?view=advanced"
          data-testid="journey-advanced-view-link"
          className="text-[10px] text-slate-400 underline underline-offset-2"
        >
          Advanced view (legacy)
        </a>
      </div>
    </div>
  );
}
