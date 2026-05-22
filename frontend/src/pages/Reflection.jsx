import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Lock,
  Wind,
  Check,
  ArrowLeft,
  Loader2,
  Heart,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import SafetyAlert from "../components/SafetyAlert";
import BreathingExercise from "../components/BreathingExercise";
import { api } from "../lib/api";
import { logError } from "../lib/logger";
import { detectSafetyConcern } from "../lib/safety";

/**
 * Personal Reflection — a private journaling space with calming breathing
 * exercises. Entries are private to the user and feed (optionally) into the
 * AI-generated Mediation Summary as additional context.
 */
const PROMPTS = [
  {
    id: "child_lens",
    label: "Through your child's eyes",
    placeholder:
      "If your child described the last week of co-parenting to a teacher, what would they say?",
    icon: Heart,
  },
  {
    id: "own_part",
    label: "Your own part",
    placeholder:
      "Without blaming anyone, what's one thing you contributed to the difficulty? (No one else will see this.)",
    icon: Sparkles,
  },
  {
    id: "best_outcome",
    label: "Your best-case outcome",
    placeholder:
      "Six months from now, what does a calmer week of co-parenting look like for everyone — including your co-parent?",
    icon: Wind,
  },
  {
    id: "release",
    label: "What you'd like to set down",
    placeholder:
      "What feeling, story, or hope are you carrying that you'd like to release before mediation?",
    icon: Lock,
  },
];

export default function Reflection() {
  const [entries, setEntries] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setEntries((r.data?.reflection) || {});
      })
      .catch((err) => logError("Failed to load reflection:", err))
      .finally(() => setLoading(false));
  }, []);

  const updateEntry = (id, val) =>
    setEntries((prev) => ({ ...prev, [id]: val }));

  // Run safety detection over all entries
  const safetyLevel = useMemo(() => {
    const combined = Object.values(entries || {}).filter(Boolean).join(" \n ");
    return detectSafetyConcern(combined);
  }, [entries]);
  const [safetyDismissed, setSafetyDismissed] = useState(false);

  const hasContent = Object.values(entries || {}).some(
    (v) => (v || "").trim().length > 0,
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/reflection", entries);
      setSavedAt(new Date());
      toast.success("Reflection saved privately.");
    } catch (err) {
      logError("Save reflection failed:", err);
      toast.error("Couldn't save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <div className="fade-up max-w-3xl mx-auto" data-testid="reflection-page">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-[#5C7A6A] hover:text-[#849D8E] mb-5"
          data-testid="reflection-back-link"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </Link>

        <div className="eyebrow mb-3">Personal Reflection</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#2A3631] leading-tight">
          A quieter conversation with yourself.
        </h1>
        <p className="text-[15px] text-[#5C6B64] mt-4 leading-relaxed max-w-2xl">
          Before mediation, take ten minutes to listen to your own quieter voice.
          Everything here stays private to you — nothing is ever shared with anyone
          unless you choose to.
        </p>

        <div className="mt-3 flex items-center gap-2 text-[12px] text-[#8A9A92]">
          <Lock size={12} className="text-[#849D8E]" />
          <span>End-to-end private. Only you can read this. <Link to="/delete-account" className="underline hover:text-[#5C6B64]">Delete anytime</Link>.</span>
        </div>

        {/* Breathing exercise card */}
        <div className="mt-8">
          <BreathingExercise cycles={4} />
        </div>

        {/* Safety guardrail */}
        {safetyLevel && !safetyDismissed && (
          <SafetyAlert
            level={safetyLevel}
            onDismiss={() => setSafetyDismissed(true)}
          />
        )}

        {/* Journal prompts */}
        <div className="mt-10">
          <div className="eyebrow mb-4">Prompts</div>
          {loading ? (
            <div className="text-sm text-[#8A9A92]">Loading…</div>
          ) : (
            <div className="space-y-4">
              {PROMPTS.map((p) => (
                <PromptCard
                  key={p.id}
                  prompt={p}
                  value={entries[p.id] || ""}
                  onChange={(v) => updateEntry(p.id, v)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Save bar */}
        <div className="sticky bottom-4 mt-10">
          <div className="card-soft p-4 sm:p-5 flex items-center justify-between gap-4">
            <div className="text-[13px] text-[#5C6B64] flex items-center gap-2 min-w-0">
              {savedAt ? (
                <>
                  <Check size={14} className="text-[#849D8E] shrink-0" />
                  <span className="truncate">
                    Saved {savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </>
              ) : hasContent ? (
                <span className="italic text-[#8A9A92]">Unsaved changes</span>
              ) : (
                <span className="text-[#8A9A92]">Your words stay with you.</span>
              )}
            </div>
            <button
              onClick={handleSave}
              disabled={saving || !hasContent}
              className="btn-sage inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="reflection-save-button"
            >
              {saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Saving…
                </>
              ) : (
                "Save reflection"
              )}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function PromptCard({ prompt, value, onChange }) {
  const { id, label, placeholder, icon: Icon } = prompt;
  return (
    <div className="card-soft p-5 sm:p-6" data-testid={`reflection-prompt-${id}`}>
      <div className="flex items-start gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center shrink-0">
          <Icon size={16} />
        </div>
        <div className="font-serif text-lg sm:text-xl text-[#2A3631] leading-snug">
          {label}
        </div>
      </div>
      <textarea
        rows={4}
        className="input-soft resize-none"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={`reflection-textarea-${id}`}
      />
    </div>
  );
}
