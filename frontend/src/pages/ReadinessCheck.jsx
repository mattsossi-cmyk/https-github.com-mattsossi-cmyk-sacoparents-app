import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";

const QUESTIONS = [
  { id: "listen", text: "I can listen without interrupting." },
  { id: "past", text: "I can discuss issues without raising past relationship pain." },
  { id: "future", text: "I am willing to focus on future solutions." },
  { id: "separate", text: "I can separate parenting from personal hurt." },
  { id: "calm", text: "I have strategies to stay calm under pressure." },
  { id: "respect", text: "I can speak respectfully even when I disagree." },
];

const SCALE = [
  { v: 1, label: "Not yet" },
  { v: 2, label: "Sometimes" },
  { v: 3, label: "Often" },
  { v: 4, label: "Usually" },
  { v: 5, label: "Yes, consistently" },
];

const READINESS_PREPARED_THRESHOLD = 75;
const READINESS_MODERATE_THRESHOLD = 50;
const SCALE_MAX = 5;

const READINESS_BADGES = {
  prepared: { label: "Prepared for Mediation", color: "#849D8E" },
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
      .catch((err) => console.error("Failed to load prep:", err));
  }, []);

  const { total, pct, badge } = useMemo(() => {
    const vals = QUESTIONS.map((q) => answers[q.id] || 0);
    const t = vals.reduce((a, b) => a + b, 0);
    const max = QUESTIONS.length * SCALE_MAX;
    const p = Math.round((t / max) * 100);
    return { total: t, pct: p, badge: scoreToLabel(p) };
  }, [answers]);

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/readiness", { answers });
      toast.success("Readiness saved.");
      navigate("/summary");
    } catch (err) {
      console.error("Save readiness failed:", err);
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
        title="How prepared do you feel — honestly?"
        description="There is no wrong answer. This score is for you, not against you."
        completed={completed}
        saving={saving}
        onNext={onNext}
        nextLabel="Generate my summary"
      >
        <div className="space-y-6">
          {QUESTIONS.map((q) => (
            <div key={q.id}>
              <div className="text-[#2A3631] mb-2">{q.text}</div>
              <div className="grid grid-cols-5 gap-2">
                {SCALE.map((s) => {
                  const isOn = answers[q.id] === s.v;
                  return (
                    <button
                      key={s.v}
                      type="button"
                      onClick={() => setAnswers({ ...answers, [q.id]: s.v })}
                      data-testid={`readiness-${q.id}-${s.v}`}
                      className={`rounded-xl px-2 py-2 text-xs sm:text-sm transition-all ${
                        isOn
                          ? "bg-[#849D8E] text-white"
                          : "bg-[#F5F3E9] text-[#5C6B64] hover:bg-[#E8ECE9]"
                      }`}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          <div
            className="mt-8 rounded-2xl p-6 border"
            style={{ background: `${badge.color}14`, borderColor: `${badge.color}40` }}
            data-testid="readiness-result-card"
          >
            <div className="eyebrow mb-1">Your current readiness</div>
            <div className="flex items-end justify-between">
              <div className="font-serif text-3xl" style={{ color: badge.color }}>
                {badge.label}
              </div>
              <div className="text-sm text-[#5C6B64]">
                {total} / {QUESTIONS.length * SCALE_MAX} · {pct}%
              </div>
            </div>
            <p className="text-sm text-[#5C6B64] mt-3">{readinessAdvice(pct)}</p>
          </div>
        </div>
      </WizardLayout>
    </AppShell>
  );
}
