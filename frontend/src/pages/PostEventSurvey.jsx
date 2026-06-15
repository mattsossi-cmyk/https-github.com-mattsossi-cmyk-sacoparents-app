import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, CheckCircle2, Heart } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

/**
 * Public, token-based "How was mediation?" post-event survey.
 * No login required — the email link is the auth.
 */
function Eyebrow({ children }) {
  return (
    <div className="text-[11px] tracking-[0.22em] uppercase font-bold text-[#3D1A78] mb-2">
      {children}
    </div>
  );
}

function QuestionWrapper({ index, total, question, children }) {
  return (
    <div className="card-soft p-6" data-testid={`survey-q-${question.id}`}>
      <div className="flex items-baseline justify-between mb-3">
        <Eyebrow>
          Question {index + 1} of {total}
        </Eyebrow>
        {question.optional && (
          <span className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C]">
            Optional
          </span>
        )}
      </div>
      <h3 className="font-serif text-lg sm:text-xl text-[#1A1330] mb-4 leading-snug">
        {question.label}
      </h3>
      {children}
    </div>
  );
}

function SingleChoice({ question, value, otherText, onChange, onOtherChange }) {
  return (
    <div className="space-y-2">
      {question.options.map((opt) => {
        const selected = value === opt;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            data-testid={`survey-q-${question.id}-opt-${opt
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")}`}
            className={`w-full text-left px-4 py-3 rounded-2xl border transition-all ${
              selected
                ? "border-[#3D1A78] bg-[#EFE9F9] text-[#1A1330] shadow-sm"
                : "border-[#E5E0EE] bg-white hover:border-[#3D1A78]/50 text-[#4B4567]"
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`w-4 h-4 rounded-full border-2 ${
                  selected
                    ? "border-[#3D1A78] bg-[#3D1A78]"
                    : "border-[#857E9C]"
                }`}
              />
              <span className="text-sm">{opt}</span>
            </div>
          </button>
        );
      })}
      {question.allow_other && value === "Other" && (
        <input
          type="text"
          value={otherText || ""}
          onChange={(e) => onOtherChange(e.target.value)}
          placeholder="Tell us more…"
          data-testid={`survey-q-${question.id}-other-input`}
          className="w-full mt-2 px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78]"
        />
      )}
    </div>
  );
}

function LongText({ question, value, onChange }) {
  return (
    <textarea
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      rows={4}
      placeholder="Type your answer…"
      data-testid={`survey-q-${question.id}-textarea`}
      className="w-full px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78] resize-y"
    />
  );
}

function Scale010({ question, value, onChange }) {
  return (
    <div>
      <div className="grid grid-cols-11 gap-1.5">
        {Array.from({ length: 11 }, (_, i) => {
          const selected = value === i;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onChange(i)}
              data-testid={`survey-q-${question.id}-${i}`}
              className={`h-11 rounded-xl text-sm font-semibold transition-all ${
                selected
                  ? "bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white shadow-md"
                  : "bg-[#F0EDF7] text-[#4B4567] hover:bg-[#E5E0EE]"
              }`}
            >
              {i}
            </button>
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] uppercase tracking-[0.15em] text-[#857E9C] mt-2">
        <span>{question.low_label}</span>
        <span>{question.high_label}</span>
      </div>
    </div>
  );
}

export default function PostEventSurvey() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [survey, setSurvey] = useState(null);
  const [answers, setAnswers] = useState({});
  const [otherTexts, setOtherTexts] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .get(`/surveys/post-event/by-token/${token}`)
      .then((res) => {
        if (!alive) return;
        setSurvey(res.data);
        if (res.data.status === "responded") setDone(true);
      })
      .catch((e) => {
        logError("survey load failed", e);
        setErr(e?.response?.data?.detail || "This survey link is no longer valid.");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [token]);

  const setAnswer = (qid, val) => setAnswers((p) => ({ ...p, [qid]: val }));
  const setOther = (qid, text) => setOtherTexts((p) => ({ ...p, [qid]: text }));

  const handleSubmit = async () => {
    if (!survey) return;
    // Validate required questions (everything not flagged `optional`).
    const missing = survey.questions
      .filter((q) => !q.optional)
      .find((q) => {
        const v = answers[q.id];
        if (q.type === "scale_0_10") return typeof v !== "number";
        if (q.type === "long_text") return !v || !String(v).trim();
        return !v;
      });
    if (missing) {
      setErr(`Please answer: "${missing.label}"`);
      const el = document.querySelector(`[data-testid="survey-q-${missing.id}"]`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    setErr(null);
    setSubmitting(true);
    // Merge in any free-text "Other" details.
    const finalResponses = { ...answers };
    Object.entries(otherTexts).forEach(([qid, txt]) => {
      const t = (txt || "").trim();
      if (t && finalResponses[qid] === "Other") {
        finalResponses[qid] = `Other: ${t}`;
      }
    });
    try {
      await api.post(`/surveys/post-event/submit/${token}`, { responses: finalResponses });
      setDone(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setErr(e?.response?.data?.detail || "Could not submit your survey. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4">
        <div className="card-soft p-8 text-center">
          <Loader2 className="animate-spin w-6 h-6 mx-auto text-[#3D1A78]" />
          <p className="text-sm text-[#4B4567] mt-3">Loading your survey…</p>
        </div>
      </div>
    );
  }

  if (err && !survey) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4">
        <div
          className="card-soft p-8 text-center max-w-md"
          data-testid="survey-invalid"
        >
          <h1 className="font-serif text-2xl text-[#1A1330] mb-2">Link not valid</h1>
          <p className="text-sm text-[#4B4567]">{err}</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4 py-12">
        <div
          className="card-soft p-10 text-center max-w-lg fade-up"
          data-testid="survey-thank-you"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-lg mb-5">
            <Heart size={28} strokeWidth={2.2} />
          </div>
          <h1 className="font-serif text-3xl text-[#1A1330] mb-3">Thank you</h1>
          <p className="text-sm text-[#4B4567] leading-relaxed mb-6">
            Your feedback helps us make SA CoParenting App better for every parent
            navigating mediation. We read every response.
          </p>
          <div className="text-[11px] tracking-[0.22em] uppercase font-bold text-[#3D1A78] mb-2">
            One step at a time
          </div>
          <p className="text-xs text-[#857E9C]">
            — Matt &amp; the SA CoParenting App team
          </p>
          <a
            href="https://sacoparentsapp.online"
            className="inline-block mt-8 text-xs font-medium text-[#3D1A78] hover:underline"
            data-testid="survey-home-link"
          >
            sacoparentsapp.online →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg">
      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="text-center mb-8">
          <Eyebrow>SA CoParenting App</Eyebrow>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
            How did it go?
          </h1>
          <p className="text-sm text-[#4B4567] mt-3 max-w-md mx-auto">
            {survey.user_name ? `Hi ${survey.user_name} — ` : "Hi — "}
            this 3-minute survey helps us improve the app for other parents preparing
            for mediation. Your answers are confidential.
          </p>
        </div>

        <div className="space-y-5" data-testid="survey-questions">
          {survey.questions.map((q, idx) => (
            <QuestionWrapper
              key={q.id}
              index={idx}
              total={survey.questions.length}
              question={q}
            >
              {q.type === "single" && (
                <SingleChoice
                  question={q}
                  value={answers[q.id]}
                  otherText={otherTexts[q.id]}
                  onChange={(v) => setAnswer(q.id, v)}
                  onOtherChange={(t) => setOther(q.id, t)}
                />
              )}
              {q.type === "long_text" && (
                <LongText
                  question={q}
                  value={answers[q.id]}
                  onChange={(v) => setAnswer(q.id, v)}
                />
              )}
              {q.type === "scale_0_10" && (
                <Scale010
                  question={q}
                  value={answers[q.id]}
                  onChange={(v) => setAnswer(q.id, v)}
                />
              )}
            </QuestionWrapper>
          ))}
        </div>

        {err && (
          <div
            className="mt-5 rounded-2xl bg-[#FCE3DC] text-[#9A3A23] px-4 py-3 text-sm"
            data-testid="survey-error"
          >
            {err}
          </div>
        )}

        <div className="mt-8 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-end">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            data-testid="survey-submit-button"
            className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-60"
          >
            {submitting ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <CheckCircle2 size={16} />
            )}
            Submit my answers
          </button>
        </div>

        <p className="text-[11px] text-[#857E9C] text-center mt-10">
          SA CoParenting App ·{" "}
          <a
            href="https://sacoparentsapp.online"
            className="hover:underline text-[#3D1A78]"
          >
            sacoparentsapp.online
          </a>
        </p>
      </main>
    </div>
  );
}
