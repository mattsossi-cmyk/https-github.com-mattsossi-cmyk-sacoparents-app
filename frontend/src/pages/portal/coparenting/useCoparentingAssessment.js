import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { downloadPdf } from "../../../lib/pdf";

// 67-question Co-Parenting Assessment (Self Journey Card 2).
// Answers auto-save one-by-one to /coparenting/answer; failed saves are
// retried in bulk on the next section change / finish.
export function useCoparentingAssessment({ open, userId }) {
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState(null);
  const [mode, setMode] = useState("loading");
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const pendingRef = useRef({});

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setMode("loading");
    Promise.all([
      api.get("/coparenting/schema"),
      userId ? api.get("/coparenting/me") : Promise.resolve({ data: { exists: false } }),
    ])
      .then(([s, me]) => {
        if (cancelled) return;
        setSchema(s.data);
        const doc = me.data;
        if (doc.exists && doc.completed) {
          setAnswers({});
          setScores(doc.scores);
          setMode("results");
          return;
        }
        const saved = (doc.exists && doc.answers) || {};
        setAnswers(saved);
        const firstOpen = s.data.sections.findIndex((sec) => sec.questions.some((q) => saved[q.id] == null));
        setStep(Math.max(0, firstOpen));
        setMode(Object.keys(saved).length ? "section" : "intro");
      })
      .catch(() => !cancelled && setMode("error"));
    return () => {
      cancelled = true;
    };
  }, [open, userId]);

  const flushPending = useCallback(async () => {
    const pending = pendingRef.current;
    if (!Object.keys(pending).length) return;
    pendingRef.current = {};
    try {
      await api.post("/coparenting/answers/bulk", { answers: pending });
    } catch {
      pendingRef.current = { ...pending, ...pendingRef.current };
      throw new Error("save failed");
    }
  }, []);

  const setAnswer = useCallback((qid, value) => {
    setAnswers((a) => ({ ...a, [qid]: value }));
    api.post("/coparenting/answer", { question_id: qid, value }).catch(() => {
      pendingRef.current[qid] = value;
    });
  }, []);

  const goTo = useCallback(
    (next) => {
      flushPending().catch(() => {});
      setStep(next);
      setMode("section");
    },
    [flushPending]
  );

  const finish = useCallback(async () => {
    setBusy(true);
    try {
      await flushPending();
      const { data } = await api.post("/coparenting/complete");
      await api.post("/coparenting/report/generate");
      setScores(data.scores);
      setMode("results");
    } catch {
      toast.error("We couldn't finish your assessment. Please check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }, [flushPending]);

  const retake = useCallback(() => {
    setAnswers({});
    setScores(null);
    setStep(0);
    setMode("intro");
  }, []);

  const download = useCallback(
    () => downloadPdf("/coparenting/report/pdf", { filename: "SA_CoParents_CoParenting_Assessment.pdf", testid: "cp-assess-pdf" }),
    []
  );

  return { schema, answers, scores, mode, setMode, step, goTo, setAnswer, finish, retake, busy, download };
}
