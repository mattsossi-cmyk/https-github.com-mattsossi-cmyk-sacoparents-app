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
  ClipboardCheck,
  FileText,
  FilePenLine,
  ListChecks,
  Handshake,
  Baby,
  HelpCircle,
} from "lucide-react";

const CIRCLES = [
  {
    key: "co-parenting",
    label: "Make a Co-Parenting Agreement",
    prompt: "Prepare a mediator-ready foundation for a shared parenting agreement.",
    detail:
      "Walk the 4-step pathway: Assessment → Foundation Statement → Mediation Statement → Mediation Prep. Your co-parent takes it separately.",
    icon: Handshake,
    tone: {
      ring: "ring-[#3D1A78]/25",
      hover: "hover:ring-[#3D1A78]/60",
      bg: "bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0]",
      chip: "bg-[#EFE9F9] text-[#3D1A78]",
      accent: "text-[#3D1A78]",
    },
    pathway: [
      "Co-Parenting Assessment",
      "Foundation Statement",
      "Mediation Statement",
    ],
    cta: "Open the pathway",
    testid: "front-door-coparenting",
    expandable: true,
    endButton: "Create My Statement",
  },
  {
    key: "communication",
    label: "Communicate More Effectively",
    prompt:
      "Reflect on your patterns, get coaching, and build a message you're proud to send.",
    detail:
      "For everyday messages — pickups, illnesses, school notes. Private reflection first, then optional coaching from an AI trained on de-escalation.",
    icon: MessageCircle,
    tone: {
      ring: "ring-[#1E6FA8]/25",
      hover: "hover:ring-[#1E6FA8]/60",
      bg: "bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6]",
      chip: "bg-[#E4F1FA] text-[#1E6FA8]",
      accent: "text-[#1E6FA8]",
    },
    pathway: [
      "Individual Reflection",
      "AI Communication Coach",
      "Communication Builder",
    ],
    cta: "Start reflecting",
    route: "/communication",
    testid: "front-door-communication",
    endButton: "Build My Message",
  },
  {
    key: "safety",
    label: "Address Safety Concerns",
    prompt:
      "Private, calm, and never assumes alignment — safety comes first, always.",
    detail:
      "A private safety screen you complete alone. Nothing is shared unless you choose to share it. Includes hotlines, safety planning, and legal referrals.",
    icon: ShieldAlert,
    tone: {
      ring: "ring-[#B45F13]/25",
      hover: "hover:ring-[#B45F13]/60",
      bg: "bg-gradient-to-br from-[#B45F13] to-[#D97836]",
      chip: "bg-[#FFEEDA] text-[#8A4610]",
      accent: "text-[#8A4610]",
    },
    pathway: [
      "Private Safety Screen",
      "Family Violence Co-Parenting Assessment",
      "Safeguards & Resources",
    ],
    cta: "Enter safely",
    route: "/safety",
    testid: "front-door-safety",
    endButton: "See My Safeguards",
  },
  {
    key: "child-needs",
    label: "Address My Child's Needs",
    prompt:
      "Educational, medical, or psychological — pick the lane, get your report, invite a joint review.",
    detail:
      "Deep-dive assessments for school, doctors, therapy, or coordinated special-needs care. Each finishes with an individual report and an optional joint-report invitation.",
    icon: Baby,
    tone: {
      ring: "ring-[#1E7A55]/25",
      hover: "hover:ring-[#1E7A55]/60",
      bg: "bg-gradient-to-br from-[#1E7A55] to-[#3AA378]",
      chip: "bg-[#E1F3E8] text-[#1E7A55]",
      accent: "text-[#1E7A55]",
    },
    pathway: [
      "Educational · Medical · Psychological Assessment",
      "Individual Report",
      "Joint Report Invitation",
    ],
    cta: "Choose an area",
    testid: "front-door-child-needs",
    expandable: true,
    endButton: "Invite the Other Parent",
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

/* Co-Parenting pathway (2026-03-04 founder spec):
   Co-Parenting Assessment → Foundation Statement →
   Mediation Statement → Mediation Preparation. Every step feeds
   the joint alignment report on sacoparentsalign.com. */
const COPARENTING_PATHWAY_TILES = [
  {
    key: "assessment",
    step: 1,
    label: "Co-Parenting Assessment",
    detail:
      "Reflect on parenting consistency, decisions, exchanges, boundaries, activities, holidays — the shared child-focused terrain.",
    icon: ClipboardCheck,
    route: "/special-needs-v2",
    testid: "front-door-coparenting-assessment",
  },
  {
    key: "foundation",
    step: 2,
    label: "Foundation Statement",
    detail:
      "The four reflective prompts that become your starting point — in your own words, framed neutrally for the professional.",
    icon: FileText,
    route: "/foundation",
    testid: "front-door-coparenting-foundation",
  },
  {
    key: "mediation-statement",
    step: 3,
    label: "Mediation Statement",
    detail:
      "SA CoParents shapes your reflections into a short mediator-ready statement — kept private until you choose to share it.",
    icon: FilePenLine,
    route: "/my-plan",
    testid: "front-door-coparenting-mediation-statement",
  },
  {
    key: "mediation-prep",
    step: 4,
    label: "Mediation Preparation",
    detail:
      "Child goals, issues, priority, readiness — the packet that walks into your mediator's office ready to go.",
    icon: ListChecks,
    route: "/dashboard#dashboard-step1-hero",
    testid: "front-door-coparenting-mediation-prep",
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
  const [helpOpen, setHelpOpen] = useState(false);

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
        What would you like help with today
        {userName ? `, ${userName.split(" ")[0]}?` : "?"}
      </h1>
      <p className="text-[#4B4567] mt-3 max-w-2xl leading-relaxed text-[15px]">
        Pick the problem you want help with — SA CoParents will guide you
        through the right pathway. Every path is private, calm, and never
        shares your answers without your permission.
      </p>

      {/* The four circles */}
      <div
        className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="front-door-circles"
      >
        {CIRCLES.map((circle, idx) => (
          <FrontDoorTile
            key={circle.key}
            circle={circle}
            expanded={expandedKey === circle.key}
            onClick={() => handleCircleClick(circle)}
            index={idx}
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

      {/* Inline reveal for Co-Parenting — the 4-step pathway that
          feeds the joint alignment report on sacoparentsalign.com. */}
      {expandedKey === "co-parenting" && (
        <div
          className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F8F7FC] p-5 sm:p-6"
          data-testid="front-door-coparenting-panel"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                Co-Parenting pathway
              </div>
              <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight mt-1">
                Walk through the four steps in order — or jump to one.
              </h2>
              <p className="text-[13px] text-[#4B4567] mt-1 leading-relaxed !mb-0">
                Every step feeds the joint alignment report on
                <strong className="text-[#1A1330]"> sacoparentsalign.com</strong>{" "}
                once your professional opens the case.
              </p>
            </div>
          </div>
          <ol
            className="grid grid-cols-1 sm:grid-cols-2 gap-3"
            data-testid="front-door-coparenting-steps"
          >
            {COPARENTING_PATHWAY_TILES.map((tile) => (
              <PathwayStepTile
                key={tile.key}
                tile={tile}
                onClick={() => navigate(tile.route)}
              />
            ))}
          </ol>
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

function FrontDoorTile({ circle, expanded, onClick, index = 0 }) {
  const Icon = circle.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={circle.expandable ? expanded : undefined}
      data-testid={circle.testid}
      style={{ animationDelay: `${index * 90}ms` }}
      className={`front-door-tile group text-left rounded-3xl border border-[#EFE9F9] bg-white p-5 ring-1 ${circle.tone.ring} ${circle.tone.hover} hover:-translate-y-1 hover:shadow-xl active:translate-y-0 active:scale-[0.98] transition-all duration-200 flex flex-col`}
    >
      <div
        className={`w-14 h-14 rounded-full grid place-items-center text-white shadow-md ${circle.tone.bg} group-hover:scale-110 group-hover:shadow-lg transition-transform duration-200`}
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
        className={`inline-flex items-center gap-1.5 mt-4 text-[13px] font-semibold ${circle.tone.accent} group-hover:gap-2.5 transition-all duration-200`}
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

function PathwayStepTile({ tile, onClick }) {
  const Icon = tile.icon;
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        data-testid={tile.testid}
        className="w-full text-left rounded-2xl border border-[#D6CFE8] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition flex gap-3 items-start"
      >
        <div className="flex flex-col items-center flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-[#3D1A78] text-white grid place-items-center">
            <Icon size={18} strokeWidth={2.2} />
          </div>
          <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#3D1A78] mt-1">
            Step {tile.step}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-serif text-lg text-[#1A1330] leading-tight">
            {tile.label}
          </div>
          <p className="text-[12px] text-[#4B4567] mt-1 leading-snug">
            {tile.detail}
          </p>
        </div>
        <ArrowRight
          size={16}
          className="text-[#3D1A78] flex-shrink-0 mt-2"
          aria-hidden
        />
      </button>
    </li>
  );
}
