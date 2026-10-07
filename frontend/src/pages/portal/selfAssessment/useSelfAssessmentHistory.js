import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";
import { readJson, writeJson } from "./content";

const keyFor = (userId) => `sacoparents_self_assessment_history_v2:${userId || "local"}`;

// Completed Self-Assessments (append-only). Server is the source of truth
// when signed in; localStorage keeps it available offline / signed out.
export function useSelfAssessmentHistory(userId) {
  const [history, setHistory] = useState(() => readJson(keyFor(userId), []));

  useEffect(() => {
    setHistory(readJson(keyFor(userId), []));
    try {
      window.localStorage.removeItem("sacoparents_self_assessment_v1");
    } catch {
      /* ignore */
    }
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/self-assessment/history")
      .then(({ data }) => {
        if (cancelled) return;
        setHistory(data.entries);
        writeJson(keyFor(userId), data.entries);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const addEntry = useCallback(
    (entry) =>
      setHistory((prev) => {
        const next = [...prev, entry];
        writeJson(keyFor(userId), next);
        return next;
      }),
    [userId]
  );

  const latest = history.length ? history[history.length - 1] : null;
  return { history, latest, currentGoal: latest?.goal || "", addEntry };
}
