import { useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";
import { CONTENT, SECTIONS, readJson, sectionAnswers, sectionComplete, writeJson } from "./content";

const WELCOME = {
  label: "Welcome",
  text: "As you finish each step, I'll share a gentle, personal tip here. Answer honestly — this is just for you.",
};
const FALLBACK = "Notice one thing that's already working, and pick one small step from this section to practise this week.";
const tipKey = (id) => `sacoparents_sa_ai_tip:${id}`;

// Latest AI tip: after each completed rated section, or for the latest saved entry.
// Section tips are kept on the draft (onSectionTip); the results tip is saved on the new entry.
export function useSaInsight({ draft, mode, latest, safetyFlag, onSectionTip, onOverallTip }) {
  const [tip, setTip] = useState(WELCOME);
  const [loading, setLoading] = useState(false);
  const seen = useRef(new Set());
  const reqId = useRef(0);

  const ask = async (seenKey, label, body, cacheKey, onSaved, stored) => {
    if (seen.current.has(seenKey)) return;
    seen.current.add(seenKey);
    const cached = stored || (cacheKey && readJson(cacheKey, null));
    if (cached) {
      setTip({ label, text: cached });
      return;
    }
    const id = ++reqId.current;
    setLoading(true);
    setTip({ label, text: "" });
    try {
      const { data } = await api.post("/self-assessment/ai/tip", { ...body, safety_flagged: !!safetyFlag });
      if (id !== reqId.current) return;
      setTip({ label, text: data.tip, ai: true });
      if (cacheKey) writeJson(cacheKey, data.tip);
      if (onSaved) onSaved(data.tip);
    } catch {
      if (id === reqId.current) setTip({ label, text: FALLBACK });
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "loading") return;
    if (mode === "assess") {
      const done = SECTIONS.filter((s) => sectionComplete(s, draft.answers));
      const last = done[done.length - 1];
      if (!last) return;
      const answers = sectionAnswers(last.key, draft.answers);
      const label = CONTENT.tips.step_label.replace("{number}", last.number).replace("{title}", last.title);
      ask(`s:${JSON.stringify(answers)}`, label, { section: last.key, answers }, null,
        (text) => onSectionTip?.(last.key, text), draft.tips?.[last.key]);
    } else if (latest?.answers) {
      const fresh = mode === "results";
      ask(`e:${latest.id}`, CONTENT.tips.overall_label,
        { section: "overall", answers: latest.answers, entry_id: fresh ? latest.id : undefined },
        tipKey(latest.id), fresh ? (text) => onOverallTip?.(latest, text) : null, latest.tips?.overall);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, draft.answers, latest?.id]);

  return { tip, loading };
}

export function useFraming(safetyFlag) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (text) => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/self-assessment/ai/framing", { text, safety_flagged: !!safetyFlag });
      setResult(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "The AI guide couldn't respond right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return { result, busy, error, submit };
}
