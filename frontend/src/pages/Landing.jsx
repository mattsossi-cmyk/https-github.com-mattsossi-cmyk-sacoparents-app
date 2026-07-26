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
function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] pt-28 sm:pt-32 pb-24 sm:pb-28">
      {/* soft floating shapes */}
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
        <p className="max-w-2xl mx-auto text-base sm:text-lg text-[#1A1330] font-semibold mt-8 leading-relaxed">
          The SA CoParents App helps you understand your co-parenting
          situation, identify your child&rsquo;s individual needs, and prepare
          for child-focused discussions and mediation.
        </p>
        <p className="max-w-2xl mx-auto text-sm sm:text-base text-[#4B4567] mt-4 leading-relaxed">
          Through personalized assessments and practical reports, you can
          move forward with greater clarity, confidence, and purpose.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <PrimaryCTA testid="hero-primary-cta">Start Your Assessment</PrimaryCTA>
          <SecondaryCTA
            testid="hero-secondary-cta"
            onClick={() => scrollToId("how-it-works")}
          >
            Learn How It Works
          </SecondaryCTA>
        </div>
        <div className="mt-4">
          <button
            onClick={() => scrollToId("which-assessment")}
            className="text-sm font-semibold text-[#3D1A78] hover:text-[#1A1330] hover:underline underline-offset-2"
            data-testid="hero-which-assessment-link"
          >
            Not sure where to start? Take our 20-second guide →
          </button>
        </div>

        <div className="mt-4 text-center">
          <a
            href="/watch"
            data-testid="hero-watch-videos-link"
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#3D1A78] hover:text-[#1A1330] transition-colors"
          >
            <span aria-hidden="true" className="w-2 h-2 rounded-full bg-[#2DB5B5]" />
            Watch the 21-second and 45-second program trailers
            <ArrowRight size={14} />
          </a>
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
   ASSESSMENT SELECTOR — "Which assessment should I take?"
============================================================ */
const SELECTOR_STEPS = [
  {
    id: "situation",
    question: "Where are you right now in your co-parenting journey?",
    options: [
      { key: "mediation-soon", label: "I have a mediation session coming up.", tag: "mediation" },
      { key: "high-conflict", label: "Communication with my co-parent feels unsafe or hostile.", tag: "safety" },
      { key: "just-starting", label: "We're figuring things out — I want a full picture.", tag: "all" },
      { key: "child-needs", label: "My child has specific needs I want us to coordinate on.", tag: "special-needs" },
    ],
  },
  {
    id: "focus",
    question: "What matters most to you today?",
    options: [
      { key: "prep", label: "Arriving at mediation prepared and child-centered.", tag: "mediation" },
      { key: "safety", label: "Understanding whether direct contact is safe.", tag: "safety" },
      { key: "coordination", label: "Consistency between homes for my child.", tag: "special-needs" },
      { key: "growth", label: "Long-term co-parenting growth.", tag: "all" },
    ],
  },
  {
    id: "confidence",
    question: "How confident do you feel about the road ahead?",
    options: [
      { key: "shaky", label: "Honestly, pretty shaky.", tag: null },
      { key: "steady", label: "Steady, but I want to be sure.", tag: null },
      { key: "confident", label: "Fairly confident — I just want structure.", tag: null },
    ],
  },
];

const SELECTOR_RESULTS = {
  mediation: {
    title: "Start with the Mediation Readiness Assessment.",
    subtitle: "You'll build a child-centered agenda, name your priorities, and get a downloadable summary to bring to mediation.",
    icon: <Scale size={20} />,
    ctaLabel: "Start the readiness assessment",
    accent: "#3D1A78",
  },
  safety: {
    title: "Start with the Family Violence & Communication Safety Assessment.",
    subtitle: "A private screen that recommends the safest communication pathway — from no-direct-contact to cooperative — and surfaces Texas crisis resources.",
    icon: <ShieldCheck size={20} />,
    ctaLabel: "Start the safety assessment",
    accent: "#B85B00",
  },
  "special-needs": {
    title: "Start with the Special Needs Assessment.",
    subtitle: "7 domains, up to 6 pages of care-plan output, and a Consistency-Between-Homes score you can share with pediatricians, teachers, or your mediator.",
    icon: <Baby size={20} />,
    ctaLabel: "Start the special needs assessment",
    accent: "#0E7A7A",
  },
  all: {
    title: "Take all three over time.",
    subtitle: "You don't have to choose one. Start with the Mediation Readiness assessment for the fastest win — the others unlock as you go, and you can revisit any of them free.",
    icon: <Compass size={20} />,
    ctaLabel: "Start the guided journey",
    accent: "#3D1A78",
  },
};

function AssessmentSelector() {
  const { enter } = useEnterApp();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);

  const pick = (opt) => {
    const nextAnswers = [...answers, opt.tag];
    if (step + 1 >= SELECTOR_STEPS.length) {
      const counts = nextAnswers.reduce((acc, t) => {
        if (t) acc[t] = (acc[t] || 0) + 1;
        return acc;
      }, {});
      const priority = ["safety", "special-needs", "mediation", "all"];
      let winner = "all";
      let best = 0;
      priority.forEach((k) => {
        if ((counts[k] || 0) > best) { winner = k; best = counts[k]; }
      });
      if (best === 0) winner = "all";
      setResult(winner);
    } else {
      setAnswers(nextAnswers);
      setStep(step + 1);
    }
  };

  const reset = () => { setStep(0); setAnswers([]); setResult(null); };

  const current = SELECTOR_STEPS[step];
  const done = !!result;

  return (
    <section id="which-assessment" className="relative py-16 sm:py-20 bg-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-8">
          <Eyebrow>Not sure where to start?</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight mt-3">
            Which assessment should I take?
          </h2>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-xl mx-auto">
            Answer three quick questions and we&rsquo;ll point you to the right
            starting place. Takes about 20 seconds.
          </p>
        </div>

        {!done && (
          <div
            className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#F7F4FC] p-6 sm:p-8"
            data-testid="assessment-selector-card"
          >
            <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.12em] text-[#857E9C] mb-4">
              <span>Question {step + 1} of {SELECTOR_STEPS.length}</span>
              <span>{Math.round(((step) / SELECTOR_STEPS.length) * 100)}% done</span>
            </div>
            <div className="h-1.5 w-full bg-[#EFE9F9] rounded-full overflow-hidden mb-6">
              <div
                className="h-full bg-[#3D1A78] transition-all duration-500"
                style={{ width: `${((step) / SELECTOR_STEPS.length) * 100}%` }}
              />
            </div>
            <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mb-5" data-testid="assessment-selector-question">
              {current.question}
            </h3>
            <div className="grid gap-2.5">
              {current.options.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => pick(opt)}
                  className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-center justify-between gap-3"
                  data-testid={`assessment-selector-option-${opt.key}`}
                >
                  <span className="text-sm sm:text-base text-[#1A1330]">{opt.label}</span>
                  <ChevronRight size={16} className="text-[#857E9C] group-hover:text-[#3D1A78] shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

        {done && (() => {
          const r = SELECTOR_RESULTS[result];
          return (
            <div
              className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-9 text-center fade-up"
              data-testid="assessment-selector-result"
            >
              <div
                className="inline-flex items-center justify-center w-14 h-14 rounded-full mb-4"
                style={{ backgroundColor: `${r.accent}18`, color: r.accent }}
              >
                {r.icon}
              </div>
              <h3 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug">
                {r.title}
              </h3>
              <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-xl mx-auto">
                {r.subtitle}
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center items-center">
                <button
                  onClick={enter}
                  data-testid="assessment-selector-cta"
                  className="inline-flex items-center gap-2 bg-[#3D1A78] hover:bg-[#2D0F63] transition-colors text-white font-semibold px-6 py-3 rounded-full text-sm sm:text-base"
                >
                  {r.ctaLabel} <ArrowRight size={16} />
                </button>
                <button
                  onClick={reset}
                  className="text-sm text-[#4B4567] hover:text-[#3D1A78] hover:underline"
                  data-testid="assessment-selector-reset"
                >
                  Ask me again
                </button>
              </div>
            </div>
          );
        })()}
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
        <AssessmentSelector />
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
