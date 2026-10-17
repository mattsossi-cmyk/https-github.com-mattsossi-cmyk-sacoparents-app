/**
 * CommunicationReflection.jsx — the private 12-question communication
 * reflection that feeds the Communication Alignment Report.
 *
 * Founder spec 2026-03-04:
 *   - Neutral first-person stems only (never adjudicative).
 *   - One question per screen with a simple progress bar.
 *   - Auto-save via `PUT /communication-reflection` on each answer change
 *     (debounced 800ms).
 *   - On completion, route to `/communication/alignment` where the
 *     alignment report is generated.
 *   - Any `intake_choice === "unsafe"` from `/communication` should have
 *     already re-routed to `/safety`; this page never asks about safety.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Loader2,
  MessageCircle,
} from "lucide-react";

import AppShell from "../components/AppShell";
import BackToDashboardLink from "../components/BackToDashboardLink";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const STORAGE_KEY = "sacoparents.communication.choice";

const LIKERT_TONE = (v, selected) =>
  selected
    ? "bg-[#1E6FA8] text-white border-[#1E6FA8] shadow-md"
    : "bg-white border-[#D6CFE8] text-[#1A1330] hover:border-[#1E6FA8]";

function Likert({ id, labels, value, onChange }) {
  return (
    <div className="grid grid-cols-5 gap-2" data-testid={`comm-likert-${id}`}>
      {labels.map((label, idx) => {
        const v = idx + 1;
        const selected = value === v;
        return (
          <button
            key={v}
            type="button"
            onClick={() => onChange(v)}
            data-testid={`comm-${id}-opt-${v}`}
            data-selected={selected}
            className={`min-h-[64px] rounded-2xl border px-2 py-3 flex flex-col items-center justify-center transition-all active:scale-95 ${LIKERT_TONE(v, selected)}`}
          >
            <span className="text-lg font-bold leading-none">{v}</span>
            <span className={`text-[0.625rem] mt-1 leading-tight text-center ${selected ? "text-white/85" : "text-[#4B4567]"}`}>
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function CommunicationReflection() {
  const navigate = useNavigate();
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [notes, setNotes] = useState({});
  const [pending, setPending] = useState({});
  const [savedAt, setSavedAt] = useState(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [idx, setIdx] = useState(0);
  const advanceTimer = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const [schemaRes, mineRes] = await Promise.all([
          api.get("/communication-reflection/schema"),
          api.get("/communication-reflection/mine").catch(() => null),
        ]);
        setSchema(schemaRes.data);
        setAnswers(mineRes?.data?.answers || {});
        setNotes(mineRes?.data?.notes || {});
      } catch (err) {
        logError("comm-reflection load", err);
        toast.error("Could not load the reflection.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const intakeChoice = useMemo(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || null;
    } catch {
      return null;
    }
  }, []);

  const flushSave = useCallback(
    async (nextAnswers, nextNotes) => {
      setSaving(true);
      try {
        await api.put("/communication-reflection", {
          answers: nextAnswers,
          notes: nextNotes,
          intake_choice: intakeChoice,
        });
        setSavedAt(new Date());
      } catch (err) {
        logError("comm-reflection save", err);
        toast.error("Could not save your reflection right now.");
      } finally {
        setSaving(false);
      }
    },
    [intakeChoice],
  );

  // Debounced auto-save — 800ms after the last change.
  useEffect(() => {
    if (!Object.keys(pending).length) return;
    const t = setTimeout(() => {
      const send = { ...answers };
      setPending({});
      flushSave(send, notes);
    }, 800);
    return () => clearTimeout(t);
  }, [pending, answers, notes, flushSave]);

  if (loading || !schema) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin inline" /> Loading your reflection…
        </div>
      </AppShell>
    );
  }

  const questions = schema.questions || [];
  const total = questions.length;
  const safeIdx = Math.min(idx, total - 1);
  const q = questions[safeIdx];
  const pct = Math.round(((safeIdx + 1) / total) * 100);
  const answered = questions.filter((qq) => typeof answers[qq.id] === "number").length;
  const isLast = safeIdx === total - 1;

  const setAnswer = (qid, value) => {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
    setPending((prev) => ({ ...prev, [qid]: value }));
    // Auto-advance for likert answers
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
    advanceTimer.current = setTimeout(() => {
      if (safeIdx < total - 1) {
        setIdx(safeIdx + 1);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }, 350);
  };

  const submit = async () => {
    setCompleting(true);
    try {
      // Final flush + commit
      await flushSave(answers, notes);
      toast.success("Your reflection is saved.");
      navigate("/communication/alignment");
    } catch (err) {
      logError("comm-reflection complete", err);
      toast.error("Could not complete the reflection.");
    } finally {
      setCompleting(false);
    }
  };

  return (
    <AppShell>
      <div
        className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10"
        data-testid="comm-reflection-root"
      >
        <BackToDashboardLink
          className="mb-3"
          testId="comm-reflection-back-dashboard"
        />
        <Link
          to="/communication"
          className="inline-flex items-center gap-2 text-sm text-[#1E6FA8] hover:text-[#0E4C7A] mb-4"
          data-testid="comm-reflection-back"
        >
          <ArrowLeft size={14} /> Communication pathway
        </Link>

        <div className="flex items-start gap-3 mb-4">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6] text-white grid place-items-center shrink-0">
            <MessageCircle size={20} strokeWidth={2.2} />
          </div>
          <div>
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#1E6FA8]">
              Private communication reflection
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1">
              How I show up when I communicate
            </h1>
            <p className="text-sm text-[#4B4567] mt-2 max-w-xl leading-relaxed">
              12 short questions about your own habits — never about your
              co-parent&rsquo;s. Your answers stay private until you choose to
              share.
            </p>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-[#4B4567] mb-2">
            <div data-testid="comm-reflection-progress-label">
              Question {safeIdx + 1} of {total} · {answered} answered
            </div>
            <div className="flex items-center gap-3">
              {saving && (
                <span className="inline-flex items-center gap-1 text-[#1E6FA8]">
                  <Loader2 size={12} className="animate-spin" /> Saving…
                </span>
              )}
              {!saving && savedAt && (
                <span className="inline-flex items-center gap-1 text-[#1E7A55]">
                  <CheckCircle2 size={12} /> Saved
                </span>
              )}
            </div>
          </div>
          <div className="h-2 w-full bg-[#E5F0F8] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#1E6FA8] transition-all"
              style={{ width: `${pct}%` }}
              data-testid="comm-reflection-progress-bar"
            />
          </div>
        </div>

        {/* Current question card */}
        <div
          key={q.id}
          className="bg-white rounded-3xl border border-[#D8E7F3] p-6 sm:p-8 shadow-sm animate-[fadeUp_240ms_ease-out]"
          data-testid={`comm-reflection-q-${q.id}`}
        >
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#1E6FA8] mb-2">
            {(schema.dimensions?.[q.dimension]?.label) || q.dimension}
          </div>
          <label className="block font-serif text-lg sm:text-xl text-[#1A1330] leading-snug mb-6">
            {q.stem}
          </label>
          <Likert
            id={q.id}
            labels={schema.likert_labels || []}
            value={answers[q.id]}
            onChange={(v) => setAnswer(q.id, v)}
          />
          <textarea
            data-testid={`comm-reflection-note-${q.id}`}
            rows={2}
            placeholder="Optional context (kept private to you)…"
            value={notes[q.id] || ""}
            onChange={(e) => {
              const nv = e.target.value;
              const nextNotes = { ...notes, [q.id]: nv };
              setNotes(nextNotes);
              setPending((prev) => ({ ...prev, [`__note_${q.id}`]: nv }));
            }}
            className="mt-5 w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#1E6FA8]/30"
          />
        </div>

        {/* Nav */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => {
              if (safeIdx > 0) {
                setIdx(safeIdx - 1);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }
            }}
            disabled={safeIdx === 0}
            data-testid="comm-reflection-prev"
            className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm border border-[#D6CFE8] text-[#1A1330] bg-white disabled:opacity-40 hover:border-[#1E6FA8]"
          >
            <ArrowLeft size={14} /> Previous
          </button>

          {isLast ? (
            <button
              type="button"
              onClick={submit}
              disabled={completing}
              data-testid="comm-reflection-complete"
              className="inline-flex items-center gap-2 px-5 py-2.5 min-h-[44px] rounded-full text-sm bg-[#1E6FA8] text-white hover:brightness-110 disabled:opacity-60"
            >
              {completing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              See my Alignment Report
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setIdx(safeIdx + 1);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              data-testid="comm-reflection-next"
              className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm bg-[#1E6FA8] text-white hover:brightness-110"
            >
              Next <ArrowRight size={14} />
            </button>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link
            to="/dashboard"
            className="text-xs text-[#4B4567] underline"
            data-testid="comm-reflection-back-dashboard"
          >
            Save &amp; come back later
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
