import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const keyFor = (userId) => `sacoparents_child_needs_v2:${userId || "local"}`;

const read = (userId) => {
  try {
    return JSON.parse(window.localStorage.getItem(keyFor(userId)) || "null") || { answers: {}, completed_at: {} };
  } catch {
    return { answers: {}, completed_at: {} };
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
        if (cancelled || !Object.keys(data.answers || {}).length) return;
        setState(data);
        write(userId, data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const saveCategory = useCallback(
    async (category, answers) => {
      let next;
      if (userId) {
        ({ data: next } = await api.put(`/child-needs/me/${category}`, { answers }));
      } else {
        next = {
          answers: { ...state.answers, [category]: answers },
          completed_at: { ...state.completed_at, [category]: new Date().toISOString() },
        };
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
