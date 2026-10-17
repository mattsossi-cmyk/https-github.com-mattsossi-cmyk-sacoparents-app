import React, { useState } from "react";

/**
 * SnapshotStrip — "Recent snapshots" strip on the Coparenting Journey
 * toolkit (iter227). Shows up to 3 recently-finished Guided Journey
 * runs so parents can re-download the Snapshot PDF, Fridge Card, or
 * Fridge Card x2 without re-running the wizard from scratch.
 *
 * iter229 — also lets parents remove an individual snapshot via a
 * small ✕ in the top-right of each card (with a two-tap
 * "Delete? Yes/No" confirm so a fat-finger doesn't wipe a card).
 *
 * Props:
 *   - history: array of {id, topic, answers, saved_at, save_key,
 *     category, safety_flagged}
 *   - onDownload({topic, answers, safety_flagged, variant})
 *   - onDelete(id): called with the snapshot's stable id when the
 *     parent confirms deletion. No-op if omitted.
 *   - limit: max items to render (defaults to 3 per the founder's ask)
 */
const TOPIC_LABEL = {
  foundation: "Foundation",
  coparenting: "Co-parenting",
  safety: "Safety Check",
  medical: "Medical",
  educational: "Educational",
  psychological: "Psychological",
  // iter250 — Draft-to-Snapshot: a captured BIFF rewrite pair.
  biff_pair: "BIFF rewrite",
};

const TOPIC_ICON = {
  foundation: "fa-solid fa-heart",
  coparenting: "fa-solid fa-handshake",
  safety: "fa-solid fa-shield-halved",
  medical: "fa-solid fa-briefcase-medical",
  educational: "fa-solid fa-book-open",
  psychological: "fa-solid fa-brain",
  biff_pair: "fa-solid fa-wand-magic-sparkles",
};

function relativeAge(isoLike) {
  if (!isoLike) return "just now";
  const then = Date.parse(isoLike);
  if (Number.isNaN(then)) return "recently";
  const diffMs = Date.now() - then;
  const mins = Math.max(1, Math.round(diffMs / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  return `${months}mo ago`;
}

export function SnapshotStrip({
  history,
  onDownload,
  onDelete,
  onRename,
  onPin,
  onReorder,
  limit = 3,
}) {
  const [confirmingId, setConfirmingId] = useState(null);
  const [renamingId, setRenamingId] = useState(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [dragId, setDragId] = useState(null);
  const [overTopZone, setOverTopZone] = useState(false);
  if (!Array.isArray(history) || history.length === 0) return null;

  // iter237 — pinned snapshots float to the top (most-recently-pinned
  // first within the pinned group); unpinned keep their original
  // insertion order. Sort is pure so the server's canonical order is
  // never mutated.
  const sorted = [...history].sort((a, b) => {
    const ap = a.pinned ? 1 : 0;
    const bp = b.pinned ? 1 : 0;
    if (ap !== bp) return bp - ap;
    if (ap === 1) {
      // Both pinned — most recent pin wins.
      return String(b.pinned_at || "").localeCompare(String(a.pinned_at || ""));
    }
    // Both unpinned — keep insertion order (newest-first already).
    return 0;
  });
  const items = sorted.slice(0, limit);

  const beginRename = (snap, idx) => {
    setRenamingId(snap.id ?? idx);
    setRenameDraft(snap.label || "");
  };
  const commitRename = (snap, idx) => {
    if (typeof onRename === "function") {
      const trimmed = (renameDraft || "").trim().slice(0, 40);
      onRename(snap.id ?? idx, trimmed);
    }
    setRenamingId(null);
    setRenameDraft("");
  };
  const cancelRename = () => {
    setRenamingId(null);
    setRenameDraft("");
  };
  const togglePin = (snap, idx) => {
    if (typeof onPin !== "function") return;
    onPin(snap.id ?? idx, !snap.pinned);
  };

  return (
    <section
      className="mb-4 no-print"
      data-testid="snapshot-strip"
      aria-label="Recent snapshots"
    >
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="flex items-center gap-1.5">
          <i className="fa-solid fa-clock-rotate-left text-purple-700 text-xs"></i>
          <h3 className="text-xs font-bold text-slate-800 tracking-wide">
            Recent snapshots
          </h3>
        </div>
        <span className="text-[0.625rem] text-slate-400">
          Last {items.length} of {history.length}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2">
        {/* iter237 — drop zone above the first row. A dragged
            snapshot released here flips to pinned so parents can
            quickly "drag to the top" an active plan. The zone only
            appears while a drag is in flight to avoid empty-state
            visual noise. */}
        {dragId !== null && typeof onPin === "function" && (
          <div
            data-testid="snapshot-pin-dropzone"
            onDragOver={(e) => {
              e.preventDefault();
              setOverTopZone(true);
            }}
            onDragLeave={() => setOverTopZone(false)}
            onDrop={() => {
              onPin(dragId, true);
              setDragId(null);
              setOverTopZone(false);
            }}
            className={
              overTopZone
                ? "rounded-xl border-2 border-dashed border-amber-500 bg-amber-50 p-2 text-[0.625rem] font-bold text-amber-800 text-center"
                : "rounded-xl border-2 border-dashed border-purple-300 bg-purple-50/50 p-2 text-[0.625rem] font-semibold text-purple-700 text-center"
            }
          >
            <i className="fa-solid fa-thumbtack mr-1"></i>
            Drop here to pin to the top
          </div>
        )}
        {items.map((snap, idx) => {
          const label = TOPIC_LABEL[snap.topic] || snap.topic;
          const iconClass = TOPIC_ICON[snap.topic] || "fa-solid fa-file-lines";
          const key = snap.id || `${snap.topic}-${idx}`;
          const isPinned = !!snap.pinned;
          return (
            <div
              key={key}
              data-testid={`snapshot-item-${snap.topic}-${idx}`}
              draggable={typeof onPin === "function" ? true : undefined}
              onDragStart={() => setDragId(snap.id ?? idx)}
              onDragEnd={() => {
                setDragId(null);
                setOverTopZone(false);
              }}
              className={
                "p-2.5 bg-white border rounded-xl shadow-sm relative " +
                (isPinned
                  ? "border-amber-400 ring-1 ring-amber-100"
                  : "border-slate-200")
              }
            >
              {typeof onPin === "function" && (
                <button
                  type="button"
                  data-testid={`snapshot-pin-${idx}`}
                  onClick={() => togglePin(snap, idx)}
                  aria-label={isPinned ? "Unpin this snapshot" : "Pin this snapshot to the top"}
                  className={
                    "absolute top-1 right-7 w-6 h-6 rounded-full flex items-center justify-center transition " +
                    (isPinned
                      ? "text-amber-600 hover:bg-amber-50"
                      : "text-slate-300 hover:text-amber-600 hover:bg-amber-50")
                  }
                >
                  <i className="fa-solid fa-thumbtack text-[0.6875rem]"></i>
                </button>
              )}
              {typeof onDelete === "function" && (
                <button
                  type="button"
                  data-testid={`snapshot-delete-${idx}`}
                  onClick={() => setConfirmingId(snap.id ?? idx)}
                  aria-label="Remove this snapshot"
                  className="absolute top-1 right-1 w-6 h-6 rounded-full text-slate-300 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center"
                >
                  <i className="fa-solid fa-xmark text-[0.6875rem]"></i>
                </button>
              )}
              <div className="flex items-center gap-2 mb-2 pr-12">
                <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                  <i className={`${iconClass} text-purple-800 text-xs`}></i>
                </div>
                <div className="min-w-0 flex-1">
                  {renamingId === (snap.id ?? idx) ? (
                    <div
                      className="flex items-center gap-1"
                      data-testid={`snapshot-rename-input-wrap-${idx}`}
                    >
                      <input
                        type="text"
                        autoFocus
                        value={renameDraft}
                        maxLength={40}
                        onChange={(e) => setRenameDraft(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitRename(snap, idx);
                          if (e.key === "Escape") cancelRename();
                        }}
                        placeholder={`${label} — e.g. Emma's summer plan`}
                        data-testid={`snapshot-rename-input-${idx}`}
                        className="flex-1 min-w-0 text-[0.6875rem] font-bold text-slate-800 bg-white border border-purple-400 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                      <button
                        type="button"
                        data-testid={`snapshot-rename-save-${idx}`}
                        onClick={() => commitRename(snap, idx)}
                        aria-label="Save name"
                        className="shrink-0 w-6 h-6 rounded text-emerald-600 hover:bg-emerald-50 flex items-center justify-center"
                      >
                        <i className="fa-solid fa-check text-[0.6875rem]"></i>
                      </button>
                      <button
                        type="button"
                        data-testid={`snapshot-rename-cancel-${idx}`}
                        onClick={cancelRename}
                        aria-label="Cancel rename"
                        className="shrink-0 w-6 h-6 rounded text-slate-400 hover:bg-slate-100 flex items-center justify-center"
                      >
                        <i className="fa-solid fa-xmark text-[0.6875rem]"></i>
                      </button>
                    </div>
                  ) : (
                    <>
                      <div
                        className="text-xs font-bold text-slate-800 truncate flex items-center gap-1"
                        data-testid={`snapshot-title-${idx}`}
                      >
                        <span className="truncate">
                          {snap.label && snap.label.trim()
                            ? snap.label
                            : `${label}${snap.category ? ` — ${snap.category}` : ""}`}
                        </span>
                        {typeof onRename === "function" && (
                          <button
                            type="button"
                            data-testid={`snapshot-rename-${idx}`}
                            onClick={() => beginRename(snap, idx)}
                            aria-label="Rename this snapshot"
                            className="shrink-0 w-5 h-5 rounded text-slate-300 hover:text-purple-700 hover:bg-purple-50 flex items-center justify-center"
                          >
                            <i className="fa-solid fa-pen text-[0.5625rem]"></i>
                          </button>
                        )}
                      </div>
                      {snap.label && snap.label.trim() && (
                        <div
                          className="text-[0.5625rem] text-slate-400 uppercase tracking-wider truncate"
                          data-testid={`snapshot-topic-sub-${idx}`}
                        >
                          {label}
                          {snap.category ? ` · ${snap.category}` : ""}
                        </div>
                      )}
                      <div className="text-[0.625rem] text-slate-500">
                        {snap.answers?.length || 0} answers ·{" "}
                        {relativeAge(snap.saved_at)}
                      </div>
                    </>
                  )}
                </div>
              </div>
              {confirmingId === (snap.id ?? idx) ? (
                <div
                  className="p-2 bg-rose-50 border border-rose-200 rounded-lg space-y-1.5"
                  data-testid={`snapshot-delete-confirm-${idx}`}
                >
                  <div className="text-[0.6875rem] text-rose-800 leading-snug">
                    Delete this snapshot? You can always re-run the
                    Guided chat to make a new one.
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      data-testid={`snapshot-delete-confirm-cancel-${idx}`}
                      onClick={() => setConfirmingId(null)}
                      className="py-1.5 bg-white border border-slate-300 text-slate-600 rounded-lg font-bold text-[0.625rem]"
                    >
                      Keep it
                    </button>
                    <button
                      type="button"
                      data-testid={`snapshot-delete-confirm-yes-${idx}`}
                      onClick={() => {
                        onDelete(snap.id ?? idx);
                        setConfirmingId(null);
                      }}
                      className="py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold text-[0.625rem]"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  data-testid={`snapshot-redownload-standard-${idx}`}
                  onClick={() =>
                    onDownload({
                      topic: snap.topic,
                      answers: snap.answers,
                      safety_flagged: !!snap.safety_flagged,
                      variant: "standard",
                    })
                  }
                  className="py-1.5 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-[0.625rem]"
                >
                  <i className="fa-solid fa-file-arrow-down mr-1"></i>PDF
                </button>
                <button
                  type="button"
                  data-testid={`snapshot-redownload-fridge-${idx}`}
                  onClick={() =>
                    onDownload({
                      topic: snap.topic,
                      answers: snap.answers,
                      safety_flagged: !!snap.safety_flagged,
                      variant: "fridge",
                    })
                  }
                  className="py-1.5 bg-white hover:bg-amber-50 border border-amber-400 text-amber-800 rounded-lg font-bold text-[0.625rem]"
                >
                  <i className="fa-solid fa-note-sticky mr-1"></i>Fridge
                </button>
                <button
                  type="button"
                  data-testid={`snapshot-redownload-pair-${idx}`}
                  onClick={() =>
                    onDownload({
                      topic: snap.topic,
                      answers: snap.answers,
                      safety_flagged: !!snap.safety_flagged,
                      variant: "fridge_pair",
                    })
                  }
                  className="py-1.5 bg-white hover:bg-amber-50 border border-amber-400 text-amber-800 rounded-lg font-bold text-[0.625rem]"
                >
                  <i className="fa-solid fa-copy mr-1"></i>×2
                </button>
              </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
