import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Heart,
  Compass,
  Users,
  ArrowRight,
  Facebook,
  ShieldAlert,
  Check,
  Sparkles,
  TrendingUp,
  FileText,
  Apple,
  Play as PlayIcon,
  ChevronDown,
  Quote,
  Mail,
} from "lucide-react";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

export default function Landing() {
  return (
    <div className="min-h-screen gentle-bg">
      <MarketingHeader />
      <Hero />
      <Philosophy />
      <HowItWorks />
      <ScreenshotShowcase />
      <Features />
      <ForMediators />
      <Testimonials />
      <FAQ />
      <FinalCTA />
      <MarketingFooter />
    </div>
  );
}

/* ============================================================
   HEADER
============================================================ */
function MarketingHeader() {
  return (
    <header className="max-w-7xl mx-auto px-5 sm:px-6 py-5 sm:py-6 flex items-center justify-between sticky top-0 z-30 backdrop-blur-md bg-[#FDFAF3]/80">
      <Link to="/" className="flex items-center gap-2 sm:gap-3" data-testid="landing-brand-logo">
        <img
          src="/sa-coparents-mark.png"
          alt="SA Coparents"
          className="w-11 h-11 sm:w-14 sm:h-14 rounded-xl object-contain bg-[#FDFAF3] ring-1 ring-[#E8ECE9]"
        />
        <div className="leading-tight">
          <div className="font-serif text-lg sm:text-xl">SA Coparents</div>
          <div className="hidden sm:block text-[10px] uppercase tracking-[0.25em] text-[#8A9A92]">
            Relational Mediation Prep
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
        <Link to="/login" className="text-sm text-[#5C6B64] hover:text-[#2A3631]" data-testid="nav-sign-in">
          Sign in
        </Link>
        <Link to="/register" className="btn-sage text-sm" data-testid="nav-get-started">
          Get started
        </Link>
      </div>
    </header>
  );
}

/* ============================================================
   HERO
============================================================ */
function Hero() {
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 pt-10 pb-16 sm:pt-14 sm:pb-24 relative" data-testid="hero">
      <div className="grid lg:grid-cols-12 gap-10 lg:gap-12 items-center fade-up">
        <div className="lg:col-span-7">
          <div className="eyebrow mb-5">A quieter way to prepare</div>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl leading-[1.05] text-[#2A3631]">
            Mediation,
            <br className="hidden sm:block" /> prepared with{" "}
            <em className="text-[#849D8E] not-italic font-normal italic">care</em>.
          </h1>
          <p className="text-base sm:text-lg text-[#5C6B64] mt-6 max-w-xl leading-relaxed">
            SA Coparents helps separating parents arrive at co-parenting mediation
            child-centered and emotionally prepared. Five guided steps, AI-synthesized
            mediator-ready documents, and safety tools — all in one calm, private space.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link to="/register" className="btn-sage inline-flex items-center gap-2" data-testid="hero-start-button">
              Start your prep — free <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="btn-soft" data-testid="hero-continue-button">
              Continue my progress
            </Link>
          </div>

          <div className="mt-7 flex items-center gap-3 flex-wrap" data-testid="hero-store-badges">
            <AppStoreBadge />
            <GooglePlayBadge />
          </div>

          <div className="mt-7 flex items-center gap-5 text-xs text-[#8A9A92]">
            <span className="inline-flex items-center gap-1.5">
              <Check size={14} className="text-[#849D8E]" /> Free to use
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Check size={14} className="text-[#849D8E]" /> Private by default
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Check size={14} className="text-[#849D8E]" /> No ads
            </span>
          </div>
        </div>

        <div className="lg:col-span-5 relative">
          <div className="absolute -top-10 -right-10 w-56 h-56 rounded-full bg-[#E5D9C5]/40" />
          <div className="absolute -bottom-12 -left-10 w-44 h-44 rounded-full bg-[#849D8E]/15" />
          <div className="relative">
            <img
              src="/marketing/raw-summary.png"
              alt="SA Coparents — Your prepared documents"
              className="w-full max-w-sm mx-auto rounded-[36px] shadow-2xl ring-1 ring-[#E8ECE9]"
              data-testid="hero-screenshot"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   PHILOSOPHY STRIP
============================================================ */
function Philosophy() {
  const items = [
    { icon: Heart, title: "Child-centered", text: "Every prompt orients toward your child's emotional safety." },
    { icon: Compass, title: "Structured, not clinical", text: "A guided wizard so nothing important is forgotten on the day." },
    { icon: Users, title: "Non-judgmental", text: "No winners or losers — only a relational path forward." },
  ];
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-10 sm:py-16" data-testid="philosophy">
      <div className="grid md:grid-cols-3 gap-5 sm:gap-6">
        {items.map(({ icon: Icon, title, text }) => (
          <div key={title} className="card-soft p-6 sm:p-7" data-testid={`philosophy-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <div className="w-10 h-10 rounded-full bg-[#F5F3E9] grid place-items-center text-[#849D8E] mb-4">
              <Icon size={18} />
            </div>
            <div className="font-serif text-xl sm:text-2xl text-[#2A3631] mb-2">{title}</div>
            <p className="text-[#5C6B64] leading-relaxed text-[15px]">{text}</p>
          </div>
        ))}
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
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-14 sm:py-20" data-testid="how-it-works">
      <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-14">
        <div className="eyebrow mb-3">How it works</div>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631]">Five guided steps to clarity.</h2>
        <p className="text-[#5C6B64] mt-4 text-[15px] leading-relaxed">
          Each step is short, private, and saves automatically. You can pause any time and pick up where you left off.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {steps.map(({ n, t, d }) => (
          <div key={n} className="card-soft p-5 sm:p-6 relative" data-testid={`step-${n}`}>
            <div className="w-10 h-10 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center font-medium mb-3">
              {n}
            </div>
            <div className="font-serif text-lg text-[#2A3631] mb-1.5 leading-snug">{t}</div>
            <p className="text-[13px] text-[#5C6B64] leading-relaxed">{d}</p>
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
    { src: "/marketing/raw-dashboard.png", caption: "Your progress dashboard" },
    { src: "/marketing/raw-summary.png", caption: "AI-synthesized documents" },
    { src: "/marketing/raw-safety.png", caption: "Safety, always one tap away" },
  ];
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-14 sm:py-20" data-testid="screenshot-showcase">
      <div className="text-center mb-10 sm:mb-12">
        <div className="eyebrow mb-3">A glimpse</div>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631]">Built for calm, not conflict.</h2>
      </div>
      <div className="grid sm:grid-cols-3 gap-6 sm:gap-8 max-w-4xl mx-auto">
        {shots.map((s, i) => (
          <div key={i} className="text-center" data-testid={`screenshot-${i + 1}`}>
            <img
              src={s.src}
              alt={s.caption}
              className="w-full max-w-[260px] mx-auto rounded-[28px] shadow-xl ring-1 ring-[#E8ECE9]"
            />
            <div className="text-[13px] text-[#5C6B64] mt-3 italic">{s.caption}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   FEATURES
============================================================ */
function Features() {
  const features = [
    {
      icon: Sparkles,
      title: "AI-synthesized documents",
      text: "Generate a Mediation Summary, Co-Parenting Agreement Draft, and personal Growth Plan in seconds. Download as PDF or email directly to your mediator.",
    },
    {
      icon: ShieldAlert,
      title: "Safety, built in",
      text: "One-tap Quick Exit, 24/7 confidential hotlines, and dedicated guidance for high-conflict situations where parallel parenting may be safer.",
    },
    {
      icon: TrendingUp,
      title: "Track your growth",
      text: "Retake any assessment over time. See exactly what's changed since your last session — visible evidence of your own emotional progress.",
    },
    {
      icon: FileText,
      title: "Mediator-ready PDFs",
      text: "Every document is formatted to be brought into a mediation session — branded, structured, and professional.",
    },
  ];
  return (
    <section className="bg-[#F5F3E9]/50 border-y border-[#E8ECE9]/60 py-14 sm:py-20" data-testid="features">
      <div className="max-w-7xl mx-auto px-5 sm:px-6">
        <div className="text-center mb-10 sm:mb-14 max-w-2xl mx-auto">
          <div className="eyebrow mb-3">Features</div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631]">Everything you need, nothing you don't.</h2>
        </div>
        <div className="grid sm:grid-cols-2 gap-5 sm:gap-7 max-w-4xl mx-auto">
          {features.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="bg-white border border-[#E8ECE9] rounded-2xl p-6 sm:p-7"
              data-testid={`feature-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <div className="w-11 h-11 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center mb-4">
                <Icon size={20} />
              </div>
              <div className="font-serif text-xl text-[#2A3631] mb-2">{title}</div>
              <p className="text-[14px] text-[#5C6B64] leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   FOR MEDIATORS
============================================================ */
function ForMediators() {
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-6 py-14 sm:py-20" data-testid="for-mediators">
      <div className="grid lg:grid-cols-12 gap-10 items-center">
        <div className="lg:col-span-7">
          <div className="eyebrow mb-3">For mediators &amp; family lawyers</div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631] leading-tight">
            Your clients arrive prepared.
            <br />
            Your sessions move faster.
          </h2>
          <p className="text-[15px] text-[#5C6B64] mt-5 leading-relaxed max-w-xl">
            Recommend SA Coparents before the first session and your clients walk in with a
            child-centered summary, a draft agreement, and a clear sense of what they want
            to discuss. Less venting, more substance — without you having to coach them
            yourself.
          </p>
          <ul className="mt-6 space-y-2.5 text-[14px] text-[#2A3631]">
            <li className="flex gap-2.5"><Check size={16} className="text-[#849D8E] mt-1 shrink-0" /> Reduces session time spent on agenda-setting</li>
            <li className="flex gap-2.5"><Check size={16} className="text-[#849D8E] mt-1 shrink-0" /> Builds a shared vocabulary around the 11 legal custody categories</li>
            <li className="flex gap-2.5"><Check size={16} className="text-[#849D8E] mt-1 shrink-0" /> Includes safety guidance for high-conflict clients</li>
            <li className="flex gap-2.5"><Check size={16} className="text-[#849D8E] mt-1 shrink-0" /> Free for clients — no subscription required</li>
          </ul>
          <a
            href="mailto:mattsossi@bsossi.com?subject=Mediator%20partnership%20inquiry"
            className="btn-sage inline-flex items-center gap-2 mt-7"
            data-testid="mediator-contact-button"
          >
            <Mail size={16} /> Get in touch
          </a>
        </div>

        <div className="lg:col-span-5 relative">
          <div className="absolute -top-6 -left-6 w-40 h-40 rounded-full bg-[#849D8E]/10" />
          <img
            src="/marketing/raw-summary.png"
            alt="A mediator-ready summary"
            className="relative w-full max-w-sm mx-auto rounded-[32px] shadow-xl ring-1 ring-[#E8ECE9]"
          />
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
    <section className="bg-[#FDFAF3] py-14 sm:py-20 border-y border-[#E8ECE9]/60" data-testid="testimonials">
      <div className="max-w-7xl mx-auto px-5 sm:px-6">
        <div className="text-center mb-10 sm:mb-14">
          <div className="eyebrow mb-3">What people say</div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631]">From parents and mediators.</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-5 sm:gap-6 max-w-5xl mx-auto">
          {quotes.map((q, i) => (
            <div
              key={i}
              className="bg-white border border-[#E8ECE9] rounded-2xl p-6 sm:p-7"
              data-testid={`testimonial-${i + 1}`}
            >
              <Quote className="text-[#C28771] mb-3" size={20} />
              <p className="text-[14px] text-[#2A3631] leading-relaxed italic">{q.q}</p>
              <div className="text-[12px] text-[#8A9A92] mt-4 uppercase tracking-wider">{q.a}</div>
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
      q: "Is SA Coparents free?",
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
      a: "No. Many parents use SA Coparents to figure out whether they're ready for mediation in the first place. The Readiness Check helps you decide.",
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
    <section className="max-w-3xl mx-auto px-5 sm:px-6 py-14 sm:py-20" data-testid="faq">
      <div className="text-center mb-8 sm:mb-12">
        <div className="eyebrow mb-3">Questions</div>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631]">Things you might be wondering.</h2>
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
    <div className="border border-[#E8ECE9] rounded-2xl bg-white" data-testid={`faq-item-${idx + 1}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex items-center justify-between gap-3 px-5 sm:px-6 py-4 sm:py-5"
        data-testid={`faq-toggle-${idx + 1}`}
      >
        <span className="font-serif text-[16px] sm:text-[18px] text-[#2A3631] leading-snug">{q}</span>
        <ChevronDown
          size={18}
          className={`text-[#849D8E] transition-transform shrink-0 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-5 sm:px-6 pb-5 text-[14px] text-[#5C6B64] leading-relaxed" data-testid={`faq-answer-${idx + 1}`}>
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
    <section className="max-w-5xl mx-auto px-5 sm:px-6 py-16 sm:py-24" data-testid="final-cta">
      <div className="relative card-soft px-6 sm:px-12 py-12 sm:py-16 text-center overflow-hidden">
        <div className="absolute -top-16 -right-20 w-72 h-72 rounded-full bg-[#E5D9C5]/40" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-[#849D8E]/10" />
        <div className="relative">
          <div className="eyebrow mb-4">Ready when you are</div>
          <h2 className="font-serif text-3xl sm:text-5xl text-[#2A3631] leading-tight max-w-2xl mx-auto">
            From reactive to prepared — in one quiet afternoon.
          </h2>
          <p className="text-[15px] sm:text-base text-[#5C6B64] mt-5 max-w-xl mx-auto leading-relaxed">
            Start your free preparation today. Nothing is shared with anyone unless you choose to share it.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link to="/register" className="btn-sage inline-flex items-center gap-2" data-testid="final-cta-start-button">
              Start your prep — free <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="btn-soft" data-testid="final-cta-signin-button">
              I already have an account
            </Link>
          </div>
          <div className="mt-7 flex items-center justify-center gap-3 flex-wrap">
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
    <footer className="border-t border-[#E8ECE9] py-10" data-testid="landing-footer">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <img src="/sa-coparents-mark.png" alt="SA Coparents" className="w-9 h-9 rounded-lg ring-1 ring-[#E8ECE9]" />
            <div className="font-serif text-lg text-[#2A3631]">SA Coparents</div>
          </div>
          <p className="text-[13px] text-[#8A9A92] leading-relaxed">
            Relational mediation prep for co-parents. Built with care in San Antonio, Texas.
          </p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#8A9A92] mb-3">Product</div>
          <ul className="space-y-2 text-[14px] text-[#5C6B64]">
            <li><Link to="/register" className="hover:text-[#2A3631]" data-testid="footer-register-link">Get started</Link></li>
            <li><Link to="/login" className="hover:text-[#2A3631]" data-testid="footer-login-link">Sign in</Link></li>
            <li><Link to="/safety" className="hover:text-[#2A3631]" data-testid="footer-safety-link">Safety resources</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#8A9A92] mb-3">Legal</div>
          <ul className="space-y-2 text-[14px] text-[#5C6B64]">
            <li><Link to="/privacy" className="hover:text-[#2A3631]" data-testid="footer-privacy-link">Privacy policy</Link></li>
            <li><Link to="/terms" className="hover:text-[#2A3631]" data-testid="footer-terms-link">Terms of use</Link></li>
            <li><Link to="/delete-account" className="hover:text-[#2A3631]" data-testid="footer-delete-account-link">Delete my account</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#8A9A92] mb-3">Contact</div>
          <ul className="space-y-2 text-[14px] text-[#5C6B64]">
            <li>
              <a href="mailto:mattsossi@bsossi.com" className="hover:text-[#2A3631]" data-testid="footer-email-link">
                mattsossi@bsossi.com
              </a>
            </li>
            <li>
              <a href="tel:2102241667" className="hover:text-[#2A3631]" data-testid="footer-phone-link">
                210-224-1667
              </a>
            </li>
            {FB_URL && (
              <li>
                <a
                  href={FB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-[#2A3631]"
                  data-testid="footer-facebook-link"
                >
                  <Facebook size={14} /> Facebook
                </a>
              </li>
            )}
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-5 sm:px-6 mt-8 pt-6 border-t border-[#E8ECE9]/70 text-[11px] text-[#8A9A92] flex flex-wrap items-center justify-between gap-2">
        <span>© SA Coparents — Relational Mediation Prep</span>
        <span>16607 Blanco #703, San Antonio, Texas 78232</span>
      </div>
    </footer>
  );
}

/* ============================================================
   APP STORE BADGES (inline SVG-styled buttons)
============================================================ */
function AppStoreBadge() {
  return (
    <a
      href="#"
      onClick={(e) => e.preventDefault()}
      className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#2A3631] text-white hover:bg-[#1d2723] transition-colors"
      data-testid="badge-app-store"
      title="Coming soon to the Apple App Store"
    >
      <Apple size={22} strokeWidth={1.5} />
      <div className="leading-tight text-left">
        <div className="text-[9px] tracking-wider uppercase opacity-80">Coming soon</div>
        <div className="text-sm font-medium">App Store</div>
      </div>
    </a>
  );
}

function GooglePlayBadge() {
  return (
    <a
      href="#"
      onClick={(e) => e.preventDefault()}
      className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#2A3631] text-white hover:bg-[#1d2723] transition-colors"
      data-testid="badge-google-play"
      title="Coming soon to Google Play"
    >
      <PlayIcon size={22} strokeWidth={1.5} className="fill-white" />
      <div className="leading-tight text-left">
        <div className="text-[9px] tracking-wider uppercase opacity-80">Coming soon</div>
        <div className="text-sm font-medium">Google Play</div>
      </div>
    </a>
  );
}
