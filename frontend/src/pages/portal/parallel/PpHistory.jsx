import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { downloadPdf } from "./usePp";

const when = (iso) =>
  new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });

function Version({ v, current, onDownload, busy }) {
  const [open, setOpen] = useState(false);
  const shown = open ? v.changes : v.changes.slice(0, 4);
  return (
    <li data-testid={`pp-version-${v.id}`} className="py-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {when(v.created_at)}
            {current && <span className="ml-2 text-[10px] font-bold uppercase text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-full">Current</span>}
          </p>
          <p className="text-[11px] text-slate-500">
            {v.reason} · {v.choices} choices
          </p>
        </div>
        <button
          type="button"
          data-testid={`pp-version-pdf-${v.id}`}
          onClick={() => onDownload(v)}
          disabled={busy}
          className="text-xs font-bold text-[#4a2574] hover:underline disabled:opacity-60"
        >
          <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-file-arrow-down"} mr-1`}></i>PDF
        </button>
      </div>
      <ul data-testid={`pp-version-changes-${v.id}`} className="mt-1.5 space-y-0.5">
        {v.first ? (
          <li className="text-xs text-slate-600">First saved version</li>
        ) : (
          shown.map((c) => (
            <li key={c} className="text-xs text-slate-700">
              <i className="fa-solid fa-pen-to-square text-[#8251b8] mr-1.5"></i>
              {c}
            </li>
          ))
        )}
      </ul>
      {v.changes.length > 4 && (
        <button type="button" data-testid={`pp-version-more-${v.id}`} onClick={() => setOpen(!open)} className="mt-1 text-[11px] font-semibold text-[#4a2574] hover:underline">
          {open ? "Show less" : `Show all ${v.changes.length} changes`}
        </button>
      )}
    </li>
  );
}

// "Plan history": saved versions of the plan (newest first) with what changed in each.
export function PpHistory({ tick }) {
  const [versions, setVersions] = useState(null);
  const [busyId, setBusyId] = useState(null);
  useEffect(() => {
    api
      .get("/parallel-parenting/versions")
      .then(({ data }) => setVersions(data.versions))
      .catch(() => setVersions([]));
  }, [tick]);

  const download = async (v) => {
    setBusyId(v.id);
    try {
      await downloadPdf(`/parallel-parenting/versions/${v.id}/pdf`, `SA_CoParents_Parallel_Parenting_Plan_${v.created_at.slice(0, 10)}.pdf`, "get");
    } catch {
      toast.error("Couldn't download that version right now.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section data-testid="pp-history" className="rounded-2xl border border-purple-100 p-4 sm:p-5">
      <h3 className="text-sm font-extrabold text-[#2d1548] flex items-center gap-2">
        <i className="fa-solid fa-clock-rotate-left text-[#4a2574]"></i> Plan history
      </h3>
      <p className="text-[11px] text-slate-500 mt-0.5">
        A new version is saved when you finish your plan or download its PDF, if something changed. Your last 20 versions are kept.
      </p>
      {versions === null ? (
        <div data-testid="pp-history-loading" className="mt-3 h-10 rounded-xl bg-slate-100 animate-pulse" />
      ) : versions.length === 0 ? (
        <p data-testid="pp-history-empty" className="mt-3 text-xs text-slate-500">No saved versions yet.</p>
      ) : (
        <ul data-testid="pp-history-list" className="mt-2 divide-y divide-purple-50">
          {versions.map((v, i) => (
            <Version key={v.id} v={v} current={i === 0} onDownload={download} busy={busyId === v.id} />
          ))}
        </ul>
      )}
    </section>
  );
}
