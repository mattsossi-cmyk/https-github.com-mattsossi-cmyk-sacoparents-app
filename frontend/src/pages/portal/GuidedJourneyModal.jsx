import React, { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../lib/api";

/**
 * GuidedJourneyModal — one-question-at-a-time chat wizard for the six
 * Coparenting Journey topics. Coach messages (Claude via Emergent LLM
 * Key) alternate with parent answers. After the final scripted
 * question, the parent can hit "Save & continue" and we hand a
 * structured summary back to the caller via `onSave`.
 *
 * Props:
 *   - topic: 'foundation' | 'safety' | 'coparenting' |
 *            'medical' | 'educational' | 'psychological'
 *   - open, onClose
 *   - safetyFlagged : bool — pipes through to backend for grey-rock voice
 *   - onSave({save_key, category, answers, summary})
 *              save_key & category tell the caller how to store
 *              the answers (foundation_text vs align_record etc.)
 */
const TOPIC_TITLES = {
  foundation: "Foundation Statement — guided",
  safety: "Safety Check — guided",
  coparenting: "Co-parenting Assessment — guided",
  medical: "Medical Needs Assessment — guided",
  educational: "Educational Assessment — guided",
  psychological: "Psychological Assessment — guided",
};

export function GuidedJourneyModal({
  topic,
  open,
  onClose,
  onSave,
  safetyFlagged = false,
}) {
  // Conversation history: array of {role: 'coach'|'parent', text}
  const [history, setHistory] = useState([]);
  // 0-based index of the question the parent has JUST answered.
  // -1 means intro not sent yet.
  const [stepIndex, setStepIndex] = useState(-1);
  const [progress, setProgress] = useState({ step: 0, total: 5 });
  const [isFinal, setIsFinal] = useState(false);
  const [saveKey, setSaveKey] = useState(null);
  const [category, setCategory] = useState(null);
  const [nextQuestion, setNextQuestion] = useState("");
  const [answers, setAnswers] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  // Reset when the modal opens (or topic changes).
  useEffect(() => {
    if (!open) return;
    setHistory([]);
    setStepIndex(-1);
    setProgress({ step: 0, total: 5 });
    setIsFinal(false);
    setSaveKey(null);
    setCategory(null);
    setNextQuestion("");
    setAnswers([]);
    setInput("");
    setError("");
    // fire the intro turn
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.post("/portal/guided-journey/step", {
          topic,
          step_index: -1,
          parent_answer: "",
          safety_flagged: !!safetyFlagged,
        });
        setHistory([
          { role: "coach", text: data.coach_message },
          { role: "coach", text: data.next_question, isQuestion: true },
        ]);
        setStepIndex(0);
        setProgress({ step: data.step_number, total: data.total_steps });
        setIsFinal(!!data.is_final);
        setSaveKey(data.save_key);
        setCategory(data.category || null);
        setNextQuestion(data.next_question || "");
      } catch (e) {
        setError("Coach is warming up — please close and try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, [open, topic, safetyFlagged]);

  // Auto-scroll to bottom on new message.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, loading]);

  const submitAnswer = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || loading || isFinal) return;
    const answeredIndex = stepIndex;
    // Optimistically show parent's answer
    setHistory((h) => [...h, { role: "parent", text: trimmed }]);
    setAnswers((a) => [
      ...a,
      { question: nextQuestion, answer: trimmed },
    ]);
    setInput("");
    setLoading(true);
    try {
      const { data } = await api.post("/portal/guided-journey/step", {
        topic,
        step_index: answeredIndex,
        parent_answer: trimmed,
        safety_flagged: !!safetyFlagged,
      });
      setHistory((h) => [
        ...h,
        { role: "coach", text: data.coach_message },
        ...(data.next_question
          ? [{ role: "coach", text: data.next_question, isQuestion: true }]
          : []),
      ]);
      setProgress({ step: data.step_number, total: data.total_steps });
      setIsFinal(!!data.is_final);
      setNextQuestion(data.next_question || "");
      setStepIndex(answeredIndex + 1);
    } catch (e) {
      setError("Coach is warming up — please try again.");
    } finally {
      setLoading(false);
    }
  }, [
    input,
    loading,
    isFinal,
    stepIndex,
    topic,
    safetyFlagged,
    nextQuestion,
  ]);

  const commitSave = useCallback(() => {
    // Build a plain summary from Q&A pairs.
    const summary = answers
      .map((qa, i) => `Q${i + 1}: ${qa.question}\nA: ${qa.answer}`)
      .join("\n\n");
    onSave({ save_key: saveKey, category, answers, summary });
  }, [answers, saveKey, category, onSave]);

  if (!open) return null;

  const percent = progress.total
    ? Math.round((progress.step / progress.total) * 100)
    : 0;

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 no-print"
      data-testid={`modal-guided-${topic}`}
    >
      <div className="bg-white w-full max-w-sm sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col h-[85vh] sm:h-[85vh]">
        {/* Header */}
        <div className="flex justify-between items-center border-b border-slate-100 p-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span
                className={
                  safetyFlagged
                    ? "bg-slate-900 text-amber-300 text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider"
                    : "bg-purple-100 text-purple-800 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
                }
              >
                {safetyFlagged ? "Grey-rock" : "Guided"}
              </span>
              <span className="text-[10px] text-slate-500">
                Step {progress.step} of {progress.total}
              </span>
            </div>
            <h3 className="font-bold text-slate-800 text-sm mt-0.5 truncate">
              {TOPIC_TITLES[topic] || "Guided Journey"}
            </h3>
          </div>
          <button
            data-testid={`close-guided-${topic}`}
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1"
            aria-label="Close guided journey"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-slate-100 no-print">
          <div
            className="h-1 bg-purple-700 transition-all"
            style={{ width: `${percent}%` }}
            data-testid={`guided-progress-${topic}`}
          />
        </div>

        {/* Chat scroll */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50"
          data-testid={`guided-chat-${topic}`}
        >
          {history.map((m, i) => (
            <div
              key={i}
              className={
                m.role === "coach"
                  ? "flex justify-start"
                  : "flex justify-end"
              }
            >
              <div
                className={
                  m.role === "coach"
                    ? "max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-800 leading-snug shadow-sm"
                    : "max-w-[85%] bg-purple-800 text-white rounded-2xl rounded-tr-sm p-2.5 text-[12px] leading-snug"
                }
                data-testid={`guided-msg-${m.role}-${i}`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {loading && (
            <div
              className="flex justify-start"
              data-testid={`guided-typing-${topic}`}
            >
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[12px] text-slate-500 italic">
                Coach is typing…
              </div>
            </div>
          )}
          {error && (
            <div className="p-2 bg-rose-50 border border-rose-200 rounded-lg text-[11px] text-rose-800">
              {error}
            </div>
          )}
        </div>

        {/* Footer — input or save panel */}
        <div className="border-t border-slate-100 p-2 space-y-2 bg-white">
          {isFinal ? (
            <>
              <div className="text-[11px] text-slate-500 leading-snug px-1">
                Done — I saved your {answers.length} answers as a working
                draft. Tap save to store them on your device (and to
                your account if you're signed in).
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid={`guided-save-${topic}`}
                  onClick={commitSave}
                  className="flex-1 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-floppy-disk mr-1"></i>Save &
                  continue
                </button>
                <button
                  type="button"
                  data-testid={`guided-discard-${topic}`}
                  onClick={onClose}
                  className="px-3 py-2 border border-slate-300 text-slate-600 rounded-lg font-semibold text-xs"
                >
                  Discard
                </button>
              </div>
            </>
          ) : (
            <div className="flex gap-2 items-end">
              <textarea
                data-testid={`guided-input-${topic}`}
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    submitAnswer();
                  }
                }}
                placeholder={loading ? "…" : "Type your answer"}
                disabled={loading}
                className="flex-1 p-2 border border-slate-300 rounded-lg text-xs resize-none"
                maxLength={4000}
              />
              <button
                type="button"
                data-testid={`guided-send-${topic}`}
                onClick={submitAnswer}
                disabled={!input.trim() || loading}
                className="py-2 px-3 bg-purple-800 hover:bg-purple-900 disabled:opacity-40 text-white rounded-lg font-bold text-xs shrink-0"
              >
                <i className="fa-solid fa-paper-plane"></i>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
