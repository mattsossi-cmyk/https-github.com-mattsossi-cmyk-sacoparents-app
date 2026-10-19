import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDialogFocus } from "../../lib/useDialogFocus";

import { api } from "../../lib/api";
import { AiGuardFrame, useAiGuard } from "../../components/aiNotice/AiGuard";
import {
  GUIDED_DRAFT_KEY_PREFIX,
  GUIDED_DRAFT_TTL_MS,
  RECORDS_ENABLED,
} from "./portalStorage";

/**
 * GuidedJourneyModal — one-question-at-a-time chat wizard for the six
 * Coparenting Journey topics.
 *
 * iter221 additions:
 *  - Resume: on open, if a fresh (<14 day) draft exists for this
 *    topic we surface a resume prompt (Continue / Start fresh /
 *    Discard) instead of firing a new intro turn. Drafts auto-save
 *    on every send + on close.
 *  - Recap: when the final scripted question is answered, tapping
 *    "Save & continue" no longer commits immediately — instead we
 *    show a plain-language recap card so the parent can see exactly
 *    what will land in their record. Confirm to commit; edit to go
 *    back to the last question.
 *
 * Coach messages (Claude via Emergent LLM Key) alternate with parent
 * answers. `onSave({save_key, category, answers, summary})` is called
 * from the recap step so the caller writes into the right field.
 *
 * Props:
 *   - topic: 'foundation' | 'safety' | 'coparenting' |
 *            'medical' | 'educational' | 'psychological'
 *   - open, onClose
 *   - safetyFlagged : bool — pipes through to backend for grey-rock voice
 *   - onSave({save_key, category, answers, summary})
 */
const TOPIC_TITLES = {
  foundation: "Foundation Statement — guided",
  safety: "Safety Check — guided",
  coparenting: "Co-parenting Assessment — guided",
  medical: "Medical Needs Assessment — guided",
  educational: "Educational Assessment — guided",
  psychological: "Psychological Assessment — guided",
};

const SAVE_KEY_LABELS = {
  foundation_text: "Foundation Statement (a paragraph you can save + print as PDF)",
  cop_assessment_note: "Co-parenting Assessment note (attached to your Health Index)",
  cop_assessment: "Co-parenting Assessment note (attached to your Health Index)",
  align_record: RECORDS_ENABLED
    ? "Align-Before-Agreement record (added to your folder)"
    : "Nothing is saved. Your child's details stay private and are not kept as a record",
  safety_ack: "Private Safety Check summary (kept on this device)",
};

function draftKey(topic) {
  return `${GUIDED_DRAFT_KEY_PREFIX}${topic}`;
}

function readDraft(topic) {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(draftKey(topic));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    if (!parsed.updated_at) return null;
    const age = Date.now() - Number(parsed.updated_at);
    if (Number.isNaN(age) || age > GUIDED_DRAFT_TTL_MS) return null;
    if (!Array.isArray(parsed.history) || !Array.isArray(parsed.answers)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeDraft(topic, snapshot) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      draftKey(topic),
      JSON.stringify({ ...snapshot, updated_at: Date.now() })
    );
  } catch {
    /* ignore quota */
  }
}

function clearDraft(topic) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(draftKey(topic));
  } catch {
    /* noop */
  }
}

export function GuidedJourneyModal({
  topic,
  open,
  onClose,
  onSave,
  safetyFlagged = false,
  onDownloadSnapshot,
  onDraftPersist,
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
  const guard = useAiGuard("guided_journey", input);
  const { acked: aiAcked, openNotice: openAiNotice } = guard;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // iter221 — resume prompt shown when a fresh draft is found on open.
  const [resumePrompt, setResumePrompt] = useState(null);
  // iter221 — recap card shown after Save & continue on the final step.
  const [showRecap, setShowRecap] = useState(false);
  // iter222 — hold-to-record voice input state.
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioStreamRef = useRef(null);
  const scrollRef = useRef(null);

  const runIntroTurn = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/portal/guided-journey/step", {
        topic,
        step_index: -1,
        parent_answer: "",
        safety_flagged: !!safetyFlagged,
      });
      setHistory([
        { role: "coach", text: data.coach_message },
        { role: "coach", text: data.next_question },
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
  }, [topic, safetyFlagged]);

  // Reset when the modal opens (or topic changes). If a fresh draft
  // exists, we surface the resume prompt INSTEAD of firing the intro
  // turn so we don't burn a Claude call the parent will discard.
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
    setShowRecap(false);

    const draft = readDraft(topic);
    if (draft) {
      setResumePrompt(draft);
      return;
    }
    setResumePrompt(null);
    // Nothing goes to the AI (not even the intro turn) until the AI notice is accepted.
    if (aiAcked) runIntroTurn();
    else openAiNotice();
  }, [open, topic, runIntroTurn, aiAcked, openAiNotice]);

  // Auto-scroll to bottom on new message.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, loading, showRecap]);

  // Auto-save the wizard state as a draft after each parent turn (or
  // when the intro turn lands) so a parent who closes mid-flow can
  // resume on the next visit. We skip while `showRecap` is true —
  // once the parent has hit save-and-review the draft is "done" and
  // will be cleared on Confirm.
  useEffect(() => {
    if (!open || resumePrompt || showRecap) return;
    // Skip until we have at least the intro coach messages.
    if (history.length < 2) return;
    writeDraft(topic, {
      history,
      answers,
      stepIndex,
      progress,
      isFinal,
      saveKey,
      category,
      nextQuestion,
    });
    if (typeof onDraftPersist === "function") {
      onDraftPersist();
    }
  }, [
    open,
    resumePrompt,
    showRecap,
    topic,
    history,
    answers,
    stepIndex,
    progress,
    isFinal,
    saveKey,
    category,
    nextQuestion,
    onDraftPersist,
  ]);

  const applyDraft = useCallback((draft) => {
    setHistory(draft.history || []);
    setAnswers(draft.answers || []);
    setStepIndex(typeof draft.stepIndex === "number" ? draft.stepIndex : 0);
    setProgress(draft.progress || { step: 0, total: 5 });
    setIsFinal(!!draft.isFinal);
    setSaveKey(draft.saveKey || null);
    setCategory(draft.category || null);
    setNextQuestion(draft.nextQuestion || "");
    setResumePrompt(null);
  }, []);

  const startFresh = useCallback(() => {
    clearDraft(topic);
    if (typeof onDraftPersist === "function") onDraftPersist();
    setResumePrompt(null);
    if (aiAcked) runIntroTurn();
    else openAiNotice();
  }, [topic, runIntroTurn, onDraftPersist, aiAcked, openAiNotice]);

  const discardDraftAndClose = useCallback(() => {
    clearDraft(topic);
    if (typeof onDraftPersist === "function") onDraftPersist();
    setResumePrompt(null);
    onClose();
  }, [topic, onClose, onDraftPersist]);

  const submitAnswer = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || loading || isFinal) return;
    if (!(await guard.confirmSend(trimmed))) return;
    const answeredIndex = stepIndex;
    // Clear any transient error the moment the parent retries.
    setError("");
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
          ? [{ role: "coach", text: data.next_question }]
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
    guard,
  ]);

  const openRecap = useCallback(() => {
    setShowRecap(true);
  }, []);

  const backFromRecap = useCallback(() => {
    setShowRecap(false);
  }, []);

  const summary = useMemo(
    () =>
      answers
        .map((qa, i) => `Q${i + 1}: ${qa.question}\nA: ${qa.answer}`)
        .join("\n\n"),
    [answers]
  );

  const commitSave = useCallback(() => {
    clearDraft(topic);
    if (typeof onDraftPersist === "function") onDraftPersist();
    onSave({ save_key: saveKey, category, answers, summary });
  }, [topic, answers, saveKey, category, onSave, summary, onDraftPersist]);

  // iter222 — download the Coparent Snapshot PDF from the recap card.
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  // iter225 — "Print two side-by-side" toggle for the fridge variant.
  const [pairPrint, setPairPrint] = useState(false);
  const downloadSnapshot = useCallback(
    async (variant = "standard") => {
      if (typeof onDownloadSnapshot !== "function") return;
      // Fridge downloads honour the pair-print toggle.
      const resolved =
        variant === "fridge" && pairPrint ? "fridge_pair" : variant;
      setSnapshotBusy(variant);
      try {
        await onDownloadSnapshot({
          topic,
          answers,
          safety_flagged: !!safetyFlagged,
          variant: resolved,
        });
      } finally {
        setSnapshotBusy(false);
      }
    },
    [onDownloadSnapshot, topic, answers, safetyFlagged, pairPrint]
  );

  // iter222 — hold-to-record voice note via MediaRecorder → Whisper.
  // We store the transcript into the composer input so the parent can
  // review + edit before sending — no auto-submit.
  const startRecording = useCallback(async () => {
    if (recording || transcribing || loading) return;
    if (!aiAcked) {
      openAiNotice();
      return;
    }
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia
    ) {
      setError("Voice input isn't supported on this device.");
      return;
    }
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const rec = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      rec.addEventListener("dataavailable", (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      });
      rec.addEventListener("stop", async () => {
        try {
          const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          audioChunksRef.current = [];
          if (audioStreamRef.current) {
            audioStreamRef.current.getTracks().forEach((t) => t.stop());
            audioStreamRef.current = null;
          }
          // Guard: ignore ultra-short taps (<300 ms of audio ≈ <8 KB).
          if (blob.size < 4000) return;
          setTranscribing(true);
          const fd = new FormData();
          fd.append("audio", blob, "voice_note.webm");
          const { data } = await api.post("/portal/voice-transcribe", fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          const text = (data && data.text) || "";
          if (text) {
            setInput((prev) => (prev ? prev + " " + text : text));
          } else {
            setError("Didn't catch that — try recording again or type instead.");
          }
        } catch (err) {
          setError("Voice transcription failed — please type instead.");
        } finally {
          setTranscribing(false);
        }
      });
      rec.start();
      mediaRecorderRef.current = rec;
      setRecording(true);
    } catch (err) {
      setError("Microphone access denied — please type instead.");
    }
  }, [recording, transcribing, loading, aiAcked, openAiNotice]);

  const stopRecording = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    }
    mediaRecorderRef.current = null;
    setRecording(false);
  }, []);

  // Safety net: stop any active recording when the modal closes.
  useEffect(() => {
    if (open) return;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        /* noop */
      }
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((t) => t.stop());
      audioStreamRef.current = null;
    }
    setRecording(false);
    setTranscribing(false);
  }, [open]);

  const dialogRef = useRef(null);
  useDialogFocus(open, dialogRef, onClose);

  if (!open) return null;

  const percent = progress.total
    ? Math.round((progress.step / progress.total) * 100)
    : 0;

  const savePlacementLabel =
    SAVE_KEY_LABELS[saveKey] || "your Coparenting Journey record";

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 no-print"
      data-testid={`modal-guided-${topic}`}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`guided-title-${topic}`}
        tabIndex={-1}
        className="bg-white w-full max-w-sm sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col h-[85vh] sm:h-[85vh] outline-none"
      >
        {/* Header */}
        <div className="flex justify-between items-center border-b border-slate-100 p-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span
                className={
                  safetyFlagged
                    ? "bg-slate-900 text-amber-300 text-[0.5625rem] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider"
                    : "bg-purple-100 text-purple-800 text-[0.5625rem] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
                }
              >
                {safetyFlagged ? "Grey-rock" : "Guided"}
              </span>
              <span className="text-[0.625rem] text-slate-500">
                {showRecap
                  ? "Recap — review before saving"
                  : `Step ${progress.step} of ${progress.total}`}
              </span>
            </div>
            <h3 id={`guided-title-${topic}`} className="font-bold text-slate-800 text-sm mt-0.5 truncate">
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

        {/* Resume prompt (before we've fired the intro turn) */}
        {resumePrompt ? (
          <div
            className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50"
            data-testid={`guided-resume-${topic}`}
          >
            <div className="bg-white border border-purple-200 rounded-2xl p-3 space-y-2 shadow-sm">
              <div className="flex items-start gap-2">
                <i className="fa-solid fa-clock-rotate-left text-purple-700 mt-0.5"></i>
                <div className="min-w-0">
                  <div className="font-bold text-slate-800 text-sm">
                    Pick up where you left off?
                  </div>
                  <p className="text-[0.6875rem] text-slate-500 leading-snug">
                    You have a saved draft from{" "}
                    {new Date(resumePrompt.updated_at).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                    . You were on step {resumePrompt.progress?.step || 0} of{" "}
                    {resumePrompt.progress?.total || 5} with{" "}
                    {resumePrompt.answers?.length || 0} answers saved.
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  data-testid={`guided-resume-continue-${topic}`}
                  onClick={() => applyDraft(resumePrompt)}
                  className="p-2 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-play mr-1"></i>Continue
                </button>
                <button
                  type="button"
                  data-testid={`guided-resume-restart-${topic}`}
                  onClick={startFresh}
                  className="p-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 rounded-lg font-bold text-xs"
                >
                  <i className="fa-solid fa-rotate-left mr-1"></i>Start over
                </button>
              </div>
              <button
                type="button"
                data-testid={`guided-resume-discard-${topic}`}
                onClick={discardDraftAndClose}
                className="w-full min-h-6 text-[0.625rem] text-slate-600 hover:text-rose-700 underline"
              >
                Discard draft and close
              </button>
            </div>
          </div>
        ) : showRecap ? (
          /* Recap card — plain-language preview before commit */
          <div
            className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50"
            ref={scrollRef}
            data-testid={`guided-recap-${topic}`}
          >
            <div className="bg-white border border-purple-200 rounded-2xl p-3 space-y-2 shadow-sm">
              <div className="flex items-start gap-2">
                <i className="fa-solid fa-clipboard-check text-emerald-700 mt-0.5"></i>
                <div className="min-w-0">
                  <div className="font-bold text-slate-800 text-sm">
                    Here's what will be saved
                  </div>
                  <p
                    className="text-[0.6875rem] text-slate-500 leading-snug"
                    data-testid={`guided-recap-target-${topic}`}
                  >
                    This will be added to your <b>{savePlacementLabel}</b>.
                  </p>
                </div>
              </div>
              <ul className="space-y-2 pt-1">
                {answers.map((qa, i) => (
                  <li
                    key={i}
                    className="p-2 bg-slate-50 rounded-lg border border-slate-200"
                    data-testid={`guided-recap-item-${i}`}
                  >
                    <div className="text-[0.625rem] font-bold text-purple-800 uppercase tracking-wider">
                      Q{i + 1}
                    </div>
                    <div className="text-[0.6875rem] text-slate-600 leading-snug">
                      {qa.question}
                    </div>
                    <div className="text-[0.75rem] text-slate-900 font-medium mt-1 leading-snug">
                      {qa.answer}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          /* Chat scroll (normal wizard) */
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
                      ? "max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[0.75rem] text-slate-800 leading-snug shadow-sm"
                      : "max-w-[85%] bg-purple-800 text-white rounded-2xl rounded-tr-sm p-2.5 text-[0.75rem] leading-snug"
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
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-2.5 text-[0.75rem] text-slate-500 italic">
                  Coach is typing…
                </div>
              </div>
            )}
            {error && (
              <div
                className="p-2 bg-rose-50 border border-rose-200 rounded-lg text-[0.6875rem] text-rose-800"
                data-testid={`guided-error-${topic}`}
              >
                {error}
              </div>
            )}
          </div>
        )}

        {/* Footer — input or save/recap panel */}
        {!resumePrompt && (
          <div className="border-t border-slate-100 p-2 space-y-2 bg-white">
            {showRecap ? (
              <>
                <div className="text-[0.625rem] text-slate-500 leading-snug px-1">
                  Nothing has been saved yet — tap Confirm to store your
                  answers, or go back to edit.
                </div>
                {typeof onDownloadSnapshot === "function" && (
                  <>
                    <div
                      className="grid grid-cols-2 gap-2"
                      data-testid={`guided-recap-actions-${topic}`}
                    >
                      <button
                        type="button"
                        data-testid={`guided-recap-snapshot-${topic}`}
                        onClick={() => downloadSnapshot("standard")}
                        disabled={!!snapshotBusy}
                        className="py-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-xs disabled:opacity-40"
                      >
                        <i className="fa-solid fa-file-arrow-down mr-1"></i>
                        {snapshotBusy === "standard"
                          ? "Preparing…"
                          : "Snapshot PDF"}
                      </button>
                      <button
                        type="button"
                        data-testid={`guided-recap-fridge-${topic}`}
                        onClick={() => downloadSnapshot("fridge")}
                        disabled={!!snapshotBusy}
                        className="py-2 bg-white hover:bg-amber-50 border border-amber-400 text-amber-800 rounded-lg font-bold text-xs disabled:opacity-40"
                      >
                        <i className="fa-solid fa-note-sticky mr-1"></i>
                        {snapshotBusy === "fridge"
                          ? "Preparing…"
                          : pairPrint
                          ? "Fridge Card \u00d72"
                          : "Fridge Card"}
                      </button>
                    </div>
                    <label
                      data-testid={`guided-recap-pair-toggle-${topic}`}
                      className="flex items-center gap-1.5 pt-1 text-[0.625rem] text-slate-600 cursor-pointer select-none"
                    >
                      <input
                        type="checkbox"
                        data-testid={`guided-recap-pair-checkbox-${topic}`}
                        checked={pairPrint}
                        onChange={(e) => setPairPrint(e.target.checked)}
                        className="accent-amber-600 w-3.5 h-3.5"
                      />
                      <span>
                        Print two side-by-side (both parents get a fridge
                        card from one print)
                      </span>
                    </label>
                  </>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid={`guided-recap-back-${topic}`}
                    onClick={backFromRecap}
                    className="px-3 py-2 border border-slate-300 text-slate-600 rounded-lg font-semibold text-xs"
                  >
                    <i className="fa-solid fa-arrow-left mr-1"></i>Back
                  </button>
                  <button
                    type="button"
                    data-testid={`guided-recap-confirm-${topic}`}
                    onClick={commitSave}
                    className="flex-1 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs"
                  >
                    <i className="fa-solid fa-check mr-1"></i>Confirm & save
                  </button>
                </div>
              </>
            ) : isFinal ? (
              <>
                <div className="text-[0.6875rem] text-slate-500 leading-snug px-1">
                  Done — I've captured {answers.length} answers. Tap
                  Save to review a plain-language recap before it goes
                  into your record.
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid={`guided-save-${topic}`}
                    onClick={openRecap}
                    className="flex-1 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs"
                  >
                    <i className="fa-solid fa-floppy-disk mr-1"></i>Save &
                    review recap
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
              <AiGuardFrame tp={`guided-${topic}`} guard={guard}>
              <div className="flex gap-2 items-end">
                <textarea
                  {...guard.inputProps}
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
                  placeholder={
                    transcribing
                      ? "Transcribing…"
                      : recording
                      ? "Recording… release to send"
                      : loading
                      ? "…"
                      : "Type your answer or hold the mic"
                  }
                  disabled={loading || transcribing}
                  className="flex-1 p-2 border border-slate-300 rounded-lg text-xs resize-none"
                  maxLength={4000}
                />
                <button
                  type="button"
                  data-testid={`guided-mic-${topic}`}
                  onMouseDown={startRecording}
                  onMouseUp={stopRecording}
                  onMouseLeave={recording ? stopRecording : undefined}
                  onTouchStart={(e) => {
                    e.preventDefault();
                    startRecording();
                  }}
                  onTouchEnd={(e) => {
                    e.preventDefault();
                    stopRecording();
                  }}
                  disabled={loading || transcribing}
                  aria-label="Hold to record voice note"
                  title="Hold to record — release to transcribe"
                  className={
                    recording
                      ? "py-2 px-3 bg-rose-600 text-white rounded-lg font-bold text-xs shrink-0 animate-pulse"
                      : "py-2 px-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 rounded-lg font-bold text-xs shrink-0 border border-slate-300"
                  }
                >
                  <i
                    className={
                      transcribing
                        ? "fa-solid fa-spinner fa-spin"
                        : recording
                        ? "fa-solid fa-stop"
                        : "fa-solid fa-microphone"
                    }
                  ></i>
                </button>
                <button
                  type="button"
                  data-testid={`guided-send-${topic}`}
                  onClick={submitAnswer}
                  disabled={!input.trim() || loading || transcribing}
                  className="py-2 px-3 bg-purple-800 hover:bg-purple-900 disabled:opacity-40 text-white rounded-lg font-bold text-xs shrink-0"
                >
                  <i className="fa-solid fa-paper-plane"></i>
                </button>
              </div>
              </AiGuardFrame>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
