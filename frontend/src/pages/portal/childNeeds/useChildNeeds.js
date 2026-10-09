import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const keyFor = (userId) => `sacoparents_child_needs_v2:${userId || "local"}`;
const EMPTY = { answers: {}, completed_at: {}, drafts: {}, notice_ack_at: null };
const hasData = (d) => Object.keys(d.answers || {}).length || Object.keys(d.drafts || {}).length || d.notice_ack_at;

const read = (userId) => {
  try {
    return { ...EMPTY, ...(JSON.parse(window.localStorage.getItem(keyFor(userId)) || "null") || {}) };
  } catch {
    return EMPTY;
  }
};

const write = (userId, state) => {
  try {
    window.localStorage.setItem(keyFor(userId), JSON.stringify(state));
  } catch {
    /* storage unavailable */
  }
};

// Card 3 · Medical / Educational / Psychological needs. localStorage-first,
// mirrored to /child-needs/me when signed in.
export function useChildNeeds(userId) {
  const [state, setState] = useState(() => read(userId));

  useEffect(() => {
    setState(read(userId));
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/child-needs/me")
      .then(({ data }) => {
        if (cancelled || !hasData(data)) return;
        const next = { ...EMPTY, ...data };
        setState(next);
        write(userId, next);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  // `draft` saves a separate copy without marking complete; `acknowledged` = first-time privacy notice tick.
  const saveCategory = useCallback(
    async (category, answers, { draft = false, acknowledged = false } = {}) => {
      let next;
      if (userId) {
        ({ data: next } = await api.put(`/child-needs/me/${category}`, { answers, draft, acknowledged }));
        next = { ...EMPTY, ...next };
      } else {
        const now = new Date().toISOString();
        const { [category]: _old, ...otherDrafts } = state.drafts || {};
        next = draft
          ? { ...state, drafts: { ...otherDrafts, [category]: answers } }
          : {
              ...state,
              answers: { ...state.answers, [category]: answers },
              completed_at: { ...state.completed_at, [category]: now },
              drafts: otherDrafts,
            };
        next.notice_ack_at = state.notice_ack_at || now;
      }
      setState(next);
      write(userId, next);
      return next;
    },
    [userId, state]
  );

  const downloadReport = useCallback(async (answers, parentName) => {
    try {
      const res = await api.post(
        "/child-needs/pdf",
        { parent_name: parentName || "", answers },
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Child_Specific_Needs.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return true;
    } catch {
      toast.error("Couldn't build the report right now. Please try again.");
      return false;
    }
  }, []);

  return { state, saveCategory, downloadReport };
}
