/**
 * JourneyStepper.jsx — the ONE canonical six-step framework the whole
 * app renders. Introduced 2026-03-06 to replace the three drifting
 * versions previously scattered across Landing, Dashboard, and the
 * "companion" flow:
 *   - Reflect → Understand → Identify → Explore → Align → Agree
 *   - Assess → Understand Your Child → Set Priorities → Build Foundation → Prepare for Mediation → Review Progress
 *   - What's Going On? → Co-Parenting Assessment → Child Needs → Foundation Statement → Joint Assessment → Co-Parenting Agreement
 *
 * The single canonical framework (per 2026-03-06 product review):
 *   1. Reflect on Your Situation
 *   2. Identify Your Child's Needs
 *   3. Establish Parenting Priorities
 *   4. Explore Options and Resources
 *   5. Compare Perspectives
 *   6. Build an Agreement
 *
 * Anywhere the app needs to explain "how it works", import from here.
 * Never rewrite the labels inline.
 */
import React from "react";
import {
  Check,
  Compass,
  Eye,
  Handshake,
  Heart,
  ScrollText,
  Users,
} from "lucide-react";

export const JOURNEY_STEPS = [
  {
    key: "reflect",
    number: 1,
    title: "Reflect on Your Situation",
    blurb: "A short, private reflection about what's working and what isn't — no sharing yet.",
    icon: Eye,
  },
  {
    key: "child-needs",
    number: 2,
    title: "Identify Your Child's Needs",
    blurb: "Note what your child needs from both homes — medical, educational, emotional.",
    icon: Heart,
  },
  {
    key: "priorities",
    number: 3,
    title: "Establish Parenting Priorities",
    blurb: "Draft your own priorities in plain language before comparing anything.",
    icon: Compass,
  },
  {
    key: "explore",
    number: 4,
    title: "Explore Options and Resources",
    blurb: "See practical options — from parallel parenting to co-parenting apps to mediation.",
    icon: ScrollText,
  },
  {
    key: "compare",
    number: 5,
    title: "Compare Perspectives",
    blurb: "When both of you have reflected, see shared ground and gaps side by side.",
    icon: Users,
  },
  {
    key: "agree",
    number: 6,
    title: "Build an Agreement",
    blurb: "Turn shared ground into a written co-parenting agreement your mediator can refine.",
    icon: Handshake,
  },
];

/**
 * Compact horizontal stepper — used on Dashboard + inside pathway
 * pages. Optional `currentStepKey` highlights the parent's active
 * step; `completedKeys` shows a check on any finished ones.
 */
export function JourneyStepperCompact({
  currentStepKey = null,
  completedKeys = [],
  testId = "journey-stepper-compact",
}) {
  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
      data-testid={testId}
    >
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-3">
        The six-step journey
      </div>
      <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {JOURNEY_STEPS.map((step) => {
          const Icon = step.icon;
          const done = completedKeys.includes(step.key);
          const active = currentStepKey === step.key;
          return (
            <li
              key={step.key}
              data-testid={`journey-step-${step.key}`}
              data-active={active}
              data-done={done}
              className={`flex items-start gap-3 rounded-2xl border px-3 py-2.5 transition ${
                active
                  ? "border-[#3D1A78] bg-[#F5F1FB]"
                  : done
                    ? "border-[#C7E5D3] bg-[#F1F9F4]"
                    : "border-[#EFECF6] bg-white"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full grid place-items-center shrink-0 text-xs font-bold ${
                  done
                    ? "bg-[#1E7A55] text-white"
                    : active
                      ? "bg-[#3D1A78] text-white"
                      : "bg-[#F1EEF7] text-[#3D1A78]"
                }`}
              >
                {done ? <Check size={14} strokeWidth={2.6} /> : step.number}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[0.625rem] uppercase tracking-[0.14em] font-bold text-[#4B4567] flex items-center gap-1 mb-0.5">
                  <Icon size={11} strokeWidth={2.4} /> Step {step.number}
                </div>
                <div className="text-sm font-semibold text-[#1A1330] leading-tight">
                  {step.title}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/**
 * Verbose version — used on Landing + `/for-professionals`. Renders
 * the same six steps with a longer explanatory blurb under each.
 */
export function JourneyStepperVerbose({ testId = "journey-stepper-verbose" }) {
  return (
    <ol
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      data-testid={testId}
    >
      {JOURNEY_STEPS.map((step) => {
        const Icon = step.icon;
        return (
          <li
            key={step.key}
            data-testid={`journey-verbose-${step.key}`}
            className="rounded-3xl border border-[#E5E0EE] bg-white p-5 flex flex-col gap-3"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[#F1EEF7] text-[#3D1A78] grid place-items-center shrink-0">
                <Icon size={18} strokeWidth={2.2} />
              </div>
              <div>
                <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                  Step {step.number}
                </div>
                <div className="font-serif text-lg text-[#1A1330] leading-tight">
                  {step.title}
                </div>
              </div>
            </div>
            <p className="text-sm text-[#4B4567] leading-relaxed">
              {step.blurb}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

export default JourneyStepperCompact;
