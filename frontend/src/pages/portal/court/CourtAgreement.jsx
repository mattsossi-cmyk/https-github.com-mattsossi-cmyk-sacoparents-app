import React, { useEffect, useState } from "react";

const NOTE_MAX = 300;

export function AgreeProgress({
  progress,
  notice,
  testid = "court-agree-progress",
}) {
  const pct = progress.total
    ? Math.round((progress.agreed / progress.total) * 100)
    : 0;
  return (
    <div data-testid={testid} className="mb-3">
      <div className="flex items-center justify-between text-xs font-bold text-[#3b1566] mb-1.5">
        <span data-testid={`${testid}-label`}>
          {progress.agreed} of {progress.total} areas agreed
        </span>
        {progress.all_agreed && (
          <span className="text-emerald-700">
            <i className="fa-solid fa-circle-check mr-1"></i>All agreed
          </span>
        )}
      </div>
      <div className="h-2 rounded-full bg-[#e7dbf8] overflow-hidden">
        <div
          className="h-full rounded-full bg-[#2fa144] transition-[width] duration-500"
          style={{ width: `${pct}%` }}
        ></div>
      </div>
      {notice && (
        <p
          data-testid={`${testid}-notice`}
          className="mt-2 text-[10.5px] leading-snug text-[#5c2c8e]"
        >
          {notice}
        </p>
      )}
    </div>
  );
}

function whoMarked(row) {
  if (row.by_me && row.by_them) return "Marked agreed by both of you";
  return row.by_me ? "Marked agreed by you" : "Marked agreed by your co-parent";
}

// Per-area agreement: either parent's mark agrees it for both; each parent can only undo their own mark.
export function AgreeControls({ row, i, compare, step4 }) {
  const [note, setNote] = useState(row.note);
  useEffect(() => setNote(row.note), [row.note]);
  const busy = compare.agreeBusy === row.key;
  const small =
    "text-[11px] font-bold px-3 py-1.5 rounded-full transition-colors disabled:opacity-60";
  if (!row.agreed) {
    return (
      <button
        type="button"
        data-testid={`court-agree-${i}`}
        disabled={busy}
        onClick={() => compare.setAgreed(row.key, true)}
        className={`mt-2 ${small} bg-[#2fa144] hover:bg-[#268537] text-white`}
      >
        <i
          className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-handshake"} mr-1.5`}
        ></i>
        Mark as agreed
      </button>
    );
  }
  return (
    <div
      data-testid={`court-agreed-${i}`}
      className="mt-2 bg-emerald-50 border border-emerald-100 rounded-lg p-2.5"
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-[11px] font-extrabold text-emerald-800">
          <i className="fa-solid fa-handshake mr-1"></i>Agreed
        </span>
        <span
          data-testid={`court-agreed-by-${i}`}
          className="text-[11px] text-emerald-900"
        >
          {whoMarked(row)}
        </span>
        {row.by_me ? (
          <button
            type="button"
            data-testid={`court-agree-undo-${i}`}
            disabled={busy}
            onClick={() => compare.setAgreed(row.key, false)}
            className={`${small} bg-white border border-emerald-200 text-emerald-800 hover:bg-emerald-100`}
          >
            Undo my mark
          </button>
        ) : (
          <button
            type="button"
            data-testid={`court-agree-also-${i}`}
            disabled={busy}
            onClick={() => compare.setAgreed(row.key, true)}
            className={`${small} bg-white border border-emerald-200 text-emerald-800 hover:bg-emerald-100`}
          >
            I agree too
          </button>
        )}
      </div>
      <label
        htmlFor={`court-agree-note-${i}`}
        className="block text-[10px] font-bold uppercase tracking-wider text-emerald-900 mb-1"
      >
        What we agreed (optional)
      </label>
      <textarea
        id={`court-agree-note-${i}`}
        data-testid={`court-agree-note-${i}`}
        rows={2}
        maxLength={NOTE_MAX}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="e.g. Handoffs at the school gate at 3:15, with a text 10 minutes before."
        className="w-full text-xs rounded-md border border-emerald-200 bg-white px-2.5 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400"
      />
      <div className="flex items-center justify-between mt-1">
        <span className="text-[10px] text-emerald-900/70">
          {note.length}/{NOTE_MAX} · Both of you can see this
        </span>
        <span className="flex items-center gap-1.5">
          {row.note && (
            <button
              type="button"
              data-testid={`court-agree-to-step4-${i}`}
              disabled={step4.has(row)}
              onClick={() => step4.add([row])}
              className={`${small} bg-white border border-emerald-200 text-emerald-800 hover:bg-emerald-100`}
            >
              <i className="fa-solid fa-file-import mr-1"></i>
              {step4.has(row) ? "In Foundation Statement" : "Add to Foundation Statement"}
            </button>
          )}
          <button
            type="button"
            data-testid={`court-agree-note-save-${i}`}
            disabled={busy || note.trim().replace(/\s+/g, " ") === row.note}
            onClick={() => compare.saveNote(row.key, note)}
            className={`${small} bg-emerald-700 hover:bg-emerald-800 text-white`}
          >
            Save note
          </button>
        </span>
      </div>
    </div>
  );
}

export function AgreedList({ rows }) {
  return (
    <div data-testid="court-agreed-list" className="mt-3">
      <p className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-800 mb-1.5">
        <i className="fa-solid fa-handshake mr-1"></i>Agreed after talking
      </p>
      <ul className="space-y-1.5">
        {rows.map((r) => (
          <li
            key={r.key}
            className="border border-emerald-100 bg-emerald-50 rounded-lg px-3 py-2"
          >
            <p className="text-xs font-semibold text-[#202124]">{r.area}</p>
            {r.note && (
              <p className="text-[11px] text-emerald-900 mt-0.5">{r.note}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// Card under the picture so both parents see agreement progress at a glance.
export function CourtAgreeCard({ compare, onOpen }) {
  const progress = compare.data?.progress;
  if (compare.data?.state !== "ready" || !progress?.total) return null;
  return (
    <button
      type="button"
      data-testid="court-agree-card"
      onClick={onOpen}
      className="w-full text-left bg-white rounded-2xl border border-[#e0d5ed] hover:border-[#5c2c8e] shadow-sm px-5 py-4 transition-colors"
    >
      <p className="text-sm font-extrabold text-[#3b1566] mb-2 flex items-center gap-2">
        <i className="fa-solid fa-handshake text-[#2fa144]"></i> Agreement
        progress with your co-parent
      </p>
      <AgreeProgress progress={progress} testid="court-agree-card-progress" />
    </button>
  );
}
