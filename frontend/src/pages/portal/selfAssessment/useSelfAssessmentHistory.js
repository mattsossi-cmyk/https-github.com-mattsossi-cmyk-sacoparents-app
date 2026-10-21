import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { REASSESS_AFTER_DAYS, daysSince, readJson, todayLocal, writeJson } from "./content";

const keyFor = (userId) => `sacoparents_self_assessment_history_v2:${userId || "local"}`;
const practiceKeyFor = (userId) => `sacoparents_goal_practice_v1:${userId || "local"}`;

// Completed Self-Assessments (append-only) + goal practice check-ins.
// Server is the source of truth when signed in; localStorage keeps it
// available offline / signed out.
export function useSelfAssessmentHistory(userId) {
  const [history, setHistory] = useState(() => readJson(keyFor(userId), []));
  const [practice, setPractice] = useState(() => readJson(practiceKeyFor(userId), null));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setHistory(readJson(keyFor(userId), []));
    setPractice(readJson(practiceKeyFor(userId), null));
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
        if (data.goal_practice) {
          setPractice(data.goal_practice);
          writeJson(practiceKeyFor(userId), data.goal_practice);
        }
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoaded(true));
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

  const updateEntry = useCallback(
    (id, patch) =>
      setHistory((prev) => {
        const next = prev.map((e) => (e.id === id ? { ...e, ...patch } : e));
        writeJson(keyFor(userId), next);
        return next;
      }),
    [userId]
  );

  const latest = history.length ? history[history.length - 1] : null;
  const markReached = useCallback(
    async (entryId, reached) => {
      let reachedAt = reached ? new Date().toISOString() : null;
      if (userId) ({ data: { reached_at: reachedAt } } = await api.post("/self-assessment/goal/reached", { entry_id: entryId, reached }));
      updateEntry(entryId, { reached_at: reachedAt });
    },
    [userId, updateEntry]
  );
  const current = useMemo(
    () => (latest && practice?.entry_id === latest.id ? practice : { entry_id: latest?.id, count: 0, last_date: null }),
    [latest, practice]
  );

  const practise = useCallback(async () => {
    if (!latest) return;
    const date = todayLocal();
    try {
      let next;
      if (userId) {
        ({ data: next } = await api.post("/self-assessment/goal/checkin", { entry_id: latest.id, date }));
      } else {
        next =
          current.last_date === date
            ? current
            : {
                ...current,
                count: current.count + 1,
                last_date: date,
                recent_dates: [...(current.recent_dates || []), date].slice(-60),
              };
      }
      setPractice(next);
      writeJson(practiceKeyFor(userId), next);
      toast.success("Nice work — practice logged for today.");
    } catch {
      toast.error("Couldn't log today's practice. Please try again.");
    }
  }, [latest, userId, current]);

  return {
    history,
    loaded,
    latest,
    currentGoal: latest?.goal || "",
    practice: {
      count: current.count,
      practisedToday: current.last_date === todayLocal(),
      recentDates: current.recent_dates || [],
    },
    practise,
    dueDays: latest && daysSince(latest.completed_at) >= REASSESS_AFTER_DAYS ? daysSince(latest.completed_at) : 0,
    addEntry,
    updateEntry,
    markReached,
  };
}
