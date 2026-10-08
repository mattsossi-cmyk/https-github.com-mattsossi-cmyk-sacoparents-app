import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";
import { emptyDraft, readJson, scoreAnswers, toDraftPayload, writeJson } from "./content";

const keyFor = (userId) => `sacoparents_self_assessment_draft_v2:${userId || "local"}`;
const ts = (iso) => (iso ? Date.parse(iso) || 0 : 0);
const hasProgress = (d) => !!d && (d.started || Object.keys(d.answers || {}).length > 0);

// In-progress chat answers. Every edit lands in localStorage instantly and,
// when signed in, is debounced to PUT /self-assessment/me.
export function useSelfAssessmentDraft({ open, userId, parentName, onCompleted }) {
  const [draft, setDraft] = useState(() => emptyDraft(parentName));
  const [rev, setRev] = useState(0);
  const revRef = useRef(0);
  const pendingRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [savedAt, setSavedAt] = useState(null);
  const [ready, setReady] = useState(false);

  const flush = useCallback(async () => {
    const payload = pendingRef.current;
    if (!payload) return;
    pendingRef.current = null;
    setStatus("saving");
    try {
      const { data } = await api.put("/self-assessment/me", payload);
      setSavedAt(data.updated_at);
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    const local = readJson(keyFor(userId), null);
    setDraft({ ...emptyDraft(parentName), ...(local || {}) });
    revRef.current = 0;
    setRev(0);
    setStatus(userId ? "idle" : "local");
    setReady(!userId);
    if (!userId) return undefined;
    api
      .get("/self-assessment/me")
      .then(({ data }) => {
        if (cancelled || revRef.current > 0) return;
        if (data?.updated_at && ts(data.updated_at) > ts(local?.updated_at)) {
          const next = { ...emptyDraft(parentName), ...toDraftPayload(data) };
          setDraft(next);
          writeJson(keyFor(userId), { ...next, updated_at: data.updated_at });
          setSavedAt(data.updated_at);
          setStatus("saved");
        } else if (hasProgress(local)) {
          pendingRef.current = toDraftPayload(local);
          flush();
        }
      })
      .catch(() => !cancelled && setStatus("local"))
      .finally(() => !cancelled && setReady(true));
    return () => {
      cancelled = true;
    };
  }, [open, userId, parentName, flush]);

  useEffect(() => {
    if (rev === 0) return undefined;
    writeJson(keyFor(userId), { ...draft, updated_at: new Date().toISOString() });
    if (!userId) {
      setStatus("local");
      return undefined;
    }
    pendingRef.current = toDraftPayload(draft);
    setStatus("pending");
    const t = setTimeout(flush, 800);
    return () => clearTimeout(t);
  }, [rev, draft, userId, flush]);

  const update = useCallback((fn) => {
    revRef.current += 1;
    setDraft(fn);
    setRev(revRef.current);
  }, []);

  const resetDraft = useCallback(() => {
    pendingRef.current = null;
    revRef.current = 0;
    setRev(0);
    const fresh = emptyDraft(parentName);
    setDraft(fresh);
    writeJson(keyFor(userId), fresh);
  }, [parentName, userId]);

  const complete = useCallback(
    async (finalDraft) => {
      pendingRef.current = null;
      const payload = toDraftPayload(finalDraft);
      let entry;
      if (userId) {
        const { data } = await api.post("/self-assessment/complete", payload);
        entry = data;
      } else {
        entry = {
          id: `local-${Date.now()}`,
          completed_at: new Date().toISOString(),
          parent_name: payload.parent_name,
          answers: payload.answers,
          reflections: payload.reflections,
          goal: (payload.goal || "").trim(),
          scores: scoreAnswers(payload.answers),
        };
      }
      resetDraft();
      onCompleted(entry);
      return entry;
    },
    [userId, resetDraft, onCompleted]
  );

  return { draft, update, status, savedAt, flush, complete, ready };
}
