/**
 * InterventionCompliance — Weekly check-in on which enforced
 * interventions the parent is actually following.
 *
 * Aggregates items from the parent's latest Safety Assessment, ND Risk
 * Assessment, and Dimension Companion — grouped by source with a per-
 * item toggle, an optional notes field, and a running week compliance
 * gauge. A small sparkline of the last 8 weeks lives at the top so the
 * parent can see the trend.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Loader2,
  RefreshCw,
  StickyNote,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

function formatWeek(iso) {
  if (!iso) return "";
  try {
    const start = new Date(`${iso}T00:00:00Z`);
    const end = new Date(start.getTime() + 6 * 24 * 60 * 60 * 1000);
    const fmt = (d) =>
      d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      });
    return `${fmt(start)} – ${fmt(end)}`;
  } catch {
    return iso;
  }
}

function ComplianceGauge({ pct, total, followed }) {
  const label = total === 0
    ? "No interventions to track yet"
    : `${followed} of ${total} interventions followed`;
  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6"
      data-testid="compliance-gauge"
    >
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
        This week
      </div>
      <div className="flex items-baseline gap-3 flex-wrap mt-1">
        <span
          className="text-4xl font-bold text-[#1A1330]"
          data-testid="compliance-pct"
        >
          {pct.toFixed(0)}%
        </span>
        <span className="text-sm text-[#4B4567]">{label}</span>
      </div>
      <div className="h-2 mt-3 rounded-full bg-[#F0EEF8] overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
          style={{ width: `${Math.max(1, pct)}%` }}
        />
      </div>
    </div>
  );
}

function HistoryStrip({ weeks }) {
  if (!weeks?.length) return null;
  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6"
      data-testid="compliance-history"
    >
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
        Last {weeks.length} weeks
      </div>
      <div className="flex items-center gap-2 mt-1">
        <TrendingUp size={14} className="text-[#3D1A78]" />
        <span className="text-sm text-[#4B4567]">
          Consistency trend
        </span>
      </div>
      <div className="mt-4 flex items-end gap-1 h-24">
        {weeks.map((w) => {
          const pct = w.compliance_pct;
          const height = pct === null ? 4 : Math.max(4, pct * 0.9);
          const empty = pct === null;
          return (
            <div
              key={w.week_start}
              className="flex-1 flex flex-col items-center justify-end gap-1"
              title={
                empty
                  ? `${w.week_start}: no data`
                  : `${w.week_start}: ${pct}%`
              }
              data-testid={`compliance-history-bar-${w.week_start}`}
            >
              <div
                className={`w-full rounded-t ${empty ? "bg-[#F0EEF8]" : "bg-gradient-to-t from-[#3D1A78] to-[#2DB5B5]"}`}
                style={{ height: `${height}%`, minHeight: 4 }}
              />
              <div className="text-[9px] text-[#8471B3]">
                {w.week_start.slice(5)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function InterventionRow({ item, onToggle, onNotesChange, saving }) {
  const [notesOpen, setNotesOpen] = useState(Boolean(item.notes));
  const [notes, setNotes] = useState(item.notes || "");
  const dirtyRef = useMemo(() => ({ prev: item.notes || "" }), [item.notes]);

  const commitNotes = () => {
    if (notes === dirtyRef.prev) return;
    dirtyRef.prev = notes;
    onNotesChange(notes);
  };

  return (
    <div
      className={`rounded-2xl border p-4 sm:p-5 transition ${
        item.followed
          ? "border-[#1F5C3B]/40 bg-[#F1FAF3]"
          : "border-[#E5E0EE] bg-white"
      }`}
      data-testid={`compliance-item-${item.key}`}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={() => onToggle(!item.followed)}
          disabled={saving}
          data-testid={`compliance-toggle-${item.key}`}
          aria-pressed={item.followed}
          className="shrink-0 mt-0.5"
        >
          {item.followed ? (
            <CheckCircle2 size={22} className="text-[#1F5C3B]" />
          ) : (
            <Circle size={22} className="text-[#B7AECC]" />
          )}
        </button>
        <div className="flex-1">
          <div className="text-sm text-[#1A1330] leading-relaxed">
            {item.text}
          </div>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => setNotesOpen((v) => !v)}
              className="inline-flex items-center gap-1 text-[11px] text-[#3D1A78] font-semibold hover:underline"
              data-testid={`compliance-notes-toggle-${item.key}`}
            >
              <StickyNote size={11} />
              {notesOpen ? "Hide notes" : (item.notes ? "Edit notes" : "Add notes")}
            </button>
            {item.updated_at && (
              <span className="text-[10px] text-[#8471B3]">
                Updated {new Date(item.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>
          {notesOpen && (
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={commitNotes}
              placeholder="What worked, what got in the way, notes for next week…"
              rows={2}
              maxLength={800}
              data-testid={`compliance-notes-input-${item.key}`}
              className="mt-2 w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default function InterventionCompliance() {
  const [log, setLog] = useState(null);
  const [history, setHistory] = useState(null);
  const [savingKey, setSavingKey] = useState(null);
  const [reloading, setReloading] = useState(false);

  const load = async () => {
    try {
      const [logRes, histRes] = await Promise.all([
        api.get("/interventions/log"),
        api.get("/interventions/log/history", { params: { weeks: 8 } }),
      ]);
      setLog(logRes.data);
      setHistory(histRes.data.weeks || []);
    } catch (err) {
      logError("Compliance load failed", err);
      toast.error("Couldn't load your compliance log. Please refresh.");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const groups = useMemo(() => {
    if (!log?.items) return [];
    const map = new Map();
    for (const it of log.items) {
      if (!map.has(it.group)) map.set(it.group, []);
      map.get(it.group).push(it);
    }
    return Array.from(map.entries()).map(([group, items]) => ({ group, items }));
  }, [log]);

  const updateItem = async (item, patch) => {
    setSavingKey(item.key);
    // Optimistic update
    setLog((prev) => {
      if (!prev) return prev;
      const next = { ...prev, items: prev.items.map((x) => x.key === item.key ? { ...x, ...patch } : x) };
      const followed = next.items.filter((x) => x.followed).length;
      const total = next.items.length;
      next.summary = { total, followed, compliance_pct: total ? Math.round((followed / total) * 1000) / 10 : 0 };
      return next;
    });
    try {
      await api.post("/interventions/log", {
        intervention_key: item.key,
        source:           item.source,
        text:             item.text,
        group:            item.group,
        followed:         patch.followed ?? item.followed,
        notes:            patch.notes    ?? item.notes,
      });
    } catch (err) {
      logError("Compliance save failed", err);
      toast.error("Couldn't save. Please try again.");
      load();  // resync
    } finally {
      setSavingKey(null);
    }
  };

  if (!log) {
    return (
      <AppShell>
        <div className="p-10 inline-flex items-center gap-2 text-sm text-[#4B4567]">
          <Loader2 size={14} className="animate-spin" /> Loading your compliance log…
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="intervention-compliance">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <div className="flex items-start justify-between gap-3 flex-wrap mb-6">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Intervention Compliance Log
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1">
              Which interventions are you following?
            </h1>
            <p className="text-sm text-[#4B4567] mt-2">
              Week of <strong>{formatWeek(log.week_start)}</strong>.
              Tick every intervention you've genuinely followed this week —
              honest data helps you and your mediator see what's actually
              working.
            </p>
          </div>
          <button
            type="button"
            onClick={async () => { setReloading(true); await load(); setReloading(false); }}
            disabled={reloading}
            data-testid="compliance-refresh"
            className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] font-semibold hover:underline"
          >
            <RefreshCw size={12} className={reloading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          <ComplianceGauge
            pct={log.summary.compliance_pct}
            total={log.summary.total}
            followed={log.summary.followed}
          />
          <HistoryStrip weeks={history || []} />
        </div>

        {log.items.length === 0 ? (
          <div
            className="rounded-3xl border border-dashed border-[#E5E0EE] bg-[#FAF8FE] p-8 text-center"
            data-testid="compliance-empty"
          >
            <div className="font-serif text-lg text-[#1A1330]">
              Nothing to log yet
            </div>
            <p className="text-sm text-[#4B4567] mt-1 max-w-md mx-auto">
              Complete a Safety, ND Risk, or Companion Assessment first —
              their enforced interventions will populate here so you can
              track weekly follow-through.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {groups.map(({ group, items }) => (
              <section key={group} data-testid={`compliance-group-${group}`}>
                <div className="mb-2 text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
                  {group}
                </div>
                <div className="space-y-2">
                  {items.map((item) => (
                    <InterventionRow
                      key={item.key}
                      item={item}
                      saving={savingKey === item.key}
                      onToggle={(followed) => updateItem(item, { followed })}
                      onNotesChange={(notes) => updateItem(item, { notes })}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
