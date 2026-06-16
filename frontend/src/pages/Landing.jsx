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
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { markOrientationSeen } from "./Orientation";
import IntroTourModal from "../components/IntroTourModal";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

/* ============================================================
   ENTER-APP CONTEXT
   Every "Take the Free Assessment" CTA flows through the same
   provider so the intro video always plays first.
============================================================ */
const EnterAppContext = React.createContext(null);

function EnterAppProvider({ children }) {
  const { startGuest } = useAuth();
  const navigate = useNavigate();
  const [showIntro, setShowIntro] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const proceed = async () => {
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

  const enter = () => {
    if (loading || showIntro) return;
    setError(null);
    setLoading(true);
    setShowIntro(true);
  };

  const handleVideoEnd = async () => {
    setShowIntro(false);
    await proceed();
  };

  return (
    <EnterAppContext.Provider value={{ enter, loading, error }}>
      {children}
      <IntroTourModal open={showIntro} onClose={handleVideoEnd} />
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
  const { enter, loading } = useEnterApp();
  return (
    <button
      type="button"
      onClick={enter}
      disabled={loading}
      data-testid={testid}
      className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
    >
      {loading ? "Loading…" : children}
      {!loading && <ArrowRight size={16} />}
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
function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] pt-28 sm:pt-32 pb-24 sm:pb-28">
      {/* soft floating shapes */}
      <div className="absolute -top-32 -left-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/40 blur-3xl" />
      <div className="absolute -bottom-40 -right-32 w-[30rem] h-[30rem] rounded-full bg-[#A8DCDC]/40 blur-3xl" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 text-center fade-up">
        <Eyebrow>The SA CoParents App</Eyebrow>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-[1.05] tracking-tight">
          Stop Parent Conflict Before
          <br className="hidden sm:block" /> It Reaches the Courtroom
        </h1>
        <p className="max-w-2xl mx-auto text-base sm:text-lg text-[#4B4567] mt-7 leading-relaxed">
          The SA CoParents App helps separated and divorced parents{" "}
          <strong className="text-[#1A1330]">reduce conflict</strong>, improve
          communication, and become better partners in raising their children.
        </p>
        <p className="max-w-2xl mx-auto text-sm sm:text-base text-[#4B4567] mt-4 leading-relaxed">
          Build healthier co-parenting habits, keep your children at the center
          of every decision, and gain the tools needed to create lasting family
          stability.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <PrimaryCTA testid="hero-primary-cta">Take the Free Assessment</PrimaryCTA>
          <SecondaryCTA
            testid="hero-secondary-cta"
            onClick={() => scrollToId("how-it-works")}
          >
            See How It Works
          </SecondaryCTA>
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
          <PrimaryCTA testid="final-primary-cta">Take the Free Assessment</PrimaryCTA>
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
        <TheProblem />
        <HowItWorks />
        <WhyDifferent />
        <ChildFocusedMediation />
        <FinalCTA />
        <MarketingFooter />
      </div>
    </EnterAppProvider>
  );
}
