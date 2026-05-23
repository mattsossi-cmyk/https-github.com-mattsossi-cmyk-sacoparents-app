import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Heart,
  Compass,
  Sparkles,
  Lock,
  FileCheck,
  Wind,
  ArrowRight,
  ArrowLeft,
  Check,
  ShieldAlert,
  X,
} from "lucide-react";

/**
 * App Orientation — a one-time onboarding walkthrough that teaches parents
 * what relational mediation is and how this app fits into it. Stored in
 * localStorage so the user only sees it automatically once, but can revisit
 * any time from the dashboard.
 */
const ORIENTATION_KEY = "sacoparents.orientation_seen.v1";

export function hasSeenOrientation() {
  try {
    return localStorage.getItem(ORIENTATION_KEY) === "true";
  } catch (_e) {
    return false;
  }
}

export function markOrientationSeen() {
  try {
    localStorage.setItem(ORIENTATION_KEY, "true");
  } catch (_e) {
    // Private-browsing mode — ignore silently
  }
}

const SLIDES = [
  {
    eyebrow: "Welcome",
    title: "Mediation, prepared with care.",
    body:
      "Separation and co-parenting mediation can feel overwhelming. This app exists to help you arrive prepared — child-centered, emotionally regulated, and clear about what you want to say.",
    icon: Heart,
    accent: "rose",
  },
  {
    eyebrow: "What is relational mediation?",
    title: "Not a courtroom. A conversation.",
    body:
      "Relational mediation is different from courtroom litigation. It's not about winning. It's about finding a sustainable way to co-parent — one that centres your child's emotional safety. The mediator's role is to keep the conversation productive, not to choose sides.",
    icon: Compass,
    accent: "sage",
  },
  {
    eyebrow: "How this app helps",
    title: "Five guided steps. Then AI does the synthesis.",
    bullets: [
      "Child-Centered Goals — what you want your child to experience",
      "Issues & Concerns — what you'd like to raise, factually",
      "Priority Ranking — the eleven legal custody categories, sorted",
      "Communication Style — your patterns, gently reframed",
      "Readiness Check — how prepared you actually feel",
    ],
    body:
      "Each step takes 5–10 minutes. You can pause any time. Nothing is graded.",
    icon: Sparkles,
    accent: "sage",
  },
  {
    eyebrow: "Privacy",
    title: "Your answers stay with you.",
    body:
      "Everything you write is private to your account. Your co-parent cannot see your prep. The mediator never sees anything unless you explicitly choose to email or download a document. You can delete your account and all data anytime — instantly.",
    icon: Lock,
    accent: "sand",
  },
  {
    eyebrow: "Safety, always",
    title: "If you're in a high-conflict or unsafe situation",
    body:
      "Every page has a Quick Exit. Domestic violence and suicide hotlines are one tap away on the Safety screen. If your situation feels dangerous, mediation may not be the right next step — and we'll surface alternative resources, including parallel parenting guidance, as you go.",
    icon: ShieldAlert,
    accent: "warn",
  },
  {
    eyebrow: "What you'll leave with",
    title: "Three mediator-ready documents.",
    bullets: [
      "Mediation Summary — focused, professional, downloadable PDF",
      "Co-Parenting Agreement Draft — a neutral starting point",
      "Things I Can Improve On — your private growth plan",
    ],
    body:
      "Email any document to your mediator directly. Retake any assessment later — the app shows you what's shifted since last time.",
    icon: FileCheck,
    accent: "sage",
  },
];

const ACCENTS = {
  rose: { ring: "ring-[#C28771]/30", icon: "bg-[#C28771]/15 text-[#C28771]" },
  sage: { ring: "ring-[#849D8E]/30", icon: "bg-[#849D8E]/15 text-[#849D8E]" },
  sand: { ring: "ring-[#E5D9C5]", icon: "bg-[#F5F3E9] text-[#5C7A6A]" },
  warn: { ring: "ring-[#C28771]/40", icon: "bg-[#C28771]/15 text-[#C28771]" },
};

export default function Orientation() {
  const navigate = useNavigate();
  const [idx, setIdx] = useState(0);
  const total = SLIDES.length;
  const slide = SLIDES[idx];

  const isLast = idx === total - 1;
  const isFirst = idx === 0;

  const next = () => {
    if (isLast) {
      markOrientationSeen();
      navigate("/dashboard");
    } else {
      setIdx((i) => i + 1);
    }
  };
  const prev = () => {
    if (!isFirst) setIdx((i) => i - 1);
  };
  const skip = () => {
    markOrientationSeen();
    navigate("/dashboard");
  };

  const Icon = slide.icon;
  const a = ACCENTS[slide.accent] || ACCENTS.sage;

  return (
    <div className="min-h-screen gentle-bg flex flex-col" data-testid="orientation-page">
      {/* Top bar */}
      <header className="px-5 sm:px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img
            src="/sa-coparents-mark.png"
            alt="SA Coparents"
            className="w-10 h-10 rounded-lg ring-1 ring-[#E8ECE9]"
          />
          <div className="leading-tight">
            <div className="font-serif text-base text-[#2A3631]">SA Coparents</div>
            <div className="text-[9px] uppercase tracking-[0.25em] text-[#8A9A92]">
              Orientation
            </div>
          </div>
        </div>
        <button
          onClick={skip}
          className="text-[12px] text-[#5C6B64] hover:text-[#2A3631] inline-flex items-center gap-1.5"
          data-testid="orientation-skip-button"
        >
          Skip <X size={12} />
        </button>
      </header>

      {/* Slide card */}
      <main className="flex-1 flex items-center justify-center px-5 sm:px-8 py-8">
        <div className="max-w-2xl w-full">
          <div className={`bg-white rounded-3xl ring-1 ${a.ring} p-7 sm:p-10 shadow-sm relative overflow-hidden`} data-testid={`orientation-slide-${idx}`}>
            <div className="absolute -top-12 -right-12 w-44 h-44 rounded-full bg-[#F5F3E9]/60 pointer-events-none" />
            <div className="relative">
              <div className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl ${a.icon} mb-6`}>
                <Icon size={24} />
              </div>
              <div className="eyebrow mb-3">{slide.eyebrow}</div>
              <h2 className="font-serif text-3xl sm:text-4xl text-[#2A3631] leading-tight mb-4">
                {slide.title}
              </h2>
              {slide.body && (
                <p className="text-[15px] sm:text-[16px] text-[#5C6B64] leading-relaxed">
                  {slide.body}
                </p>
              )}
              {slide.bullets && (
                <ul className="mt-5 space-y-2.5">
                  {slide.bullets.map((b, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2.5 text-[14px] sm:text-[15px] text-[#2A3631]"
                      data-testid={`orientation-bullet-${idx}-${i}`}
                    >
                      <Check size={16} className="text-[#849D8E] mt-1 shrink-0" />
                      <span className="leading-relaxed">{b}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Pagination dots */}
          <div className="flex items-center justify-center gap-2 mt-7" data-testid="orientation-dots">
            {SLIDES.map((_, i) => (
              <button
                key={i}
                onClick={() => setIdx(i)}
                aria-label={`Go to step ${i + 1}`}
                className={`h-2 rounded-full transition-all ${
                  i === idx ? "w-8 bg-[#849D8E]" : "w-2 bg-[#E8ECE9] hover:bg-[#C2D0C8]"
                }`}
                data-testid={`orientation-dot-${i}`}
              />
            ))}
          </div>

          {/* Navigation row */}
          <div className="mt-7 flex items-center justify-between gap-3">
            <button
              onClick={prev}
              disabled={isFirst}
              className="btn-soft inline-flex items-center gap-2 disabled:opacity-0 disabled:cursor-default"
              data-testid="orientation-prev-button"
            >
              <ArrowLeft size={14} /> Back
            </button>

            <div className="text-[12px] text-[#8A9A92]">
              {idx + 1} / {total}
            </div>

            <button
              onClick={next}
              className="btn-sage inline-flex items-center gap-2"
              data-testid="orientation-next-button"
            >
              {isLast ? "Start your prep" : "Next"} <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </main>

      <footer className="text-center pb-5 text-[11px] text-[#8A9A92]">
        <span className="inline-flex items-center gap-1.5">
          <Wind size={11} className="text-[#849D8E]" />
          Take a breath if you need to — this is your space.
        </span>
      </footer>
    </div>
  );
}
