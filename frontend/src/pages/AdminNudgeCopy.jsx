/**
 * AdminNudgeCopy — admin-only editor for the Child-Needs share
 * nudge microcopy. Two textareas (headline + subhead), a note
 * field for the audit trail, and a live preview card that renders
 * exactly like the real nudge on the SNCv2 report page.
 *
 * Reads/writes:
 *   * GET  /api/public/nudge-copy/child-needs-share
 *   * POST /api/admin/nudge-copy/child-needs-share
 *   * POST /api/admin/nudge-copy/child-needs-share/reset
 *
 * Copy limits mirror the Pydantic validator (6-120, 10-600) so a
 * client-side counter shows the same guardrails the server enforces.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { toast } from "sonner";
import { Users, RotateCcw, Save, ShieldCheck, History, CornerUpLeft, Check, X as XIcon, Monitor, Smartphone, Camera } from "lucide-react";
import { toPng } from "html-to-image";
import { wordDiff } from "../utils/wordDiff";

const HEADLINE_MIN = 6;
const HEADLINE_MAX = 120;
const SUBHEAD_MIN = 10;
const SUBHEAD_MAX = 600;

function CharCounter({ value, min, max, testid }) {
  const len = (value || "").length;
  const overMax = len > max;
  const underMin = len > 0 && len < min;
  const cls = overMax
    ? "text-[#AA0033]"
    : underMin
    ? "text-[#B6663B]"
    : "text-[#857E9C]";
  return (
    <span
      className={`text-[10px] uppercase tracking-[0.14em] font-bold ${cls}`}
      data-testid={testid}
    >
      {len} / {max}
      {underMin ? ` · need ${min - len} more` : ""}
    </span>
  );
}

/**
 * Relative time formatter for the history list. "3d ago", "12h ago",
 * "just now". Falls back to the raw ISO if parsing fails so the row
 * still surfaces something usable.
 */
function relativeTime(iso) {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const diff = Date.now() - t;
  if (diff < 0) return "just now";
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  const mo = Math.floor(d / 30);
  if (mo < 12) return `${mo}mo ago`;
  const y = Math.floor(mo / 12);
  return `${y}y ago`;
}

/**
 * Render one side of a word diff. `side` is either "current" (dimmed
 * base + red strikethrough on removed tokens) or "incoming" (normal
 * base + bold+underline on added tokens). We render one <span> per
 * token so pure-whitespace tokens keep their layout without adding
 * visual highlight.
 */
function DiffText({ tokens, side, className = "" }) {
  const baseCurrent = "text-[#857E9C] leading-relaxed";
  const baseIncoming = "text-[#4B4567] leading-relaxed";
  const base = side === "current" ? baseCurrent : baseIncoming;
  return (
    <p className={`${base} ${className}`}>
      {tokens.map((tok, i) => {
        const isWhitespace = /^\s+$/.test(tok.text);
        if (isWhitespace) return <span key={i}>{tok.text}</span>;
        if (side === "current" && tok.removed) {
          return (
            <span
              key={i}
              className="line-through decoration-[#C43C3C] decoration-2 text-[#8A4747] bg-[#FBEAEA] rounded px-0.5"
            >
              {tok.text}
            </span>
          );
        }
        if (side === "incoming" && tok.added) {
          return (
            <span
              key={i}
              className="font-bold text-[#1A1330] bg-[#EADDF7] rounded px-0.5 underline decoration-[#3D1A78] decoration-2 underline-offset-2"
            >
              {tok.text}
            </span>
          );
        }
        return <span key={i}>{tok.text}</span>;
      })}
    </p>
  );
}

export default function AdminNudgeCopy() {
  const { user, loading } = useAuth();
  const [headline, setHeadline] = useState("");
  const [subhead, setSubhead] = useState("");
  const [note, setNote] = useState("");
  const [isDefault, setIsDefault] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  // Two-step Restore: clicking a history row's Restore button sets
  // `pendingRestore = { headline, subhead, reason }`. That surfaces
  // a diff card above the editor showing current (dimmed) vs incoming
  // (bold), and the admin explicitly clicks Apply to load into the
  // textareas. Prevents accidental clobbering of unsaved edits.
  const [pendingRestore, setPendingRestore] = useState(null);
  // Preview viewport toggle. "desktop" (default) renders the nudge at
  // the column's natural width — matches what parents on laptop/tablet
  // see. "mobile" wraps the same card in a 390px iPhone-shaped chrome
  // so admins can eyeball line breaks + button wrap on small screens
  // without leaving the editor.
  const [viewportMode, setViewportMode] = useState("desktop");
  const [downloadingPng, setDownloadingPng] = useState(false);
  // Ref on the outer wrapper of the iPhone frame + caption so
  // html-to-image can rasterize the phone chrome + the "iPhone ·
  // 390px viewport" label together into a single PNG that reads as
  // one polished artefact in Slack.
  const mobileFrameRef = useRef(null);

  const handleDownloadPng = async () => {
    if (!mobileFrameRef.current) return;
    setDownloadingPng(true);
    try {
      const dataUrl = await toPng(mobileFrameRef.current, {
        // Bake a soft page-tone background so the phone bezel does
        // not look like it's floating on a checkerboard when Slack
        // renders the PNG on a light theme.
        backgroundColor: "#F6F4FA",
        cacheBust: true,
        pixelRatio: 1,
      });
      // Trigger a native download with a dated filename so admins
      // can drop multiple exports into a Slack thread without
      // clobbering the previous one.
      const link = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 10);
      link.download = `sacoparents-nudge-preview-${stamp}.png`;
      link.href = dataUrl;
      link.click();
      toast.success("Downloaded — ready to drop into Slack.");
    } catch (err) {
      logError("admin-nudge-copy: png export failed", err);
      toast.error("Could not export the preview. Try again in a moment.");
    } finally {
      setDownloadingPng(false);
    }
  };

  const load = () =>
    api
      .get("/public/nudge-copy/child-needs-share")
      .then((r) => {
        setHeadline(r.data?.headline || "");
        setSubhead(r.data?.subhead || "");
        setIsDefault(!!r.data?.is_default);
      })
      .catch((err) => {
        logError("admin-nudge-copy: fetch failed", err);
      });

  const loadHistory = () =>
    api
      .get("/admin/nudge-copy/child-needs-share/history", { params: { limit: 5 } })
      .then((r) => {
        setHistory(r.data?.entries || []);
        setHistoryLoaded(true);
      })
      .catch((err) => {
        // Non-fatal — if admin gating fails here it also fails on
        // save, so let the save path own the "forbidden" transition.
        logError("admin-nudge-copy: fetch history failed", err);
        setHistory([]);
        setHistoryLoaded(true);
      });

  useEffect(() => {
    if (!user) return;
    load();
    loadHistory();
  }, [user]);

  const canSave = useMemo(() => {
    const h = headline.trim();
    const s = subhead.trim();
    return (
      h.length >= HEADLINE_MIN &&
      h.length <= HEADLINE_MAX &&
      s.length >= SUBHEAD_MIN &&
      s.length <= SUBHEAD_MAX &&
      !saving
    );
  }, [headline, subhead, saving]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const r = await api.post("/admin/nudge-copy/child-needs-share", {
        headline: headline.trim(),
        subhead: subhead.trim(),
        note: note.trim() || null,
      });
      setHeadline(r.data?.headline || "");
      setSubhead(r.data?.subhead || "");
      setIsDefault(!!r.data?.is_default);
      toast.success("Nudge copy updated — live for parents now.");
      // Refresh the history list so the freshly-saved row appears at
      // the top with a proper timestamp + updated_by attribution.
      loadHistory();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setForbidden(true);
        return;
      }
      logError("admin-nudge-copy: save failed", err);
      const msg = err?.response?.data?.detail || "Could not save the copy.";
      toast.error(typeof msg === "string" ? msg : "Could not save the copy.");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (
      !window.confirm(
        "Revert to the hardcoded default copy? This clears your admin override immediately.",
      )
    ) {
      return;
    }
    setResetting(true);
    try {
      const r = await api.post(
        "/admin/nudge-copy/child-needs-share/reset",
      );
      setHeadline(r.data?.headline || "");
      setSubhead(r.data?.subhead || "");
      setNote("");
      setIsDefault(!!r.data?.is_default);
      toast.success("Reverted to defaults.");
    } catch (err) {
      logError("admin-nudge-copy: reset failed", err);
      toast.error("Could not reset the copy.");
    } finally {
      setResetting(false);
    }
  };

  const handleRestore = (entry) => {
    // Prompt for a fresh audit-trail note so the next save row
    // captures WHY the admin rolled back. Falls back to the prior
    // note when the admin dismisses or leaves it blank, so the
    // history row is never blank on a restore.
    const suggested = entry.note
      ? `Reverting from: ${entry.note}`
      : "Reverting to prior wording";
    const reason = window.prompt(
      `Restore this version?\n\n` +
        `Headline: ${entry.headline}\n\n` +
        `Add a note explaining why (kept on the next save's audit trail):`,
      suggested,
    );
    if (reason === null) return; // Cancel → no state change
    // Stage the restore so the admin sees a diff (current vs incoming)
    // before the textareas are clobbered. They confirm via Apply.
    setPendingRestore({
      headline: entry.headline || "",
      subhead: entry.subhead || "",
      reason: (reason || "").trim() || entry.note || suggested,
    });
    toast.info(
      "Loaded prior version — review the diff below and click Apply.",
    );
    // Scroll editor into view so the diff card is obvious.
    try {
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (_) { /* ignore */ }
  };

  const applyPendingRestore = () => {
    if (!pendingRestore) return;
    setHeadline(pendingRestore.headline);
    setSubhead(pendingRestore.subhead);
    setNote(pendingRestore.reason);
    setPendingRestore(null);
    toast.success(
      "Loaded into the editor. Click Save to make it live for parents.",
    );
  };

  const cancelPendingRestore = () => {
    setPendingRestore(null);
  };

  // Word-level diffs for the Diff card. Only computed when a restore
  // is staged — the memo shortcuts otherwise. Both sides reference
  // the CURRENT editor values (headline/subhead), so if the admin
  // typed manual edits before clicking Restore, those edits are what
  // the diff highlights against — not the stale server-side copy.
  const headlineDiff = useMemo(() => {
    if (!pendingRestore) return null;
    return wordDiff(headline, pendingRestore.headline);
  }, [pendingRestore, headline]);
  const subheadDiff = useMemo(() => {
    if (!pendingRestore) return null;
    return wordDiff(subhead, pendingRestore.subhead);
  }, [pendingRestore, subhead]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  if (forbidden) {
    return (
      <AppShell>
        <div
          className="card-soft p-8 text-center max-w-lg mx-auto"
          data-testid="admin-nudge-copy-forbidden"
        >
          <div className="w-12 h-12 mx-auto rounded-full bg-[#FFF1E2] grid place-items-center text-[#B6663B] mb-3">
            <ShieldCheck size={20} />
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">
            This editor is restricted to the SA CoParents app owner.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="fade-up space-y-6 max-w-5xl mx-auto" data-testid="admin-nudge-copy">
        <div className="card-soft p-7 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative">
            <div className="eyebrow mb-2">Admin · microcopy</div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">
              Child-Needs share nudge
            </h1>
            <p className="text-sm text-[#4B4567] mt-2 max-w-2xl">
              Edit the headline + subhead parents see on the SNCv2 report
              page. Saved copy is live for every parent on next page
              load — no build required.{" "}
              {isDefault ? (
                <span
                  className="inline-block ml-1 px-2 py-0.5 rounded-full bg-[#F5EFFB] text-[10px] uppercase tracking-[0.14em] font-bold text-[#3D1A78]"
                  data-testid="admin-nudge-copy-default-badge"
                >
                  Showing defaults
                </span>
              ) : (
                <span
                  className="inline-block ml-1 px-2 py-0.5 rounded-full bg-[#FFF3D6] text-[10px] uppercase tracking-[0.14em] font-bold text-[#7A4D0C]"
                  data-testid="admin-nudge-copy-override-badge"
                >
                  Custom override active
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Diff card — visible only while a Restore is pending. Lets
            the admin eyeball the delta before clobbering unsaved edits. */}
        {pendingRestore && (
          <div
            className="card-soft border-2 border-[#3D1A78] p-6"
            data-testid="admin-nudge-copy-diff"
            role="dialog"
            aria-labelledby="admin-nudge-copy-diff-heading"
          >
            <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
              <div>
                <div className="eyebrow text-[#3D1A78]">Restore preview</div>
                <h2
                  id="admin-nudge-copy-diff-heading"
                  className="font-serif text-xl text-[#1A1330] mt-1"
                >
                  Compare before you apply
                </h2>
                <p className="text-xs text-[#857E9C] mt-1">
                  Grey = what's in the editor now. Purple = incoming version.
                  Nothing is saved until you click Apply <em>then</em> Save.
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  type="button"
                  onClick={cancelPendingRestore}
                  data-testid="admin-nudge-copy-diff-cancel"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white border border-[#3D1A78]/25 text-[#3D1A78] text-sm font-semibold hover:bg-[#F5EFFB]"
                >
                  <XIcon size={14} />
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={applyPendingRestore}
                  data-testid="admin-nudge-copy-diff-apply"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2B0F60]"
                >
                  <Check size={14} />
                  Apply to editor
                </button>
              </div>
            </div>
            {/* Headline diff */}
            <div className="grid sm:grid-cols-2 gap-3 sm:gap-5">
              <div
                className="rounded-2xl bg-[#F6F4FA] border border-[#EEE8F7] p-4"
                data-testid="admin-nudge-copy-diff-current"
              >
                <div className="eyebrow mb-2 text-[#857E9C]">
                  Current headline
                </div>
                {headline ? (
                  <DiffText
                    tokens={headlineDiff?.current || []}
                    side="current"
                    className="text-sm"
                  />
                ) : (
                  <p className="text-sm text-[#857E9C] italic">(empty)</p>
                )}
                <div className="eyebrow mt-4 mb-2 text-[#857E9C]">
                  Current subhead
                </div>
                {subhead ? (
                  <DiffText
                    tokens={subheadDiff?.current || []}
                    side="current"
                    className="text-[13px] whitespace-pre-line"
                  />
                ) : (
                  <p className="text-[13px] text-[#857E9C] italic">(empty)</p>
                )}
              </div>
              <div
                className="rounded-2xl bg-[#F5EFFB] border-2 border-[#3D1A78] p-4"
                data-testid="admin-nudge-copy-diff-incoming"
              >
                <div className="eyebrow mb-2 text-[#3D1A78]">
                  Incoming headline
                </div>
                <DiffText
                  tokens={headlineDiff?.incoming || []}
                  side="incoming"
                  className="text-sm"
                />
                <div className="eyebrow mt-4 mb-2 text-[#3D1A78]">
                  Incoming subhead
                </div>
                <DiffText
                  tokens={subheadDiff?.incoming || []}
                  side="incoming"
                  className="text-[13px] whitespace-pre-line"
                />
              </div>
            </div>
            <div className="mt-3 text-[11px] text-[#857E9C] italic flex flex-wrap gap-x-3 gap-y-1">
              <span>
                <span className="line-through decoration-[#C43C3C] decoration-2 text-[#8A4747] bg-[#FBEAEA] rounded px-0.5 not-italic">
                  removed
                </span>{" "}
                on the current side
              </span>
              <span>·</span>
              <span>
                <span className="font-bold text-[#1A1330] bg-[#EADDF7] rounded px-0.5 underline decoration-[#3D1A78] decoration-2 underline-offset-2 not-italic">
                  added
                </span>{" "}
                on the incoming side
              </span>
            </div>
            <div className="mt-2 text-[11px] text-[#857E9C] italic">
              Restore note will be pre-filled:{" "}
              <span className="text-[#3D1A78] font-semibold not-italic">
                {pendingRestore.reason}
              </span>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Editor */}
          <div className="card-soft p-6 space-y-5">
            <div>
              <div className="flex items-baseline justify-between mb-1">
                <label
                  htmlFor="admin-nudge-copy-headline"
                  className="eyebrow"
                >
                  Headline
                </label>
                <CharCounter
                  value={headline}
                  min={HEADLINE_MIN}
                  max={HEADLINE_MAX}
                  testid="admin-nudge-copy-headline-counter"
                />
              </div>
              <textarea
                id="admin-nudge-copy-headline"
                rows={2}
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                maxLength={HEADLINE_MAX + 20}
                className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                data-testid="admin-nudge-copy-headline-input"
              />
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-1">
                <label
                  htmlFor="admin-nudge-copy-subhead"
                  className="eyebrow"
                >
                  Subhead
                </label>
                <CharCounter
                  value={subhead}
                  min={SUBHEAD_MIN}
                  max={SUBHEAD_MAX}
                  testid="admin-nudge-copy-subhead-counter"
                />
              </div>
              <textarea
                id="admin-nudge-copy-subhead"
                rows={5}
                value={subhead}
                onChange={(e) => setSubhead(e.target.value)}
                maxLength={SUBHEAD_MAX + 40}
                className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                data-testid="admin-nudge-copy-subhead-input"
              />
            </div>

            <div>
              <label
                htmlFor="admin-nudge-copy-note"
                className="eyebrow block mb-1"
              >
                Note <span className="lowercase text-[#857E9C] font-normal">(optional · audit trail)</span>
              </label>
              <input
                id="admin-nudge-copy-note"
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={200}
                placeholder="e.g. softer variant, week of 2026-09-15"
                className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                data-testid="admin-nudge-copy-note-input"
              />
            </div>

            <div className="flex flex-wrap gap-3 pt-1">
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                data-testid="admin-nudge-copy-save"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2B0F60] disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Save size={14} />
                {saving ? "Saving…" : "Save copy"}
              </button>
              <button
                type="button"
                onClick={handleReset}
                disabled={resetting || isDefault}
                data-testid="admin-nudge-copy-reset"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white border border-[#3D1A78]/25 text-[#3D1A78] text-sm font-semibold hover:bg-[#F5EFFB] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <RotateCcw size={14} />
                {resetting ? "Resetting…" : "Revert to defaults"}
              </button>
            </div>
          </div>

          {/* Live preview — mimics ShareChildNeedsNudge.jsx */}
          <div className="min-w-0">
            <div className="mb-2 flex items-center justify-between gap-2 flex-wrap">
              <div className="eyebrow flex items-center gap-2">
                Live preview
                <span className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
                  (as parents see it)
                </span>
              </div>
              {/* Desktop / Mobile viewport toggle. Segmented control
                  — the active pill has the purple fill, the inactive
                  pill is white with a subtle border. Buttons are the
                  same width for a stable click target. The Download
                  PNG action lives next to the toggle and only surfaces
                  in Mobile mode (Desktop mode is not a shareable
                  artefact — it's just a card). */}
              <div className="flex items-center gap-2 flex-wrap">
                {viewportMode === "mobile" && (
                  <button
                    type="button"
                    onClick={handleDownloadPng}
                    disabled={downloadingPng}
                    data-testid="admin-nudge-copy-preview-download-png"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-[#3D1A78]/25 text-[11px] font-bold uppercase tracking-[0.12em] text-[#3D1A78] hover:bg-[#F5EFFB] disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    <Camera size={12} />
                    {downloadingPng ? "Saving…" : "Download PNG"}
                  </button>
                )}
                <div
                  className="inline-flex rounded-full bg-white border border-[#D6CFE8] p-0.5 shadow-sm"
                  role="group"
                  aria-label="Preview viewport"
                  data-testid="admin-nudge-copy-preview-frame-toggle"
                >
                  <button
                    type="button"
                    onClick={() => setViewportMode("desktop")}
                    aria-pressed={viewportMode === "desktop"}
                    data-testid="admin-nudge-copy-preview-desktop"
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.12em] transition-colors ${
                      viewportMode === "desktop"
                        ? "bg-[#3D1A78] text-white"
                        : "text-[#4B4567] hover:bg-[#F5EFFB]"
                    }`}
                  >
                    <Monitor size={12} />
                    Desktop
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewportMode("mobile")}
                    aria-pressed={viewportMode === "mobile"}
                    data-testid="admin-nudge-copy-preview-mobile"
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.12em] transition-colors ${
                      viewportMode === "mobile"
                        ? "bg-[#3D1A78] text-white"
                        : "text-[#4B4567] hover:bg-[#F5EFFB]"
                    }`}
                  >
                    <Smartphone size={12} />
                    Mobile
                  </button>
                </div>
              </div>
            </div>
            {viewportMode === "mobile" ? (
              // iPhone-shaped frame at 390px viewport width. Pure CSS
              // — no image assets. The outer div is the phone bezel
              // (dark, rounded, subtle shadow). The inner scroll area
              // simulates the phone screen and is exactly 390px so
              // Tailwind's `sm:` breakpoints inside the nudge card
              // resolve to their mobile variants (identical to what a
              // real iPhone renders).
              //
              // `overflow-x-auto` on the wrapper lets the 418px frame
              // stay side-by-side with the editor at desktop widths,
              // and on very narrow admin screens (like the admin's own
              // phone) the frame scrolls horizontally instead of
              // widening the grid column.
              <div
                className="overflow-x-auto -mx-2 px-2"
                data-testid="admin-nudge-copy-preview-mobile-frame"
              >
                <div ref={mobileFrameRef} className="mx-auto" style={{ width: "414px" }}>
                  <div className="relative rounded-[3rem] bg-[#1A1330] p-3 shadow-2xl">
                  {/* Dynamic Island / notch — visual anchor so the
                      frame reads as a phone at a glance. */}
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 h-6 w-28 rounded-full bg-black z-10" />
                  <div
                    className="rounded-[2.25rem] bg-[#FAF6FF] overflow-hidden"
                    style={{ width: "390px", height: "720px" }}
                  >
                    {/* Fake iOS status bar so the phone illusion holds. */}
                    <div className="h-11 flex items-end justify-between px-6 pb-1 text-[11px] font-semibold text-[#1A1330]">
                      <span>9:41</span>
                      <span className="opacity-0">·</span>
                      <span className="tracking-tight">•••</span>
                    </div>
                    <div className="h-[calc(720px-2.75rem)] overflow-y-auto px-4 pb-8">
                      <section
                        className="rounded-3xl border-2 border-[#D6CFE8] bg-gradient-to-br from-[#FAF6FF] to-[#F1E7FA] p-5"
                        data-testid="admin-nudge-copy-preview"
                      >
                        <div className="flex items-start gap-3">
                          <div className="rounded-full bg-white/70 p-2 mt-0.5 shrink-0">
                            <Users size={16} className="text-[#3D1A78]" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                              Optional · you're in control
                            </div>
                            <h3
                              className="font-serif text-lg text-[#1A1330] mt-1 leading-snug"
                              data-testid="admin-nudge-copy-preview-headline"
                            >
                              {headline || <span className="text-[#857E9C] italic">Headline will appear here</span>}
                            </h3>
                            <p
                              className="text-sm text-[#4B4567] mt-2 leading-relaxed whitespace-pre-line"
                              data-testid="admin-nudge-copy-preview-subhead"
                            >
                              {subhead || <span className="text-[#857E9C] italic">Subhead will appear here</span>}
                            </p>
                          </div>
                        </div>
                        <div className="mt-4 rounded-2xl border border-[#EEE8F7] bg-white p-3">
                          <div className="text-[13px] font-semibold text-[#1A1330]">
                            SA-DEMO01
                            <span className="text-[#4B4567] font-normal"> · with Riley Parent</span>
                          </div>
                          <div className="text-[11px] uppercase tracking-[0.14em] font-bold mt-1 text-[#857E9C]">
                            Neither has consented yet
                          </div>
                        </div>
                        <p className="mt-3 text-[11px] text-[#857E9C] italic leading-relaxed">
                          Educational and organizational — not a diagnosis, not a court
                          submission. You can change this any time from the joint report
                          page.
                        </p>
                      </section>
                    </div>
                  </div>
                </div>
                <p className="text-center text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mt-3">
                  iPhone · 390px viewport
                </p>
                </div>
              </div>
            ) : (
              <section
                className="rounded-3xl border-2 border-[#D6CFE8] bg-gradient-to-br from-[#FAF6FF] to-[#F1E7FA] p-5 sm:p-6"
                data-testid="admin-nudge-copy-preview"
              >
                <div className="flex items-start gap-3">
                  <div className="rounded-full bg-white/70 p-2 mt-0.5 shrink-0">
                    <Users size={16} className="text-[#3D1A78]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                      Optional · you're in control
                    </div>
                    <h3
                      className="font-serif text-lg sm:text-xl text-[#1A1330] mt-1 leading-snug"
                      data-testid="admin-nudge-copy-preview-headline"
                    >
                      {headline || <span className="text-[#857E9C] italic">Headline will appear here</span>}
                    </h3>
                    <p
                      className="text-sm text-[#4B4567] mt-2 leading-relaxed whitespace-pre-line"
                      data-testid="admin-nudge-copy-preview-subhead"
                    >
                      {subhead || <span className="text-[#857E9C] italic">Subhead will appear here</span>}
                    </p>
                  </div>
                </div>
                <div className="mt-4 rounded-2xl border border-[#EEE8F7] bg-white p-3 sm:p-4">
                  <div className="text-[13px] font-semibold text-[#1A1330]">
                    SA-DEMO01
                    <span className="text-[#4B4567] font-normal"> · with Riley Parent</span>
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.14em] font-bold mt-1 text-[#857E9C]">
                    Neither has consented yet
                  </div>
                </div>
                <p className="mt-3 text-[11px] text-[#857E9C] italic leading-relaxed">
                  Educational and organizational — not a diagnosis, not a court
                  submission. You can change this any time from the joint report
                  page.
                </p>
              </section>
            )}
          </div>
        </div>

        {/* Recent versions — restore-only, no in-place edit. */}
        <div
          className="card-soft p-6"
          data-testid="admin-nudge-copy-history"
        >
          <div className="flex items-center justify-between mb-3 gap-3">
            <div className="eyebrow flex items-center gap-2">
              <History size={12} className="text-[#3D1A78]" />
              Recent versions
            </div>
            <span className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
              Last {history.length || 0} of 5
            </span>
          </div>
          {!historyLoaded ? (
            <p className="text-sm text-[#857E9C] animate-pulse">
              Loading revision log…
            </p>
          ) : history.length === 0 ? (
            <p
              className="text-sm text-[#857E9C] italic"
              data-testid="admin-nudge-copy-history-empty"
            >
              No custom versions saved yet. Your first Save will appear
              here as version 1 with a Restore button.
            </p>
          ) : (
            <ol className="space-y-3" data-testid="admin-nudge-copy-history-list">
              {history.map((entry, idx) => (
                <li
                  key={`${entry.updated_at}-${idx}`}
                  className="rounded-2xl border border-[#EEE8F7] bg-white p-4 flex items-start gap-3"
                  data-testid={`admin-nudge-copy-history-item-${idx}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold text-[#1A1330] truncate">
                      {entry.headline}
                    </div>
                    <div className="text-[12px] text-[#4B4567] mt-1 line-clamp-2">
                      {entry.subhead}
                    </div>
                    {entry.note && (
                      <div className="text-[11px] text-[#857E9C] mt-1 italic truncate">
                        Note: {entry.note}
                      </div>
                    )}
                    <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] mt-2 flex flex-wrap gap-x-3 gap-y-0.5">
                      <span>{relativeTime(entry.updated_at)}</span>
                      <span>· {entry.updated_by}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRestore(entry)}
                    data-testid={`admin-nudge-copy-history-restore-${idx}`}
                    className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-[#3D1A78]/25 text-xs font-semibold text-[#3D1A78] hover:bg-[#F5EFFB]"
                  >
                    <CornerUpLeft size={12} />
                    Restore
                  </button>
                </li>
              ))}
            </ol>
          )}
          <p className="text-[11px] text-[#857E9C] italic mt-3 leading-relaxed">
            Restore loads a prior version into the editor without
            saving. Click Save once you've reviewed it to make it live.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
