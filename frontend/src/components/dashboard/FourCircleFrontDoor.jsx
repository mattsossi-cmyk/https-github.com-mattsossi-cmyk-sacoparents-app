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
import React, { useEffect, useMemo, useState } from "react";
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
    prompt: "Put a written plan together you can bring to your mediator.",
    detail:
      "Say what you want in your own words, and let SA CoParents shape it into something a mediator or attorney can read at a glance. Your co-parent goes through the same steps separately.",
    clinicalDetail:
      "Under the hood: Co-Parenting Assessment → Foundation Statement → Mediation Statement → Mediation Prep.",
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
    prompt: "Draft a message you're proud to send.",
    detail:
      "For everyday messages — pickups, sick days, school notes. Think it through privately, then let AI help you write something calm and clear.",
    clinicalDetail:
      "Includes a private communication reflection and an optional AI coaching pass that borrows from de-escalation research.",
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
    prompt: "A private check-in — nothing is ever shared without your say-so.",
    detail:
      "Answer a few questions on your own to see what a professional would notice. You'll leave with hotlines, a safety plan you can print, and clear next-step options.",
    clinicalDetail:
      "Includes the Trauma-Informed Safety & Functioning Lens (TISFL) family-violence screen and Texas HB 300-aligned resource referrals.",
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
    prompt: "Get a clear picture of school, doctor, or emotional support.",
    detail:
      "Take a deep look at what your child needs — one area at a time. You'll get your own report, and you can invite the other parent to compare notes side-by-side.",
    clinicalDetail:
      "Under the hood: 25-question deep dives for Educational, Medical, and Psychological alignment, plus the Joint Alignment Report.",
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

/* "Help me choose" mini-quiz — a very short, no-wrong-answer wizard for
   parents who aren't sure which of the four circles fits their situation.
   Two questions, each answer maps to one of the four keys. The final
   recommendation highlights the matching circle in-place with a
   "Recommended for you" badge. Keeps parents from having to guess. */
const HELPER_QUESTIONS = [
  {
    id: "focus",
    prompt: "What's most on your mind right now?",
    options: [
      {
        key: "safety",
        label: "I don't feel safe or things are escalating at home",
        recommends: "safety",
      },
      {
        key: "message",
        label: "A specific message or exchange I don't know how to handle",
        recommends: "communication",
      },
      {
        key: "child",
        label: "Something about my child — school, doctor, therapy",
        recommends: "child-needs",
      },
      {
        key: "agreement",
        label: "Getting a written co-parenting plan together",
        recommends: "co-parenting",
      },
    ],
  },
  {
    id: "urgency",
    prompt: "And how soon do you need this?",
    options: [
      {
        key: "now",
        label: "This week — I have something specific happening",
        // Urgency doesn't override safety or communication.
        recommends: null,
      },
      {
        key: "soon",
        label: "Over the next few weeks",
        recommends: null,
      },
      {
        key: "long",
        label: "No specific deadline — I want the full picture",
        recommends: null,
      },
    ],
  },
];

const CIRCLE_LABELS = {
  "co-parenting": "Make a Co-Parenting Agreement",
  communication: "Communicate More Effectively",
  safety: "Address Safety Concerns",
  "child-needs": "Address My Child's Needs",
};

// Persist the two helper answers so returning parents see the
// recommended pathway highlighted immediately — no need to re-run the
// quiz on every visit. Scoped to this browser (localStorage). The
// parent can always tap "Answer the questions again" or the close
// button to clear.
const HELPER_STORAGE_KEY = "sacoparents.frontdoor.helper.v1";

function loadHelperAnswers() {
  try {
    const raw = window.localStorage.getItem(HELPER_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveHelperAnswers(answers) {
  try {
    if (answers && Object.keys(answers).length) {
      window.localStorage.setItem(HELPER_STORAGE_KEY, JSON.stringify(answers));
    } else {
      window.localStorage.removeItem(HELPER_STORAGE_KEY);
    }
  } catch {
    /* private mode — best-effort only */
  }
}

export default function FourCircleFrontDoor({ userName }) {
  const navigate = useNavigate();
  const [expandedKey, setExpandedKey] = useState(null);
  // Load any previously saved quiz answers so the "Recommended" badge
  // greets returning parents instead of making them re-quiz. If nothing
  // was saved, we start with an empty object and the panel stays closed.
  const [helpAnswers, setHelpAnswers] = useState(loadHelperAnswers);
  const [helpOpen, setHelpOpen] = useState(
    () => Object.keys(loadHelperAnswers()).length > 0,
  );

  // Persist every time the answers change so refreshes and next visits
  // land on the same state.
  useEffect(() => {
    saveHelperAnswers(helpAnswers);
  }, [helpAnswers]);

  const recommendedKey = useMemo(() => {
    const focus = HELPER_QUESTIONS[0].options.find(
      (o) => o.key === helpAnswers.focus,
    );
    return focus?.recommends || null;
  }, [helpAnswers.focus]);

  const handleCircleClick = (circle) => {
    if (circle.expandable) {
      setExpandedKey((prev) => (prev === circle.key ? null : circle.key));
      return;
    }
    if (circle.route) navigate(circle.route);
  };

  const resetHelper = () => {
    setHelpAnswers({});
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
            recommended={recommendedKey === circle.key}
            onClick={() => handleCircleClick(circle)}
            index={idx}
          />
        ))}
      </div>

      {/* "I'm not sure — help me choose" bridge. Sits directly below the
          circles and, when tapped, opens a compact two-question wizard
          that recommends one of the four circles in place (with a
          "Recommended for you" badge) instead of forcing parents to
          guess. Sticks to the founder's rule: no wrong answers, and
          the recommendation never opens a new route — the parent still
          taps the highlighted circle themselves. */}
      <div className="mt-5" data-testid="front-door-helper-wrap">
        {helpOpen ? (
          <HelpMeChoosePanel
            answers={helpAnswers}
            setAnswers={setHelpAnswers}
            recommendedKey={recommendedKey}
            onDismiss={() => {
              // Keep the saved answers so the "Recommended" badge stays
              // lit; just fold the panel. The parent can reopen the
              // helper any time from the pill below.
              setHelpOpen(false);
            }}
            onReset={resetHelper}
          />
        ) : recommendedKey ? (
          // Returning parent — the helper has already recommended a
          // pathway. Show a soft "saved" chip so they see it stuck and
          // can revise or clear the answer any time.
          <div
            className="inline-flex items-center gap-2 rounded-full border border-[#D6CFE8] bg-[#F5F1FB] px-3 py-1.5 text-xs text-[#3D1A78]"
            data-testid="front-door-helper-saved-chip"
          >
            <Sparkles size={12} strokeWidth={2.4} />
            <span>
              Recommended for you:{" "}
              <strong className="font-semibold">
                {CIRCLE_LABELS[recommendedKey]}
              </strong>
            </span>
            <button
              type="button"
              onClick={() => setHelpOpen(true)}
              data-testid="front-door-helper-change"
              className="ml-1 underline text-[#3D1A78] font-semibold hover:text-[#2A0F5F]"
            >
              Change my answer
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setHelpOpen(true)}
            data-testid="front-door-helper-open"
            className="inline-flex items-center gap-2 rounded-full border border-[#D6CFE8] bg-white px-4 py-2 text-sm text-[#3D1A78] font-semibold hover:bg-[#F5F1FB] transition-colors"
          >
            <HelpCircle size={14} />
            I&rsquo;m not sure — help me choose
          </button>
        )}
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
          {/* Now that the parent has expanded the tile, they've told us
              they're interested — so surface the clinical terminology
              they'll see downstream (25-question deep dives, joint
              alignment report). */}
          <ClinicalDetailChip
            text={CIRCLES.find((c) => c.key === "child-needs")?.clinicalDetail}
            tone="green"
            testId="front-door-child-needs-clinical"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
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
          {/* Surface the clinical steps now that the parent has opened
              this pathway — they'll see these labels on the pages
              they're about to visit, so name them here first. */}
          <ClinicalDetailChip
            text={CIRCLES.find((c) => c.key === "co-parenting")?.clinicalDetail}
            tone="purple"
            testId="front-door-coparenting-clinical"
          />
          <ol
            className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4"
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

function FrontDoorTile({ circle, expanded, onClick, index = 0, recommended = false }) {
  const Icon = circle.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={circle.expandable ? expanded : undefined}
      data-testid={circle.testid}
      style={{ animationDelay: `${index * 90}ms` }}
      className={`front-door-tile group text-left rounded-3xl border ${recommended ? "border-[#3D1A78] shadow-lg ring-2 ring-[#3D1A78]/40" : "border-[#EFE9F9]"} bg-white p-5 ring-1 ${!recommended ? circle.tone.ring : ""} ${circle.tone.hover} hover:-translate-y-1 hover:shadow-xl active:translate-y-0 active:scale-[0.98] transition-all duration-200 flex flex-col relative`}
    >
      {recommended && (
        <span
          className="absolute -top-2 left-4 inline-flex items-center gap-1 rounded-full bg-[#3D1A78] text-white px-2.5 py-0.5 text-[10px] uppercase tracking-[0.15em] font-bold shadow-md"
          data-testid={`${circle.testid}-recommended`}
        >
          <Sparkles size={10} strokeWidth={2.4} /> Recommended
        </span>
      )}
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

function HelpMeChoosePanel({ answers, setAnswers, recommendedKey, onDismiss, onReset }) {
  const focusPicked = Boolean(answers.focus);
  const urgencyPicked = Boolean(answers.urgency);
  const step = focusPicked ? 2 : 1;
  const showResult = focusPicked && urgencyPicked && recommendedKey;

  return (
    <div
      className="rounded-3xl border border-[#D6CFE8] bg-gradient-to-br from-[#F8F7FC] to-white p-5 sm:p-6"
      data-testid="front-door-helper-panel"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-[#3D1A78] text-white grid place-items-center shrink-0">
            <HelpCircle size={18} strokeWidth={2.2} />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
              Step {step} of 2
            </div>
            <h3 className="font-serif text-xl text-[#1A1330] leading-tight mt-1">
              Let&rsquo;s find the right pathway together
            </h3>
            <p className="text-[13px] text-[#4B4567] mt-1 leading-relaxed max-w-xl">
              Two quick questions. There are no wrong answers — SA CoParents
              simply highlights the pathway that best fits what you told us.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          data-testid="front-door-helper-close"
          className="text-xs text-[#4B4567] hover:text-[#3D1A78] underline shrink-0"
        >
          Close
        </button>
      </div>

      {!showResult && (
        <div className="mt-5 space-y-4">
          {HELPER_QUESTIONS.map((q, qIdx) => {
            // Only render the second question once the first is picked.
            if (qIdx === 1 && !focusPicked) return null;
            const currentAnswer = answers[q.id];
            return (
              <fieldset
                key={q.id}
                data-testid={`front-door-helper-q-${q.id}`}
                className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
              >
                <legend className="text-sm font-semibold text-[#1A1330] px-1">
                  {q.prompt}
                </legend>
                <div className="mt-3 grid gap-2">
                  {q.options.map((opt) => {
                    const selected = currentAnswer === opt.key;
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() =>
                          setAnswers((prev) => ({ ...prev, [q.id]: opt.key }))
                        }
                        data-testid={`front-door-helper-q-${q.id}-opt-${opt.key}`}
                        className={`text-left rounded-xl border px-3.5 py-2.5 text-sm transition-all ${
                          selected
                            ? "border-[#3D1A78] bg-[#EFE9F9] text-[#1A1330] font-semibold shadow-sm"
                            : "border-[#E5E0EE] bg-white text-[#1A1330] hover:border-[#3D1A78]"
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
            );
          })}
        </div>
      )}

      {showResult && (
        <div
          className="mt-5 rounded-2xl border-2 border-[#3D1A78]/40 bg-white p-4"
          data-testid="front-door-helper-result"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#3D1A78] text-white grid place-items-center shrink-0">
              <Sparkles size={18} strokeWidth={2.2} />
            </div>
            <div className="flex-1">
              <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                Recommended for you
              </div>
              <div
                className="font-serif text-xl text-[#1A1330] leading-tight mt-1"
                data-testid="front-door-helper-result-label"
              >
                {CIRCLE_LABELS[recommendedKey]}
              </div>
              <p className="text-[13px] text-[#4B4567] mt-2 leading-relaxed">
                Look above — this pathway is now highlighted for you. Tap it
                when you&rsquo;re ready to start. You can always change your
                answer later.
              </p>
              <button
                type="button"
                onClick={onReset}
                data-testid="front-door-helper-restart"
                className="mt-3 text-xs text-[#3D1A78] font-semibold hover:underline"
              >
                Answer the questions again
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
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


/**
 * ClinicalDetailChip — a small "Under the hood" strip shown inside the
 * expanded pathway panels. Delays the formal / clinical terminology
 * (Foundation Statement, TISFL, Joint Alignment Report, etc.) until
 * *after* the parent has told us they want to explore this pathway,
 * per the 2026-03-05 founder rule: everyday language first, clinical
 * terms revealed once they've selected.
 */
function ClinicalDetailChip({ text, tone = "purple", testId }) {
  if (!text) return null;
  const palette = {
    purple: "border-[#D6CFE8] bg-white text-[#4B4567]",
    green: "border-[#C9E7D4] bg-white text-[#215D3E]",
  };
  return (
    <div
      className={`inline-flex items-start gap-2 rounded-full border ${palette[tone] || palette.purple} px-3 py-1.5 text-[11px] leading-snug`}
      data-testid={testId}
    >
      <span className="text-[10px] uppercase tracking-[0.16em] font-bold shrink-0 pt-[1px]">
        Under the hood
      </span>
      <span className="text-[11px] leading-snug">{text}</span>
    </div>
  );
}
