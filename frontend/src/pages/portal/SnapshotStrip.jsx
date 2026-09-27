import React from "react";

/**
 * SnapshotStrip — "Recent snapshots" strip on the Coparenting Journey
 * toolkit (iter227). Shows up to 3 recently-finished Guided Journey
 * runs so parents can re-download the Snapshot PDF, Fridge Card, or
 * Fridge Card x2 without re-running the wizard from scratch.
 *
 * Props:
 *   - history: array of {id, topic, answers, saved_at, save_key,
 *     category, safety_flagged}
 *   - onDownload({topic, answers, safety_flagged, variant})
 *   - limit: max items to render (defaults to 3 per the founder's ask)
 */
const TOPIC_LABEL = {
  foundation: "Foundation",
  coparenting: "Co-parenting",
  safety: "Safety Check",
  medical: "Medical",
  educational: "Educational",
  psychological: "Psychological",
};

const TOPIC_ICON = {
  foundation: "fa-solid fa-heart",
  coparenting: "fa-solid fa-handshake",
  safety: "fa-solid fa-shield-halved",
  medical: "fa-solid fa-briefcase-medical",
  educational: "fa-solid fa-book-open",
  psychological: "fa-solid fa-brain",
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

export function SnapshotStrip({ history, onDownload, limit = 3 }) {
  if (!Array.isArray(history) || history.length === 0) return null;
  const items = history.slice(0, limit);

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
        <span className="text-[10px] text-slate-400">
          Last {items.length} of {history.length}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2">
        {items.map((snap, idx) => {
          const label = TOPIC_LABEL[snap.topic] || snap.topic;
          const iconClass = TOPIC_ICON[snap.topic] || "fa-solid fa-file-lines";
          const key = snap.id || `${snap.topic}-${idx}`;
          return (
            <div
              key={key}
              data-testid={`snapshot-item-${snap.topic}-${idx}`}
              className="p-2.5 bg-white border border-slate-200 rounded-xl shadow-sm"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                  <i className={`${iconClass} text-purple-800 text-xs`}></i>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-bold text-slate-800 truncate">
                    {label}
                    {snap.category ? ` — ${snap.category}` : ""}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {snap.answers?.length || 0} answers ·{" "}
                    {relativeAge(snap.saved_at)}
                  </div>
                </div>
              </div>
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
                  className="py-1.5 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-[10px]"
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
                  className="py-1.5 bg-white hover:bg-amber-50 border border-amber-400 text-amber-800 rounded-lg font-bold text-[10px]"
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
                  className="py-1.5 bg-white hover:bg-amber-50 border border-amber-400 text-amber-800 rounded-lg font-bold text-[10px]"
                >
                  <i className="fa-solid fa-copy mr-1"></i>×2
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
