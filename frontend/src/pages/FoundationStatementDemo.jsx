/**
 * Foundation Statement — public demo view.
 *
 * Route: `/foundation/demo` (public, no auth required)
 *
 * Purpose:
 *   Before a parent commits to writing their own Foundation Statement, they
 *   can peek at what a completed one looks like. This resolves the "empty
 *   tile with 'Write it →' but nothing to see first" friction the /my-plan
 *   Foundation card had.
 *
 *   The four prompts here mirror `Reflection.jsx` exactly. Content is
 *   fictional / composite, not derived from any real parent. Every panel
 *   is watermarked "Example" so this can never be confused with real data.
 *
 *   Also share-able — this URL renders without auth so it can go in
 *   marketing emails or on Landing.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Heart,
  Sparkles,
  Wind,
  Lock,
  PencilLine,
} from "lucide-react";

import SignedInEscapeHatch from "../components/SignedInEscapeHatch";

// Kept in-file (not extracted) — this is a demo page, no reuse expected.
const DEMO_ENTRIES = [
  {
    id: "child_lens",
    icon: Heart,
    label: "Through your child's eyes",
    prompt:
      "If your child described the last week of co-parenting to a teacher, what would they say?",
    body:
      "She'd probably say the drop-offs feel rushed. Last Tuesday she asked me if we could \"just say goodbye before the car,\" and I realised I'd been standing on my phone. The rest of the week felt fine — we baked, we read her chapter book, we called her dad from the couch. But those handovers stay with her longer than I'd like to admit.",
  },
  {
    id: "own_part",
    icon: Sparkles,
    label: "Your own part",
    prompt:
      "Without blaming anyone, what's one thing you contributed to the difficulty? (No one else will see this.)",
    body:
      "I tend to reply to texts about scheduling within a minute, and it puts pressure on him to do the same. When he doesn't, I read it as disinterest and get sharp. I could set a 6-hour window for scheduling messages so we're both replying from a calmer place, not from the school pickup line.",
  },
  {
    id: "best_outcome",
    icon: Wind,
    label: "Your best-case outcome",
    prompt:
      "Six months from now, what does a calmer week of co-parenting look like for everyone — including your co-parent?",
    body:
      "We use the shared calendar for everything and don't argue about the small stuff on text. Handovers are unhurried — five extra minutes at the door for a hug, not a status update. He and I have one 20-minute check-in every Sunday about the week ahead, and we keep it to logistics. My daughter stops asking whether we're \"friends yet\" because the question feels less urgent to her.",
  },
  {
    id: "coparent_feedback",
    icon: Lock,
    label: "Through your co-parent's eyes",
    prompt:
      "What feedback might my child's other parent give about how I handled this interaction? (Try to imagine it honestly — even if you disagree.)",
    body:
      "He'd probably say I lead with the schedule and forget the human on the other side of it. That I'm quick to point out what's missing and slow to say when he did something well. Honestly, he's not wrong. Next time our daughter comes home with a new song she learned at his house, I want to text him and just say \"thank you\" — nothing else attached.",
  },
];

function DemoBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#8C5A2C] bg-[#FFF6EC] border border-[#F3D9B5] rounded-full px-2.5 py-1">
      <Sparkles size={10} /> Example
    </span>
  );
}

function EntryCard({ entry }) {
  const Icon = entry.icon;
  return (
    <div
      className="card-soft p-6 sm:p-7"
      data-testid={`foundation-demo-entry-${entry.id}`}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-2xl bg-[#F1EEF7] grid place-items-center text-[#3D1A78] shrink-0">
          <Icon size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="font-serif text-lg text-[#1A1330]">
              {entry.label}
            </div>
            <DemoBadge />
          </div>
          <p className="mt-1 text-xs text-[#6E6787] italic">
            {entry.prompt}
          </p>
          <p className="mt-3 text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap">
            {entry.body}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function FoundationStatementDemo() {
  return (
    <div className="min-h-screen bg-[#F8F7FC]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Signed-in parents see this — anonymous visitors see nothing. */}
        <SignedInEscapeHatch
          testid="foundation-demo-signed-in-back"
          label="Back to your dashboard"
        />
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4"
          data-testid="foundation-demo-back-home"
        >
          <ArrowLeft size={12} /> SA CoParents home
        </Link>

        <div className="eyebrow mb-3 text-[#3D1A78]">
          Foundation Statement · Demo
        </div>
        <h1
          className="font-serif text-3xl sm:text-4xl md:text-5xl text-[#1A1330] leading-tight"
          data-testid="foundation-demo-title"
        >
          A Foundation Statement, seen up close.
        </h1>
        <p
          className="text-[#4B4567] mt-4 max-w-2xl leading-relaxed"
          data-testid="foundation-demo-intro"
        >
          Four short reflections — always private to you — that hold the whole
          app together. This is a composite example: none of the words below
          come from a real parent. Yours will be your own.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3 text-xs text-[#4B4567]">
          <span className="inline-flex items-center gap-1.5">
            <Lock size={12} className="text-[#3D1A78]" />
            Private — never shared with your co-parent
          </span>
          <span className="text-[#D8D3E8]">·</span>
          <span>Takes about 12 minutes</span>
          <span className="text-[#D8D3E8]">·</span>
          <span>Editable anytime</span>
        </div>

        <div className="mt-8 space-y-4" data-testid="foundation-demo-entries">
          {DEMO_ENTRIES.map((e) => (
            <EntryCard key={e.id} entry={e} />
          ))}
        </div>

        <div
          className="mt-10 card-soft p-6 sm:p-8 bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white"
          data-testid="foundation-demo-cta"
        >
          <div className="flex items-start gap-4">
            <div className="w-11 h-11 rounded-2xl bg-white/20 grid place-items-center shrink-0">
              <PencilLine size={20} strokeWidth={2.2} />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-2xl sm:text-3xl leading-tight">
                Write your own — quietly, at your pace.
              </h2>
              <p className="text-sm text-white/85 mt-2 max-w-xl leading-relaxed">
                Nobody else sees this. Save each reflection as you go — come
                back tomorrow if today felt like too much. It becomes the
                private anchor your other assessments build from.
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <Link
                  to="/reflection"
                  className="inline-flex items-center gap-2 rounded-full bg-white text-[#3D1A78] px-5 py-2.5 text-sm font-semibold shadow-sm hover:bg-[#F5F1FB] transition-all"
                  data-testid="foundation-demo-start-cta"
                >
                  Start my Foundation Statement
                  <ArrowRight size={14} />
                </Link>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 rounded-full border border-white/40 text-white px-5 py-2.5 text-sm font-semibold hover:bg-white/10 transition-all"
                  data-testid="foundation-demo-dashboard-cta"
                >
                  Explore the dashboard first
                </Link>
              </div>
            </div>
          </div>
        </div>

        <p className="text-[0.6875rem] text-[#6E6787] mt-8 text-center">
          Example content — not a real parent's words. SA CoParents ·
          sacoparentsapp.online
        </p>
      </div>
    </div>
  );
}
