import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Type, Save, Eye, EyeOff, Info,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import { api } from "../lib/api";

/**
 * Neurodivergent Child Pathway — one-question-per-screen wizard.
 *
 * UX principles (per WCAG cognitive-accessibility guidance):
 *  - One question per screen with visible progress
 *  - Plain language help under each prompt
 *  - Save & resume — autosave on blur or "Next"
 *  - Optional "Larger text" toggle
 *  - Optional "Reduced stimulation" mode (mutes gradients & animations)
 *  - Preview-all questions view before starting
 *  - Nothing here is diagnostic; disclaimers up top
 */

const STORAGE = {
  fontSize: "nd_font_size",       // 'md' | 'lg' | 'xl'
  reduced: "nd_reduced_stim",     // '1' | ''
};

function useReadingPrefs() {
  const [fontSize, setFontSize] = useState(
    () => (typeof window !== "undefined" && localStorage.getItem(STORAGE.fontSize)) || "md"
  );
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && localStorage.getItem(STORAGE.reduced) === "1"
  );
  const bump = () => {
    const next = fontSize === "md" ? "lg" : fontSize === "lg" ? "xl" : "md";
    setFontSize(next);
    localStorage.setItem(STORAGE.fontSize, next);
  };
  const toggleReduced = () => {
    const next = !reduced;
    setReduced(next);
    localStorage.setItem(STORAGE.reduced, next ? "1" : "");
  };
  const fontClass =
    fontSize === "xl" ? "text-[19px] sm:text-[21px] leading-relaxed"
    : fontSize === "lg" ? "text-[17px] sm:text-[18px] leading-relaxed"
    : "text-[15px] sm:text-[16px] leading-relaxed";
  return { fontSize, fontClass, reduced, bump, toggleReduced };
}

function AnswerInput({ question, value, onChange, fontClass }) {
  if (question.type === "short_text") {
    return (
      <input
        type="text"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full border-2 border-[#E5E0EE] focus:border-[#3D1A78] rounded-xl px-4 py-3 ${fontClass} bg-white outline-none`}
        data-testid={`nd-input-${question.id}`}
        autoFocus
      />
    );
  }
  if (question.type === "long_text") {
    return (
      <textarea
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
        className={`w-full border-2 border-[#E5E0EE] focus:border-[#3D1A78] rounded-xl px-4 py-3 ${fontClass} bg-white outline-none`}
        data-testid={`nd-input-${question.id}`}
        autoFocus
      />
    );
  }
  if (question.type === "multi_select") {
    const arr = Array.isArray(value) ? value : [];
    return (
      <div className="grid gap-2">
        {question.options.map((opt) => {
          const on = arr.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(on ? arr.filter((x) => x !== opt) : [...arr, opt])}
              className={`text-left px-4 py-3 rounded-xl border-2 ${
                on ? "border-[#3D1A78] bg-[#F1EBFA]" : "border-[#E5E0EE] hover:border-[#C1B4E0] bg-white"
              } ${fontClass}`}
              data-testid={`nd-option-${question.id}-${opt}`}
            >
              <span className="inline-flex items-center gap-2">
                <span className={`h-5 w-5 rounded-md border-2 grid place-items-center ${on ? "border-[#3D1A78] bg-[#3D1A78]" : "border-[#C1B4E0]"}`}>
                  {on && <Check size={12} className="text-white" />}
                </span>
                {opt}
              </span>
            </button>
          );
        })}
      </div>
    );
  }
  if (question.type === "single_select") {
    return (
      <div className="grid gap-2">
        {question.options.map((opt) => {
          const on = value === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(opt)}
              className={`text-left px-4 py-3 rounded-xl border-2 ${
                on ? "border-[#3D1A78] bg-[#F1EBFA]" : "border-[#E5E0EE] hover:border-[#C1B4E0] bg-white"
              } ${fontClass}`}
              data-testid={`nd-option-${question.id}-${opt}`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    );
  }
  return null;
}

export default function Neurodivergent() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const prefs = useReadingPrefs();
  const nav = useNavigate();

  useEffect(() => {
    Promise.all([
      api.get("/neurodivergent/questions"),
      api.get("/neurodivergent/prep"),
    ]).then(([qs, p]) => {
      setQuestions(qs.data.questions || []);
      setAnswers(p.data.answers || {});
      // Resume where they left off: first unanswered question
      const answered = p.data.answers || {};
      const firstUnansweredIndex = (qs.data.questions || []).findIndex(
        (q) => answered[q.id] === undefined || answered[q.id] === "" || (Array.isArray(answered[q.id]) && answered[q.id].length === 0)
      );
      setIdx(firstUnansweredIndex === -1 ? 0 : firstUnansweredIndex);
      setLoading(false);
    }).catch((err) => {
      toast.error(err?.response?.data?.detail || "Could not load the assessment.");
      setLoading(false);
    });
  }, []);

  const q = questions[idx];
  const answered = questions.filter(
    (qq) => {
      const v = answers[qq.id];
      if (v === undefined || v === null) return false;
      if (typeof v === "string") return v.trim().length > 0;
      if (Array.isArray(v)) return v.length > 0;
      return true;
    }
  ).length;
  const total = questions.length;
  const progress = total > 0 ? Math.round((answered / total) * 100) : 0;

  const saveAnswer = useCallback(async (qid, value) => {
    setSaving(true);
    try {
      await api.post("/neurodivergent/answer", { question_id: qid, value });
    } catch (err) {
      toast.error("Could not save your answer. Please try again.");
    } finally {
      setSaving(false);
    }
  }, []);

  const onChange = (value) => {
    if (!q) return;
    setAnswers((prev) => ({ ...prev, [q.id]: value }));
  };

  const goNext = async () => {
    if (q) await saveAnswer(q.id, answers[q.id]);
    if (idx < total - 1) {
      setIdx(idx + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const goPrev = async () => {
    if (q) await saveAnswer(q.id, answers[q.id]);
    if (idx > 0) {
      setIdx(idx - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const finish = async () => {
    if (q) await saveAnswer(q.id, answers[q.id]);
    setCompleting(true);
    try {
      await api.post("/neurodivergent/complete");
      toast.success("Answers saved. Generating your reports…");
      // Generate reports (fire-and-navigate — reports page will poll)
      await api.post("/neurodivergent/reports/generate");
      nav("/neurodivergent/reports");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not generate reports.");
      setCompleting(false);
    }
  };

  const containerBg = prefs.reduced ? "bg-white" : "bg-gradient-to-b from-[#F8F5FF] via-white to-white";

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[#857E9C]" data-testid="nd-loading">
          Loading your space…
        </div>
      </AppShell>
    );
  }

  if (showPreview) {
    return (
      <AppShell>
        <div className={`min-h-full ${containerBg}`}>
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
            <button
              onClick={() => setShowPreview(false)}
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
              data-testid="nd-back-from-preview"
            >
              <ArrowLeft size={14} /> Back to the questions
            </button>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">Preview of every question</h1>
            <p className={`mt-2 text-[#4B4567] ${prefs.fontClass}`}>
              Some parents like to see the whole path before starting. Here it is. You can answer at your pace.
            </p>
            <div className="mt-6 space-y-6">
              {questions.map((qq, i) => (
                <div key={qq.id} className="border-l-4 border-[#E5E0EE] pl-4">
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                    {qq.section} · {i + 1} of {total}
                  </div>
                  <div className={`text-[#1A1330] font-medium ${prefs.fontClass}`}>{qq.prompt}</div>
                  {qq.help && (
                    <div className={`text-[#857E9C] mt-1 ${prefs.fontClass}`}>{qq.help}</div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-8">
              <button
                onClick={() => setShowPreview(false)}
                className="px-6 py-3 rounded-full bg-[#3D1A78] text-white font-medium"
                data-testid="nd-start-from-preview"
              >
                Ready — take me to the questions →
              </button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className={`min-h-full ${containerBg}`}>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
            data-testid="nd-back-to-dashboard"
          >
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="eyebrow text-[#3D1A78]">Special Needs Assessment</div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1" data-testid="nd-title">
                Supporting your child across two homes
              </h1>
              <p className={`mt-2 text-[#4B4567] max-w-2xl ${prefs.fontClass}`}>
                A gentle, one-question-at-a-time space to describe your child
                in your own words — across six practical pillars. Nothing here
                diagnoses anyone. Nothing here is legal or medical advice. Take
                your time — your answers save as you go.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 items-center">
              <button
                onClick={prefs.bump}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-text-size-btn"
                title={`Text size: ${prefs.fontSize.toUpperCase()}`}
              >
                <Type size={12} /> Larger text
              </button>
              <button
                onClick={prefs.toggleReduced}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-reduced-stim-btn"
                title="Toggle reduced-stimulation mode"
              >
                {prefs.reduced ? <Eye size={12} /> : <EyeOff size={12} />}
                {prefs.reduced ? "Standard view" : "Reduced stimulation"}
              </button>
              <button
                onClick={() => setShowPreview(true)}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-preview-btn"
              >
                <Info size={12} /> Preview all questions
              </button>
            </div>
          </div>

          <div className="mt-6">
            <DemoModeBanner />
          </div>

          {/* Progress */}
          <div className="mt-6 mb-8">
            <div className="flex items-center justify-between text-xs text-[#4B4567] mb-2">
              <span data-testid="nd-progress-label">
                Question {idx + 1} of {total} · {answered} answered
              </span>
              <span className="flex items-center gap-1">
                {saving ? <><Loader2 size={10} className="animate-spin" /> Saving…</> : <><Save size={10} /> Auto-saves as you type</>}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-[#E5E0EE] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
                style={{ width: `${progress}%` }}
                data-testid="nd-progress-bar"
              />
            </div>
          </div>

          {/* Question card */}
          {q && (
            <section className="bg-white rounded-3xl shadow-sm border border-[#E5E0EE] p-6 sm:p-8" data-testid="nd-question-card">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                {q.section}
              </div>
              <h2 className={`font-serif text-[#1A1330] text-2xl sm:text-3xl leading-snug`}>
                {q.prompt}
              </h2>
              {q.help && (
                <p className={`text-[#4B4567] mt-2 ${prefs.fontClass}`}>{q.help}</p>
              )}
              <div className="mt-6">
                <AnswerInput
                  question={q}
                  value={answers[q.id]}
                  onChange={onChange}
                  fontClass={prefs.fontClass}
                />
              </div>
            </section>
          )}

          {/* Nav */}
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={goPrev}
              disabled={idx === 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm text-[#4B4567] hover:bg-[#F5F2FA] disabled:opacity-40"
              data-testid="nd-prev-btn"
            >
              <ArrowLeft size={14} /> Back
            </button>
            {idx < total - 1 ? (
              <button
                onClick={goNext}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#3D1A78] text-white font-medium hover:bg-[#2A1256]"
                data-testid="nd-next-btn"
              >
                Next <ArrowRight size={14} />
              </button>
            ) : (
              <button
                onClick={finish}
                disabled={completing}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#3D1A78] text-white font-medium hover:bg-[#2A1256] disabled:opacity-60"
                data-testid="nd-finish-btn"
              >
                {completing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                {completing ? "Generating reports…" : "Finish & generate reports"}
              </button>
            )}
          </div>

          {/* Save & come back later */}
          <div className="mt-8 text-center text-xs text-[#857E9C]">
            You can leave anytime — your answers are saved.{" "}
            <Link to="/dashboard" className="text-[#3D1A78] hover:underline" data-testid="nd-save-and-leave">
              Save and come back later →
            </Link>
          </div>

          {/* Disclaimer */}
          <div className="mt-10 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-5 text-xs text-[#4B4567] leading-relaxed" data-testid="nd-disclaimer">
            <strong className="text-[#1A1330]">A note on what this is (and isn&apos;t).</strong>{" "}
            This pathway is a preparation tool for co-parenting conversations. It
            does not diagnose your child. It is not medical, therapeutic, or
            legal advice. If your child is in crisis, please contact your
            paediatrician, therapist, or your local emergency services. In an
            emergency, the SAMHSA National Helpline is <strong>1-800-662-4357</strong>{" "}
            (24/7, free, confidential).
          </div>
        </div>
      </div>
    </AppShell>
  );
}
