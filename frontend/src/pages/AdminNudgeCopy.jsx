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
import React, { useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { toast } from "sonner";
import { Users, RotateCcw, Save, ShieldCheck, History, CornerUpLeft } from "lucide-react";

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
    setHeadline(entry.headline || "");
    setSubhead(entry.subhead || "");
    setNote((reason || "").trim() || entry.note || suggested);
    toast.info(
      "Loaded prior version into the editor — click Save to activate.",
    );
    // Scroll editor into view so it's obvious the textareas changed.
    try {
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (_) { /* ignore */ }
  };

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
          <div>
            <div className="eyebrow mb-2 flex items-center gap-2">
              Live preview
              <span className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
                (as parents see it)
              </span>
            </div>
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
