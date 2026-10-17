import React, { useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { useAiGuard } from "../../../components/aiNotice/AiGuard";

// "Help me answer": asks the Child Needs Guide for a short editable draft for one question.
export function FieldHelp({ category, field, values, onUse }) {
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const guard = useAiGuard("child_needs_help");
  const ask = async () => {
    if (!(await guard.confirmSend(values[field.id] || ""))) return;
    setBusy(true);
    try {
      const { data } = await api.post("/journey-guide/child-needs/suggest", {
        category,
        field_id: field.id,
        draft: values[field.id] || "",
        answers: values,
      });
      setText(data.suggestion);
    } catch (e) {
      toast.error(e?.response?.status === 401 ? "Sign in to use Help me answer." : e?.response?.data?.detail || "The Guide couldn't suggest an answer right now.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mt-1.5">
      <button
        type="button"
        data-testid={`child-needs-help-${field.id}`}
        onClick={ask}
        disabled={busy}
        className="text-[0.6875rem] font-bold text-[#611663] hover:underline disabled:opacity-60"
      >
        <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-wand-magic-sparkles"} mr-1`}></i>
        {busy ? "Asking your Guide…" : "Help me answer"}
      </button>
      {text && (
        <div data-testid={`child-needs-suggestion-${field.id}`} className="mt-2 rounded-lg border border-purple-200 bg-white p-3 text-[0.8125rem] text-slate-700 shadow-sm">
          <p data-testid={`child-needs-suggestion-text-${field.id}`}>{text}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid={`child-needs-use-${field.id}`}
              onClick={() => {
                onUse(text);
                setText("");
              }}
              className="px-3 py-1.5 rounded-md bg-[#4A154B] hover:bg-[#350D36] text-white text-[0.6875rem] font-bold transition-colors"
            >
              Use this
            </button>
            <button
              type="button"
              data-testid={`child-needs-dismiss-${field.id}`}
              onClick={() => setText("")}
              className="px-3 py-1.5 rounded-md bg-[#F4EEF5] hover:bg-[#E2D6E5] text-[#4A154B] text-[0.6875rem] font-bold transition-colors"
            >
              Dismiss
            </button>
            <span className="text-[0.625rem] text-slate-500">Edit anything in [brackets] before saving.</span>
          </div>
        </div>
      )}
    </div>
  );
}
