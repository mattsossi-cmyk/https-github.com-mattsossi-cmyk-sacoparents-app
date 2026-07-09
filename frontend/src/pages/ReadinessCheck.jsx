import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import WatchFirstVideo from "../components/WatchFirstVideo";
import SectionCoaching from "../components/SectionCoaching";

// 1-5 agreement scale (used for Sections A–C and E)
const AGREE_SCALE = [
  { v: 1, label: "Strongly disagree" },
  { v: 2, label: "Disagree" },
  { v: 3, label: "Neutral" },
  { v: 4, label: "Agree" },
  { v: 5, label: "Strongly agree" },
];

// Frequency scale (used for Section D — Conflict).
// Reverse-scored: "Never" = 5 (best), "Very often" = 1 (most concerning).
const FREQ_SCALE = [
  { v: 5, label: "Never" },
  { v: 4, label: "Rarely" },
  { v: 3, label: "Sometimes" },
  { v: 2, label: "Often" },
  { v: 1, label: "Very often" },
];

const SECTIONS = [
  {
    id: "child_centered",
    title: "Section B — Child-Centeredness",
    description: "Where your child sits in the picture.",
    scale: AGREE_SCALE,
    questions: [
      { id: "child_centered_needs", text: "I place my child's needs above my conflict with the other parent." },
      { id: "child_centered_love", text: "My child feels free to love both parents." },
      { id: "child_centered_encourage", text: "I encourage a positive relationship between my child and the other parent." },
      { id: "child_centered_court", text: "I avoid discussing court issues with my child." },
      { id: "child_centered_protect", text: "I protect my child from adult conflict." },
    ],
  },
  {
    id: "coparent_capacity",
    title: "Section C — Co-Parenting Capacity",
    description: "How you work together on the parenting itself.",
    scale: AGREE_SCALE,
    questions: [
      { id: "coparent_communicate", text: "I can communicate respectfully with the other parent." },
      { id: "coparent_decisions", text: "I can make decisions jointly when necessary." },
      { id: "coparent_compromise", text: "I am willing to compromise for the benefit of our child." },
      { id: "coparent_separate_issues", text: "I can separate parenting issues from relationship issues." },
      { id: "coparent_follow_agreements", text: "I follow existing parenting agreements." },
    ],
  },
  {
    id: "conflict",
    title: "Section D — Conflict Assessment",
    description: "In the last 6 months, how often have you…",
    scale: FREQ_SCALE,
    questions: [
      { id: "conflict_argued_in_front", text: "Argued with the other parent in front of the child?" },
      { id: "conflict_hostile_msgs", text: "Sent hostile text messages or emails?" },
      { id: "conflict_prevented_contact", text: "Prevented contact between the child and the other parent?" },
      { id: "conflict_involved_child", text: "Involved the child in disputes?" },
      { id: "conflict_called_authorities", text: "Contacted police, courts, or agencies regarding disputes?" },
    ],
  },
  {
    id: "self_awareness",
    title: "Section E — Self-Awareness & Emotional Regulation",
    description: "How you hold yourself in moments of pressure.",
    scale: AGREE_SCALE,
    questions: [
      { id: "self_stress", text: "I manage stress effectively." },
      { id: "self_emotions", text: "I am able to regulate my emotions during disagreements." },
      { id: "self_listen", text: "I can listen to differing viewpoints." },
      { id: "self_open_help", text: "I am open to counselling or therapy if recommended." },
    ],
  },
  {
    id: "mediation_readiness",
    title: "Section F — Mediation Readiness",
    description: "Tuning into how prepared you feel for the mediation room itself.",
    scale: AGREE_SCALE,
    questions: [
      { id: "listen", text: "I can listen without interrupting." },
      { id: "past", text: "I can discuss issues without raising past relationship pain." },
      { id: "future", text: "I am willing to focus on future solutions." },
      { id: "separate", text: "I can separate parenting from personal hurt." },
      { id: "calm", text: "I have strategies to stay calm under pressure." },
      { id: "respect", text: "I can speak respectfully even when I disagree." },
    ],
  },
];

// Flatten for scoring / saving
const ALL_QUESTIONS = SECTIONS.flatMap((s) => s.questions);
const SCALE_MAX = 5;
const TOTAL_QUESTIONS = ALL_QUESTIONS.length;
const TOTAL_MAX = TOTAL_QUESTIONS * SCALE_MAX;

const READINESS_PREPARED_THRESHOLD = 75;
const READINESS_MODERATE_THRESHOLD = 50;

const READINESS_BADGES = {
  prepared: { label: "Prepared for Mediation", color: "#3D1A78" },
  moderate: { label: "Moderately Ready", color: "#D6A374" },
  needs_support: { label: "Needs Support", color: "#C28771" },
};

function scoreToLabel(pct) {
  if (pct >= READINESS_PREPARED_THRESHOLD) return READINESS_BADGES.prepared;
  if (pct >= READINESS_MODERATE_THRESHOLD) return READINESS_BADGES.moderate;
  return READINESS_BADGES.needs_support;
}

function readinessAdvice(pct) {
  if (pct >= READINESS_PREPARED_THRESHOLD) {
    return "You're in a strong place. Carry this calm into the room.";
  }
  if (pct >= READINESS_MODERATE_THRESHOLD) {
    return "You're getting there. Consider one more reflection or a coaching session before mediation.";
  }
  return "Consider individual therapy or coaching before mediation. Preparation here is still valuable.";
}

export default function ReadinessCheck() {
  const navigate = useNavigate();
  const [completed, setCompleted] = useState({});
  const [answers, setAnswers] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setCompleted(r.data?.completed || {});
        if (r.data?.readiness?.answers) setAnswers(r.data.readiness.answers);
      })
      .catch((err) => logError("Failed to load prep:", err));
    // Mount-only fetch. `api`, setters, logError are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { total, pct, badge, answered } = useMemo(() => {
    const vals = ALL_QUESTIONS.map((q) => answers[q.id] || 0);
    const t = vals.reduce((a, b) => a + b, 0);
    const a = vals.filter((v) => v > 0).length;
    const p = Math.round((t / TOTAL_MAX) * 100);
    return { total: t, pct: p, badge: scoreToLabel(p), answered: a };
  }, [answers]);

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/readiness", { answers });
      toast.success("Readiness saved.");
      navigate("/summary");
    } catch (err) {
      logError("Save readiness failed:", err);
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <WizardLayout
        currentKey="readiness"
        eyebrow="Step 5 of 5"
        title="Let's assess your situation — honestly."
        description="Five sections, about 5 minutes. There are no wrong answers; this score is for you, not against you."
        completed={completed}
        saving={saving}
        onNext={onNext}
        nextLabel="Generate my summary"
      >
        <div className="space-y-10" data-testid="readiness-sections">
          <WatchFirstVideo
            videoSrc="/videos/readiness-reflection.mp4"
            subtitle="Prepare for Mediation — watch before you begin"
            testid="readiness-watch"
          />
          {SECTIONS.map((section, sIdx) => (
            <section
              key={section.id}
              className="space-y-5"
              data-testid={`readiness-section-${section.id}`}
            >
              <div className="border-l-4 border-[#3D1A78] pl-4">
                <div className="eyebrow text-[#3D1A78]">
                  Part {sIdx + 1} of {SECTIONS.length}
                </div>
                <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1">
                  {section.title}
                </h3>
                <p className="text-sm text-[#4B4567] mt-1">{section.description}</p>
              </div>

              <div className="space-y-5">
                {section.questions.map((q) => (
                  <div key={q.id}>
                    <div className="text-[15px] text-[#1A1330] mb-2 leading-relaxed">
                      {q.text}
                    </div>
                    <div className="grid grid-cols-5 gap-2">
                      {section.scale.map((s) => {
                        const isOn = answers[q.id] === s.v;
                        return (
                          <button
                            key={s.v}
                            type="button"
                            onClick={() =>
                              setAnswers({ ...answers, [q.id]: s.v })
                            }
                            data-testid={`readiness-${q.id}-${s.v}`}
                            className={`rounded-xl px-2 py-2.5 text-[11px] sm:text-xs leading-tight transition-all min-h-[60px] flex items-center justify-center text-center ${
                              isOn
                                ? "bg-[#3D1A78] text-white shadow-sm"
                                : "bg-[#EFE9F9] text-[#4B4567] hover:bg-[#E5E0EE]"
                            }`}
                          >
                            {s.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}

          {/* Sticky-ish result card at the bottom */}
          <div
            className="mt-8 rounded-2xl p-6 border"
            style={{ background: `${badge.color}14`, borderColor: `${badge.color}40` }}
            data-testid="readiness-result-card"
          >
            <div className="eyebrow mb-1">Your current readiness</div>
            <div className="flex items-end justify-between flex-wrap gap-2">
              <div className="font-serif text-3xl" style={{ color: badge.color }}>
                {badge.label}
              </div>
              <div className="text-sm text-[#4B4567]">
                {answered} / {TOTAL_QUESTIONS} answered · {total} / {TOTAL_MAX} · {pct}%
              </div>
            </div>
            <p className="text-sm text-[#4B4567] mt-3">{readinessAdvice(pct)}</p>
            {answered < TOTAL_QUESTIONS && (
              <p
                className="text-xs text-[#857E9C] mt-2"
                data-testid="readiness-incomplete-hint"
              >
                Answer the remaining {TOTAL_QUESTIONS - answered} for a more accurate
                picture.
              </p>
            )}
          </div>

          <SectionCoaching
            section="readiness"
            ready={answered === TOTAL_QUESTIONS}
            data={{
              score_total: total,
              max_score: TOTAL_MAX,
              pct,
              label: badge.label,
              answers,
              section_averages: SECTIONS.map((s) => ({
                key: s.key,
                title: s.title,
                avg:
                  s.questions.reduce(
                    (acc, q) => acc + (Number(answers[q.id]) || 0),
                    0,
                  ) / s.questions.length,
              })),
            }}
          />
        </div>
      </WizardLayout>
    </AppShell>
  );
}
