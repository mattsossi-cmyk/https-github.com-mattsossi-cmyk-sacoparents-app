import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

const EMPTY = { answers: {}, notes: {}, tips: {}, step: 0, completed_at: null };
const detailOf = (e, fallback) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
};

// Saved Parallel Parenting plan: autosaves answers/notes, asks the AI for a tip after each step.
export function usePpPlan() {
  const [plan, setPlan] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [tipBusy, setTipBusy] = useState(null);
  const [tipError, setTipError] = useState("");
  const latest = useRef(EMPTY);
  const timer = useRef(null);

  useEffect(() => {
    api
      .get("/parallel-parenting/me")
      .then(({ data }) => {
        latest.current = { ...EMPTY, ...data };
        setPlan(latest.current);
      })
      .catch(() => {
        latest.current = EMPTY;
        setPlan(EMPTY);
        setLoadError(true);
      });
    return () => clearTimeout(timer.current);
  }, []);

  const commit = (patch) => {
    latest.current = { ...latest.current, ...patch };
    setPlan(latest.current);
  };

  const save = useCallback(async (extra = {}) => {
    clearTimeout(timer.current);
    const { answers, notes, step } = latest.current;
    try {
      const { data } = await api.put("/parallel-parenting/me", { answers, notes, step, ...extra });
      commit({ completed_at: data.completed_at, updated_at: data.updated_at });
    } catch {
      setLoadError(true);
    }
  }, []);

  const queueSave = (patch) => {
    commit(patch);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => save(), 700);
  };

  const setAnswer = (qid, oid) => queueSave({ answers: { ...latest.current.answers, [qid]: oid } });
  const setNote = (key, text) => queueSave({ notes: { ...latest.current.notes, [key]: text } });
  const goStep = (step, extra) => {
    commit({ step });
    return save(extra);
  };

  const requestTip = async (step, safetyFlag) => {
    const answers = Object.fromEntries(
      step.questions.filter((q) => latest.current.answers[q.id]).map((q) => [q.id, latest.current.answers[q.id]])
    );
    if (!Object.keys(answers).length) return;
    setTipBusy(step.key);
    setTipError("");
    try {
      const { data } = await api.post("/parallel-parenting/ai/tip", {
        step: step.key,
        answers,
        notes: latest.current.notes[step.key] || "",
        safety_flagged: !!safetyFlag,
      });
      commit({ tips: { ...latest.current.tips, [step.key]: data.tip } });
    } catch (e) {
      setTipError(detailOf(e, "Your Guide couldn't share a tip right now."));
    } finally {
      setTipBusy(null);
    }
  };

  return { plan, loadError, save, setAnswer, setNote, goStep, requestTip, tipBusy, tipError };
}

// Guide chat: one ongoing session per parent, stored on the server.
export function usePpChat({ step, safetyFlag }) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/parallel-parenting/ai/chat")
      .then(({ data }) => {
        setSessionId(data.session_id);
        setMessages(data.messages || []);
      })
      .catch(() => {});
  }, []);

  const send = async (message) => {
    setMessages((m) => [...m, { role: "user", text: message }]);
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/parallel-parenting/ai/chat", {
        message,
        session_id: sessionId,
        step,
        safety_flagged: !!safetyFlag,
      });
      setSessionId(data.session_id);
      setMessages((m) => [...m, { role: "guide", text: data.reply }]);
      return true;
    } catch (e) {
      setMessages((m) => m.slice(0, -1));
      setError(detailOf(e, "Your Guide couldn't reply right now. Please try again."));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setSessionId(null);
    setMessages([]);
    setError("");
  };

  return { messages, busy, error, send, reset };
}
