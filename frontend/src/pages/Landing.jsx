import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Heart,
  MessageCircle,
  Users,
  ArrowRight,
  Facebook,
  ShieldAlert,
  Check,
  Sparkles,
  TrendingUp as TrendingUpIcon,
  FileText,
  Apple,
  Play as PlayIcon,
  ChevronDown,
  Quote,
  Mail,
  BookOpen,
  Lock,
  HeartHandshake,
  Brain,
  Target as TargetIcon,
} from "lucide-react";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#F8F7FC]">
      <MarketingHeader />
      <Hero />
      <WaveDivider flip color="#F8F7FC" bgColor="transparent" />
      <Philosophy />
      <Features />
      <WaveDivider color="#F8F7FC" bgColor="transparent" />
      <HowItWorks />
      <ScreenshotShowcase />
      <ForMediators />
      <Testimonials />
      <FAQ />
      <FinalCTA />
      <MarketingFooter />
    </div>
  );
}

/* ============================================================
   BRAND MARK — SVG (heart-shaped family in purple→teal)
============================================================ */
function BrandMark({ size = 44, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id="bmGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3D1A78" />
          <stop offset="55%" stopColor="#5E2DB5" />
          <stop offset="100%" stopColor="#2DB5B5" />
        </linearGradient>
      </defs>
      <path
        d="M32 56 C12 42, 4 30, 12 18 C18 9, 28 10, 32 18 C36 10, 46 9, 52 18 C60 30, 52 42, 32 56 Z"
        fill="url(#bmGrad)"
      />
      <circle cx="24" cy="26" r="4" fill="white" opacity="0.95" />
      <circle cx="40" cy="26" r="4" fill="white" opacity="0.95" />
      <path
        d="M22 36 Q32 44 42 36"
        stroke="white"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
        opacity="0.9"
      />
    </svg>
  );
}

/* ============================================================
   HEADER
============================================================ */
function MarketingHeader() {
  return (
    <header className="max-w-7xl mx-auto px-5 sm:px-6 py-4 sm:py-5 flex items-center justify-between sticky top-0 z-30 backdrop-blur-md bg-[#F8F7FC]/85 border-b border-[#E5E0EE]/60">
      <Link to="/" className="flex items-center gap-2.5 sm:gap-3" data-testid="landing-brand-logo">
        <BrandMark size={44} className="shrink-0" />
        <div className="leading-tight">
          <div className="font-sans text-lg sm:text-xl font-extrabold tracking-tight text-[#1A1330]">
            <span className="text-brand-gradient">SACO</span>Parents
          </div>
          <div className="hidden sm:block text-[10px] uppercase tracking-[0.2em] text-[#857E9C]">
            Helping families communicate better
          </div>
        </div>
      </Link>
      <div className="flex items-center gap-2 sm:gap-3">
        <Link
          to="/safety"
          className="hidden md:inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-[#C28771]/10 text-[#C28771] hover:bg-[#C28771]/15"
          data-testid="landing-header-safety-link"
        >
          <ShieldAlert size={12} />
          Safety
        </Link>
        <Link to="/login" className="text-sm text-[#4B4567] hover:text-[#1A1330] font-semibold" data-testid="nav-sign-in">
          Sign in
        </Link>
        <Link to="/register" className="btn-gradient text-sm" data-testid="nav-get-started">
          Get started
        </Link>
      </div>
    </header>
  );
}

/* ============================================================
   HERO — bold gradient panel
============================================================ */
function Hero() {
  return (
    <section className="relative overflow-hidden" data-testid="hero">
      <div className="bg-brand-gradient text-white">
        <div className="max-w-7xl mx-auto px-5 sm:px-6 pt-14 pb-24 sm:pt-20 sm:pb-32 relative">
          <div className="grid lg:grid-cols-12 gap-10 lg:gap-12 items-center fade-up">
            <div className="lg:col-span-7">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 backdrop-blur-sm text-[11px] uppercase tracking-[0.2em] mb-6">
                <Sparkles size={12} />
                Introducing SACOParents
              </div>
              <h1 className="font-sans font-extrabold text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight">
                Smarter Communication.
                <br />
                <span className="text-[#A8E8E8]">Healthier Co-Parenting.</span>
                <br />
                Stronger Families.
              </h1>
              <p className="text-[15px] sm:text-lg text-white/85 mt-6 max-w-xl leading-relaxed">
                A modern co-parenting platform designed to reduce conflict, improve
                communication, and keep children at the center of every parenting decision.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-white text-[#3D1A78] font-bold shadow-lg active:scale-95 transition-transform"
                  data-testid="hero-start-button"
                >
                  Start your prep — free <ArrowRight size={16} />
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-white/15 text-white font-semibold backdrop-blur-sm hover:bg-white/25 active:scale-95 transition"
                  data-testid="hero-continue-button"
                >
                  I have an account
                </Link>
              </div>

              <div className="mt-8 flex items-center gap-5 text-xs text-white/80 flex-wrap">
                <span className="inline-flex items-center gap-1.5">
                  <Check size={14} className="text-[#A8E8E8]" /> Free to use
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Check size={14} className="text-[#A8E8E8]" /> Private by default
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Check size={14} className="text-[#A8E8E8]" /> No ads
                </span>
              </div>
            </div>

            <div className="lg:col-span-5 relative">
              <div className="absolute -top-12 -right-12 w-72 h-72 rounded-full bg-white/10 blur-2xl" />
              <div className="absolute -bottom-16 -left-12 w-56 h-56 rounded-full bg-[#2DB5B5]/30 blur-2xl" />
              <div className="relative flex items-center justify-center">
                <div className="bg-white/95 rounded-[36px] p-4 sm:p-5 shadow-2xl ring-4 ring-white/20 backdrop-blur-sm overflow-hidden">
                  <img
                    src="/sacoparents-3d-logo.jpg"
                    alt="SACOParents logo"
                    className="w-full max-w-[360px] mx-auto rounded-[24px]"
                    data-testid="hero-logo"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        {/* curved bottom edge */}
        <WaveDivider color="#F8F7FC" bgColor="transparent" />
      </div>
    </section>
  );
}

/* ============================================================
   WAVE DIVIDER
============================================================ */
function WaveDivider({ color = "#F8F7FC", bgColor = "transparent", flip = false }) {
  return (
    <div className="divider-wave" style={{ background: bgColor, transform: flip ? "scaleY(-1)" : "none" }}>
      <svg viewBox="0 0 1440 100" preserveAspectRatio="none" aria-hidden>
        <path
          fill={color}
          d="M0,40 C240,90 480,90 720,55 C960,20 1200,20 1440,55 L1440,100 L0,100 Z"
        />
      </svg>
    </div>
  );
}

/* ============================================================
   PHILOSOPHY (Co-Parenting Shouldn't Feel Like a Battle)
============================================================ */
function Philosophy() {
  const struggles = [
    { icon: MessageCircle, text: "Tense or reactive conversations" },
    { icon: MessageCircle, text: "Misunderstandings through text messaging" },
    { icon: Users, text: "Scheduling and parenting disagreements" },
    { icon: Brain, text: "Emotional triggers during communication" },
    { icon: Heart, text: "Keeping children out of adult conflict" },
  ];
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="philosophy">
      <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-14">
        <h2 className="font-sans font-extrabold text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] tracking-tight leading-tight">
          Co-Parenting Shouldn't
          <br />
          Feel Like a <span className="text-brand-gradient">Battle</span>.
        </h2>
        <p className="text-[#4B4567] mt-5 leading-relaxed">
          Separation and divorce can create emotional stress for parents and children alike.
          Miscommunication, conflict escalation, and emotional reactions often make co-parenting
          more difficult than it needs to be.
        </p>
      </div>

      <div className="bg-brand-gradient-soft rounded-3xl p-6 sm:p-10 max-w-3xl mx-auto border border-[#E5E0EE]">
        <div className="text-center mb-6">
          <div className="inline-block px-5 py-2 rounded-full bg-brand-gradient text-white font-semibold text-sm">
            Many parents struggle with:
          </div>
        </div>
        <ul className="space-y-3 max-w-xl mx-auto">
          {struggles.map(({ icon: Icon, text }, i) => (
            <li
              key={i}
              className="flex items-center gap-4 bg-white rounded-2xl px-5 py-3.5 border border-[#E5E0EE]"
              data-testid={`philosophy-item-${i + 1}`}
            >
              <span className="icon-circle icon-circle-purple w-10 h-10">
                <Icon size={18} />
              </span>
              <span className="text-[#1A1330] font-medium text-[15px]">{text}</span>
            </li>
          ))}
        </ul>
        <p className="text-center text-[#3D1A78] font-script text-2xl sm:text-3xl mt-7 leading-snug max-w-lg mx-auto">
          Children are affected most when conflict remains unresolved.
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   FEATURES — brochure 5-card grid
============================================================ */
function Features() {
  const features = [
    {
      icon: MessageCircle,
      tone: "purple",
      title: "Guided Communication Support",
      text: "Prompts and communication tools designed to encourage respectful, child-centered conversations.",
    },
    {
      icon: HeartHandshake,
      tone: "teal",
      title: "State Goals, Concerns & Needs",
      text: "A clear, structured way to articulate what matters most — your goals for your child, your concerns about the situation, and the needs you want addressed in mediation.",
    },
    {
      icon: Heart,
      tone: "magenta",
      title: "Child-Focused Co-Parenting",
      text: "Encourages decisions that prioritize consistency, emotional safety, and healthy parenting relationships.",
    },
    {
      icon: BookOpen,
      tone: "blue",
      title: "Educational Resources",
      text: "Access practical guidance, communication tips, and co-parenting support tools developed to strengthen family relationships.",
    },
    {
      icon: Lock,
      tone: "green",
      title: "Convenient & Secure",
      text: "Accessible anytime from your mobile device, giving parents a structured place to support healthier communication.",
    },
  ];

  return (
    <section className="bg-white py-16 sm:py-24 border-y border-[#E5E0EE]" data-testid="features">
      <div className="max-w-7xl mx-auto px-5 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div className="font-script text-2xl sm:text-3xl text-[#3D1A78] mb-2">Introducing</div>
          <h2 className="font-sans font-extrabold text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] tracking-tight">
            <span className="text-brand-gradient">SACOParents</span>
          </h2>
          <p className="text-[#4B4567] mt-5 leading-relaxed">
            A co-parenting communication and support platform built to help separated and divorced
            parents create healthier communication patterns while focusing on the emotional well-being
            of their children.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-7 max-w-6xl mx-auto">
          {features.map(({ icon: Icon, tone, title, text }) => (
            <div
              key={title}
              className="bg-white border border-[#E5E0EE] rounded-2xl p-6 sm:p-7 hover:shadow-lg transition-shadow"
              data-testid={`feature-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <div className={`icon-circle icon-circle-${tone} mb-5`}>
                <Icon size={20} />
              </div>
              <div className="font-sans font-bold text-xl text-[#1A1330] mb-2">{title}</div>
              <p className="text-[14px] text-[#4B4567] leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   HOW IT WORKS — 5 STEPS
============================================================ */
function HowItWorks() {
  const steps = [
    { n: 1, t: "Child-Centered Goals", d: "Define what you want for your child — emotional safety, schedule, relationships." },
    { n: 2, t: "Issues & Concerns", d: "Map the concerns you want to raise, calmly and clearly." },
    { n: 3, t: "Priority Ranking", d: "Sort the eleven legal custody topics into urgency buckets." },
    { n: 4, t: "Communication Style", d: "Reflect on your patterns and get AI-coached reframes." },
    { n: 5, t: "Readiness Check", d: "A short self-assessment that scores how prepared you really are." },
  ];
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="how-it-works">
      <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
        <div className="eyebrow text-[#3D1A78] mb-3">How it works</div>
        <h2 className="font-sans font-extrabold text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] tracking-tight">
          Five guided steps to <span className="text-brand-gradient">clarity</span>.
        </h2>
        <p className="text-[#4B4567] mt-4 leading-relaxed">
          Each step is short, private, and saves automatically. You can pause any time and pick up where you left off.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {steps.map(({ n, t, d }) => (
          <div
            key={n}
            className="bg-white border border-[#E5E0EE] rounded-2xl p-5 sm:p-6 hover:shadow-lg hover:-translate-y-1 transition"
            data-testid={`step-${n}`}
          >
            <div className="w-11 h-11 rounded-full bg-brand-gradient text-white grid place-items-center font-bold text-lg mb-4 shadow-md">
              {n}
            </div>
            <div className="font-sans font-bold text-lg text-[#1A1330] mb-1.5 leading-snug">{t}</div>
            <p className="text-[13px] text-[#4B4567] leading-relaxed">{d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   SCREENSHOT SHOWCASE
============================================================ */
function ScreenshotShowcase() {
  const shots = [
    { variant: "assess", caption: "Assess Your Situation" },
    { variant: "home", caption: "Safety, always one tap away" },
    { variant: "mediator", caption: "AI-synthesized documents" },
  ];
  return (
    <section className="bg-[#EFE9F9] py-16 sm:py-24" data-testid="screenshot-showcase">
      <div className="max-w-7xl mx-auto px-5 sm:px-6">
        <div className="text-center mb-12">
          <div className="eyebrow text-[#3D1A78] mb-3">A glimpse</div>
          <h2 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">
            Built for calm, not conflict.
          </h2>
        </div>
        <div className="grid sm:grid-cols-3 gap-6 sm:gap-8 max-w-4xl mx-auto">
          {shots.map((s, i) => (
            <div key={i} className="text-center" data-testid={`screenshot-${i + 1}`}>
              <PhoneMockup variant={s.variant} className="!max-w-[220px]" />
              <div className="text-[13px] text-[#4B4567] mt-4 font-semibold">{s.caption}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   FOR MEDIATORS — gradient panel
============================================================ */
function ForMediators() {
  const bullets = [
    "Reduces session time spent on agenda-setting",
    "Builds shared vocabulary around the 11 legal custody categories",
    "Includes safety guidance for high-conflict clients",
    "Free for clients — no subscription required",
  ];
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="for-mediators">
      <div className="bg-brand-gradient text-white rounded-[32px] p-8 sm:p-14 shadow-2xl overflow-hidden relative">
        <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-[#2DB5B5]/30 blur-3xl" />

        <div className="relative grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 text-[11px] uppercase tracking-[0.2em] mb-5">
              For mediators & family lawyers
            </div>
            <h2 className="font-sans font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-tight tracking-tight">
              Your clients arrive prepared.
              <br />
              <span className="text-[#A8E8E8]">Your sessions move faster.</span>
            </h2>
            <p className="text-white/85 mt-5 leading-relaxed max-w-xl">
              Recommend SACOParents before the first session and your clients walk in with a
              child-centered summary, a draft agreement, and a clear sense of what they want
              to discuss. Less venting, more substance.
            </p>
            <ul className="mt-7 space-y-2.5">
              {bullets.map((b) => (
                <li key={b} className="flex gap-3 text-[14px]">
                  <Check size={18} className="text-[#A8E8E8] shrink-0 mt-0.5" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
            <a
              href="mailto:mattsossi@bsossi.com?subject=Mediator%20partnership%20inquiry"
              className="inline-flex items-center gap-2 mt-8 px-7 py-3.5 rounded-full bg-white text-[#3D1A78] font-bold shadow-lg active:scale-95 transition-transform"
              data-testid="mediator-contact-button"
            >
              <Mail size={16} /> Get in touch
            </a>
          </div>

          <div className="lg:col-span-5 relative">
            <PhoneMockup variant="mediator" />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   TESTIMONIALS
============================================================ */
function Testimonials() {
  const quotes = [
    {
      q: "I walked into my mediation calmer than I'd been in months. Having my answers already on paper made the conversation about my daughter, not about us.",
      a: "Parent · San Antonio, TX",
    },
    {
      q: "The 'Things I Can Improve On' section was hard to read but exactly what I needed. It changed how I show up.",
      a: "Parent · Cape Town, ZA",
    },
    {
      q: "I recommend it to every client before our first session. They come prepared and we get to the substance faster.",
      a: "Family Mediator",
    },
  ];
  return (
    <section className="bg-white py-16 sm:py-24 border-y border-[#E5E0EE]" data-testid="testimonials">
      <div className="max-w-7xl mx-auto px-5 sm:px-6">
        <div className="text-center mb-12">
          <div className="eyebrow text-[#3D1A78] mb-3">What people say</div>
          <h2 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">
            From parents and mediators.
          </h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {quotes.map((q, i) => (
            <div
              key={i}
              className="bg-[#F8F7FC] border border-[#E5E0EE] rounded-2xl p-7 hover:shadow-lg transition-shadow"
              data-testid={`testimonial-${i + 1}`}
            >
              <Quote className="text-[#3D1A78] mb-4" size={22} />
              <p className="text-[14px] text-[#1A1330] leading-relaxed italic">{q.q}</p>
              <div className="text-[11px] text-[#857E9C] mt-5 uppercase tracking-wider font-semibold">
                {q.a}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   FAQ
============================================================ */
function FAQ() {
  const faqs = [
    {
      q: "Is SACOParents free?",
      a: "Yes. Every prep step, AI-generated document, PDF download, and safety resource is free. We don't sell your data and we don't show ads.",
    },
    {
      q: "Is what I write private?",
      a: "Your answers are private to you and never shared with anyone — including your co-parent — unless you explicitly choose to (by emailing your mediator or sharing a download link). Your data is encrypted in transit and at rest.",
    },
    {
      q: "Can my co-parent see what I write?",
      a: "No. Each parent has their own private account. The Mediation Summary, Agreement Draft, and Growth Plan are yours alone — you decide whether and how to share.",
    },
    {
      q: "Do I need a mediator already booked?",
      a: "No. Many parents use SACOParents to figure out whether they're ready for mediation in the first place. The Readiness Check helps you decide.",
    },
    {
      q: "Can I delete my account and all my data?",
      a: "Yes — anytime, instantly, from the app or from the public delete-account page. Everything is wiped from our servers immediately.",
    },
    {
      q: "What if I'm in a high-conflict or unsafe situation?",
      a: "The Safety page provides one-tap Quick Exit, 24/7 domestic violence hotlines, and dedicated guidance on parallel parenting — a safer alternative when traditional co-parenting isn't viable.",
    },
  ];
  return (
    <section className="max-w-3xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="faq">
      <div className="text-center mb-12">
        <div className="eyebrow text-[#3D1A78] mb-3">Questions</div>
        <h2 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">
          Things you might be wondering.
        </h2>
      </div>
      <div className="space-y-3">
        {faqs.map((f, i) => (
          <FAQItem key={i} idx={i} q={f.q} a={f.a} />
        ))}
      </div>
    </section>
  );
}

function FAQItem({ idx, q, a }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div
      className="border border-[#E5E0EE] rounded-2xl bg-white overflow-hidden"
      data-testid={`faq-item-${idx + 1}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex items-center justify-between gap-3 px-5 sm:px-6 py-4 sm:py-5"
        data-testid={`faq-toggle-${idx + 1}`}
      >
        <span className="font-sans font-bold text-[15px] sm:text-[17px] text-[#1A1330] leading-snug">
          {q}
        </span>
        <ChevronDown
          size={18}
          className={`text-[#3D1A78] transition-transform shrink-0 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div
          className="px-5 sm:px-6 pb-5 text-[14px] text-[#4B4567] leading-relaxed"
          data-testid={`faq-answer-${idx + 1}`}
        >
          {a}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   FINAL CTA
============================================================ */
function FinalCTA() {
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="final-cta">
      <div className="relative bg-brand-gradient text-white rounded-[32px] px-6 sm:px-12 py-16 sm:py-20 text-center overflow-hidden shadow-2xl">
        <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-[#2DB5B5]/40 blur-3xl" />
        <div className="relative">
          <div className="font-script text-3xl sm:text-4xl text-[#A8E8E8] mb-3">
            Start Building Better
          </div>
          <h2 className="font-sans font-extrabold text-3xl sm:text-5xl tracking-tight leading-tight max-w-3xl mx-auto">
            Co-Parenting Conversations Today.
          </h2>
          <p className="text-white/85 mt-6 max-w-xl mx-auto leading-relaxed">
            Start your free preparation today. Nothing is shared with anyone unless you choose to share it.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-white text-[#3D1A78] font-bold shadow-lg active:scale-95 transition-transform"
              data-testid="final-cta-start-button"
            >
              Start your prep — free <ArrowRight size={16} />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-white/15 text-white font-semibold backdrop-blur-sm hover:bg-white/25 active:scale-95 transition"
              data-testid="final-cta-signin-button"
            >
              I already have an account
            </Link>
          </div>
          <div className="mt-8 flex items-center justify-center gap-3 flex-wrap">
            <AppStoreBadge />
            <GooglePlayBadge />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   FOOTER
============================================================ */
function MarketingFooter() {
  return (
    <footer className="bg-[#1A1330] text-white py-14" data-testid="landing-footer">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
        <div>
          <div className="flex items-center gap-2.5 mb-4">
            <BrandMark size={40} />
            <div className="font-sans font-extrabold text-lg">
              <span className="text-brand-gradient">SACO</span>Parents
            </div>
          </div>
          <p className="text-[13px] text-white/65 leading-relaxed">
            Helping families communicate better. Built with care in San Antonio, Texas.
          </p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-white/50 mb-3 font-semibold">
            Product
          </div>
          <ul className="space-y-2 text-[14px] text-white/80">
            <li><Link to="/register" className="hover:text-white" data-testid="footer-register-link">Get started</Link></li>
            <li><Link to="/login" className="hover:text-white" data-testid="footer-login-link">Sign in</Link></li>
            <li><Link to="/safety" className="hover:text-white" data-testid="footer-safety-link">Safety resources</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-white/50 mb-3 font-semibold">
            Legal
          </div>
          <ul className="space-y-2 text-[14px] text-white/80">
            <li><Link to="/privacy" className="hover:text-white" data-testid="footer-privacy-link">Privacy policy</Link></li>
            <li><Link to="/terms" className="hover:text-white" data-testid="footer-terms-link">Terms of use</Link></li>
            <li><Link to="/delete-account" className="hover:text-white" data-testid="footer-delete-account-link">Delete my account</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-white/50 mb-3 font-semibold">
            Contact
          </div>
          <ul className="space-y-2 text-[14px] text-white/80">
            <li>
              <a href="mailto:mattsossi@bsossi.com" className="hover:text-white" data-testid="footer-email-link">
                mattsossi@bsossi.com
              </a>
            </li>
            <li>
              <a href="tel:2102241667" className="hover:text-white" data-testid="footer-phone-link">
                210-224-1667
              </a>
            </li>
            {FB_URL && (
              <li>
                <a
                  href={FB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-white"
                  data-testid="footer-facebook-link"
                >
                  <Facebook size={14} /> Facebook
                </a>
              </li>
            )}
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-5 sm:px-6 mt-10 pt-6 border-t border-white/10 text-[11px] text-white/50 flex flex-wrap items-center justify-between gap-2">
        <span>© SACOParents — Helping families communicate better</span>
        <span>16607 Blanco #703, San Antonio, Texas 78232</span>
      </div>
    </footer>
  );
}

/* ============================================================
   PHONE MOCKUP — inline, brand-correct (no legacy screenshots)
============================================================ */
function PhoneMockup({ variant = "home", className = "" }) {
  return (
    <div
      className={`relative w-full max-w-[300px] mx-auto ${className}`}
      data-testid={`phone-mockup-${variant}`}
    >
      <div className="aspect-[9/19] rounded-[40px] bg-[#1A1330] p-[10px] shadow-2xl ring-4 ring-white/20">
        <div className="w-full h-full rounded-[32px] bg-white overflow-hidden relative">
          {/* notch */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 w-20 h-5 rounded-full bg-[#1A1330] z-10" />
          <PhoneScreen variant={variant} />
        </div>
      </div>
    </div>
  );
}

function PhoneScreen({ variant }) {
  if (variant === "assess") {
    const items = [
      { icon: MessageCircle, tone: "purple", label: "Separate facts from feelings" },
      { icon: Lock, tone: "teal", label: "Identify what you can and cannot control" },
      { icon: TrendingUpIcon, tone: "magenta", label: "Evaluate patterns, not isolated events" },
      { icon: Heart, tone: "blue", label: "Consider the impact on everyone involved" },
      { icon: TargetIcon, tone: "green", label: "Define your realistic goals" },
    ];
    return (
      <div className="h-full flex flex-col">
        <div className="bg-brand-gradient text-white px-4 pt-10 pb-3">
          <div className="text-[8px] uppercase tracking-[0.2em] opacity-80 mb-0.5">Step 1</div>
          <div className="font-extrabold text-sm leading-tight">Assess Your Situation</div>
        </div>
        <div className="flex-1 px-2.5 py-2.5 space-y-1 bg-[#F8F7FC]">
          {items.map(({ icon: Icon, tone, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 bg-white rounded-lg border border-[#E5E0EE] px-2 py-1.5"
            >
              <span className={`icon-circle icon-circle-${tone} w-6 h-6 shrink-0`}>
                <Icon size={10} />
              </span>
              <span className="text-[9.5px] font-semibold text-[#1A1330] leading-tight">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (variant === "mediator") {
    return (
      <div className="h-full flex flex-col">
        <div className="bg-brand-gradient text-white px-5 pt-12 pb-6">
          <div className="text-[9px] uppercase tracking-[0.2em] opacity-80 mb-1">Step 3</div>
          <div className="font-extrabold text-lg leading-tight">Your prepared documents</div>
        </div>
        <div className="flex-1 px-4 py-4 space-y-2.5 bg-[#F8F7FC]">
          <DocRow icon="🗎" label="Mediation Summary" tone="purple" />
          <DocRow icon="✦" label="Co-Parenting Agreement" tone="teal" />
          <DocRow icon="↗" label="Things I Can Improve" tone="magenta" />
          <div className="pt-3">
            <div className="text-[9px] uppercase tracking-[0.15em] text-[#857E9C] mb-1.5 font-semibold">
              Readiness
            </div>
            <div className="bg-white rounded-xl border border-[#E5E0EE] p-3">
              <div className="flex items-end justify-between mb-2">
                <span className="text-[11px] text-[#4B4567] font-semibold">Prepared</span>
                <span className="text-base font-extrabold text-[#3D1A78]">75/100</span>
              </div>
              <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden">
                <div className="h-full bg-brand-gradient" style={{ width: "75%" }} />
              </div>
            </div>
          </div>
          <button className="w-full mt-2 py-2.5 rounded-full bg-brand-gradient text-white text-xs font-bold">
            Download PDF
          </button>
        </div>
      </div>
    );
  }

  // home variant — brochure-style module list
  const modules = [
    { tone: "purple", label: "State Goals, Issues & Concerns" },
    { tone: "teal", label: "Begin Co-Parenting Statement" },
    { tone: "magenta", label: "Create Mediation Plan" },
  ];
  return (
    <div className="h-full flex flex-col">
      <div className="bg-brand-gradient text-white px-5 pt-12 pb-6">
        <div className="text-[10px] uppercase tracking-[0.2em] opacity-80 mb-1">Step 2</div>
        <div className="font-extrabold text-lg leading-tight">
          Plan your path forward.
        </div>
      </div>
      <div className="flex-1 px-4 py-4 space-y-2.5 bg-[#F8F7FC]">
        {modules.map((m) => (
          <div
            key={m.label}
            className="flex items-center gap-3 bg-white rounded-xl border border-[#E5E0EE] px-3 py-2.5"
          >
            <span className={`icon-circle icon-circle-${m.tone} w-9 h-9`}>
              <Heart size={14} />
            </span>
            <span className="text-[12px] font-semibold text-[#1A1330] leading-tight">
              {m.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DocRow({ icon, label, tone }) {
  return (
    <div className="flex items-center gap-3 bg-white rounded-xl border border-[#E5E0EE] px-3 py-2.5">
      <span className={`icon-circle icon-circle-${tone} w-8 h-8 text-xs font-bold`}>{icon}</span>
      <span className="text-[12px] font-semibold text-[#1A1330]">{label}</span>
    </div>
  );
}

/* ============================================================
   APP STORE BADGES
============================================================ */
function AppStoreBadge() {
  return (
    <a
      href="#"
      onClick={(e) => e.preventDefault()}
      className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#1A1330] text-white hover:bg-[#0F0A1F] transition-colors"
      data-testid="badge-app-store"
      title="Coming soon to the Apple App Store"
    >
      <Apple size={22} strokeWidth={1.5} />
      <div className="leading-tight text-left">
        <div className="text-[9px] tracking-wider uppercase opacity-80">Coming soon</div>
        <div className="text-sm font-bold">App Store</div>
      </div>
    </a>
  );
}

function GooglePlayBadge() {
  return (
    <a
      href="#"
      onClick={(e) => e.preventDefault()}
      className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#1A1330] text-white hover:bg-[#0F0A1F] transition-colors"
      data-testid="badge-google-play"
      title="Coming soon to Google Play"
    >
      <PlayIcon size={22} strokeWidth={1.5} className="fill-white" />
      <div className="leading-tight text-left">
        <div className="text-[9px] tracking-wider uppercase opacity-80">Coming soon</div>
        <div className="text-sm font-bold">Google Play</div>
      </div>
    </a>
  );
}
