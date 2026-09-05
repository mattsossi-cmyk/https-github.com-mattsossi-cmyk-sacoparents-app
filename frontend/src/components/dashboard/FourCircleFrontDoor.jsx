/**
 * FourCircleFrontDoor — the signed-in dashboard's new hero.
 *
 * The information architecture the founder specified on 2026-03-04:
 * four large "circles" at the front door, each opening its own
 * pathway. Child Needs reveals four sub-circles inline (School &
 * Education / Medical / Emotional & Psychological / Special Needs)
 * without navigating away, plus a "Complete Child Needs Assessment"
 * escape hatch.
 *
 *   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
 *   │ 🟣 Co-Par. │   │ 🔵 Comms   │   │ 🟠 Safety  │   │ 🟢 Needs   │
 *   └────────────┘   └────────────┘   └────────────┘   └────────────┘
 *                                                       │ School    │
 *                                                       │ Medical   │
 *                                                       │ Emotional │
 *                                                       │ Special   │
 *                                                       │ Complete  │
 *
 * Underneath every circle, the same six-step process:
 *   Reflect → Understand → Identify → Explore → Align → Agree
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users,
  MessageCircle,
  ShieldAlert,
  Sparkles,
  GraduationCap,
  Stethoscope,
  Brain,
  Puzzle,
  ArrowRight,
  Phone,
} from "lucide-react";

const CIRCLES = [
  {
    key: "co-parenting",
    label: "Co-Parenting",
    prompt: "How are we doing as co-parents?",
    icon: Users,
    tone: {
      ring: "ring-[#3D1A78]/25",
      hover: "hover:ring-[#3D1A78]/60",
      bg: "bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0]",
      chip: "bg-[#EFE9F9] text-[#3D1A78]",
      accent: "text-[#3D1A78]",
    },
    detail:
      "Consistency, decision-making, schedules, exchanges, boundaries, activities, holidays, supporting each parent's bond, agreements & disagreements.",
    cta: "Start the reflection →",
    route: "/special-needs-v2/compare",
    testid: "front-door-coparenting",
  },
  {
    key: "communication",
    label: "Communication",
    prompt: "How can we communicate more effectively?",
    icon: MessageCircle,
    tone: {
      ring: "ring-[#1E6FA8]/25",
      hover: "hover:ring-[#1E6FA8]/60",
      bg: "bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6]",
      chip: "bg-[#E4F1FA] text-[#1E6FA8]",
      accent: "text-[#1E6FA8]",
    },
    detail:
      "BIFF · CLEAR Path · boundaries · written communication · response expectations · child-focused messaging · conflict reduction · structured comms.",
    cta: "Start the intake →",
    route: "/communication",
    testid: "front-door-communication",
  },
  {
    key: "safety",
    label: "Family Violence & Safety",
    prompt:
      "What structure and safeguards may be needed to support safe parenting and the child's needs?",
    icon: ShieldAlert,
    tone: {
      ring: "ring-[#B45F13]/25",
      hover: "hover:ring-[#B45F13]/60",
      bg: "bg-gradient-to-br from-[#B45F13] to-[#D97836]",
      chip: "bg-[#FFEEDA] text-[#8A4610]",
      accent: "text-[#8A4610]",
    },
    detail:
      "Safety Reflection → risks & power imbalances → communication safety → parenting structure → safeguards → options & resources. Safety comes first — alignment is not the objective here.",
    cta: "Enter safely →",
    route: "/safety",
    testid: "front-door-safety",
  },
  {
    key: "child-needs",
    label: "Child Needs",
    prompt: "Help us address our child's needs.",
    icon: Sparkles,
    tone: {
      ring: "ring-[#1E7A55]/25",
      hover: "hover:ring-[#1E7A55]/60",
      bg: "bg-gradient-to-br from-[#1E7A55] to-[#3AA378]",
      chip: "bg-[#E1F3E8] text-[#1E7A55]",
      accent: "text-[#1E7A55]",
    },
    detail:
      "Pick one, several, or the complete assessment. Every choice below opens its own reflection → alignment pathway.",
    cta: "Choose an area →",
    // No `route` — expands inline into CHILD_NEEDS_TILES.
    testid: "front-door-child-needs",
    expandable: true,
  },
];

const CHILD_NEEDS_TILES = [
  {
    key: "education",
    label: "School & Education",
    detail:
      "School performance, teachers, attendance, homework, tutoring, IEP/ARD, educational decisions.",
    icon: GraduationCap,
    route: "/edu-deep",
    testid: "front-door-child-education",
  },
  {
    key: "medical",
    label: "Medical",
    detail:
      "Doctors, appointments, prescriptions, treatment recommendations, sharing medical info & decisions.",
    icon: Stethoscope,
    route: "/med-deep",
    testid: "front-door-child-medical",
  },
  {
    key: "psychological",
    label: "Emotional & Psychological",
    detail:
      "Counseling, behavioral concerns, ADHD, psychological care, medication discussions.",
    icon: Brain,
    route: "/psych-deep",
    testid: "front-door-child-psychological",
  },
  {
    key: "special-needs",
    label: "Special Needs",
    detail:
      "More complex educational, medical, developmental, or psychological needs requiring coordination.",
    icon: Puzzle,
    route: "/special-needs-v2",
    testid: "front-door-child-special-needs",
  },
];

const JOURNEY_STEPS = [
  { label: "Reflect", accent: "text-[#3D1A78]" },
  { label: "Understand", accent: "text-[#3D1A78]" },
  { label: "Identify", accent: "text-[#3D1A78]" },
  { label: "Explore", accent: "text-[#3D1A78]" },
  { label: "Align", accent: "text-[#3D1A78]" },
  { label: "Agree", accent: "text-[#3D1A78]" },
];

export default function FourCircleFrontDoor({ userName }) {
  const navigate = useNavigate();
  const [expandedKey, setExpandedKey] = useState(null);

  const handleCircleClick = (circle) => {
    if (circle.expandable) {
      setExpandedKey((prev) => (prev === circle.key ? null : circle.key));
      return;
    }
    if (circle.route) navigate(circle.route);
  };

  return (
    <section
      className="mt-4 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-8 shadow-sm"
      data-testid="four-circle-front-door"
    >
      <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
        Start here
      </div>
      <h1
        className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight"
        data-testid="front-door-title"
      >
        Where would you like to start
        {userName ? `, ${userName.split(" ")[0]}?` : "?"}
      </h1>
      <p className="text-[#4B4567] mt-3 max-w-2xl leading-relaxed text-[15px]">
        SA CoParents is one guided system — pick the door that fits your
        family right now. Each pathway walks you through the same six steps:
        <span className="ml-1 font-medium text-[#1A1330]">
          Reflect → Understand → Identify → Explore → Align → Agree.
        </span>
      </p>

      {/* Journey stepper — the unifying philosophy the founder called out */}
      <div
        className="mt-5 flex flex-wrap gap-x-2 gap-y-1 items-center text-[12px] sm:text-[13px]"
        data-testid="front-door-journey-strip"
      >
        {JOURNEY_STEPS.map((step, idx) => (
          <React.Fragment key={step.label}>
            <span
              className={`${step.accent} font-medium tracking-tight`}
              data-testid={`front-door-journey-step-${idx + 1}`}
            >
              {idx + 1}. {step.label}
            </span>
            {idx < JOURNEY_STEPS.length - 1 && (
              <ArrowRight size={13} className="text-[#C7BFDC]" aria-hidden />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* The four circles */}
      <div
        className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="front-door-circles"
      >
        {CIRCLES.map((circle) => (
          <FrontDoorTile
            key={circle.key}
            circle={circle}
            expanded={expandedKey === circle.key}
            onClick={() => handleCircleClick(circle)}
          />
        ))}
      </div>

      {/* Inline reveal for Child Needs */}
      {expandedKey === "child-needs" && (
        <div
          className="mt-6 rounded-2xl border border-[#D0EBDE] bg-[#F1F9F4] p-5 sm:p-6"
          data-testid="front-door-child-needs-panel"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#1E7A55]">
                Child needs
              </div>
              <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight mt-1">
                Which area would you like to focus on?
              </h2>
            </div>
            <button
              type="button"
              onClick={() => navigate("/special-needs-v2")}
              className="inline-flex items-center gap-2 rounded-full bg-[#1E7A55] text-white px-4 py-2 text-sm font-semibold hover:bg-[#186142] transition"
              data-testid="front-door-child-needs-complete-cta"
            >
              Complete Child Needs Assessment
              <ArrowRight size={14} />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {CHILD_NEEDS_TILES.map((tile) => (
              <ChildNeedsTile
                key={tile.key}
                tile={tile}
                onClick={() => navigate(tile.route)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Safety-first crisis reminder — always visible below the circles */}
      <div
        className="mt-6 flex items-start gap-3 rounded-2xl bg-[#FFF6EA] border border-[#F1D9B7] px-4 py-3 text-[13px] text-[#5A3C10]"
        data-testid="front-door-crisis-strip"
      >
        <Phone size={16} className="text-[#B45F13] flex-shrink-0 mt-0.5" />
        <p className="!m-0 leading-relaxed">
          <strong>In immediate danger?</strong> Call{" "}
          <a href="tel:911" className="underline font-semibold">
            911
          </a>{" "}
          or the National DV Hotline{" "}
          <a href="tel:18007997233" className="underline font-semibold">
            1-800-799-7233
          </a>{" "}
          · text <strong>START</strong> to <strong>88788</strong>.
        </p>
      </div>
    </section>
  );
}

function FrontDoorTile({ circle, expanded, onClick }) {
  const Icon = circle.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={circle.expandable ? expanded : undefined}
      data-testid={circle.testid}
      className={`group text-left rounded-3xl border border-[#EFE9F9] bg-white p-5 ring-1 ${circle.tone.ring} ${circle.tone.hover} hover:shadow-lg transition-all duration-200 flex flex-col`}
    >
      <div
        className={`w-14 h-14 rounded-full grid place-items-center text-white shadow-md ${circle.tone.bg}`}
      >
        <Icon size={26} strokeWidth={2.1} />
      </div>
      <h3 className="font-serif text-xl text-[#1A1330] mt-4 leading-tight">
        {circle.label}
      </h3>
      <p
        className={`text-[13px] italic mt-1 leading-snug ${circle.tone.accent}`}
      >
        {circle.prompt}
      </p>
      <p className="text-[13px] text-[#4B4567] mt-3 leading-relaxed flex-1">
        {circle.detail}
      </p>
      <span
        className={`inline-flex items-center gap-1.5 mt-4 text-[13px] font-semibold ${circle.tone.accent}`}
      >
        {circle.expandable
          ? expanded
            ? "Hide areas"
            : circle.cta
          : circle.cta}
      </span>
    </button>
  );
}

function ChildNeedsTile({ tile, onClick }) {
  const Icon = tile.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={tile.testid}
      className="text-left rounded-2xl border border-[#D0EBDE] bg-white p-4 hover:border-[#1E7A55] hover:shadow-md transition flex gap-3 items-start"
    >
      <div className="w-10 h-10 rounded-full bg-[#1E7A55] text-white grid place-items-center flex-shrink-0">
        <Icon size={18} strokeWidth={2.2} />
      </div>
      <div className="flex-1">
        <div className="font-serif text-lg text-[#1A1330] leading-tight">
          {tile.label}
        </div>
        <p className="text-[12px] text-[#4B4567] mt-1 leading-snug">
          {tile.detail}
        </p>
      </div>
      <ArrowRight
        size={16}
        className="text-[#1E7A55] flex-shrink-0 mt-2"
        aria-hidden
      />
    </button>
  );
}
