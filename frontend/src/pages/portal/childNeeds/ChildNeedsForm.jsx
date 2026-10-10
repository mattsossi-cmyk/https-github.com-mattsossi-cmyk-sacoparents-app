import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import CONTENT from "../childNeedsContent.json";
import { AckTick, NoticesBox } from "./ChildNeedsNotices";
import { FieldHelp } from "./FieldHelp";
import { RatingMatrix } from "./RatingMatrix";

const inputCls =
  "w-full px-3.5 py-2.5 border border-[#E2E8F0] rounded-md text-sm text-slate-800 bg-white focus:outline-none focus:border-[#4A154B] focus:ring-[3px] focus:ring-[#4A154B]/10 transition-colors";

function Field({ field, value, onChange }) {
  const tid = `child-needs-field-${field.id}`;
  if (field.type === "select") {
    return (
      <select data-testid={tid} id={field.id} value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
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
    return <textarea data-testid={tid} id={field.id} value={value} placeholder={field.placeholder} onChange={(e) => onChange(e.target.value)} rows={4} maxLength={2000} className={`${inputCls} resize-y min-h-[100px]`} />;
  }
  return <input data-testid={tid} id={field.id} type="text" value={value} placeholder={field.placeholder} onChange={(e) => onChange(e.target.value)} maxLength={2000} className={inputCls} />;
}

function FieldList({ category, fields, values, set }) {
  const out = [];
  for (let i = 0; i < fields.length; i += 1) {
    const f = fields[i];
    if (f.type === "rating") {
      const run = [f];
      while (fields[i + 1]?.type === "rating" && fields[i + 1].matrix === f.matrix) run.push(fields[(i += 1)]);
      out.push(<RatingMatrix key={f.id} label={f.matrix} fields={run} scale={CONTENT.rating_scale} values={values} onChange={set} />);
      continue;
    }
    out.push(
      <div key={f.id} data-field={f.id} className="rounded-lg">
        <label htmlFor={f.id} className="block text-[13px] font-bold text-slate-700 mb-1.5">
          {f.label}
        </label>
        <Field field={f} value={values[f.id] || ""} onChange={(v) => set(f.id, v)} />
        {f.type !== "select" && f.help !== false && <FieldHelp category={category.key} field={f} values={values} onUse={(v) => set(f.id, v)} />}
      </div>
    );
  }
  return out;
}

// One Child Needs form: notices, the design's questions, "Across both homes", one-time tick, Save Draft / Submit.
export function ChildNeedsForm({ category, initial, ackDate, onSubmit, onDraft, shareSlot = null }) {
  const [values, setValues] = useState(initial || {});
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(null);
  useEffect(() => {
    setValues(initial || {});
  }, [initial]);
  const set = (id, v) => setValues((s) => ({ ...s, [id]: v }));
  const filled = Object.values(values).some((v) => (v || "").trim());

  const run = async (kind) => {
    if (!filled) return toast.error("Fill in at least one question before saving.");
    if (!ackDate && !ack) return toast.error(CONTENT.notices.ack_required);
    setBusy(kind);
    try {
      await (kind === "draft" ? onDraft : onSubmit)(values, !ackDate && ack);
    } finally {
      setBusy(null);
    }
    return null;
  };

  return (
    <form
      data-testid={`child-needs-form-${category.key}`}
      onSubmit={(e) => {
        e.preventDefault();
        run("submit");
      }}
      className="space-y-5"
    >
      <NoticesBox ackDate={ackDate} />
      <FieldList category={category} fields={category.fields.filter((f) => f.group !== "home")} values={values} set={set} />
      <div className="pt-4 border-t-2 border-[#F4EEF5]">
        <h4 data-testid="child-needs-home-title" className="text-base font-extrabold text-[#4A154B]">
          <i className="fa-solid fa-house-chimney-user mr-1.5"></i>
          {CONTENT.home_group_title}
        </h4>
        <p className="text-[12px] text-slate-500">{CONTENT.home_group_desc}</p>
      </div>
      <FieldList category={category} fields={category.fields.filter((f) => f.group === "home")} values={values} set={set} />
      {!ackDate && <AckTick checked={ack} onChange={setAck} />}
      <div className="flex flex-col-reverse sm:flex-row sm:justify-between sm:items-center gap-3 pt-5 border-t border-[#E2E8F0]">
        <button
          type="button"
          data-testid="child-needs-save-draft"
          onClick={() => run("draft")}
          disabled={!!busy}
          className="px-5 py-2.5 rounded-md bg-[#F4EEF5] hover:bg-[#E2D6E5] text-[#4A154B] text-sm font-semibold transition-colors disabled:opacity-60"
        >
          {busy === "draft" ? <i className="fa-solid fa-spinner fa-spin"></i> : CONTENT.draft_label}
        </button>
        <div className="flex flex-col-reverse sm:flex-row gap-3">
          {shareSlot}
          <button
            type="submit"
            data-testid="child-needs-submit"
            disabled={!!busy}
            className="px-5 py-2.5 rounded-md bg-[#4A154B] hover:bg-[#350D36] text-white text-sm font-semibold transition-colors disabled:opacity-60"
          >
            {busy === "submit" ? <i className="fa-solid fa-spinner fa-spin"></i> : category.submit_label}
          </button>
        </div>
      </div>
    </form>
  );
}
