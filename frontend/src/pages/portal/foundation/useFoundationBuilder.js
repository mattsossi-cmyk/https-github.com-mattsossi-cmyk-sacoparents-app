import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const LEGACY_KEY = "sacoparents_foundation_statement_v1";
const keyFor = (userId) => `sacoparents_foundation_builder_v2:${userId || "local"}`;
const ts = (iso) => (iso ? Date.parse(iso) || 0 : 0);

const read = (userId) => {
  try {
    const v = JSON.parse(window.localStorage.getItem(keyFor(userId)) || "null");
    if (v) return v;
    const legacy = JSON.parse(window.localStorage.getItem(LEGACY_KEY) || "null");
    return legacy ? { fields: legacy, updated_at: null, saved_at: null } : { fields: {}, updated_at: null, saved_at: null };
  } catch {
    return { fields: {}, updated_at: null, saved_at: null };
  }
};

const write = (userId, state) => {
  try {
    window.localStorage.setItem(keyFor(userId), JSON.stringify(state));
  } catch {
    /* storage unavailable */
  }
};

// Card 4 · Foundation Statement builder. Saves as you type (localStorage
// instantly, account via debounced PUT when signed in) + branded PDF.
export function useFoundationBuilder(userId, parentName) {
  const [state, setState] = useState(() => read(userId));
  const [status, setStatus] = useState("idle");
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);
  const latest = useRef(state);
  latest.current = state;

  useEffect(() => {
    const local = read(userId);
    setState(local);
    if (!userId) return undefined;
    let cancelled = false;
    api
      .get("/foundation-builder/me")
      .then(({ data }) => {
        if (cancelled || !data.updated_at || ts(data.updated_at) <= ts(local.updated_at)) return;
        const next = { fields: data.fields, updated_at: data.updated_at, saved_at: data.updated_at };
        setState(next);
        write(userId, next);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const push = useCallback(async () => {
    clearTimeout(timer.current);
    if (!userId) {
      const next = { ...latest.current, saved_at: new Date().toISOString() };
      setState(next);
      write(userId, next);
      setStatus("local");
      return true;
    }
    setStatus("saving");
    try {
      const { data } = await api.put("/foundation-builder/me", { fields: latest.current.fields });
      const next = { fields: latest.current.fields, updated_at: data.updated_at, saved_at: data.updated_at };
      setState(next);
      write(userId, next);
      setStatus("saved");
      return true;
    } catch {
      setStatus("error");
      return false;
    }
  }, [userId]);

  const update = useCallback(
    (key, value) => {
      setState((s) => {
        const next = { ...s, fields: { ...s.fields, [key]: value }, updated_at: new Date().toISOString() };
        write(userId, next);
        return next;
      });
      setStatus("pending");
      clearTimeout(timer.current);
      timer.current = setTimeout(push, 1000);
    },
    [userId, push]
  );

  const save = useCallback(async () => {
    const ok = await push();
    if (ok) toast.success("Saved ✓ — your Foundation Statement is safe.");
    else toast.error("Saved on this device — we couldn't reach your account. Please try again.");
    return ok;
  }, [push]);

  const download = useCallback(async () => {
    setBusy(true);
    try {
      const fields = { parent_names: parentName || "", ...latest.current.fields };
      const res = await api.post("/foundation-builder/pdf", { fields }, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Foundation_Statement.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Foundation Statement PDF is ready.");
    } catch {
      toast.error("Write at least one part of your statement, then try again.");
    } finally {
      setBusy(false);
    }
  }, [parentName]);

  return { fields: state.fields || {}, savedAt: state.saved_at, status, busy, update, save, download };
}
