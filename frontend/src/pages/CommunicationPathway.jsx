/**
 * Communication Pathway (Phase 1 placeholder).
 *
 * Route: `/communication`
 *
 * Founder spec 2026-03-04:
 *   1. Ask "What best describes your communication?" with 5 choices.
 *   2. Recommend appropriate tools (BIFF, CLEAR Path, boundaries, etc.).
 *   3. If the answer indicates fear / coercion / threats / safety
 *      concerns → route to the Family Violence & Safety pathway.
 *
 * This page is intentionally a placeholder: the reflection surface and
 * eventual Communication Alignment Report land in Phase 2. Today the
 * page captures the intake answer, saves it to localStorage so the
 * dashboard can remember, and either (a) shows the recommended tools or
 * (b) escalates to /safety.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageCircle,
  ShieldAlert,
  ArrowLeft,
  ArrowRight,
  Sparkles,
  BookOpen,
  Lock,
} from "lucide-react";

import AppShell from "../components/AppShell";

const CHOICES = [
  {
    key: "productive",
    label: "Generally productive",
    detail:
      "We can talk about the kids without much friction. Occasional bumps but nothing systemic.",
    tone: "bg-[#E1F3E8] text-[#186142] border-[#B7DEC6]",
    tools: ["BIFF", "Child-focused messaging", "Response expectations"],
    unsafe: false,
  },
  {
    key: "difficult",
    label: "Difficult",
    detail:
      "Conversations regularly get tense, off-topic, or emotional. We often walk away frustrated.",
    tone: "bg-[#FFF6EA] text-[#8A4610] border-[#F1D9B7]",
    tools: [
      "BIFF",
      "CLEAR Path",
      "Written communication",
      "Structured messaging",
    ],
    unsafe: false,
  },
  {
    key: "high-conflict",
    label: "High conflict",
    detail:
      "Most exchanges escalate. We may argue in front of the kids or via long text threads.",
    tone: "bg-[#FBE9EA] text-[#8F1D24] border-[#EDBFC2]",
    tools: [
      "CLEAR Path",
      "Written-only channels (OFW / TalkingParents)",
      "Boundaries",
      "Conflict-reduction messaging",
    ],
    unsafe: false,
  },
  {
    key: "very-limited",
    label: "Very limited",
    detail:
      "We barely communicate. Handoffs are minimal, we rely on the kids to relay information, or one parent doesn't respond.",
    tone: "bg-[#EFE9F9] text-[#3D1A78] border-[#D6CFE8]",
    tools: [
      "Structured written communication",
      "Parallel-parenting protocols",
      "Response-time expectations",
    ],
    unsafe: false,
  },
  {
    key: "unsafe",
    label: "Communication feels unsafe",
    detail:
      "There is fear, coercion, threats, monitoring, or safety concerns when we communicate.",
    tone: "bg-[#FDECEC] text-[#8F1D24] border-[#F5C5C5]",
    tools: [],
    unsafe: true,
  },
];

const STORAGE_KEY = "sacoparents.communication.choice";

export default function CommunicationPathway() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  const handleSelect = (choiceKey) => {
    setSelected(choiceKey);
    try {
      localStorage.setItem(STORAGE_KEY, choiceKey);
    } catch {
      /* non-blocking */
    }
  };

  const activeChoice = CHOICES.find((c) => c.key === selected);

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12"
        data-testid="communication-pathway"
      >
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:text-[#2A0F5F] mb-6"
          data-testid="communication-back-link"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </button>

        <div className="rounded-3xl bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6] text-white p-6 sm:p-8 shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-white/15 grid place-items-center backdrop-blur-sm">
              <MessageCircle size={22} strokeWidth={2.2} />
            </div>
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-white/85">
              Communication pathway
            </div>
          </div>
          <h1
            className="font-serif text-3xl sm:text-4xl leading-tight mt-4"
            data-testid="communication-title"
          >
            How can we communicate more effectively?
          </h1>
          <p className="text-white/85 mt-3 max-w-2xl leading-relaxed text-[15px]">
            Start with the option that best describes your communication
            today. We&rsquo;ll recommend tools that fit — and if anything you
            answer suggests it isn&rsquo;t safe to communicate, we&rsquo;ll
            route you to the Family Violence &amp; Safety pathway instead.
          </p>
        </div>

        <div className="mt-8">
          <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#1E6FA8] mb-2">
            Step 1
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] leading-tight">
            What best describes your communication?
          </h2>
          <div
            className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3"
            data-testid="communication-choices"
          >
            {CHOICES.map((choice) => {
              const isActive = selected === choice.key;
              return (
                <button
                  key={choice.key}
                  type="button"
                  onClick={() => handleSelect(choice.key)}
                  className={`text-left rounded-2xl border-2 p-4 transition ${
                    isActive
                      ? "border-[#1E6FA8] shadow-md bg-white"
                      : "border-[#E5E0EE] bg-white hover:border-[#3A9DD6]"
                  }`}
                  data-testid={`communication-choice-${choice.key}`}
                >
                  <div
                    className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold ${choice.tone}`}
                  >
                    {choice.label}
                  </div>
                  <p className="text-[13px] text-[#4B4567] mt-3 leading-snug">
                    {choice.detail}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Recommendation surface */}
        {activeChoice && !activeChoice.unsafe && (
          <div
            className="mt-8 rounded-3xl border border-[#D8E7F3] bg-white p-6 sm:p-8"
            data-testid="communication-recommendation"
          >
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-[#1E6FA8]" />
              <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#1E6FA8]">
                Recommended for &ldquo;{activeChoice.label}&rdquo;
              </div>
            </div>
            <h3 className="font-serif text-xl text-[#1A1330] leading-tight mt-2">
              Tools that fit where you are today
            </h3>
            <ul className="mt-4 space-y-2">
              {activeChoice.tools.map((tool) => (
                <li
                  key={tool}
                  className="flex items-start gap-2 text-[14px] text-[#1A1330] leading-relaxed"
                >
                  <BookOpen size={14} className="text-[#1E6FA8] mt-1 flex-shrink-0" />
                  <span>{tool}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6 rounded-2xl bg-[#EEF5FA] border border-[#D0E4EE] p-4 flex items-start gap-3 text-[13px] text-[#1E6FA8]">
              <Lock size={15} className="flex-shrink-0 mt-0.5" />
              <p className="!m-0 leading-relaxed text-[#1A1330]">
                <strong>Coming next:</strong> your Communication Reflection
                and Communication Alignment Report. Today this pathway
                captures your intake; the reflection and joint report land in
                the next release.
              </p>
            </div>
          </div>
        )}

        {/* Safety escalation surface */}
        {activeChoice && activeChoice.unsafe && (
          <div
            className="mt-8 rounded-3xl border-2 border-[#8F1D24] bg-[#FDECEC] p-6 sm:p-8"
            data-testid="communication-safety-escalation"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-[#8F1D24] text-white grid place-items-center">
                <ShieldAlert size={22} strokeWidth={2.2} />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#8F1D24]">
                  Safety comes first
                </div>
                <h3 className="font-serif text-xl text-[#1A1330] leading-tight mt-1">
                  Let&rsquo;s move you to the safety pathway
                </h3>
              </div>
            </div>
            <p className="text-[14px] text-[#4B4567] mt-4 leading-relaxed">
              When communication feels unsafe, the goal isn&rsquo;t
              alignment — it&rsquo;s structure and safeguards. The Family
              Violence &amp; Safety pathway walks through communication
              safety, parenting structure, professional channels, and
              resources without asking you to align on anything you
              shouldn&rsquo;t.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => navigate("/safety")}
                className="inline-flex items-center gap-2 rounded-full bg-[#8F1D24] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#7A1720] transition"
                data-testid="communication-goto-safety"
              >
                Go to Family Violence &amp; Safety
                <ArrowRight size={14} />
              </button>
              <a
                href="tel:18007997233"
                className="inline-flex items-center gap-2 rounded-full bg-white text-[#8F1D24] border border-[#8F1D24] px-5 py-2.5 text-sm font-semibold hover:bg-[#FBE9EA] transition"
              >
                Call 1-800-799-7233
              </a>
            </div>
            <p className="text-[12px] text-[#4B4567] italic mt-4 leading-relaxed">
              In immediate danger? Call{" "}
              <a href="tel:911" className="underline font-semibold text-[#8F1D24]">
                911
              </a>
              . Text <strong>START</strong> to <strong>88788</strong>.
            </p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
