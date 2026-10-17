/**
 * ProfessionalJointAlignmentBulkHistory — audit history of past
 * CSV bulk imports for the current mediator.
 *
 * Left column: paginated list of imports (most-recent first, 20 max),
 * each row showing filename · started → finished · created/skipped/
 * errored counts.
 * Right pane: click a row → detail view with the full list of
 * created case IDs, skipped duplicates, and errored rows.
 *
 * Backed by:
 *   GET /api/professional/joint-alignment/bulk/history?limit=20
 *   GET /api/professional/joint-alignment/bulk/history/{import_id}
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  History,
  RefreshCcw,
  Loader2,
  CheckCircle2,
  MinusCircle,
  AlertTriangle,
  FileSpreadsheet,
  ChevronRight,
  Upload,
} from "lucide-react";
import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

function formatTimestamp(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function CountPill({ tone, count, label, testid }) {
  const palette = {
    ok:   "bg-[#E6F4EC] text-[#1F5C3B]",
    skip: "bg-[#F1EEF7] text-[#3D1A78]",
    warn: "bg-[#FCE3DC] text-[#9A3A23]",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold ${palette[tone]}`}
      data-testid={testid}
    >
      {count} {label}
    </span>
  );
}

function ImportRow({ item, selected, onSelect }) {
  const {
    import_id, filename, started_at, total_rows,
    created_count, skipped_count, errored_count, variant,
  } = item;
  return (
    <button
      type="button"
      onClick={() => onSelect(import_id)}
      className={`w-full text-left rounded-2xl border p-4 transition-colors ${
        selected
          ? "border-[#3D1A78] bg-[#F5F1FB]"
          : "border-[#E5E0EE] bg-white hover:bg-[#FAF8FD]"
      }`}
      data-testid={`bulk-history-row-${import_id}`}
      data-selected={selected ? "true" : "false"}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
            <FileSpreadsheet size={11} />
            {variant === "stream" ? "Streaming import" : "Bulk import"}
          </div>
          <div
            className="text-sm font-semibold text-[#1A1330] mt-1 truncate"
            title={filename || "Untitled upload"}
          >
            {filename || "Untitled upload"}
          </div>
          <div className="text-[0.6875rem] text-[#6E6787] mt-1">
            {formatTimestamp(started_at)} · {total_rows} row{total_rows === 1 ? "" : "s"}
          </div>
        </div>
        <ChevronRight size={16} className="text-[#6E6787] mt-1 flex-shrink-0" />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <CountPill tone="ok" count={created_count} label="created"
          testid={`bulk-history-row-${import_id}-created`} />
        {skipped_count > 0 && (
          <CountPill tone="skip" count={skipped_count} label="skipped"
            testid={`bulk-history-row-${import_id}-skipped`} />
        )}
        {errored_count > 0 && (
          <CountPill tone="warn" count={errored_count} label="errored"
            testid={`bulk-history-row-${import_id}-errored`} />
        )}
      </div>
    </button>
  );
}

function ImportDetail({ detail, loading, error }) {
  if (loading) {
    return (
      <div className="p-8 text-center text-[#6E6787]" data-testid="bulk-history-detail-loading">
        <Loader2 className="animate-spin inline mr-2" size={16} />
        Loading import details…
      </div>
    );
  }
  if (error) {
    return (
      <div
        role="alert"
        className="p-4 rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] text-sm"
        data-testid="bulk-history-detail-error"
      >
        {error}
      </div>
    );
  }
  if (!detail) return null;

  const {
    import_id, filename, started_at, finished_at,
    default_assessment_type, default_reminder_note,
    total_rows, created_count, skipped_count, errored_count,
    case_ids, skipped_case_ids, errored_rows,
  } = detail;

  return (
    <div data-testid="bulk-history-detail">
      <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
        {import_id}
      </div>
      <h2 className="font-serif text-2xl text-[#1A1330] mt-1 break-all">
        {filename || "Untitled upload"}
      </h2>
      <div className="mt-2 text-[0.75rem] text-[#4B4567] leading-relaxed">
        Started <strong>{formatTimestamp(started_at)}</strong>
        {finished_at ? (
          <> · Finished <strong>{formatTimestamp(finished_at)}</strong></>
        ) : null}
      </div>
      {(default_assessment_type || default_reminder_note) && (
        <div className="mt-2 text-[0.6875rem] text-[#6E6787]">
          {default_assessment_type && (
            <span className="mr-3">
              Default lane: <span className="text-[#3D1A78] font-semibold">{default_assessment_type}</span>
            </span>
          )}
          {default_reminder_note && (
            <span>Default note: <em>&ldquo;{default_reminder_note}&rdquo;</em></span>
          )}
        </div>
      )}

      <div className="mt-5 grid grid-cols-3 gap-3">
        <div className="rounded-2xl border border-[#B5DFC5] bg-[#E6F4EC] p-4">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#1F5C3B] opacity-70">Created</div>
          <div className="text-2xl font-serif text-[#1F5C3B] mt-1"
               data-testid="bulk-history-detail-count-created">{created_count}</div>
        </div>
        <div className="rounded-2xl border border-[#D6CFE8] bg-[#F1EEF7] p-4">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] opacity-70">Skipped</div>
          <div className="text-2xl font-serif text-[#3D1A78] mt-1"
               data-testid="bulk-history-detail-count-skipped">{skipped_count}</div>
        </div>
        <div className="rounded-2xl border border-[#F5D0C5] bg-[#FCE3DC] p-4">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#9A3A23] opacity-70">Errored</div>
          <div className="text-2xl font-serif text-[#9A3A23] mt-1"
               data-testid="bulk-history-detail-count-errored">{errored_count}</div>
        </div>
      </div>

      {(case_ids?.length || 0) > 0 && (
        <div className="mt-6" data-testid="bulk-history-detail-created-list">
          <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-[#1F5C3B]" />
            Cases created ({case_ids.length})
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {case_ids.map((cid) => (
              <li key={cid}>
                <Link
                  to={`/professional/joint-alignment/mine?search=${encodeURIComponent(cid)}`}
                  className="inline-flex rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] px-2 py-0.5 text-[0.6875rem] font-mono font-semibold transition-colors"
                  data-testid={`bulk-history-case-${cid}`}
                >
                  {cid}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(skipped_case_ids?.length || 0) > 0 && (
        <div className="mt-6" data-testid="bulk-history-detail-skipped-list">
          <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
            <MinusCircle size={14} className="text-[#3D1A78]" />
            Skipped duplicates ({skipped_case_ids.length})
          </h3>
          <p className="text-[0.6875rem] text-[#6E6787] mt-1">
            These rows already had an active case with you — nothing sent.
          </p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {skipped_case_ids.map((cid, i) => (
              <li key={`${cid}-${i}`}>
                <span className="inline-flex rounded-full bg-[#F1EEF7] text-[#6E6787] px-2 py-0.5 text-[0.6875rem] font-mono">
                  {cid}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(errored_rows?.length || 0) > 0 && (
        <div className="mt-6" data-testid="bulk-history-detail-errored-list">
          <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-[#9A3A23]" />
            Errored rows ({errored_rows.length})
          </h3>
          <ul className="mt-2 divide-y divide-[#EEE8F7] rounded-xl border border-[#F5D0C5] bg-[#FFF9F7]">
            {errored_rows.map((e, i) => (
              <li key={`${e.row}-${i}`} className="p-2.5 text-[0.75rem]">
                <span className="text-[#9A3A23] font-semibold">Row {e.row}:</span>{" "}
                <span className="text-[#1A1330]">{e.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {total_rows > 0 &&
        (case_ids?.length || 0) === 0 &&
        (skipped_case_ids?.length || 0) === 0 &&
        (errored_rows?.length || 0) === 0 && (
        <div className="mt-6 text-sm text-[#6E6787]">No row detail was recorded for this import.</div>
      )}
    </div>
  );
}

export default function ProfessionalJointAlignmentBulkHistory() {
  const [imports, setImports] = useState(null);  // null=loading, []=empty
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const loadHistory = async () => {
    setError(null);
    try {
      const r = await api.get("/professional/joint-alignment/bulk/history?limit=20");
      const rows = r.data?.imports || [];
      setImports(rows);
      if (rows.length && !selectedId) {
        setSelectedId(rows[0].import_id);
      }
    } catch (err) {
      logError("bulk history load failed", err);
      setError("Couldn't load your bulk-import history.");
      setImports([]);
    }
  };

  useEffect(() => { loadHistory(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    let cancelled = false;
    const load = async () => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const r = await api.get(`/professional/joint-alignment/bulk/history/${selectedId}`);
        if (!cancelled) setDetail(r.data);
      } catch (err) {
        logError("bulk history detail load failed", err);
        if (!cancelled) {
          setDetailError("Couldn't load import details.");
          setDetail(null);
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [selectedId]);

  const handleRefresh = async () => {
    await loadHistory();
    if (selectedId) {
      setSelectedId((prev) => prev);  // re-triggers detail load
      // force re-fetch by clearing and restoring
      const cur = selectedId;
      setSelectedId(null);
      setTimeout(() => setSelectedId(cur), 0);
    }
    toast.success("History refreshed.");
  };

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/professional/joint-alignment/mine"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="bulk-history-back-link"
        >
          <ArrowLeft size={14} /> Back to my cases
        </Link>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
              <Sparkles size={12} /> Bulk import history
            </div>
            <h1
              className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
              data-testid="bulk-history-title"
            >
              Every caseload you&rsquo;ve uploaded
            </h1>
            <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
              Audit of every CSV bulk import you&rsquo;ve run — file
              name, when you uploaded it, and which rows landed as
              cases, duplicates, or errors. Last 20 imports.
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={handleRefresh}
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#E5E0EE] hover:bg-[#F5F1FB] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold"
              data-testid="bulk-history-refresh"
            >
              <RefreshCcw size={12} /> Refresh
            </button>
            <Link
              to="/professional/joint-alignment/bulk"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold"
              data-testid="bulk-history-new-import"
            >
              <Upload size={12} /> New import
            </Link>
          </div>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] px-4 py-3 text-sm"
            data-testid="bulk-history-error"
          >
            {error}
          </div>
        )}

        {imports === null && (
          <div className="mt-8 text-center text-[#6E6787]" data-testid="bulk-history-loading">
            <Loader2 className="animate-spin inline mr-2" size={16} />
            Loading your bulk imports…
          </div>
        )}

        {imports !== null && imports.length === 0 && (
          <div
            className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-10 text-center"
            data-testid="bulk-history-empty"
          >
            <History size={22} className="mx-auto text-[#6E6787]" />
            <h2 className="font-serif text-2xl text-[#1A1330] mt-3">
              No bulk imports yet
            </h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-md mx-auto">
              Upload a CSV to spin up a caseload at once — every
              import you run will show up here for future reference.
            </p>
            <Link
              to="/professional/joint-alignment/bulk"
              className="inline-flex items-center gap-1.5 mt-4 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
              data-testid="bulk-history-empty-cta"
            >
              <Upload size={13} /> Start a bulk import
            </Link>
          </div>
        )}

        {imports !== null && imports.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-[minmax(280px,360px)_1fr] gap-6">
            <div
              className="flex flex-col gap-2"
              data-testid="bulk-history-list"
              aria-label="Bulk import history"
            >
              {imports.map((item) => (
                <ImportRow
                  key={item.import_id}
                  item={item}
                  selected={selectedId === item.import_id}
                  onSelect={setSelectedId}
                />
              ))}
            </div>
            <div
              className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm min-h-[240px]"
              data-testid="bulk-history-detail-pane"
            >
              <ImportDetail
                detail={detail}
                loading={detailLoading}
                error={detailError}
              />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
