import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { api } from "../../lib/api";
import CONTENT from "./selfAssessmentContent.json";

// Copy lives in selfAssessmentContent.json — mirrored on the backend
// (self_assessment_content.json) so the PDF stays in lockstep.
const STORAGE_KEY = "sacoparents_self_assessment_v1";
const { sections: SECTIONS, tiers: TIERS, scale: SCALE } = CONTENT;
const MAX_VALUE = Math.max(...SCALE.map((s) => s.value));
const QUESTION_COUNT = SECTIONS.reduce((n, s) => n + s.questions.length, 0);
const TOTAL_MAX = QUESTION_COUNT * MAX_VALUE;
const TIER_CHIPS = [
  "bg-emerald-100 text-emerald-800 border-emerald-200",
  "bg-amber-100 text-amber-800 border-amber-200",
  "bg-orange-100 text-orange-800 border-orange-200",
  "bg-rose-100 text-rose-800 border-rose-200",
];

const readStored = () => {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
};

const writeStored = (state) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* storage unavailable */
  }
};

const normalize = (src, parentName) => ({
  meta: {
    parent_name: src?.meta?.parent_name || parentName || "",
    date: src?.meta?.date || new Date().toISOString().slice(0, 10),
    child: src?.meta?.child || "",
    case_ref: src?.meta?.case_ref || "",
  },
  answers: src?.answers || {},
  foundation: {
    going_well: src?.foundation?.going_well || ["", "", ""],
    improve: src?.foundation?.improve || ["", "", ""],
    shared_goals: src?.foundation?.shared_goals || "",
  },
});

const hasContent = (s) =>
  !!s &&
  (Object.keys(s.answers || {}).length > 0 ||
    [...(s.foundation?.going_well || []), ...(s.foundation?.improve || []), s.foundation?.shared_goals]
      .some((x) => (x || "").trim()));

const ts = (iso) => (iso ? Date.parse(iso) || 0 : 0);

const sectionScore = (answers, s) =>
  s.questions.reduce((sum, _q, i) => sum + (answers[`${s.key}${i + 1}`] || 0), 0);

const inputCls =
  "mt-1 px-2 py-1.5 border border-slate-300 rounded text-xs font-normal text-slate-900";
const areaCls =
  "w-full px-2 py-1.5 border border-slate-300 rounded text-xs text-slate-900 resize-y";

function MetaGrid({ meta, onChange }) {
  const fields = [
    ["parent_name", "Parent name", "text", "parent"],
    ["date", "Date", "date", "date"],
    ["child", "Child(ren)", "text", "child"],
    ["case_ref", "Case / Reference", "text", "case"],
  ];
  return (
    <div
      data-testid="self-assessment-meta"
      className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-50 border border-slate-200 rounded-lg p-3"
    >
      {fields.map(([key, label, type, tid]) => (
        <label key={key} className="flex flex-col text-[11px] font-semibold text-slate-600">
          {label}
          <input
            type={type}
            data-testid={`self-assessment-meta-${tid}`}
            value={meta[key]}
            onChange={(e) => onChange(key, e.target.value)}
            className={inputCls}
          />
        </label>
      ))}
    </div>
  );
}

function SectionBlock({ section, answers, onAnswer }) {
  const max = section.questions.length * MAX_VALUE;
  return (
    <div data-testid={`self-assessment-section-${section.key}`}>
      <div className="bg-purple-700 text-white rounded px-3 py-2 flex items-center justify-between text-sm font-bold">
        <span>
          Section {section.key} — {section.label}
        </span>
        <span data-testid={`self-assessment-section-${section.key}-score`} className="text-xs font-semibold">
          {sectionScore(answers, section)} / {max}
        </span>
      </div>
      <div className="divide-y divide-slate-100">
        {section.questions.map((q, idx) => {
          const qKey = `${section.key}${idx + 1}`;
          const value = answers[qKey] || 0;
          return (
            <div key={qKey} className="py-2.5 flex flex-col sm:flex-row sm:items-center sm:gap-3">
              <div className="flex-1 text-[12px] text-slate-800 leading-snug">
                <span className="font-bold mr-1">{qKey}.</span>
                {q}
              </div>
              <div className="flex items-center gap-1.5 mt-1.5 sm:mt-0">
                {SCALE.map(({ value: v }) => (
                  <label
                    key={v}
                    className={`cursor-pointer px-2.5 py-1 rounded border text-[11px] font-semibold select-none transition-colors ${
                      value === v
                        ? "bg-purple-700 text-white border-purple-700"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-purple-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`sa-${qKey}`}
                      value={v}
                      checked={value === v}
                      data-testid={`self-assessment-${qKey}-${v}`}
                      onChange={() => onAnswer(qKey, v)}
                      className="sr-only"
                    />
                    {v}
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SummaryCard({ answers }) {
  const total = SECTIONS.reduce((n, s) => n + sectionScore(answers, s), 0);
  const answered = Object.keys(answers).length;
  const tierIdx = answered === QUESTION_COUNT ? TIERS.findIndex((t) => total >= t.min) : -1;
  const tier = tierIdx >= 0 ? TIERS[tierIdx] : null;
  return (
    <div data-testid="self-assessment-summary" className="bg-slate-50 border border-slate-200 rounded-lg p-3">
      <h3 className="text-sm font-bold text-slate-900">Your reflection summary</h3>
      <table className="w-full mt-2 text-[12px]">
        <tbody>
          {SECTIONS.map((s) => (
            <tr key={s.key} className="border-b border-slate-200 last:border-0">
              <td className="py-1.5 text-slate-700">{s.label}</td>
              <td data-testid={`self-assessment-summary-${s.key}`} className="py-1.5 text-right font-semibold text-slate-900">
                {sectionScore(answers, s)} / {s.questions.length * MAX_VALUE}
              </td>
            </tr>
          ))}
          <tr className="bg-slate-200">
            <td className="py-2 px-1 font-bold">Total score</td>
            <td data-testid="self-assessment-total" className="py-2 px-1 text-right font-bold">
              {total} / {TOTAL_MAX}
            </td>
          </tr>
        </tbody>
      </table>
      {tier ? (
        <div data-testid="self-assessment-tier" className={`mt-3 p-2.5 rounded border ${TIER_CHIPS[tierIdx]}`}>
          <div className="font-bold text-[12px]">{tier.title}</div>
          <p className="text-[11px] mt-0.5 leading-snug">{tier.body}</p>
        </div>
      ) : (
        <p data-testid="self-assessment-tier-pending" className="mt-3 text-[11px] text-slate-500">
          {CONTENT.tier_pending.replace("{n}", QUESTION_COUNT)} ({answered} of {QUESTION_COUNT} answered)
        </p>
      )}
    </div>
  );
}

function FoundationBlock({ foundation, onArr, onGoals }) {
  const f = CONTENT.foundation;
  const list = (key, tid) => (
    <div>
      <label className="text-[11px] font-semibold text-slate-700">{f[key]}</label>
      <div className="space-y-1 mt-1">
        {foundation[key].map((v, i) => (
          <textarea
            key={`${key}-${i}`}
            data-testid={`self-assessment-${tid}-${i}`}
            value={v}
            placeholder={`${i + 1}.`}
            onChange={(e) => onArr(key, i, e.target.value)}
            rows={2}
            className={areaCls}
          />
        ))}
      </div>
    </div>
  );
  return (
    <div data-testid="self-assessment-foundation" className="space-y-2">
      <h4 className="text-sm font-bold text-slate-900">{f.heading}</h4>
      {list("going_well", "going-well")}
      {list("improve", "improve")}
      <div>
        <label className="text-[11px] font-semibold text-slate-700">{f.shared_goals}</label>
        <textarea
          data-testid="self-assessment-shared-goals"
          value={foundation.shared_goals}
          onChange={(e) => onGoals(e.target.value)}
          rows={3}
          className={`${areaCls} mt-1`}
        />
      </div>
    </div>
  );
}

const STATUS_COPY = {
  idle: { icon: "fa-cloud", text: "Changes save to your account automatically", cls: "text-slate-500" },
  pending: { icon: "fa-cloud-arrow-up", text: "Saving to your account…", cls: "text-slate-500" },
  saving: { icon: "fa-cloud-arrow-up", text: "Saving to your account…", cls: "text-slate-500" },
  saved: { icon: "fa-circle-check", text: "Saved to your account", cls: "text-emerald-700" },
  local: { icon: "fa-mobile-screen", text: "Saved on this device — sign in to keep it in your account", cls: "text-slate-500" },
  error: { icon: "fa-triangle-exclamation", text: "Saved on this device — couldn't reach your account, we'll retry on your next change", cls: "text-amber-700" },
};

function SaveStatus({ status, savedAt }) {
  const c = STATUS_COPY[status] || STATUS_COPY.idle;
  const time =
    status === "saved" && savedAt
      ? ` · ${new Date(savedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
      : "";
  return (
    <p data-testid="self-assessment-save-status" data-status={status} className={`text-[11px] ${c.cls} flex items-center gap-1.5`}>
      <i className={`fa-solid ${c.icon}`}></i>
      {c.text}
      {time}
    </p>
  );
}

const toPayload = (s) => ({ meta: s.meta, answers: s.answers, foundation: s.foundation });

function useSelfAssessmentSync({ open, userId, parentName }) {
  const [state, setState] = useState(() => normalize(null, parentName));
  const [rev, setRev] = useState(0);
  const revRef = useRef(0);
  const pendingRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [savedAt, setSavedAt] = useState(null);

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
    const local = readStored();
    setState(normalize(local, parentName));
    revRef.current = 0;
    setRev(0);
    setStatus(userId ? "idle" : "local");
    if (!userId) return undefined;
    api
      .get("/self-assessment/me")
      .then(({ data }) => {
        if (cancelled || revRef.current > 0) return;
        if (data?.updated_at && ts(data.updated_at) > ts(local?.updated_at)) {
          const next = normalize(data, parentName);
          setState(next);
          writeStored({ ...next, updated_at: data.updated_at });
          setSavedAt(data.updated_at);
          setStatus("saved");
        } else if (hasContent(local)) {
          pendingRef.current = toPayload(normalize(local, parentName));
          flush();
        }
      })
      .catch(() => !cancelled && setStatus("local"));
    return () => {
      cancelled = true;
    };
  }, [open, userId, parentName, flush]);

  useEffect(() => {
    if (rev === 0) return undefined;
    writeStored({ ...state, updated_at: new Date().toISOString() });
    if (!userId) {
      setStatus("local");
      return undefined;
    }
    pendingRef.current = toPayload(state);
    setStatus("pending");
    const t = setTimeout(flush, 800);
    return () => clearTimeout(t);
  }, [rev, state, userId, flush]);

  const update = (fn) => {
    revRef.current += 1;
    setState(fn);
    setRev(revRef.current);
  };

  return { state, update, status, savedAt, flush };
}

function useDownloadPdf() {
  const [busy, setBusy] = useState(false);
  const download = async (state) => {
    setBusy(true);
    try {
      const res = await api.post("/self-assessment/pdf", toPayload(state), { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Self_Assessment.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Self-Assessment PDF is ready.");
    } catch {
      toast.error("Couldn't build the PDF right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return { busy, download };
}

export function SelfAssessmentModal({ open, onOpenChange, parentName, userId }) {
  const { state, update, status, savedAt, flush } = useSelfAssessmentSync({ open, userId, parentName });
  const { busy, download } = useDownloadPdf();

  const handleOpenChange = (next) => {
    if (!next) flush();
    onOpenChange(next);
  };
  const setMeta = (key, value) => update((s) => ({ ...s, meta: { ...s.meta, [key]: value } }));
  const setAnswer = (qKey, v) => update((s) => ({ ...s, answers: { ...s.answers, [qKey]: v } }));
  const setArr = (key, idx, value) =>
    update((s) => {
      const arr = [...s.foundation[key]];
      arr[idx] = value;
      return { ...s, foundation: { ...s.foundation, [key]: arr } };
    });
  const setGoals = (value) => update((s) => ({ ...s, foundation: { ...s.foundation, shared_goals: value } }));

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent data-testid="self-assessment-modal" className="max-w-3xl max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-purple-900">{CONTENT.title}</DialogTitle>
          <DialogDescription>{CONTENT.subtitle}</DialogDescription>
        </DialogHeader>

        <MetaGrid meta={state.meta} onChange={setMeta} />

        <div className="bg-blue-50 border-l-4 border-blue-500 text-blue-900 text-[12px] p-2.5 rounded">
          <span className="font-semibold">How to use this assessment:</span> {CONTENT.how_to_use}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 border border-slate-200 rounded p-2 text-[11px] font-semibold text-slate-700 text-center">
          {SCALE.map((s) => (
            <div key={s.value}>
              {s.value} = {s.label}
            </div>
          ))}
        </div>

        <div className="space-y-3">
          {SECTIONS.map((s) => (
            <SectionBlock key={s.key} section={s} answers={state.answers} onAnswer={setAnswer} />
          ))}
        </div>

        <SummaryCard answers={state.answers} />
        <FoundationBlock foundation={state.foundation} onArr={setArr} onGoals={setGoals} />

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-2 border-t border-slate-200">
          <SaveStatus status={status} savedAt={savedAt} />
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              data-testid="self-assessment-close"
              onClick={() => handleOpenChange(false)}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold transition-colors"
            >
              Close
            </button>
            <button
              type="button"
              data-testid="self-assessment-download-pdf"
              disabled={busy}
              onClick={() => download(state)}
              className="px-3 py-1.5 rounded-lg bg-purple-700 hover:bg-purple-800 disabled:opacity-60 text-white text-xs font-bold transition-colors"
            >
              <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-file-pdf"} mr-1.5`}></i>
              {busy ? "Building PDF…" : "Download PDF"}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default SelfAssessmentModal;
