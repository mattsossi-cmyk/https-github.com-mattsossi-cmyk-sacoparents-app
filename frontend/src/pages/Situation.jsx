/**
 * `/situation` — 4-topic picker (iter196 Phase 1).
 *
 * The parent has already chosen "Starting on My Own" on the front
 * door. This page asks the second question — "What would you like
 * help with?" — and routes them into the correct pathway.
 *
 * Four topics matching the founder's spec:
 *   - Co-Parenting       → /special-needs-v2 (Co-Parenting Assessment)
 *   - Communication      → /communication
 *   - My Child's Needs   → /special-needs-v2 (deep-dive picker inside)
 *   - Safety / Family
 *     Violence           → /safety-assessment
 *
 * The route is intentionally shallow — no session required. Guest
 * parents who came in from `/` land here, pick a topic, and the
 * downstream assessment pages handle the guest-session bootstrap.
 * Authed parents already have a session and just get routed straight
 * into the assessment.
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  Handshake,
  MessageCircle,
  Baby,
  ShieldAlert,
  Phone,
} from "lucide-react";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";

const TOPICS = [
  {
    key: "co-parenting",
    label: "Co-Parenting",
    body: "Understand how you and the other parent are currently working together — decisions, exchanges, boundaries, holidays.",
    route: "/special-needs-v2",
    icon: Handshake,
    tone: {
      bg: "bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0]",
      border: "border-[#D6CFE8] hover:border-[#3D1A78]",
      chip: "bg-[#EFE9F9] text-[#3D1A78]",
      arrow: "text-[#3D1A78]",
    },
    testid: "situation-topic-co-parenting",
  },
  {
    key: "communication",
    label: "Communication",
    body: "Reflect on communication patterns and build calmer, clearer messages you're proud to send.",
    route: "/communication",
    icon: MessageCircle,
    tone: {
      bg: "bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6]",
      border: "border-[#B7D5EA] hover:border-[#1E6FA8]",
      chip: "bg-[#E4F1FA] text-[#1E6FA8]",
      arrow: "text-[#1E6FA8]",
    },
    testid: "situation-topic-communication",
  },
  {
    key: "child-needs",
    label: "My Child's Needs",
    body: "Focus on educational, medical, psychological, or other child-specific needs. Includes deep-dive assessments per area.",
    route: "/special-needs-v2",
    icon: Baby,
    tone: {
      bg: "bg-gradient-to-br from-[#1E7A55] to-[#3AA378]",
      border: "border-[#C4E4D3] hover:border-[#1E7A55]",
      chip: "bg-[#E1F3E8] text-[#1E7A55]",
      arrow: "text-[#1E7A55]",
    },
    testid: "situation-topic-child-needs",
  },
  {
    key: "safety",
    label: "Safety / Family Violence",
    body: "A private safety screen — never asks you to cooperate with the other parent. Includes hotlines and a downloadable safety plan.",
    route: "/safety-assessment",
    icon: ShieldAlert,
    tone: {
      bg: "bg-gradient-to-br from-[#B45F13] to-[#D97836]",
      border: "border-[#F1D9B7] hover:border-[#B45F13]",
      chip: "bg-[#FFEEDA] text-[#8A4610]",
      arrow: "text-[#8A4610]",
    },
    testid: "situation-topic-safety",
  },
];

export default function Situation() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const pick = (topic) => {
    // Authed users go straight in. Guests too — the destination
    // pages already handle guest-session bootstrap on demand.
    navigate(topic.route);
  };

  return (
    <AppShell>
      <div
        className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-14"
        data-testid="situation-page"
      >
        <Link
          to={user ? "/dashboard" : "/"}
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#3D1A78] mb-6"
          data-testid="situation-back"
        >
          <ArrowLeft size={14} />
          Back
        </Link>

        <div className="text-center max-w-2xl mx-auto">
          <div className="text-[11px] uppercase tracking-[0.28em] font-bold text-[#3D1A78]">
            Starting on My Own · Step 2 of 2
          </div>
          <h1
            className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-3"
            data-testid="situation-headline"
          >
            What brings you here?
          </h1>
          <p className="text-base sm:text-lg text-[#4B4567] mt-4 leading-relaxed">
            Pick the topic you want help with. SA CoParents will recommend
            the right assessment and walk you through the pathway.
          </p>
        </div>

        <div
          className="mt-10 grid gap-4 sm:grid-cols-2 max-w-4xl mx-auto"
          data-testid="situation-topics"
        >
          {TOPICS.map((topic) => (
            <TopicTile key={topic.key} topic={topic} onPick={() => pick(topic)} />
          ))}
        </div>

        <div
          className="mt-10 mx-auto max-w-3xl rounded-2xl border border-[#F1D9B7] bg-[#FFF6EA] px-5 py-4 flex items-start gap-3 text-[13px] leading-relaxed"
          data-testid="situation-crisis-strip"
        >
          <Phone size={16} className="text-[#B45F13] flex-shrink-0 mt-0.5" />
          <p className="!m-0 text-[#5A3C10]">
            <strong>In immediate danger?</strong> Call{" "}
            <a href="tel:911" className="underline font-semibold">
              911
            </a>{" "}
            · Suicide &amp; Crisis Lifeline:{" "}
            <a href="tel:988" className="underline font-semibold">
              988
            </a>{" "}
            · National DV Hotline:{" "}
            <a href="tel:18007997233" className="underline font-semibold">
              1-800-799-SAFE
            </a>
            .
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function TopicTile({ topic, onPick }) {
  const Icon = topic.icon;
  return (
    <button
      type="button"
      onClick={onPick}
      data-testid={topic.testid}
      className={`group text-left rounded-3xl bg-white border-2 ${topic.tone.border} p-6 sm:p-7 transition-all hover:-translate-y-0.5 hover:shadow-lg flex flex-col`}
    >
      <div
        className={`w-14 h-14 rounded-full grid place-items-center text-white shadow-md ${topic.tone.bg} group-hover:scale-110 group-hover:shadow-lg transition-transform duration-200`}
      >
        <Icon size={26} strokeWidth={2.1} />
      </div>
      <h2 className="font-serif text-2xl text-[#1A1330] mt-4 leading-tight">
        {topic.label}
      </h2>
      <p className="text-[14px] text-[#4B4567] mt-3 leading-relaxed flex-1">
        {topic.body}
      </p>
      <span
        className={`mt-4 inline-flex items-center gap-1.5 text-sm font-semibold ${topic.tone.arrow} group-hover:gap-2.5 transition-all`}
      >
        Continue
        <ArrowRight size={14} />
      </span>
    </button>
  );
}
