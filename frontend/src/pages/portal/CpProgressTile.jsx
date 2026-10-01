import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";

/**
 * CpProgressTile — iter234
 *
 * Lives inside the Coparenting Journey Toolkit on Alignment & Tools.
 * Reads `/api/coparenting/report/progress` and renders four things:
 *
 *   1. 60-day retake soft banner (only when `retake_due`).
 *   2. Overall-rating sparkline over every submission.
 *   3. Per-section movers — change bars (↑ improved, ↓ slipped)
 *      against the ~60-days-ago baseline.
 *   4. A compact radar comparing the most recent run to the baseline.
 *
 * All four hide cleanly when there's no history yet; in that case we
 * render a short empty-state inviting the parent to take the
 * assessment, with the public sample link beside it.
 */
const RATING_BANDS = [
  { v: 1, label: "Needs Improvement", color: "#B6663B" },
  { v: 2, label: "Fair", color: "#CBA135" },
  { v: 3, label: "Good", color: "#3F7B47" },
  { v: 4, label: "Excellent", color: "#1F5C3B" },
];

function ratingColor(rating) {
  const band = RATING_BANDS.find((b) => b.label === rating);
  return band ? band.color : "#857E9C";
}

function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "2-digit",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

// iter237 — short relative age for the Share-history strip
// ("Opened 2h ago", "Sent 3d ago"). Falls back silently if the ISO
// string is malformed so a stale row never crashes the tile.
function relativeAge(iso) {
  if (!iso) return "just now";
  const then = Date.parse(iso);
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

function Sparkline({ series }) {
  if (!series || series.length === 0) return null;
  const w = 240;
  const h = 56;
  const padX = 8;
  const padY = 10;
  const maxV = 4;
  const n = series.length;
  const xStep = n > 1 ? (w - padX * 2) / (n - 1) : 0;
  const yFor = (v) => h - padY - ((v || 0) / maxV) * (h - padY * 2);
  const points = series.map((p, i) => [padX + i * xStep, yFor(p.value)]);
  const path = points
    .map((pt, i) => (i === 0 ? `M ${pt[0]},${pt[1]}` : `L ${pt[0]},${pt[1]}`))
    .join(" ");
  const last = series[series.length - 1];
  return (
    <div data-testid="cp-progress-sparkline">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full h-14"
        preserveAspectRatio="none"
      >
        {/* rating guide lines */}
        {RATING_BANDS.map((b) => (
          <line
            key={b.v}
            x1={padX}
            x2={w - padX}
            y1={yFor(b.v)}
            y2={yFor(b.v)}
            stroke="#EEE9F7"
            strokeDasharray="2 3"
          />
        ))}
        <path
          d={path}
          fill="none"
          stroke="#3D1A78"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {points.map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="2.5"
            fill={ratingColor(series[i].rating)}
          />
        ))}
      </svg>
      <div className="flex justify-between text-[9px] text-slate-400 mt-1">
        <span>{fmtDate(series[0].submitted_at)}</span>
        <span
          className="font-bold"
          style={{ color: ratingColor(last.rating) }}
          data-testid="cp-progress-latest-rating"
        >
          Latest · {last.rating}
        </span>
        <span>{fmtDate(last.submitted_at)}</span>
      </div>
    </div>
  );
}

function MoverBars({ movers }) {
  if (!movers || movers.length === 0) return null;
  const top = movers.slice(0, 5);
  const max = Math.max(...top.map((m) => Math.abs(m.delta)), 1);
  return (
    <div className="space-y-1.5" data-testid="cp-progress-movers">
      {top.map((m) => {
        const widthPct = Math.min(100, (Math.abs(m.delta) / max) * 100);
        const isUp = m.direction === "up";
        const isDown = m.direction === "down";
        const bar =
          isUp
            ? "bg-emerald-500"
            : isDown
            ? "bg-amber-500"
            : "bg-slate-300";
        const icon = isUp ? "↑" : isDown ? "↓" : "·";
        return (
          <div
            key={m.id}
            className="text-[11px]"
            data-testid={`cp-mover-${m.id}`}
          >
            <div className="flex justify-between items-baseline">
              <span className="text-slate-700 font-medium truncate pr-2">
                {m.number}. {m.name}
              </span>
              <span
                className={
                  isUp
                    ? "text-emerald-600 font-bold tabular-nums"
                    : isDown
                    ? "text-amber-700 font-bold tabular-nums"
                    : "text-slate-400 font-bold tabular-nums"
                }
              >
                {icon} {m.delta > 0 ? "+" : ""}
                {m.delta.toFixed(2)}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden mt-0.5">
              <div
                className={`h-full ${bar} transition-all`}
                style={{
                  width: `${widthPct}%`,
                  marginLeft: isDown ? "auto" : 0,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Compact 10-axis radar comparing recent vs baseline. */
function Radar({ radar }) {
  const labels = radar?.labels || [];
  const recent = radar?.recent || [];
  const baseline = radar?.baseline || [];
  if (labels.length < 3) return null;
  const size = 180;
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 14;
  const n = labels.length;
  const maxV = 4;
  const point = (i, v) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const rr = (v / maxV) * r;
    return [cx + Math.cos(angle) * rr, cy + Math.sin(angle) * rr];
  };
  const makePath = (vals) =>
    vals
      .map((v, i) => {
        const [x, y] = point(i, v || 0);
        return `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ") + " Z";

  // Ring guides at each rating band.
  const ringPaths = [1, 2, 3, 4].map((band) =>
    Array.from({ length: n }, (_, i) => point(i, band))
      .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${y.toFixed(1)}`)
      .join(" ") + " Z"
  );
  const hasBaseline = baseline.length > 0;
  return (
    <div
      className="flex flex-col items-center"
      data-testid="cp-progress-radar"
    >
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[200px]">
        {ringPaths.map((p, i) => (
          <path
            key={i}
            d={p}
            fill="none"
            stroke="#EEE9F7"
            strokeWidth="1"
          />
        ))}
        {/* spokes */}
        {labels.map((_, i) => {
          const [x, y] = point(i, maxV);
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="#EEE9F7"
            />
          );
        })}
        {hasBaseline && (
          <path
            d={makePath(baseline)}
            fill="rgba(133,126,156,0.18)"
            stroke="#857E9C"
            strokeWidth="1.5"
            strokeDasharray="3 2"
          />
        )}
        <path
          d={makePath(recent)}
          fill="rgba(61,26,120,0.22)"
          stroke="#3D1A78"
          strokeWidth="1.8"
        />
        {labels.map((_, i) => {
          const [x, y] = point(i, maxV + 0.3);
          return (
            <text
              key={i}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="7"
              fill="#4B4567"
            >
              {i + 1}
            </text>
          );
        })}
      </svg>
      <div className="flex gap-3 text-[9px] text-slate-500 mt-1">
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-[#3D1A78]"></span>
          Latest
        </span>
        {hasBaseline && (
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm border border-dashed border-[#857E9C]"></span>
            ~60d ago
          </span>
        )}
      </div>
    </div>
  );
}

export function CpProgressTile({
  samplePdfUrl = "/api/insights/samples/coparenting-self-assessment.pdf",
  onRetake,
}) {
  const [state, setState] = useState({
    loading: true,
    error: null,
    data: null,
  });
  // iter235 — share flow state. "idle" | "open" | "sending" | "sent" | "error"
  const [shareState, setShareState] = useState("idle");
  const [shareError, setShareError] = useState("");
  const [shareForm, setShareForm] = useState({
    to_email: "",
    mediator_name: "",
    note: "",
  });
  // iter237 — recent share history with open status for the
  // "Opened by Dr. Rivera 2h ago" strip. Refreshed on mount and
  // after every successful send, plus a 30s poller while the tile
  // is mounted so a new open shows up without a page reload.
  const [shares, setShares] = useState([]);

  const refreshShares = async () => {
    try {
      const r = await api.get("/coparenting/report/progress/shares");
      setShares(Array.isArray(r?.data?.shares) ? r.data.shares : []);
    } catch {
      /* ignore — tile just hides the history strip */
    }
  };

  useEffect(() => {
    refreshShares();
    const t = window.setInterval(refreshShares, 30000);
    return () => window.clearInterval(t);
  }, []);

  const sendShare = async () => {
    const email = (shareForm.to_email || "").trim();
    if (!email || !email.includes("@")) {
      setShareError("Enter a valid email first.");
      return;
    }
    setShareError("");
    setShareState("sending");
    try {
      await api.post("/coparenting/report/progress/share", {
        to_email: email,
        mediator_name: shareForm.mediator_name.trim() || null,
        note: shareForm.note.trim() || null,
      });
      setShareState("sent");
      // Pull fresh share history so the "Share with X — not yet
      // opened" row shows up right next to the success card.
      refreshShares();
    } catch (e) {
      const detail = e?.response?.data?.detail || "Couldn't send right now.";
      setShareError(detail);
      setShareState("error");
    }
  };

  useEffect(() => {
    let alive = true;
    api
      .get("/coparenting/report/progress")
      .then((r) => {
        if (!alive) return;
        setState({ loading: false, error: null, data: r.data });
      })
      .catch((e) => {
        if (!alive) return;
        // 401 (not logged in) is a soft miss — just show the empty state.
        if (e?.response?.status === 401) {
          setState({ loading: false, error: null, data: null });
          return;
        }
        setState({ loading: false, error: String(e), data: null });
      });
    return () => {
      alive = false;
    };
  }, []);

  const fullBase = process.env.REACT_APP_BACKEND_URL || "";
  const sampleHref = samplePdfUrl.startsWith("http")
    ? samplePdfUrl
    : `${fullBase}${samplePdfUrl}`;

  if (state.loading) {
    return (
      <div
        className="rounded-2xl border border-slate-200 bg-white p-3 text-[11px] text-slate-500"
        data-testid="cp-progress-tile-loading"
      >
        Loading your assessment progress…
      </div>
    );
  }

  const data = state.data;
  const snapshots = data?.snapshots || [];
  const hasAny = snapshots.length > 0;

  // No history yet — show empty state with sample link + take-it CTA.
  if (!hasAny) {
    return (
      <div
        className="rounded-2xl border border-purple-200 bg-white p-3 space-y-2 card-box"
        data-testid="cp-progress-tile-empty"
      >
        <div className="flex items-start gap-2">
          <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
            <i className="fa-solid fa-chart-line text-purple-800 text-xs"></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
              Your assessment progress
            </div>
            <div className="text-xs font-bold text-slate-800 leading-snug">
              No check-ins yet
            </div>
            <p className="text-[11px] text-slate-600 leading-snug mt-0.5">
              Take the Co-Parenting Assessment to start a 60-day trendline.
              Preview what the finished report looks like first:
            </p>
            <a
              href={sampleHref}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="cp-progress-sample-link"
              className="inline-flex items-center gap-1 mt-1 text-[11px] font-bold text-purple-800 hover:underline"
            >
              <i className="fa-solid fa-file-pdf"></i>
              See a sample report
            </a>
          </div>
        </div>
      </div>
    );
  }

  const latest = data.recent;
  const retakeDue = !!data.retake_due;
  const days = data.days_since_last;
  const interval = data.retake_interval_days || 60;

  return (
    <div
      className="rounded-2xl border border-purple-200 bg-white p-3 space-y-3 card-box"
      data-testid="cp-progress-tile"
    >
      {retakeDue && (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 p-2.5 flex items-start gap-2"
          data-testid="cp-retake-banner"
        >
          <i className="fa-solid fa-rotate-right text-amber-700 text-xs mt-0.5"></i>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-bold text-amber-800 leading-snug">
              It's been {days} days since your last check-in
            </div>
            <p className="text-[10px] text-amber-800/80 leading-snug">
              Retake the assessment to see how you've changed since then.
            </p>
          </div>
          {typeof onRetake === "function" && (
            <button
              type="button"
              data-testid="cp-retake-btn"
              onClick={onRetake}
              className="shrink-0 py-1.5 px-3 bg-amber-700 hover:bg-amber-800 text-white rounded-md text-[10px] font-bold"
            >
              Retake
            </button>
          )}
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
            Your assessment progress
          </div>
          <div className="text-xs font-bold text-slate-800 leading-snug">
            {snapshots.length} check-in{snapshots.length === 1 ? "" : "s"} ·
            latest {fmtDate(latest.submitted_at)}
          </div>
        </div>
        <a
          href={sampleHref}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="cp-progress-sample-link"
          className="shrink-0 text-[10px] font-bold text-purple-800 hover:underline whitespace-nowrap"
        >
          <i className="fa-solid fa-file-pdf mr-1"></i>
          See sample
        </a>
      </div>

      <Sparkline series={data.overall_series || []} />

      {data.section_movers && data.section_movers.length > 0 && (
        <div className="pt-1">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
            Biggest movers vs ~{interval}d ago
          </div>
          <MoverBars movers={data.section_movers} />
        </div>
      )}

      {data.radar && (data.radar.labels || []).length >= 3 && (
        <div className="pt-1">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 text-center">
            Section balance · latest vs ~{interval}d ago
          </div>
          <Radar radar={data.radar} />
        </div>
      )}

      {/* iter235 — Share-with-mediator block.
          Download = direct PDF of this exact view.
          Share = inline mini-form, POSTs to /progress/share which
          emails a one-page attachment to the mediator with Reply-To
          set to the parent's own email. */}
      <div
        className="pt-2 border-t border-slate-100 space-y-2"
        data-testid="cp-progress-share-block"
      >
        {shareState !== "open" && shareState !== "sending" && (
          <div className="grid grid-cols-2 gap-2">
            <a
              href={`${fullBase}/api/coparenting/report/progress/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="cp-progress-download-btn"
              className="py-1.5 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-[11px] text-center"
            >
              <i className="fa-solid fa-file-arrow-down mr-1"></i>
              Download PDF
            </a>
            <button
              type="button"
              data-testid="cp-progress-open-share-btn"
              onClick={() => {
                setShareState("open");
                setShareError("");
              }}
              className="py-1.5 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-[11px]"
            >
              <i className="fa-solid fa-paper-plane mr-1"></i>
              Share with mediator
            </button>
          </div>
        )}

        {(shareState === "open" || shareState === "sending" || shareState === "error") && (
          <div
            className="p-2 rounded-xl border border-purple-200 bg-purple-50/40 space-y-1.5"
            data-testid="cp-progress-share-form"
          >
            <input
              type="email"
              value={shareForm.to_email}
              onChange={(e) =>
                setShareForm({ ...shareForm, to_email: e.target.value })
              }
              placeholder="mediator@example.com"
              data-testid="cp-progress-share-email"
              className="w-full text-[11px] px-2 py-1.5 bg-white border border-purple-300 rounded focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <input
              type="text"
              value={shareForm.mediator_name}
              onChange={(e) =>
                setShareForm({ ...shareForm, mediator_name: e.target.value })
              }
              placeholder="Mediator name (optional)"
              maxLength={120}
              data-testid="cp-progress-share-name"
              className="w-full text-[11px] px-2 py-1.5 bg-white border border-purple-300 rounded focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <textarea
              value={shareForm.note}
              onChange={(e) =>
                setShareForm({ ...shareForm, note: e.target.value })
              }
              placeholder="Add a short note (optional)"
              maxLength={1200}
              rows={2}
              data-testid="cp-progress-share-note"
              className="w-full text-[11px] px-2 py-1.5 bg-white border border-purple-300 rounded focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
            />
            {shareError && (
              <div
                className="text-[10px] text-rose-700 font-semibold leading-snug"
                data-testid="cp-progress-share-error"
              >
                {shareError}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                data-testid="cp-progress-share-cancel"
                onClick={() => {
                  setShareState("idle");
                  setShareError("");
                }}
                disabled={shareState === "sending"}
                className="py-1.5 bg-white border border-slate-300 text-slate-600 rounded font-bold text-[11px] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="cp-progress-share-send"
                onClick={sendShare}
                disabled={shareState === "sending"}
                className="py-1.5 bg-purple-800 hover:bg-purple-900 text-white rounded font-bold text-[11px] disabled:opacity-60"
              >
                {shareState === "sending" ? (
                  <>
                    <i className="fa-solid fa-circle-notch fa-spin mr-1"></i>
                    Sending…
                  </>
                ) : (
                  <>
                    <i className="fa-solid fa-paper-plane mr-1"></i>
                    Send PDF
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {shareState === "sent" && (
          <div
            className="p-2 rounded-xl border border-emerald-200 bg-emerald-50 flex items-start gap-2"
            data-testid="cp-progress-share-sent"
          >
            <i className="fa-solid fa-circle-check text-emerald-700 text-xs mt-0.5"></i>
            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-bold text-emerald-800 leading-snug">
                Progress Snapshot sent
              </div>
              <p className="text-[10px] text-emerald-800/80 leading-snug">
                We emailed the one-page PDF to{" "}
                <span className="font-semibold">{shareForm.to_email}</span>
                . Replies come straight to you.
              </p>
            </div>
            <button
              type="button"
              data-testid="cp-progress-share-sent-close"
              onClick={() => {
                setShareState("idle");
                setShareForm({ to_email: "", mediator_name: "", note: "" });
              }}
              className="shrink-0 text-[10px] font-bold text-emerald-800 underline"
            >
              Done
            </button>
          </div>
        )}

        {/* iter237 — Share history strip. One line per recent send
            with open status. Hidden entirely when there's nothing
            to show so the tile stays compact for new users. */}
        {shares.length > 0 && (
          <div
            className="pt-1"
            data-testid="cp-progress-share-history"
          >
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Share history
            </div>
            <ul className="space-y-1">
              {shares.slice(0, 3).map((s) => {
                const who =
                  (s.mediator_name && s.mediator_name.trim()) ||
                  s.to_email ||
                  "a mediator";
                const opened = !!s.opened_at;
                return (
                  <li
                    key={s.share_id}
                    data-testid={`cp-progress-share-row-${s.share_id}`}
                    className={
                      "flex items-start gap-2 p-1.5 rounded-lg border " +
                      (opened
                        ? "border-emerald-200 bg-emerald-50/60"
                        : "border-slate-200 bg-white")
                    }
                  >
                    <i
                      className={
                        opened
                          ? "fa-solid fa-envelope-open-text text-emerald-700 text-[11px] mt-0.5"
                          : "fa-solid fa-paper-plane text-slate-400 text-[11px] mt-0.5"
                      }
                    ></i>
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-semibold text-slate-800 leading-tight truncate">
                        {opened ? "Opened by " : "Sent to "}
                        <span className="text-slate-900">{who}</span>
                      </div>
                      <div className="text-[9px] text-slate-500 leading-tight">
                        {opened ? (
                          <>
                            {relativeAge(s.last_opened_at || s.opened_at)}
                            {s.open_count > 1 ? ` · ${s.open_count} opens` : ""}
                          </>
                        ) : (
                          <>Sent {relativeAge(s.sent_at)} · not yet opened</>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      {!retakeDue && days !== null && days !== undefined && (
        <p
          className="text-[10px] text-slate-400 text-center"
          data-testid="cp-progress-footnote"
        >
          Next check-in encouraged in {Math.max(0, interval - days)}{" "}
          day{Math.max(0, interval - days) === 1 ? "" : "s"}.
        </p>
      )}
    </div>
  );
}
