import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import CONTENT from "../childNeedsContent.json";

const inputCls =
  "w-full px-3 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-[#4c2889] focus:ring-2 focus:ring-purple-100";

function Field({ field, value, onChange }) {
  const tid = `child-needs-field-${field.id}`;
  if (field.type === "select") {
    return (
      <select data-testid={tid} id={field.id} value={value} onChange={(e) => onChange(e.target.value)} className={`${inputCls} bg-white`}>
        <option value="">{CONTENT.select_placeholder}</option>
        {field.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  }
  if (field.type === "textarea") {
    return (
      <textarea data-testid={tid} id={field.id} value={value} placeholder={field.placeholder} onChange={(e) => onChange(e.target.value)} rows={3} maxLength={2000} className={`${inputCls} resize-y`} />
    );
  }
  return <input data-testid={tid} id={field.id} type="text" value={value} placeholder={field.placeholder} onChange={(e) => onChange(e.target.value)} maxLength={2000} className={inputCls} />;
}

// Inline form for one Child Needs category (shown on the left of the Child Needs screen).
export function ChildNeedsForm({ category, initial, onSubmit }) {
  const [values, setValues] = useState(initial || {});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setValues(initial || {});
  }, [initial]);
  const filled = Object.values(values).some((v) => (v || "").trim());

  const submit = async (e) => {
    e.preventDefault();
    if (!filled) {
      toast.error("Fill in at least one question before saving.");
      return;
    }
    setBusy(true);
    try {
      await onSubmit(values);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form data-testid={`child-needs-form-${category.key}`} onSubmit={submit} className="space-y-4">
      {category.fields.map((f) => (
        <div key={f.id}>
          <label htmlFor={f.id} className="block text-[13px] font-bold text-slate-700 mb-1.5">
            {f.label}
          </label>
          <Field field={f} value={values[f.id] || ""} onChange={(v) => setValues((s) => ({ ...s, [f.id]: v }))} />
        </div>
      ))}
      <button
        type="submit"
        data-testid="child-needs-submit"
        disabled={busy}
        className="w-full py-3.5 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-sm font-extrabold shadow-md transition-colors disabled:opacity-60"
      >
        {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : CONTENT.submit_label}
      </button>
    </form>
  );
}
