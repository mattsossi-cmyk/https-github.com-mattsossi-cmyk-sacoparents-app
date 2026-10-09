/**
 * AlignmentReflection.jsx — Iter191 · free-text reflection form.
 *
 * Six prompts modelled on sacoparentsalign.com's Co-Parenting
 * Agreement: Primary Need / What's Working / Concerns / Desired
 * Improvements / Options / Other Parent's Likely Concerns.
 *
 * Data flow:
 *   * `GET  /alignment-reflection/schema/{subject}` — prompt schema
 *   * `GET  /alignment-reflection/{subject}/mine`  — caller's answers
 *   * `PUT  /alignment-reflection/{subject}`       — save (upsert)
 *
 * Answers auto-save 800ms after the last keystroke per prompt so
 * parents never lose progress mid-thought. Manual Save button lives
 * at the top and bottom for reassurance.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { CheckCircle2, Info, Loader2, Save, MessagesSquare, ArrowLeft } from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


const AUTOSAVE_MS = 800;


function PromptField({ prompt, value, onChange, testidBase }) {
  const [focused, setFocused] = useState(false);
  const len = (value || "").length;
  const max = prompt.max_length || 600;
  return (
    <div
      className="rounded-3xl border-2 border-[#E5E0EE] bg-white p-5 sm:p-6 space-y-3 focus-within:border-[#3D1A78] transition-colors"
      data-testid={`${testidBase}-field`}
    >
      <div>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          {prompt.label}
        </div>
        <h3 className="font-serif text-lg sm:text-xl text-[#1A1330] mt-1 leading-snug">
          {prompt.prompt}
        </h3>
        {prompt.help && (
          <p className="mt-2 text-xs text-[#857E9C] leading-relaxed flex items-start gap-1.5">
            <Info size={12} className="mt-0.5 shrink-0 text-[#857E9C]" />
            <span>{prompt.help}</span>
          </p>
        )}
      </div>
      <textarea
        rows={4}
        value={value || ""}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onChange={(e) => onChange(e.target.value.slice(0, max + 50))}
        placeholder={prompt.placeholder}
        maxLength={max + 50}
        className="w-full rounded-2xl border border-[#D6CFE8] bg-[#FAF8FE] px-4 py-3 text-sm text-[#1A1330] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/25"
        data-testid={`${testidBase}-textarea`}
      />
      <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.14em] font-bold">
        <span
          className="text-[#857E9C]"
          data-testid={`${testidBase}-hint`}
        >
          {focused ? "Ctrl-S also saves" : "Autosaved as you type"}
        </span>
        <span
          className={len > max ? "text-[#AA0033]" : "text-[#857E9C]"}
          data-testid={`${testidBase}-counter`}
        >
          {len} / {max}
        </span>
      </div>
    </div>
  );
}


export default function AlignmentReflection() {
  const params = useParams();
  const subject = params.subject || "co_parenting";
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const [schemaRes, mineRes] = await Promise.all([
          api.get(`/alignment-reflection/schema/${subject}`),
          api.get(`/alignment-reflection/${subject}/mine`).catch(() => null),
        ]);
        setSchema(schemaRes.data);
        setAnswers(mineRes?.data?.answers || {});
        setSavedAt(mineRes?.data?.updated_at || null);
      } catch (err) {
        logError("alignment-reflection load", err);
        toast.error("Could not load the reflection prompts.");
      } finally {
        setLoading(false);
      }
    })();
  }, [subject]);

  const persist = useCallback(async (next) => {
    setSaving(true);
    try {
      const res = await api.put(`/alignment-reflection/${subject}`, {
        answers: next,
      });
      setSavedAt(new Date().toISOString());
      return res.data;
    } catch (err) {
      logError("alignment-reflection save", err);
      toast.error("Could not save right now — try again in a moment.");
      return null;
    } finally {
      setSaving(false);
    }
  }, [subject]);

  const scheduleAutosave = useCallback((next) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      persist(next);
    }, AUTOSAVE_MS);
  }, [persist]);

  const setAnswer = (promptId, value) => {
    const next = { ...answers, [promptId]: value };
    setAnswers(next);
    scheduleAutosave(next);
  };

  const handleManualSave = async () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const res = await persist(answers);
    if (res) {
      toast.success("Saved — safe to close this tab any time.");
    }
  };

  // Ctrl/Cmd-S also saves.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault();
        handleManualSave();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers]);

  if (loading || !schema) {
    return (
      <AppShell>
        <div
          className="max-w-3xl mx-auto p-8 grid place-items-center text-[#857E9C]"
          data-testid="alignment-reflection-loading"
        >
          <Loader2 className="animate-spin" size={20} />
        </div>
      </AppShell>
    );
  }

  const answered = Object.values(answers).filter(
    (v) => (v || "").trim().length > 0,
  ).length;
  const total = (schema.prompts || []).length;

  return (
    <AppShell>
      <div
        className="fade-up max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6"
        data-testid="alignment-reflection-root"
      >
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78]"
        >
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        {/* Hero */}
        <div className="card-soft p-6 sm:p-7 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-[#D4C5F0]/40 pointer-events-none" />
          <div className="relative">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2">
              <MessagesSquare size={12} />
              Alignment reflection · {schema.label}
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-2 leading-tight">
              Six prompts. Your voice. Your child.
            </h1>
            <p className="mt-2 text-sm text-[#4B4567] max-w-2xl leading-relaxed">
              Reflect in your own words. Your answers stay private until
              both you and your co-parent have finished — then a neutral
              Co-Parenting Agreement highlights where you already agree,
              where you differ, and what your child needs next.
            </p>
            <div
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-white/70 backdrop-blur px-3 py-1.5 text-[11px] font-semibold text-[#3D1A78]"
              data-testid="alignment-reflection-progress"
            >
              <CheckCircle2 size={12} />
              {answered} of {total} answered
            </div>
          </div>
        </div>

        {/* Prompt cards — one per prompt, in canonical order. */}
        <div className="space-y-4" data-testid="alignment-reflection-prompts">
          {schema.prompts.map((prompt, i) => (
            <PromptField
              key={prompt.id}
              prompt={prompt}
              value={answers[prompt.id]}
              onChange={(v) => setAnswer(prompt.id, v)}
              testidBase={`alignment-reflection-${prompt.id}`}
            />
          ))}
        </div>

        {/* Save row */}
        <div className="card-soft p-5 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-[#4B4567] max-w-md">
            <strong>Nothing is shared yet.</strong> Your co-parent only sees
            the joint report once both of you have saved. You can edit
            your answers any time before then.
          </div>
          <div className="flex items-center gap-2">
            {savedAt && (
              <span
                className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]"
                data-testid="alignment-reflection-saved-at"
              >
                Saved {new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
            <button
              type="button"
              onClick={handleManualSave}
              disabled={saving}
              data-testid="alignment-reflection-save"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-sm font-semibold hover:bg-[#2B0F60] disabled:opacity-60"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              {saving ? "Saving…" : "Save reflection"}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
