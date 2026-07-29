import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ShieldCheck,
  Facebook,
  Heart,
  MessageCircle,
  Sparkles,
  ClipboardList,
  BookOpen,
  CheckCircle2,
  Users,
  Compass,
  Quote,
  ChevronRight,
  Lock,
  FlaskConical,
  LifeBuoy,
  FileText,
  BarChart3,
  Award,
  Baby,
  AlertTriangle,
  Scale,
  Handshake,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { markOrientationSeen } from "./Orientation";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

/* ============================================================
   ENTER-APP CONTEXT
   Multiple entry paths:
     - enterAssessments: scrolls to the situation picker (default primary CTA)
     - enterGuest:       creates guest session + goes straight to /dashboard
                         (skips the intro video)
     - watchIntro:       goes to /watch (public trailer)
     - enterWithFocus:   used by the situation picker — creates guest session,
                         records the user's chosen focus in localStorage so the
                         dashboard can prioritize the right assessment,
                         then navigates to /dashboard with the intro video
                         SKIPPED for safety-oriented picks.
============================================================ */
const EnterAppContext = React.createContext(null);

const FOCUS_STORAGE_KEY = "sac_recommended_focus_v1";

function EnterAppProvider({ children }) {
  const { startGuest } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const enterAssessments = () => {
    // Just scroll to the situation picker. This is the primary CTA.
    scrollToId("situation-picker");
  };

  const watchIntro = () => {
    navigate("/watch");
  };

  const enterGuest = async () => {
    if (loading) return;
    setError(null);
    setLoading(true);
    try {
      await startGuest();
      markOrientationSeen();
      navigate("/dashboard");
    } catch (err) {
      logError("Enter app failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Couldn't open the app right now. Please try again in a moment."
      );
      setLoading(false);
    }
  };

  const enterWithFocus = async ({ focus, route }) => {
    // Focus goes into localStorage so the dashboard can pin the right
    // "Do this next" card. `route` is the target path after guest session.
    if (loading) return;
    setError(null);
    setLoading(true);
    try {
      if (focus) {
        try { localStorage.setItem(FOCUS_STORAGE_KEY, focus); } catch { /* ignore */ }
      }
      await startGuest();
      markOrientationSeen();
      navigate(route || "/dashboard");
    } catch (err) {
      logError("Enter app with focus failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Couldn't open the app right now. Please try again in a moment."
      );
      setLoading(false);
    }
  };

  return (
    <EnterAppContext.Provider
      value={{ enterAssessments, enterGuest, watchIntro, enterWithFocus, loading, error }}
    >
      {children}
    </EnterAppContext.Provider>
  );
}

function useEnterApp() {
  const ctx = React.useContext(EnterAppContext);
  if (!ctx) throw new Error("useEnterApp outside EnterAppProvider");
  return ctx;
}

/* ============================================================
   SMALL UI PRIMITIVES
============================================================ */
function Eyebrow({ children, color = "text-[#3D1A78]" }) {
  return (
    <div
      className={`text-[11px] tracking-[0.28em] uppercase font-bold ${color} mb-3`}
    >
      {children}
    </div>
  );
}

function PrimaryCTA({ children, testid }) {
  const { enterAssessments } = useEnterApp();
  return (
    <button
      type="button"
      onClick={enterAssessments}
      data-testid={testid}
      className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
    >
      {children}
      <ArrowRight size={16} />
    </button>
  );
}

function TertiaryCTA({ children, onClick, testid, loading }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      data-testid={testid}
      className="text-sm font-semibold text-[#4B4567] hover:text-[#3D1A78] hover:underline underline-offset-2 disabled:opacity-60"
    >
      {loading ? "Opening…" : children}
    </button>
  );
}

function SecondaryCTA({ children, onClick, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-white text-[#3D1A78] font-semibold text-sm border border-[#3D1A78]/20 hover:border-[#3D1A78] hover:-translate-y-0.5 transition-all"
    >
      {children}
    </button>
  );
}

function scrollToId(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ============================================================
   HEADER + FOOTER
============================================================ */
function MarketingHeader() {
  return (
    <header className="absolute top-0 left-0 right-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5" data-testid="header-logo">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm">
            <Heart size={16} strokeWidth={2.4} />
          </div>
          <div className="font-serif text-[#1A1330] text-lg leading-none">
            SA CoParents
          </div>
        </Link>
        <div className="flex items-center gap-4">
          {FB_URL && (
            <a
              href={FB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="w-9 h-9 rounded-full grid place-items-center text-[#3D1A78] hover:bg-white/50 transition-colors"
              data-testid="header-facebook-link"
              aria-label="Facebook"
            >
              <Facebook size={18} />
            </a>
          )}
        </div>
      </div>
    </header>
  );
}

function MarketingFooter() {
  return (
    <footer className="bg-[#1A1330] text-white/80 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center">
              <Heart size={18} strokeWidth={2.4} />
            </div>
            <div>
              <div className="font-serif text-white text-lg leading-none">
                SA CoParents
              </div>
              <div className="text-xs text-white/60 mt-1">
                From conflict to cooperation.
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
            <Link to="/terms" className="hover:text-white" data-testid="footer-terms-link">
              Terms
            </Link>
            <Link to="/privacy" className="hover:text-white" data-testid="footer-privacy-link">
              Privacy
            </Link>
            <Link to="/data-retention" className="hover:text-white" data-testid="footer-data-retention-link">
              Data retention
            </Link>
            <Link to="/methodology" className="hover:text-white" data-testid="footer-methodology-link">
              Methodology
            </Link>
            <Link to="/accessibility" className="hover:text-white" data-testid="footer-accessibility-link">
              Accessibility
            </Link>
            {FB_URL && (
              <a
                href={FB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-white inline-flex items-center gap-1.5"
                data-testid="footer-facebook-link"
              >
                <Facebook size={14} /> facebook.com/SACoparent
              </a>
            )}
          </div>
        </div>
        <div className="text-[11px] text-white/40 mt-8 leading-relaxed max-w-2xl">
          SA CoParents is an educational and preparation tool. It is not legal
          advice, therapy, or a substitute for professional mediation. Always
          consult qualified family-law and mental-health professionals for your
          situation.
        </div>
      </div>
    </footer>
  );
}

/* ============================================================
   SECTION 1 — HERO
============================================================ */
/* ============================================================
   SITUATION-FIRST OPENING
   6 situation choices → routed to the safest & most relevant next step.
   Coercive-control / safety pickers go DIRECTLY to the Safety Assessment
   with NO cooperation messaging shown first.
============================================================ */
const SITUATIONS = [
  {
    key: "cooperate",
    label: "We generally cooperate",
    icon: <Handshake />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "You have a foundation to build on. This assessment turns your existing goodwill into a concrete, child-centered agenda you can bring to any co-parenting conversation.",
      cta: "Start the readiness assessment",
      tone: "cooperative",
      icon: <Scale size={20} />,
    },
  },
  {
    key: "difficult",
    label: "Communication is difficult",
    icon: <MessageCircle />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "The Readiness Assessment includes a communication-clarity dimension. It will name what's breaking down and give you scripts for the highest-leverage conversations.",
      cta: "Start the readiness assessment",
      tone: "warn",
      icon: <MessageCircle size={20} />,
    },
  },
  {
    key: "high-conflict",
    label: "We experience ongoing high conflict",
    icon: <AlertTriangle />,
    focus: "safety",
    route: "/safety-assessment",
    result: {
      title: "Start with the Family Violence & Communication Safety Assessment.",
      body: "Ongoing high conflict deserves a private safety screen BEFORE any cooperation work. We'll help you identify the safest communication pathway — from structured written to assisted — and surface Texas crisis resources.",
      cta: "Start the safety assessment",
      tone: "urgent",
      icon: <ShieldCheck size={20} />,
      safetyBanner: "If you are in immediate danger, call 911. Suicide & Crisis Lifeline: 988. National Domestic Violence Hotline: 1-800-799-SAFE.",
    },
  },
  {
    key: "safety",
    label: "I have safety or family-violence concerns",
    icon: <ShieldCheck />,
    focus: "safety",
    route: "/safety-assessment",
    result: {
      title: "Start with the Family Violence & Communication Safety Assessment.",
      body: "Your safety and your child's safety come first. This is a private screen that never asks you to cooperate with the other parent. It recommends the safest communication pathway (including no-direct-contact) and includes Texas crisis hotlines.",
      cta: "Start the safety assessment",
      tone: "urgent",
      icon: <ShieldCheck size={20} />,
      safetyBanner: "If you are in immediate danger, call 911. Suicide & Crisis Lifeline: 988. National Domestic Violence Hotline: 1-800-799-SAFE.",
    },
  },
  {
    key: "special-needs",
    label: "Our child has additional or special needs",
    icon: <Baby />,
    focus: "special-needs",
    route: "/dashboard",
    result: {
      title: "Start with the Special Needs Assessment.",
      body: "A 7-domain evaluation with a Consistency-Between-Homes score. You'll get a 7-part care plan you can hand to your pediatrician, school, or mediator — plus a safeguards-and-disagreement pathway if the two homes are out of sync.",
      cta: "Start the special needs assessment",
      tone: "cooperative",
      icon: <Baby size={20} />,
    },
  },
  {
    key: "mediation",
    label: "I am preparing for mediation or court",
    icon: <Scale />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "You'll build a child-centered agenda, name your priorities and flexibility areas, and download a Mediation Summary PDF ready to hand to your mediator.",
      cta: "Start the readiness assessment",
      tone: "cooperative",
      icon: <Scale size={20} />,
    },
  },
];

const TONE_STYLES = {
  cooperative: { border: "border-[#3D1A78]/25", bg: "bg-white", chipBg: "bg-[#EFE9F9]", chipText: "text-[#3D1A78]", cta: "bg-[#3D1A78] hover:bg-[#2D0F63]" },
  warn:        { border: "border-[#F5C147]/40", bg: "bg-[#FFFAEC]", chipBg: "bg-[#FFF3D1]", chipText: "text-[#B27700]", cta: "bg-[#B27700] hover:bg-[#8F6100]" },
  urgent:      { border: "border-[#B85B00]/40", bg: "bg-[#FFF3E9]", chipBg: "bg-[#FFDFC4]", chipText: "text-[#8F4600]", cta: "bg-[#B85B00] hover:bg-[#8F4600]" },
};

function SituationPicker() {
  const { enterWithFocus, loading } = useEnterApp();
  const [picked, setPicked] = useState(null);

  const choose = (s) => setPicked(s);
  const reset = () => setPicked(null);
  const proceed = () => {
    if (!picked) return;
    enterWithFocus({ focus: picked.focus, route: picked.route });
  };

  if (!picked) {
    return (
      <div
        id="situation-picker"
        className="rounded-3xl border border-[#E5E0EE] bg-white/85 backdrop-blur-sm p-6 sm:p-8 shadow-sm max-w-3xl mx-auto"
        data-testid="situation-picker"
      >
        <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
          Step 1
        </div>
        <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
          What best describes your situation?
        </h2>
        <p className="text-sm text-[#4B4567] mt-2">
          There are no wrong answers. Your choice helps us route you to the
          safest and most relevant starting point.
        </p>
        <div className="mt-5 grid sm:grid-cols-2 gap-2.5">
          {SITUATIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => choose(s)}
              className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-center gap-3"
              data-testid={`situation-${s.key}`}
            >
              <div className="shrink-0 w-9 h-9 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center group-hover:bg-[#3D1A78] group-hover:text-white transition-colors">
                {s.icon}
              </div>
              <span className="text-sm sm:text-[15px] text-[#1A1330] leading-snug">{s.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const tone = TONE_STYLES[picked.result.tone] || TONE_STYLES.cooperative;
  return (
    <div
      id="situation-picker"
      className={`rounded-3xl border-2 ${tone.border} ${tone.bg} p-6 sm:p-8 shadow-sm max-w-3xl mx-auto fade-up`}
      data-testid="situation-picker-result"
    >
      {picked.result.safetyBanner && (
        <div
          className="rounded-2xl border border-[#B85B00]/40 bg-[#FFF3E9] p-3 mb-5 text-xs sm:text-sm text-[#8F4600] leading-relaxed"
          data-testid="situation-picker-safety-banner"
        >
          <strong>Your safety comes first.</strong> {picked.result.safetyBanner}
        </div>
      )}
      <div className="flex items-center gap-3 mb-3">
        <div className={`shrink-0 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${tone.chipBg} ${tone.chipText}`}>
          {picked.result.icon}
          {picked.label}
        </div>
      </div>
      <h3 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug" data-testid="situation-picker-result-title">
        {picked.result.title}
      </h3>
      <p className="text-sm sm:text-base text-[#4B4567] mt-3 leading-relaxed">
        {picked.result.body}
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          onClick={proceed}
          disabled={loading}
          className={`inline-flex items-center gap-2 text-white font-semibold px-6 py-3 rounded-full text-sm sm:text-base transition-colors ${tone.cta} disabled:opacity-60`}
          data-testid="situation-picker-cta"
        >
          {loading ? "Opening…" : picked.result.cta}
          {!loading && <ArrowRight size={16} />}
        </button>
        <button
          onClick={reset}
          className="text-sm text-[#4B4567] hover:text-[#3D1A78] hover:underline"
          data-testid="situation-picker-reset"
        >
          Change my answer
        </button>
      </div>
    </div>
  );
}

/* ============================================================
   SECTION 1 — HERO (tagline + situation picker embedded)
============================================================ */
function Hero() {
  const { enterGuest, loading: guestLoading, watchIntro } = useEnterApp();
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] pt-28 sm:pt-32 pb-16 sm:pb-20">
      <div className="absolute -top-32 -left-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/40 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-32 w-[30rem] h-[30rem] rounded-full bg-[#A8DCDC]/40 blur-3xl pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 text-center fade-up">
        <Eyebrow>The SA CoParents App</Eyebrow>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-[1.05] tracking-tight">
          Start with your situation.
          <br />
          <span className="text-[#3D1A78]">Focus on your child.</span>
          <br />
          Leave ready to meet your child&rsquo;s&nbsp;needs.
        </h1>
        <p className="max-w-2xl mx-auto text-sm sm:text-base text-[#4B4567] mt-6 leading-relaxed">
          Personalized assessments and practical reports to move forward with
          greater clarity, confidence, and purpose.
        </p>

        {/* Hero-level situation picker */}
        <div className="mt-10">
          <SituationPicker />
        </div>

        {/* Rewired CTAs */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <SecondaryCTA
            testid="hero-watch-cta"
            onClick={watchIntro}
          >
            Watch How It Works
          </SecondaryCTA>
          <TertiaryCTA
            testid="hero-guest-cta"
            onClick={enterGuest}
            loading={guestLoading}
          >
            Or explore as a guest &rarr;
          </TertiaryCTA>
        </div>

        {/* Trust indicators */}
        <ul className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-3 max-w-4xl mx-auto">
          {[
            "Child-Centered Approach",
            "Child-Focused Mediation Preparation",
            "Practical Communication Tools",
            "Developed by Family Mediation Professionals",
          ].map((label) => (
            <li
              key={label}
              className="flex items-start gap-2 text-left text-xs sm:text-sm text-[#1A1330] bg-white/70 backdrop-blur-sm border border-white px-3.5 py-2.5 rounded-xl shadow-sm"
              data-testid={`hero-trust-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <CheckCircle2
                size={16}
                className="text-[#2DB5B5] mt-0.5 shrink-0"
              />
              <span className="leading-snug">{label}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ============================================================
   THREE REPORTS STRIP — compact "at a glance" trio showing the
   three primary artefacts parents receive.
============================================================ */
function ThreeReportsStrip() {
  return (
    <section id="three-reports" className="relative py-14 sm:py-16 bg-white border-y border-[#EFE9F9]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
        <Eyebrow>Three reports you can receive</Eyebrow>
        <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-2">
          Real deliverables you can hand to a mediator, therapist, or attorney.
        </h2>
      </div>
      <div className="mt-8 grid md:grid-cols-3 gap-4 max-w-6xl mx-auto px-4 sm:px-6">
        <ThreeReportsCover
          testid="three-reports-situation"
          number="1"
          title="Understand your co-parenting situation"
          body="A private snapshot of how you and the other parent are actually communicating today — with concrete next steps."
          accent="#3D1A78"
          sampleHref="/downloads/sacoparents-family-violence-report.pdf"
          sampleLabel="View sample safety report (PDF)"
        />
        <ThreeReportsCover
          testid="three-reports-foundation"
          number="2"
          title="Create your Foundation Statement"
          body="A one-page statement of your child-centered goals — the anchor you can return to whenever things get emotionally hot."
          accent="#2DB5B5"
          sampleHref="/downloads/sacoparents-foundation-statement.pdf"
          sampleLabel="View sample Foundation Statement (PDF)"
        />
        <ThreeReportsCover
          testid="three-reports-child-needs"
          number="3"
          title="Prepare a Child Needs Statement for mediation"
          body="A structured, child-focused agenda you can bring straight into your mediation session or attorney meeting."
          accent="#B85B00"
          sampleHref="/downloads/sacoparents-special-needs-report.pdf"
          sampleLabel="View sample Special Needs report (PDF)"
        />
      </div>
    </section>
  );
}

function ThreeReportsCover({ testid, number, title, body, accent, sampleHref, sampleLabel }) {
  return (
    <article
      data-testid={testid}
      className="rounded-2xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#F7F4FC] p-6 sm:p-7 relative overflow-hidden hover:shadow-md transition-shadow flex flex-col"
    >
      <div
        className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center font-serif text-lg font-semibold text-white"
        style={{ backgroundColor: accent }}
      >
        {number}
      </div>
      <div className="mb-3">
        <FileText size={20} style={{ color: accent }} />
      </div>
      <h3 className="font-serif text-lg text-[#1A1330] leading-snug pr-10">
        {title}
      </h3>
      <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">{body}</p>
      <div className="mt-4 text-[11px] uppercase tracking-[0.14em] font-bold" style={{ color: accent }}>
        Downloadable PDF · shareable
      </div>
      <div className="mt-auto pt-4">
        {sampleHref ? (
          <a
            data-testid={`${testid}-sample-link`}
            href={sampleHref}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-semibold rounded-full px-3.5 py-1.5 border transition-colors"
            style={{ color: accent, borderColor: accent, backgroundColor: "rgba(255,255,255,0.6)" }}
          >
            {sampleLabel}
            <span aria-hidden>→</span>
          </a>
        ) : (
          <span
            data-testid={`${testid}-sample-placeholder`}
            className="inline-flex items-center gap-1.5 text-xs italic text-[#857E9C]"
          >
            {sampleLabel}
          </span>
        )}
      </div>
    </article>
  );
}

/* ============================================================
   SECTION 2 — THE PROBLEM
============================================================ */
function TheProblem() {
  const challenges = [
    "Frequent arguments about parenting decisions",
    "Difficult text and email exchanges",
    "Children caught in the middle",
    "Repeated trips to court",
    "Lack of trust and cooperation",
    "Fear that conflict is harming the children",
  ];
  return (
    <section className="py-24 sm:py-28 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-3xl mx-auto fade-up">
          <Eyebrow color="text-[#C28771]">The Problem</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
            When Parents Fight, Children Feel It
          </h2>
          <p className="text-base text-[#4B4567] mt-6 leading-relaxed">
            Separation and divorce can create ongoing conflict that impacts
            every member of the family. Miscommunication, misunderstandings, and
            unresolved emotions often lead parents into repeated arguments,
            costly legal disputes, and increased stress for their children.
          </p>
          <p className="text-base text-[#4B4567] mt-4 leading-relaxed">
            Many parents want to do better—they simply need the right tools and
            guidance.
          </p>
        </div>

        <div className="mt-14 grid lg:grid-cols-2 gap-6 lg:gap-10 items-start">
          <div className="card-soft p-7 sm:p-8">
            <Eyebrow color="text-[#C28771]">Common Challenges</Eyebrow>
            <ul className="space-y-3 mt-2" data-testid="problem-challenges-list">
              {challenges.map((c) => (
                <li
                  key={c}
                  className="flex items-start gap-3 text-[#1A1330] text-sm sm:text-base"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C28771] mt-2.5 shrink-0" />
                  <span className="leading-relaxed">{c}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card-soft p-7 sm:p-8 bg-gradient-to-br from-[#EFE9F9] to-[#E4F1F1]">
            <Eyebrow color="text-[#2DB5B5]">The Good News</Eyebrow>
            <p className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug mt-2">
              These patterns can change.
            </p>
            <p className="text-sm sm:text-base text-[#4B4567] mt-4 leading-relaxed">
              With the right tools, support, and commitment to your child&apos;s
              well-being, parents can move from conflict toward cooperation and
              create healthier outcomes for the entire family.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 3 — HOW IT WORKS
============================================================ */
function HowItWorks() {
  const steps = [
    {
      n: "1",
      title: "Assess",
      icon: ClipboardList,
      body: "Complete a brief co-parenting assessment to identify strengths and opportunities for growth.",
    },
    {
      n: "2",
      title: "Learn",
      icon: BookOpen,
      body: "Access practical tools, exercises, and guidance designed to improve communication, manage conflict, and strengthen co-parenting skills.",
    },
    {
      n: "3",
      title: "Prepare",
      icon: Compass,
      body: "Develop the skills needed for productive conversations, healthier co-parenting, and successful Child-Focused Mediation.",
    },
  ];
  return (
    <section
      id="how-it-works"
      className="relative py-24 sm:py-28 bg-[#F8F7FC] scroll-mt-16"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto fade-up">
          <Eyebrow>How the App Works</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
            Three Steps Toward Healthier Co-Parenting
          </h2>
        </div>

        <div className="mt-16 grid md:grid-cols-3 gap-6 lg:gap-8">
          {steps.map((s) => (
            <div
              key={s.n}
              className="card-soft p-7 sm:p-8 relative"
              data-testid={`how-step-${s.n}`}
            >
              <div className="absolute -top-5 -left-2 font-serif text-[5rem] leading-none text-[#3D1A78]/8 select-none">
                {s.n}
              </div>
              <div className="relative">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm mb-5">
                  <s.icon size={20} strokeWidth={2.2} />
                </div>
                <Eyebrow>Step {s.n}</Eyebrow>
                <h3 className="font-serif text-2xl text-[#1A1330] mb-3">
                  {s.title}
                </h3>
                <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed">
                  {s.body}
                </p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-sm sm:text-base text-[#4B4567] mt-14 max-w-xl mx-auto">
          Every step is designed to help parents create a healthier environment
          for their children.
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 4 — WHY SA COPARENTS IS DIFFERENT
============================================================ */
function WhyDifferent() {
  const supports = [
    "Emotional well-being",
    "Educational success",
    "Healthy parent-child relationships",
    "Consistent parenting expectations",
    "Long-term family stability",
  ];
  return (
    <section className="py-24 sm:py-28 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-3xl mx-auto fade-up">
          <Eyebrow>Why SA CoParents is Different</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
            More Than a Co-Parenting App
          </h2>
          <p className="text-base text-[#4B4567] mt-6 leading-relaxed">
            Most co-parenting apps help parents exchange information.
          </p>
          <p className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-3 leading-snug">
            SA CoParents helps parents build a stronger foundation for raising
            their children together.
          </p>
        </div>

        <div className="mt-14 grid lg:grid-cols-2 gap-6 lg:gap-8">
          <div className="card-soft p-7 sm:p-8">
            <div className="w-12 h-12 rounded-2xl bg-[#EFE9F9] grid place-items-center text-[#3D1A78] mb-5">
              <Heart size={20} strokeWidth={2.2} />
            </div>
            <h3 className="font-serif text-2xl text-[#1A1330] mb-3">
              Child-Centered Focus
            </h3>
            <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed">
              Keep your child&apos;s needs at the center of every conversation and
              decision.
            </p>
          </div>

          <div className="card-soft p-7 sm:p-8">
            <div className="w-12 h-12 rounded-2xl bg-[#E4F1F1] grid place-items-center text-[#2DB5B5] mb-5">
              <MessageCircle size={20} strokeWidth={2.2} />
            </div>
            <h3 className="font-serif text-2xl text-[#1A1330] mb-3">
              Child-Focused Mediation Preparation
            </h3>
            <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed">
              Learn the communication and problem-solving skills that support
              successful mediation outcomes.
            </p>
          </div>
        </div>

        {/* Foundation Statement block */}
        <div className="mt-10 card-soft p-7 sm:p-10 relative overflow-hidden">
          <div className="absolute -top-16 -right-16 w-72 h-72 rounded-full bg-[#D4C5F0]/30" />
          <div className="relative grid lg:grid-cols-5 gap-8 lg:gap-12 items-start">
            <div className="lg:col-span-3">
              <Eyebrow>Foundation Statement</Eyebrow>
              <h3 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug">
                Create a Foundation Statement
              </h3>
              <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mt-4">
                Develop a shared Foundation Statement that identifies your
                child&#39;s goals, needs, values, and priorities.
              </p>
              <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mt-3">
                This Foundation Statement serves as a guiding framework for
                co-parenting decisions and can become the foundation of a
                comprehensive Co-Parenting Agreement.
              </p>
              <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mt-3">
                By focusing on shared goals rather than ongoing disagreements,
                parents create a roadmap that supports:
              </p>
            </div>
            <ul className="lg:col-span-2 space-y-2.5">
              {supports.map((s) => (
                <li
                  key={s}
                  className="flex items-start gap-2.5 text-sm text-[#1A1330] bg-[#F8F7FC] px-3.5 py-2.5 rounded-xl"
                >
                  <CheckCircle2
                    size={15}
                    className="text-[#2DB5B5] mt-0.5 shrink-0"
                  />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Agreement block */}
        <div className="mt-10 card-soft p-7 sm:p-10 bg-gradient-to-br from-[#EFE9F9] to-[#E4F1F1]">
          <Eyebrow>Co-Parenting Agreement</Eyebrow>
          <h3 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug">
            Build a Meaningful Co-Parenting Agreement
          </h3>
          <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mt-4">
            Transform your Foundation Statement into a practical Co-Parenting
            Agreement that helps parents make decisions aligned with their
            child&apos;s best interests.
          </p>
          <p className="text-sm sm:text-base text-[#1A1330] leading-relaxed mt-3">
            Rather than focusing on what parents disagree about, the process
            begins with what they both want for their child.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 5 — CHILD-FOCUSED MEDIATION
============================================================ */
function ChildFocusedMediation() {
  const helps = [
    "Communicate with greater respect and clarity",
    "Respond thoughtfully instead of reacting emotionally",
    "Focus on their children's needs rather than past disagreements",
    "Develop healthier co-parenting habits",
    "Build a foundation for long-term family stability",
  ];
  const assessmentBenefits = [
    "Identify communication patterns that contribute to conflict",
    "Measure co-parenting strengths and growth opportunities",
    "Recognize barriers to productive mediation",
    "Gain insights into child-centered decision-making",
    "Create a personalized pathway toward healthier co-parenting",
  ];
  return (
    <section
      id="child-focused-mediation"
      className="relative py-24 sm:py-28 bg-[#F8F7FC] scroll-mt-16"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-3xl mx-auto fade-up">
          <Eyebrow>Our Foundation</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
            Built on the Principles of
            <br className="hidden sm:block" /> Child-Focused Mediation
          </h2>
          <p className="text-base text-[#4B4567] mt-6 leading-relaxed">
            Child-Focused Mediation helps parents move beyond conflict and make
            decisions based on what is best for their children.
          </p>
        </div>

        <div className="mt-14 grid lg:grid-cols-2 gap-6 lg:gap-10">
          <div className="card-soft p-7 sm:p-8">
            <Eyebrow>The SA CoParents App helps parents</Eyebrow>
            <ul className="space-y-3 mt-2" data-testid="cfm-helps-list">
              {helps.map((h) => (
                <li
                  key={h}
                  className="flex items-start gap-3 text-sm sm:text-base text-[#1A1330]"
                >
                  <CheckCircle2
                    size={16}
                    className="text-[#3D1A78] mt-1 shrink-0"
                  />
                  <span className="leading-relaxed">{h}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card-soft p-7 sm:p-8">
            <Eyebrow>Pre-Mediation Assessment</Eyebrow>
            <h3 className="font-serif text-2xl text-[#1A1330] leading-snug">
              Start with a Pre-Mediation Assessment
            </h3>
            <p className="text-sm sm:text-base text-[#4B4567] mt-3 leading-relaxed">
              Before mediation can be successful, parents need a clear
              understanding of their strengths, challenges, and readiness to
              work together.
            </p>
            <div className="mt-5">
              <div className="text-xs text-[#4B4567] uppercase tracking-[0.18em] mb-2 font-bold">
                The assessment helps parents:
              </div>
              <ul className="space-y-2.5" data-testid="cfm-assessment-list">
                {assessmentBenefits.map((b) => (
                  <li
                    key={b}
                    className="flex items-start gap-2.5 text-sm text-[#1A1330]"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2DB5B5] mt-2.5 shrink-0" />
                    <span className="leading-relaxed">{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <p className="text-center text-sm sm:text-base text-[#4B4567] mt-12 max-w-2xl mx-auto leading-relaxed">
          The assessment provides a starting point for growth, helping parents
          enter mediation better prepared, more informed, and focused on
          achieving outcomes that support their children&apos;s well-being.
        </p>

        <div className="mt-14 card-soft p-8 sm:p-10 text-center bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white relative overflow-hidden">
          <Quote
            size={48}
            className="absolute top-4 left-6 text-white/15"
            strokeWidth={1.5}
          />
          <p className="font-serif text-2xl sm:text-3xl leading-snug relative">
            Children thrive when parents learn to work together,
            <br className="hidden sm:block" /> even when they live apart.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   TRUST SIGNALS — "Why parents trust SA CoParents"
============================================================ */
function TrustSignals() {
  return (
    <section id="trust" className="relative py-20 sm:py-24 bg-gradient-to-br from-[#F8F7FC] via-white to-[#EEF6F6]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-14">
          <Eyebrow>Why parents trust SA CoParents</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight mt-3">
            Built with care. Honest about limits.
          </h2>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-2xl mx-auto">
            Every assessment, PDF, and coaching prompt was designed with two
            beliefs in mind: parents deserve tools that respect their
            intelligence, and children deserve outcomes that come from real
            preparation — not a black box.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-created-by">
            <div className="shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] flex items-center justify-center text-white">
              <Users size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">Created by</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Matt Sossi · Founder, SA CoParents</h3>
              <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
                Built in San Antonio, Texas — because too many parents were
                walking into mediation reactive, unprepared, and afraid.
                Our mission is to move families from emotionally reactive
                to child-centered, one conversation at a time.
              </p>
              <div className="text-xs text-[#857E9C] mt-3">
                <a href="mailto:mattsossi@bsossi.com" className="text-[#3D1A78] hover:underline">mattsossi@bsossi.com</a>
                {" · "}
                <a href="tel:2102241667" className="text-[#3D1A78] hover:underline">210-224-1667</a>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-data">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#3D1A78]/10 flex items-center justify-center text-[#3D1A78]">
              <Lock size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">Your data is protected</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Yours to keep. Yours to delete.</h3>
              <ul className="text-sm text-[#4B4567] mt-2 space-y-1.5 leading-relaxed list-disc pl-4">
                <li>Your answers are never sold or used to train AI models.</li>
                <li>Delete your account and all data any time — deletion is complete within 30 days.</li>
                <li>Share links you create can be revoked. Locked safety sections stay in every shared PDF.</li>
              </ul>
              <div className="text-xs mt-3 flex flex-wrap gap-x-4 gap-y-1">
                <Link to="/privacy" className="text-[#3D1A78] hover:underline">Privacy policy</Link>
                <Link to="/data-retention" className="text-[#3D1A78] hover:underline">Data retention</Link>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-methodology">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#2DB5B5]/15 flex items-center justify-center text-[#0E7A7A]">
              <FlaskConical size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">What this tool can and can&rsquo;t do</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Preparation, not diagnosis.</h3>
              <div className="text-sm text-[#4B4567] mt-2 leading-relaxed space-y-2">
                <p>
                  <strong className="text-[#0E7A7A]">Can do:</strong> Help you name goals, structure your thinking, and generate reports child-focused enough to hand a mediator or pediatrician.
                </p>
                <p>
                  <strong className="text-[#B85B00]">Can&rsquo;t do:</strong> Replace a lawyer, therapist, mediator, or physician. Every score is a conversation starter — never the last word.
                </p>
              </div>
              <div className="text-xs mt-3">
                <Link to="/methodology" className="text-[#3D1A78] hover:underline">See how each score is calculated</Link>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-professional-help">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#B85B00]/12 flex items-center justify-center text-[#B85B00]">
              <LifeBuoy size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">When to seek professional help</div>
              <h3 className="font-serif text-xl text-[#1A1330]">If safety is a question, call a human.</h3>
              <ul className="text-sm text-[#4B4567] mt-2 leading-relaxed space-y-1.5">
                <li><strong>988</strong> — Suicide & Crisis Lifeline (call or text)</li>
                <li><strong>1-800-799-SAFE</strong> — National Domestic Violence Hotline</li>
                <li><strong>911</strong> — Immediate danger</li>
                <li>Consult a family law attorney before any custody agreement is signed.</li>
                <li>A licensed therapist can support your child through transition — this app can&rsquo;t.</li>
              </ul>
              <div className="text-xs mt-3">
                <Link to="/safety" className="text-[#3D1A78] hover:underline">See our crisis-resource page</Link>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SAMPLE REPORTS — Preview of what parents receive
============================================================ */
const SAMPLE_TABS = [
  { id: "mediation",      label: "Mediation Summary",       icon: <FileText size={16} />,    subtitle: "PDF · 6–8 pages · child-centered agenda for your mediator" },
  { id: "special-needs",  label: "Special Needs Care Plan", icon: <Baby size={16} />,        subtitle: "PDF · 6-part plan · Consistency-Between-Homes score included" },
  { id: "safety",         label: "Safety Assessment",       icon: <ShieldCheck size={16} />, subtitle: "PDF · pathway recommendation · Texas crisis resources" },
  { id: "progress",       label: "Growth Snapshot",         icon: <BarChart3 size={16} />,   subtitle: "In-app · longitudinal charts · updates every time you check in" },
];

function SampleReports() {
  const [tab, setTab] = useState("mediation");
  return (
    <section id="sample-reports" className="relative py-20 sm:py-24 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-10">
          <Eyebrow>See what you&rsquo;ll receive</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight mt-3">
            Real reports. Real usefulness.
          </h2>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-2xl mx-auto">
            Every assessment ends in something you can actually use — download,
            share, and hand to the people who need to see it. Here&rsquo;s a
            peek at each format.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-2 mb-8" role="tablist" data-testid="sample-reports-tabs">
          {SAMPLE_TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => setTab(t.id)}
                data-testid={`sample-tab-${t.id}`}
                className={
                  "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-colors " +
                  (active
                    ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                    : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78] hover:text-[#3D1A78]")
                }
              >
                {t.icon}
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="max-w-4xl mx-auto">
          <div className="text-center text-[13px] text-[#857E9C] mb-5">
            {SAMPLE_TABS.find((x) => x.id === tab)?.subtitle}
          </div>
          {tab === "mediation" && <SampleMediation />}
          {tab === "special-needs" && <SampleSpecialNeeds />}
          {tab === "safety" && <SampleSafety />}
          {tab === "progress" && <SampleProgress />}
        </div>

        <p className="text-center text-xs text-[#857E9C] mt-8 max-w-lg mx-auto">
          These previews use anonymized sample data. Your report is generated
          from your own answers and is never used to train AI.
        </p>
      </div>
    </section>
  );
}

function ReportPageFrame({ title, meta, children }) {
  return (
    <div className="mx-auto rounded-2xl shadow-xl border border-[#E5E0EE] bg-white overflow-hidden">
      <div className="bg-[#3D1A78] text-white px-6 py-4 flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] opacity-80">{meta}</div>
          <div className="font-serif text-lg">{title}</div>
        </div>
        <FileText size={18} className="opacity-70" />
      </div>
      <div className="p-6 sm:p-8 text-[#1A1330]">{children}</div>
    </div>
  );
}

function SampleStat({ label, value, tone }) {
  return (
    <div className="rounded-xl border border-[#E5E0EE] bg-[#FAFAFC] p-3 text-center">
      <div className="text-[10px] uppercase tracking-[0.12em] text-[#857E9C]">{label}</div>
      <div className="font-serif text-2xl mt-1" style={{ color: tone }}>{value}</div>
    </div>
  );
}

function SampleSection({ title, children }) {
  return (
    <div className="mb-4">
      <div className="text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78] mb-2">{title}</div>
      {children}
    </div>
  );
}

function SampleMediation() {
  return (
    <ReportPageFrame meta="Mediation Summary · Prepared for Alex Rivera" title="Ready for your Feb 24 session">
      <div className="grid sm:grid-cols-4 gap-3 mb-6">
        <SampleStat label="Readiness" value="78" tone="#3D1A78" />
        <SampleStat label="Child-centered" value="82" tone="#2DB5B5" />
        <SampleStat label="Priorities" value="74" tone="#3D1A78" />
        <SampleStat label="Emotional reg." value="76" tone="#2DB5B5" />
      </div>
      <SampleSection title="Child-centered goals">
        <ul className="list-disc pl-5 space-y-1 text-sm text-[#4B4567]">
          <li>Predictable weeknight bedtimes across both homes.</li>
          <li>A shared calendar Nina can read by herself (age 7).</li>
          <li>One family therapy session per month, together.</li>
        </ul>
      </SampleSection>
      <SampleSection title="Priority agenda">
        <ol className="list-decimal pl-5 space-y-1 text-sm text-[#4B4567]">
          <li><strong>Schedule</strong> — align on school-week vs weekend rotation.</li>
          <li><strong>Communication</strong> — agree on OurFamilyWizard for logistics.</li>
          <li><strong>Health</strong> — decide who books Nina&rsquo;s pediatric follow-ups.</li>
        </ol>
      </SampleSection>
    </ReportPageFrame>
  );
}

function SampleSpecialNeeds() {
  return (
    <ReportPageFrame meta="Special Needs Care Plan · Nina, age 7" title="6-part care plan · updated weekly">
      <div className="grid sm:grid-cols-3 gap-3 mb-6">
        <SampleStat label="Consistency" value="64" tone="#0E7A7A" />
        <SampleStat label="Coordination" value="71" tone="#0E7A7A" />
        <SampleStat label="Care alignment" value="58" tone="#B85B00" />
      </div>
      <SampleSection title="Coordination gaps flagged">
        <ul className="list-disc pl-5 space-y-1 text-sm text-[#4B4567]">
          <li><strong>Medication timing</strong> — different pharmacies at each home.</li>
          <li><strong>Sensory triggers</strong> — dad&rsquo;s house hasn&rsquo;t received the updated list.</li>
        </ul>
      </SampleSection>
      <SampleSection title="Immediate action (this week)">
        <ul className="list-disc pl-5 space-y-1 text-sm text-[#4B4567]">
          <li>Share the OT report with dad&rsquo;s household by Friday.</li>
          <li>Book the paediatric follow-up together — parent A leads.</li>
        </ul>
      </SampleSection>
    </ReportPageFrame>
  );
}

function SampleSafety() {
  return (
    <ReportPageFrame meta="Family Violence & Communication Safety" title="Recommended pathway: Structured written">
      <div className="rounded-2xl border border-[#B85B00]/30 bg-[#FFF8F0] p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-[#B85B00] mt-0.5" />
          <div>
            <div className="font-semibold text-[#1A1330]">Structured written communication</div>
            <p className="text-sm text-[#4B4567] mt-1">
              Based on your answers, we recommend using a monitored written
              channel (e.g. OurFamilyWizard). Live phone / in-person
              exchanges are discouraged for the next 90 days.
            </p>
          </div>
        </div>
      </div>
      <SampleSection title="Texas crisis resources (always in every share)">
        <ul className="text-sm text-[#4B4567] space-y-1">
          <li><strong>Family Violence Prevention Services (Bexar):</strong> 210-733-8810</li>
          <li><strong>National DV Hotline:</strong> 1-800-799-SAFE</li>
          <li><strong>988</strong> — Suicide & Crisis Lifeline</li>
        </ul>
      </SampleSection>
    </ReportPageFrame>
  );
}

function SampleProgress() {
  const bars = [
    { label: "Nov", v: 42 },
    { label: "Dec", v: 55 },
    { label: "Jan", v: 63 },
    { label: "Feb", v: 78 },
  ];
  return (
    <ReportPageFrame meta="Growth Snapshot · Last 4 months" title="You&rsquo;re trending up.">
      <div className="flex items-end gap-4 h-40 mb-6">
        {bars.map((b) => (
          <div key={b.label} className="flex-1 flex flex-col items-center gap-2">
            <div className="flex-1 w-full flex items-end">
              <div className="w-full rounded-t-lg bg-gradient-to-t from-[#3D1A78] to-[#2DB5B5]" style={{ height: `${b.v}%` }} />
            </div>
            <div className="text-xs text-[#4B4567]">{b.label}</div>
            <div className="text-[11px] font-semibold text-[#1A1330]">{b.v}</div>
          </div>
        ))}
      </div>
      <SampleSection title="What changed this month">
        <ul className="list-disc pl-5 space-y-1 text-sm text-[#4B4567]">
          <li>You added 3 concrete priorities to your mediation agenda.</li>
          <li>Communication clarity moved from 61 &rarr; 78.</li>
          <li>You completed the Family Violence assessment for the first time.</li>
        </ul>
      </SampleSection>
    </ReportPageFrame>
  );
}

/* ============================================================
   SECTION 6 — FINAL CTA
============================================================ */
function FinalCTA() {
  return (
    <section className="relative py-24 sm:py-32 bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] overflow-hidden">
      <div className="absolute -top-32 -right-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/30 blur-3xl" />
      <div className="absolute -bottom-40 -left-32 w-[30rem] h-[30rem] rounded-full bg-[#A8DCDC]/30 blur-3xl" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <Eyebrow>Take the First Step</Eyebrow>
        <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
          Your Children Deserve Parents
          <br className="hidden sm:block" /> Who Can Work Together
        </h2>
        <p className="text-base text-[#4B4567] mt-6 max-w-2xl mx-auto leading-relaxed">
          Every step toward healthier communication creates a stronger
          foundation for your children.
        </p>
        <p className="text-base text-[#4B4567] mt-3 max-w-2xl mx-auto leading-relaxed">
          The SA CoParents App provides the tools, assessments, and guidance
          parents need to reduce conflict, improve communication, and build a
          child-centered co-parenting relationship.
        </p>

        <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-12 leading-snug">
          Discover Your Co-Parenting Strengths and Growth Opportunities
        </h3>
        <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-xl mx-auto">
          Take the first step toward healthier communication, stronger
          cooperation, and better outcomes for your children.
        </p>

        <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
          <PrimaryCTA testid="final-primary-cta">Start Your Assessment</PrimaryCTA>
          <SecondaryCTA
            testid="final-secondary-cta"
            onClick={() => scrollToId("child-focused-mediation")}
          >
            Learn More About Child-Focused Mediation
          </SecondaryCTA>
        </div>

        <div className="mt-16 inline-flex items-center gap-2 text-xs text-[#3D1A78] font-medium tracking-wide">
          <Sparkles size={14} />
          <span>
            From Conflict to Cooperation. From Disagreement to Understanding.
            From Parenting Apart to Raising Children Together.
          </span>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   PAGE
============================================================ */
export default function Landing() {
  return (
    <EnterAppProvider>
      <div className="min-h-screen bg-[#F8F7FC]">
        <MarketingHeader />
        <Hero />
        <ThreeReportsStrip />
        <TheProblem />
        <HowItWorks />
        <SampleReports />
        <WhyDifferent />
        <TrustSignals />
        <ChildFocusedMediation />
        <FinalCTA />
        <MarketingFooter />
      </div>
    </EnterAppProvider>
  );
}
