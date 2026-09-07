import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Lock,
  Wind,
  Check,
  ArrowLeft,
  Loader2,
  Heart,
  Send,
  Trash2,
  RefreshCw,
  History as HistoryIcon,
  PencilLine,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import SafetyAlert from "../components/SafetyAlert";
import BreathingExercise from "../components/BreathingExercise";
import FoundationStatementShareModal from "../components/foundation/FoundationStatementShareModal";
import { api } from "../lib/api";
import { logError } from "../lib/logger";
import { detectSafetyConcern } from "../lib/safety";
import WatchFirstVideo from "../components/WatchFirstVideo";

const PROMPTS = [
  {
    id: "child_lens",
    label: "Through your child's eyes",
    placeholder:
      "If your child described the last week of co-parenting to a teacher, what would they say?",
    icon: Heart,
  },
  {
    id: "own_part",
    label: "Your own part",
    placeholder:
      "Without blaming anyone, what's one thing you contributed to the difficulty? (No one else will see this.)",
    icon: Sparkles,
  },
  {
    id: "best_outcome",
    label: "Your best-case outcome",
    placeholder:
      "Six months from now, what does a calmer week of co-parenting look like for everyone — including your co-parent?",
    icon: Wind,
  },
  {
    id: "coparent_feedback",
    label: "Through your co-parent's eyes",
    placeholder:
      "What feedback might my child's other parent give about how I handled this interaction? (Try to imagine it honestly — even if you disagree.)",
    icon: Lock,
  },
];

function fmtDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      return `Today · ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    const yest = new Date(now);
    yest.setDate(yest.getDate() - 1);
    if (d.toDateString() === yest.toDateString()) {
      return `Yesterday · ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function Reflection() {
  const [entries, setEntries] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [tab, setTab] = useState("write"); // "write" | "history"
  const [shareOpen, setShareOpen] = useState(false);
  // Autosave plumbing — a debounced background save fires 1.5s after
  // the parent stops typing, so nobody ever loses a keystroke to the
  // browser dying / phone sleeping / accidental back-tap. `pendingRef`
  // tracks the latest entries shape so the flusher always sends the
  // *newest* content, not a stale snapshot captured at debounce time.
  const debounceTimerRef = useRef(null);
  const pendingRef = useRef(null);
  const lastSavedJsonRef = useRef("");
  const inFlightRef = useRef(false);

  // Actual writer. Compares against `lastSavedJsonRef` so we don't
  // fire a save when nothing changed (e.g., a blur event after a
  // load with no edits). Best-effort — silent toast on failure so
  // background saves don't pester the parent.
  const flushSave = useCallback(async () => {
    if (inFlightRef.current) return;
    const snapshot = pendingRef.current;
    if (!snapshot) return;
    const json = JSON.stringify(snapshot);
    if (json === lastSavedJsonRef.current) return;
    inFlightRef.current = true;
    try {
      await api.put("/mediation/reflection", snapshot);
      lastSavedJsonRef.current = json;
      setSavedAt(new Date());
    } catch (err) {
      // Autosave is best-effort — parent can still hit the visible
      // Save button. Log for us but don't toast (would be noisy on
      // flaky Wi-Fi).
      logError("Autosave failed:", err);
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  // Clear the debounce timer on unmount so we don't schedule a save
  // against a component that's already gone.
  useEffect(() => () => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
  }, []);

  // Save-on-hide: if the parent switches tab or closes the app on
  // mobile, flush any pending edits synchronously. Uses `sendBeacon`
  // when available so the request survives the page unload.
  useEffect(() => {
    const flushOnHide = () => {
      const snapshot = pendingRef.current;
      if (!snapshot) return;
      const json = JSON.stringify(snapshot);
      if (json === lastSavedJsonRef.current) return;
      try {
        const url = `${process.env.REACT_APP_BACKEND_URL}/api/mediation/reflection`;
        if (typeof navigator !== "undefined" && navigator.sendBeacon) {
          const blob = new Blob([json], { type: "application/json" });
          navigator.sendBeacon(url, blob);
          lastSavedJsonRef.current = json;
        } else {
          flushSave();
        }
      } catch {
        /* soft-fail — the parent still has the explicit Save button */
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "hidden") flushOnHide();
    };
    window.addEventListener("pagehide", flushOnHide);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pagehide", flushOnHide);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [flushSave]);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        const reflection = r.data?.reflection || {};
        setEntries(reflection);
        // Seed the "last saved" fingerprint so autosave doesn't
        // resave the initial load or blur.
        lastSavedJsonRef.current = JSON.stringify(reflection);
        pendingRef.current = reflection;
      })
      .catch((err) => logError("Failed to load reflection:", err))
      .finally(() => setLoading(false));
    // Mount-only fetch. `api`, setters, logError are stable.
  }, []);

  const updateEntry = (id, val) => {
    setEntries((prev) => {
      const next = { ...prev, [id]: val };
      // Track newest snapshot in a ref so `flushSave` always sends
      // the latest content (avoids stale-closure bugs when the
      // debounce fires later).
      pendingRef.current = next;
      return next;
    });
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      flushSave();
    }, 1500);
  };

  // Immediate flush when a textarea loses focus — safety net so
  // "type → tab away" always persists without waiting for the debounce.
  const flushNow = useCallback(() => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    flushSave();
  }, [flushSave]);

  const safetyLevel = useMemo(() => {
    // Only concat string values — the persisted reflection dict may also
    // carry non-string flags (e.g., `private: true`) that must not be
    // coerced into "true" text or fed into `.trim()` downstream.
    const combined = Object.values(entries || {})
      .filter((v) => typeof v === "string" && v)
      .join(" \n ");
    return detectSafetyConcern(combined);
  }, [entries]);
  const [safetyDismissed, setSafetyDismissed] = useState(false);

  const hasContent = Object.values(entries || {}).some(
    (v) => typeof v === "string" && v.trim().length > 0,
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/reflection", entries);
      setSavedAt(new Date());
      toast.success("Reflection saved privately.");
    } catch (err) {
      logError("Save reflection failed:", err);
      toast.error("Couldn't save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <div className="fade-up max-w-3xl mx-auto" data-testid="reflection-page">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-5"
          data-testid="reflection-back-link"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </Link>

        <div className="eyebrow mb-3">Personal Reflection</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          A quieter conversation with yourself.
        </h1>
        <p className="text-[15px] text-[#4B4567] mt-4 leading-relaxed max-w-2xl" data-testid="reflection-intro">
          At the start of each day, take a moment to share your thoughts and feelings about
          your situation. Everything you write remains completely private and is never shared
          with anyone unless you decide to do so. Revisit your journal from time to time to
          reflect on your progress and experiences.
        </p>

        <div className="mt-3 flex items-center gap-2 text-[12px] text-[#857E9C]">
          <Lock size={12} className="text-[#3D1A78]" />
          <span>
            Private to you. Never shared, never seen by mediator unless you explicitly include it.{" "}
            <Link to="/delete-account" className="underline hover:text-[#4B4567]">
              Delete anytime
            </Link>
            .
          </span>
        </div>

        <div className="mt-3">
          <Link
            to="/foundation/demo"
            className="inline-flex items-center gap-1 text-xs text-[#3D1A78] hover:underline font-semibold"
            data-testid="reflection-see-example"
          >
            See what a finished Foundation Statement looks like →
          </Link>
        </div>

        {/* Tab strip */}
        <div className="mt-7 inline-flex bg-[#EFE9F9] rounded-full p-1" data-testid="reflection-tabs">
          <button
            type="button"
            onClick={() => setTab("write")}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition inline-flex items-center gap-1.5 ${
              tab === "write" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
            }`}
            data-testid="reflection-tab-write"
          >
            <PencilLine size={14} /> Write
          </button>
          <button
            type="button"
            onClick={() => setTab("history")}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition inline-flex items-center gap-1.5 ${
              tab === "history" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
            }`}
            data-testid="reflection-tab-history"
          >
            <HistoryIcon size={14} /> History
          </button>
        </div>

        {tab === "write" ? (
          <>
            <div className="mt-8">
              <WatchFirstVideo
                videoSrc="/videos/reflection-foundation.mp4"
                subtitle="Create Foundation Statement — watch before you write"
                testid="reflection-watch"
              />
            </div>

            {/* Breathing exercise card */}
            <div className="mt-8">
              <BreathingExercise cycles={4} />
            </div>

            {safetyLevel && !safetyDismissed && (
              <SafetyAlert
                level={safetyLevel}
                onDismiss={() => setSafetyDismissed(true)}
              />
            )}

            <div className="mt-10">
              <div className="eyebrow mb-4">Prompts</div>
              {loading ? (
                <div className="text-sm text-[#857E9C]">Loading…</div>
              ) : (
                <div className="space-y-4">
                  {PROMPTS.map((p) => (
                    <PromptCard
                      key={p.id}
                      prompt={p}
                      value={entries[p.id] || ""}
                      onChange={(v) => updateEntry(p.id, v)}
                      onBlur={flushNow}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="sticky bottom-4 mt-10">
              <div className="card-soft p-4 sm:p-5 flex items-center justify-between gap-4">
                <div className="text-[13px] text-[#4B4567] flex items-center gap-2 min-w-0">
                  {savedAt ? (
                    <>
                      <Check size={14} className="text-[#3D1A78] shrink-0" />
                      <span className="truncate">
                        Autosaved {savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </>
                  ) : hasContent ? (
                    <span className="italic text-[#857E9C]">
                      Autosaving as you type…
                    </span>
                  ) : (
                    <span className="text-[#857E9C]">
                      Your words stay with you — saved automatically.
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {savedAt && hasContent && (
                    <button
                      type="button"
                      onClick={() => setShareOpen(true)}
                      className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-2 text-sm font-semibold transition-colors"
                      data-testid="reflection-share-button"
                    >
                      <Send size={13} /> Send to co-parent or mediator
                    </button>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={saving || !hasContent}
                    className="btn-sage inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="reflection-save-button"
                  >
                    {saving ? (
                      <>
                        <Loader2 size={14} className="animate-spin" /> Saving…
                      </>
                    ) : (
                      "Save reflection"
                    )}
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <JournalHistory />
        )}
      </div>
      <FoundationStatementShareModal
        open={shareOpen}
        onClose={() => setShareOpen(false)}
      />
    </AppShell>
  );
}

function PromptCard({ prompt, value, onChange, onBlur }) {
  const { id, label, placeholder, icon: Icon } = prompt;
  return (
    <div className="card-soft p-5 sm:p-6" data-testid={`reflection-prompt-${id}`}>
      <div className="flex items-start gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-[#3D1A78]/15 text-[#3D1A78] grid place-items-center shrink-0">
          <Icon size={16} />
        </div>
        <div className="font-serif text-lg sm:text-xl text-[#1A1330] leading-snug">
          {label}
        </div>
      </div>
      <textarea
        rows={4}
        className="input-soft resize-none"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        data-testid={`reflection-textarea-${id}`}
      />
    </div>
  );
}

/* ============================================================
   HISTORY TAB — Journal
============================================================ */
function JournalHistory() {
  const [prompt, setPrompt] = useState(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recap, setRecap] = useState(null);
  const [recapLoading, setRecapLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/journal/prompt").then((r) => r.data),
      api.get("/journal/entries?limit=50").then((r) => r.data),
    ])
      .then(([p, list]) => {
        setPrompt(p);
        setEntries(list.entries || []);
      })
      .catch((err) => logError("Load journal failed:", err))
      .finally(() => setLoading(false));
  }, []);

  // Lazy-fetch the weekly recap (only when there's enough material)
  useEffect(() => {
    if (entries.length < 2) return;
    setRecapLoading(true);
    api
      .get("/journal/weekly-recap")
      .then((r) => setRecap(r.data))
      .catch((err) => logError("Recap failed:", err))
      .finally(() => setRecapLoading(false));
  }, [entries.length]);

  const submitDaily = async (e) => {
    e?.preventDefault?.();
    const content = draft.trim();
    if (!content || saving) return;
    setSaving(true);
    try {
      const r = await api.post("/journal/entries", {
        content,
        prompt_id: prompt?.prompt_id,
      });
      setEntries((prev) => [r.data, ...prev]);
      setDraft("");
      toast.success("Saved to your journal.");
    } catch (err) {
      logError("Create journal entry failed:", err);
      toast.error("Couldn't save the entry.");
    } finally {
      setSaving(false);
    }
  };

  const deleteEntry = async (entry_id) => {
    try {
      await api.delete(`/journal/entries/${entry_id}`);
      setEntries((prev) => prev.filter((e) => e.entry_id !== entry_id));
      toast.success("Entry removed.");
    } catch (err) {
      logError("Delete entry failed:", err);
      toast.error("Couldn't delete.");
    }
  };

  if (loading) {
    return (
      <div className="mt-8 text-sm text-[#857E9C]" data-testid="journal-loading">
        Loading your journal…
      </div>
    );
  }

  return (
    <div className="mt-8 space-y-6" data-testid="journal-history">
      {/* Today's prompt + quick add */}
      <form
        onSubmit={submitDaily}
        className="card-soft p-5 sm:p-6"
        data-testid="journal-quick-add"
      >
        <div className="eyebrow text-[#3D1A78] mb-2">Today's gentle prompt</div>
        <p className="font-serif text-lg sm:text-xl text-[#1A1330] mb-4 leading-snug">
          {prompt?.prompt_text || "What's on your mind today?"}
        </p>
        <textarea
          rows={3}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="A sentence or two is plenty…"
          className="input-soft resize-none"
          data-testid="journal-draft-textarea"
        />
        <div className="flex items-center justify-between mt-3 gap-3">
          <div className="text-xs text-[#857E9C]">
            Saved privately to your journal.
          </div>
          <button
            type="submit"
            disabled={saving || !draft.trim()}
            className="btn-gradient inline-flex items-center gap-2 disabled:opacity-50"
            data-testid="journal-add-button"
          >
            {saving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Add to journal
          </button>
        </div>
      </form>

      {/* Weekly recap (if available) */}
      <RecapCard recap={recap} loading={recapLoading} entries={entries} />

      {/* Entries */}
      <div className="space-y-3" data-testid="journal-entry-list">
        {entries.length === 0 ? (
          <div className="card-soft p-6 text-center" data-testid="journal-empty-state">
            <div className="font-serif text-lg text-[#1A1330]">
              Your journal starts here.
            </div>
            <p className="text-sm text-[#857E9C] mt-1">
              Daily entries and saved reflections will appear in this stream.
            </p>
          </div>
        ) : (
          entries.map((e) => (
            <EntryCard key={e.entry_id} entry={e} onDelete={() => deleteEntry(e.entry_id)} />
          ))
        )}
      </div>
    </div>
  );
}

function RecapCard({ recap, loading, entries }) {
  if (loading) {
    return (
      <div
        className="card-soft p-5 flex items-center gap-3"
        data-testid="journal-recap-loading"
      >
        <Loader2 size={14} className="animate-spin text-[#3D1A78]" />
        <span className="text-sm text-[#857E9C]">Reflecting on your week…</span>
      </div>
    );
  }
  if (!recap?.recap_text) {
    if (entries.length < 2) {
      return (
        <div
          className="card-soft p-5 border border-dashed border-[#E5E0EE]"
          data-testid="journal-recap-empty"
        >
          <div className="eyebrow text-[#3D1A78] mb-1">Weekly recap</div>
          <p className="text-sm text-[#4B4567]">
            Once you've added a couple of entries this week, we'll surface what
            showed up most. Delivered each Sunday.
          </p>
        </div>
      );
    }
    return null;
  }
  return (
    <div
      className="rounded-2xl p-5 sm:p-6 border border-[#E5E0EE] bg-gradient-to-br from-[#EFE9F9] to-[#D5F2F2]/40"
      data-testid="journal-recap-card"
    >
      <div className="flex items-center gap-2 mb-2">
        <RefreshCw size={14} className="text-[#3D1A78]" />
        <div className="eyebrow text-[#3D1A78]">
          What showed up this week
        </div>
      </div>
      <p className="text-[15px] text-[#1A1330] leading-relaxed">
        {recap.recap_text}
      </p>
      {recap.themes?.length > 0 && (
        <div className="mt-4 flex items-center flex-wrap gap-1.5">
          {recap.themes.map((t) => (
            <span
              key={t}
              className="text-[11px] uppercase tracking-[0.15em] px-2 py-1 rounded-full bg-white/70 text-[#3D1A78] border border-white"
              data-testid={`journal-recap-theme-${t}`}
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {recap.generated_at && (
        <div className="text-[10px] text-[#857E9C] mt-3 uppercase tracking-[0.15em]">
          Updated {fmtDate(recap.generated_at)}
        </div>
      )}
    </div>
  );
}

function EntryCard({ entry, onDelete }) {
  const isSnapshot = entry.kind === "reflection_snapshot";
  return (
    <div
      className="card-soft p-5"
      data-testid={`journal-entry-${entry.entry_id}`}
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.15em] px-2 py-0.5 rounded-full ${
              isSnapshot
                ? "bg-[#D5F2F2] text-[#0E7A7A]"
                : "bg-[#EFE9F9] text-[#3D1A78]"
            }`}
          >
            {isSnapshot ? (
              <>
                <Heart size={10} /> Reflection
              </>
            ) : (
              <>
                <PencilLine size={10} /> Daily
              </>
            )}
          </span>
          <span className="text-xs text-[#857E9C]">
            {fmtDate(entry.created_at)}
          </span>
        </div>
        <button
          type="button"
          onClick={onDelete}
          className="text-[#857E9C] hover:text-[#9B3B3B] p-1 rounded"
          aria-label="Delete entry"
          data-testid={`journal-entry-delete-${entry.entry_id}`}
        >
          <Trash2 size={14} />
        </button>
      </div>
      {entry.prompt_text && (
        <div className="text-xs italic text-[#857E9C] mb-2">
          "{entry.prompt_text}"
        </div>
      )}
      <div className="text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap">
        {entry.content}
      </div>
    </div>
  );
}
