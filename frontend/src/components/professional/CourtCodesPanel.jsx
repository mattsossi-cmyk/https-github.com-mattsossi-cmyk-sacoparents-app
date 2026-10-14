import React, { useEffect, useMemo, useState } from "react";
import { KeyRound, Loader2, Plus, Search, X } from "lucide-react";

import { api } from "../../lib/api";
import { logError } from "../../lib/logger";
import { ArchiveFinishedButton } from "./ArchiveFinishedButton";
import { CourtCodeForm } from "./CourtCodeForm";
import { CourtCodeItem, isFinishedCode } from "./CourtCodeItem";

// "My cases": court codes this professional created, with status-only progress per parent who entered the code.
export const CourtCodesPanel = () => {
  const [codes, setCodes] = useState(null);
  const [open, setOpen] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [q, setQ] = useState("");
  const load = () =>
    api.get("/professional/court-codes").then((r) => setCodes(r.data?.codes || [])).catch((err) => {
      logError("court codes load failed:", err);
      setCodes([]);
    });
  useEffect(() => { load(); }, []);
  const all = codes || [];
  const archived = all.filter((c) => c.archived_at);
  const finished = all.filter((c) => !c.archived_at && isFinishedCode(c)).length;
  const query = q.trim().toLowerCase();
  // A search looks through active and archived codes (by reference or private label).
  const shown = useMemo(() => all.filter((c) => (query
    ? c.case_id.toLowerCase().includes(query) || (c.label || "").toLowerCase().includes(query)
    : !c.archived_at || showArchived)), [all, query, showArchived]);

  return (
    <section className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 mb-4" data-testid="court-codes-panel">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
            <KeyRound size={12} /> Court codes
          </div>
          <p className="text-sm text-[#4B4567] mt-1 max-w-xl leading-relaxed">
            Give a parent a code and the assessments you pick are ticked for them on their Court page.
            You&rsquo;ll see only Done, In progress or Not started, never their answers.
          </p>
        </div>
        <button type="button" onClick={() => setOpen((o) => !o)} data-testid="court-code-toggle"
          className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors">
          {open ? <X size={12} /> : <Plus size={12} />} {open ? "Close" : "Create a court code"}
        </button>
      </div>
      {open && <div className="mb-3"><CourtCodeForm onCreated={load} /></div>}
      {all.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <label className="relative flex-1 min-w-[200px] max-w-sm">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#857E9C]" aria-hidden />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search codes by reference or label" aria-label="Search court codes"
              className="w-full rounded-full border border-[#E5E0EE] bg-white pl-8 pr-8 py-1.5 text-xs focus:outline-none focus:border-[#3D1A78]" data-testid="court-codes-search" />
            {q && (
              <button type="button" onClick={() => setQ("")} aria-label="Clear search" data-testid="court-codes-search-clear"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#857E9C] hover:text-[#3D1A78]"><X size={12} /></button>
            )}
          </label>
          <ArchiveFinishedButton kind="codes" count={finished} onDone={load} testid="court-codes-archive-finished" />
        </div>
      )}
      {codes === null ? (
        <p className="text-xs text-[#857E9C]" data-testid="court-codes-loading"><Loader2 size={12} className="animate-spin inline mr-1" /> Loading codes…</p>
      ) : all.length === 0 ? (
        <p className="text-xs text-[#857E9C]" data-testid="court-codes-empty">No court codes yet.</p>
      ) : (
        <>
          {shown.length === 0 && (
            <p className="text-xs text-[#857E9C]" data-testid={query ? "court-codes-no-match" : "court-codes-all-archived"}>
              {query ? "No codes match your search." : "All your court codes are archived."}
            </p>
          )}
          <ul className="space-y-2.5" data-testid="court-codes-list">
            {shown.map((c) => <CourtCodeItem key={c.case_id} c={c} onChanged={load} />)}
          </ul>
          {archived.length > 0 && !query && (
            <button type="button" onClick={() => setShowArchived((v) => !v)} aria-pressed={showArchived} data-testid="court-codes-show-archived"
              className="mt-3 text-xs font-semibold text-[#3D1A78] hover:underline">
              {showArchived ? "Hide archived" : `Show archived (${archived.length})`}
            </button>
          )}
        </>
      )}
    </section>
  );
};
