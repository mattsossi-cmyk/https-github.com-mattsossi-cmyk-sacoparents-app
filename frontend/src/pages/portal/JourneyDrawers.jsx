import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { BiffTab } from "./BiffTab";
import { GreyRockToggleChip } from "./AlignmentHub";
import { SafetySoftBanner } from "./SafetyScreen";

/**
 * JourneyDrawers — iter248 (Inline Phase B tail).
 *
 * Three modal drawers that absorb the last heavy surfaces still
 * living on the old `screen === "parent-journey"` screen:
 *   - BiffCoachDrawer   → Step 4 "Explore Options"
 *   - RecordsDrawer     → Step 3 "Focus on My Child"
 *   - FoundationDrawer  → Step 5 "Create My Plan"
 *
 * Each drawer is a full-screen bottom-sheet (mobile-first). All
 * invoke the SAME handlers the old parent-journey screen called —
 * zero PDF/AI/report code touched; this is pure UI relocation.
 *
 * BiffCoachDrawer additionally mounts the GreyRockToggleChip above
 * the BIFF content so a parent revising a message can clear grey-
 * rock mode without navigating back (iter248 "BIFF Grey-Rock
 * Mirror" ask).
 */

/* ------------------------------------------------------------------ */
/*  Shared modal shell                                                 */
/* ------------------------------------------------------------------ */

function DrawerShell({ open, onClose, title, testId, children }) {
  // Lock body scroll + support ESC-to-close for keyboard users.
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm"
      data-testid={testId}
    >
      <div
        className="bg-slate-50 w-full sm:max-w-md max-h-[92vh] rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col"
      >
        <header className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white rounded-t-3xl">
          <h2 className="font-bold text-slate-900 text-sm">{title}</h2>
          <button
            type="button"
            data-testid={`${testId}-close`}
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center transition"
            aria-label="Close"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {children}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BiffCoachDrawer — Step 4                                           */
/* ------------------------------------------------------------------ */

export function BiffCoachDrawer({
  open,
  onClose,
  // iter248 BIFF Grey-Rock Mirror — the toggle chip is rendered
  // inside the drawer so a parent revising a message can clear
  // grey-rock mode without navigating back to Step 2.
  safetyFlagged = false,
  onClearGreyRock = () => {},
  onOpenSafetyRetake = () => {},
  // iter250 Draft-to-Snapshot — one-tap action to file the raw
  // first-draft + BIFF rewrite pair into the Snapshot Library.
  // Returns true on successful save (both texts non-empty).
  onSaveBiffSnapshot = () => false,
  // BiffTab props (threaded through verbatim).
  ...biffProps
}) {
  const rawInput = biffProps.rawInput || "";
  const biffOutput = biffProps.biffOutput || "";
  const canSave = rawInput.trim().length > 0 && biffOutput.trim().length > 0;
  const [savedId, setSavedId] = useState(0);

  const handleSave = () => {
    if (!canSave) return;
    const ok = onSaveBiffSnapshot({
      raw: rawInput,
      biff: biffOutput,
    });
    if (ok) {
      setSavedId((n) => n + 1);
      toast.success("Filed to your Snapshot Library.", {
        description:
          "Your mediator will see the before and after when you share it next.",
        duration: 3500,
      });
    }
  };

  return (
    <DrawerShell
      open={open}
      onClose={onClose}
      title="BIFF Coach"
      testId="biff-coach-drawer"
    >
      {safetyFlagged && <SafetySoftBanner context="biff" />}
      {safetyFlagged && (
        <GreyRockToggleChip
          onClear={onClearGreyRock}
          onRetake={onOpenSafetyRetake}
        />
      )}
      <BiffTab safetyFlagged={safetyFlagged} {...biffProps} />

      {/* iter250 — Draft-to-Snapshot. Rendered BELOW the BIFF
          output so the parent sees the rewrite first, then the
          save CTA. Disabled until both the raw draft and the
          rewrite are non-empty. */}
      <div
        className="bg-white border border-purple-200 rounded-xl p-3 space-y-2"
        data-testid="biff-draft-to-snapshot-card"
      >
        <div className="flex items-start gap-2">
          <i className="fa-solid fa-camera-retro text-purple-700 mt-0.5"></i>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase font-bold text-purple-800 tracking-wider">
              Draft-to-Snapshot
            </div>
            <p className="text-[11px] text-slate-600 leading-snug">
              File this rewrite into your Snapshot Library so your
              mediator can see your tone progression — not just the
              rewrite in isolation.
            </p>
          </div>
        </div>
        <button
          type="button"
          data-testid="biff-save-snapshot-btn"
          onClick={handleSave}
          disabled={!canSave}
          className={
            canSave
              ? "w-full py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg font-bold text-xs transition"
              : "w-full py-2 bg-slate-100 text-slate-400 rounded-lg font-bold text-xs cursor-not-allowed"
          }
        >
          <i className="fa-solid fa-floppy-disk mr-1.5"></i>
          {canSave
            ? "File this draft + rewrite as a Snapshot"
            : "Rewrite a message to enable snapshot filing"}
        </button>
        {savedId > 0 && (
          <p
            data-testid="biff-save-snapshot-hint"
            className="text-[10px] text-emerald-700 font-semibold text-center"
          >
            <i className="fa-solid fa-check mr-1"></i>Saved — view it
            in your Snapshot Library on Step 5.
          </p>
        )}
      </div>
    </DrawerShell>
  );
}

/* ------------------------------------------------------------------ */
/*  RecordsDrawer — Step 3                                             */
/* ------------------------------------------------------------------ */

export function RecordsDrawer({
  open,
  onClose,
  alignmentCounts,
  folderFilter,
  setFolderFilter,
  filteredRecords,
  onAddAlignment,
}) {
  return (
    <DrawerShell
      open={open}
      onClose={onClose}
      title="Alignment Records"
      testId="records-drawer"
    >
      <div
        id="assessment-records-section"
        data-testid="assessment-records-section"
        className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3"
      >
        <div className="flex justify-between items-center border-b border-slate-100 pb-2">
          <div>
            <span className="text-[10px] font-bold text-emerald-600 uppercase">
              Assessments
            </span>
            <h3 className="font-bold text-slate-800 text-sm">
              Medical, Educational &amp; Psychological
            </h3>
          </div>
          <button
            data-testid="add-alignment-btn"
            onClick={onAddAlignment}
            className="bg-emerald-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-lg"
          >
            + Add Record
          </button>
        </div>

        <div className="space-y-2 text-xs">
          <button
            type="button"
            className="w-full p-3 bg-emerald-50 rounded-xl border border-emerald-100 flex justify-between items-center text-left"
            onClick={() => setFolderFilter("Medical")}
            data-testid="folder-medical"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-notes-medical text-emerald-600"></i>
              <span className="font-bold text-slate-800">
                Child's Medical Folder
              </span>
            </div>
            <span
              data-testid="count-medical"
              className="bg-white text-emerald-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Medical} Records
            </span>
          </button>

          <button
            type="button"
            className="w-full p-3 bg-blue-50 rounded-xl border border-blue-100 flex justify-between items-center text-left"
            onClick={() => setFolderFilter("Educational")}
            data-testid="folder-educational"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-graduation-cap text-blue-600"></i>
              <span className="font-bold text-slate-800">
                Educational Assessment Folder
              </span>
            </div>
            <span
              data-testid="count-educational"
              className="bg-white text-blue-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Educational} Records
            </span>
          </button>

          <button
            type="button"
            className="w-full p-3 bg-purple-50 rounded-xl border border-purple-100 flex justify-between items-center text-left"
            onClick={() => setFolderFilter("Psychological")}
            data-testid="folder-psychological"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-brain text-purple-600"></i>
              <span className="font-bold text-slate-800">
                Psychological Assessment Folder
              </span>
            </div>
            <span
              data-testid="count-psychological"
              className="bg-white text-purple-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Psychological} Records
            </span>
          </button>
        </div>

        {folderFilter !== "All" && (
          <button
            type="button"
            onClick={() => setFolderFilter("All")}
            data-testid="clear-folder-filter"
            className="text-[10px] text-purple-700 font-bold underline"
          >
            Show all records
          </button>
        )}

        <div className="space-y-2 pt-2" data-testid="alignment-records-grid">
          {filteredRecords.length === 0 ? (
            <div
              className="p-4 bg-emerald-50 border border-dashed border-emerald-300 rounded-xl text-center space-y-2"
              data-testid={`assessment-empty-${folderFilter.toLowerCase()}`}
            >
              <i className="fa-solid fa-folder-open text-emerald-600 text-lg"></i>
              <div className="font-bold text-slate-800 text-xs">
                {folderFilter === "All"
                  ? "You have 0 assessment records yet"
                  : `You have 0 ${folderFilter.toLowerCase()} records yet`}
              </div>
              <p className="text-[10px] text-slate-500 leading-snug">
                {folderFilter === "All"
                  ? "Add your first record — a provider name, a date, a short note. It saves privately to this device."
                  : folderFilter === "Medical"
                  ? "Log a provider, a diagnosis, a medication, or an upcoming appointment."
                  : folderFilter === "Educational"
                  ? "Log an IEP review, a teacher note, tutoring hours, or a school observation."
                  : "Log a therapist, an evaluation, a behavioural note, or a treatment plan."}
              </p>
              <button
                type="button"
                data-testid={`assessment-empty-add-${folderFilter.toLowerCase()}`}
                onClick={onAddAlignment}
                className="mt-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px]"
              >
                <i className="fa-solid fa-plus mr-1"></i>Add your first{" "}
                {folderFilter === "All"
                  ? "record"
                  : folderFilter.toLowerCase() + " record"}
              </button>
            </div>
          ) : (
            filteredRecords.map((item) => (
              <div
                key={item.id}
                className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1"
                data-testid={`alignment-record-${item.id}`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-bold text-slate-800">{item.title}</span>
                  <span className="text-[10px] text-slate-400 font-medium">
                    {item.date}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 font-medium">
                  Specialist: {item.provider}
                </div>
                <div className="text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-slate-100">
                  {item.summary}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </DrawerShell>
  );
}

/* ------------------------------------------------------------------ */
/*  FoundationDrawer — Step 5                                          */
/* ------------------------------------------------------------------ */

export function FoundationDrawer({
  open,
  onClose,
  foundationText,
  setFoundationText,
  saveFoundationText,
  downloadFoundationPdf,
  onShareFoundation,
  shareStatus,
  safetyFlagged = false,
  onEmailFoundationToCoparent,
}) {
  return (
    <DrawerShell
      open={open}
      onClose={onClose}
      title="Foundation Statement"
      testId="foundation-drawer"
    >
      <div
        id="foundation-statement-section"
        className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3"
      >
        <div className="flex justify-between items-start border-b border-slate-100 pb-2">
          <div>
            <span className="text-[10px] font-bold text-purple-700 uppercase">
              Step 5 Anchor
            </span>
            <h3 className="font-bold text-slate-800 text-sm">
              Foundation Statement
            </h3>
          </div>
          <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2 py-0.5 rounded">
            Anchor PDF
          </span>
        </div>
        <p className="text-xs text-slate-500">
          Your one-page child-focused anchor statement to return to
          whenever emotions get hot.
        </p>
        <textarea
          data-testid="foundation-text"
          rows={5}
          value={foundationText}
          onChange={(e) => setFoundationText(e.target.value)}
          className="w-full p-3 bg-purple-50/50 border border-purple-200 rounded-xl text-xs text-purple-950 font-medium focus:outline-none"
          placeholder="Enter your foundation statement commitment..."
        />
        <div className="flex gap-2">
          <button
            data-testid="save-foundation-btn"
            onClick={saveFoundationText}
            className="flex-1 bg-purple-800 hover:bg-purple-900 text-white font-bold py-2 rounded-xl text-xs transition"
          >
            <i className="fa-solid fa-floppy-disk"></i> Save Foundation Text
          </button>
          <button
            data-testid="export-foundation-pdf-btn"
            onClick={downloadFoundationPdf}
            className="bg-slate-100 text-slate-700 font-bold px-3 py-2 rounded-xl text-xs border border-slate-200"
          >
            <i className="fa-solid fa-file-pdf"></i> PDF
          </button>
          <button
            data-testid="share-foundation-btn"
            onClick={onShareFoundation}
            title="Copy a 30-day share link"
            className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-2 rounded-xl text-xs shadow disabled:opacity-60"
            disabled={shareStatus?.foundation === "loading"}
          >
            <i className="fa-solid fa-link"></i>{" "}
            {shareStatus?.foundation === "loading"
              ? "…"
              : shareStatus?.foundation === "copied"
              ? "Copied!"
              : "Share"}
          </button>
        </div>

        {/* Email-to-coparent — iter219 safety guardrail. Blocked
            when the parent's own Safety Check flagged risk. */}
        {safetyFlagged ? (
          <div
            data-testid="foundation-email-coparent-blocked"
            className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-[11px]"
          >
            <div className="flex items-start gap-2">
              <i className="fa-solid fa-shield-heart text-rose-700 mt-0.5"></i>
              <div>
                <div className="font-bold text-rose-900">
                  Email to co-parent blocked
                </div>
                <p className="text-rose-800 leading-snug mt-0.5">
                  You flagged safety concerns on your Quick Safety
                  Check, so we won't help send your Foundation
                  Statement directly to your co-parent. Route through
                  your attorney or mediator instead.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            data-testid="email-foundation-coparent-btn"
            onClick={onEmailFoundationToCoparent}
            disabled={shareStatus?.foundation_email === "loading"}
            className="w-full p-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-xl font-bold text-[11px] transition flex items-center justify-center gap-2 disabled:opacity-40"
          >
            <i className="fa-solid fa-envelope"></i>
            {shareStatus?.foundation_email === "loading"
              ? "Preparing email…"
              : "Email my Foundation Statement to my co-parent"}
          </button>
        )}
      </div>
    </DrawerShell>
  );
}
