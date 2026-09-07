/**
 * ProfessionalJointAlignmentBulk — CSV bulk-import page for
 * mediators / paralegals who want to mint a caseload's worth of
 * Joint Alignment cases in one shot instead of clicking through
 * `/professional/joint-alignment/new` 30 times.
 *
 * Flow:
 *   1. Download the CSV template (headers + example row).
 *   2. Fill in up to 100 rows.
 *   3. Upload → backend parses, mints one case per row.
 *   4. Result table shows created ✓, skipped (duplicate) 〰️,
 *      errored (bad row) ⚠️.
 *
 * Backed by:
 *   GET  /api/professional/joint-alignment/cases/bulk-csv/template
 *   POST /api/professional/joint-alignment/cases/bulk-csv
 */
import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Upload,
  Download,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  MinusCircle,
  FileSpreadsheet,
  Copy,
  Sparkles,
} from "lucide-react";
import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const API_ROOT = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ASSESSMENT_LANES = [
  { value: "", label: "Set per-row from CSV" },
  { value: "communication",  label: "Communication" },
  { value: "co-parenting",   label: "Co-Parenting" },
  { value: "educational",    label: "Educational" },
  { value: "medical",        label: "Medical" },
  { value: "psychological",  label: "Psychological" },
  { value: "special-needs",  label: "Special Needs" },
];

function StatusPill({ tone, label, count, testid }) {
  const palette = {
    ok:    "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
    skip:  "bg-[#F1EEF7] text-[#3D1A78] border-[#D6CFE8]",
    warn:  "bg-[#FCE3DC] text-[#9A3A23] border-[#F5D0C5]",
  };
  return (
    <div
      className={`rounded-2xl border px-4 py-3 ${palette[tone]}`}
      data-testid={testid}
    >
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold opacity-70">{label}</div>
      <div className="text-2xl font-serif mt-1">{count}</div>
    </div>
  );
}

export default function ProfessionalJointAlignmentBulk() {
  const [file, setFile] = useState(null);
  const [defaultLane, setDefaultLane] = useState("");
  const [defaultNote, setDefaultNote] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  // Live-progress state (populated as NDJSON events stream in from
  // the /bulk-csv/stream endpoint).
  const [progress, setProgress] = useState({
    total: 0, done: 0, created: 0, skipped: 0, errored: 0, lastRow: null,
  });
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  const handleTemplate = async () => {
    try {
      const r = await api.get(
        "/professional/joint-alignment/cases/bulk-csv/template",
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(
        new Blob([r.data], { type: "text/csv;charset=utf-8" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "joint-alignment-bulk-template.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Template downloaded.");
    } catch (err) {
      logError("bulk template download failed", err);
      toast.error("Couldn't download the template.");
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    setProgress({ total: 0, done: 0, created: 0, skipped: 0, errored: 0, lastRow: null });

    // We collect the streamed events into these arrays as they
    // arrive so we can render the same rich results table the
    // non-streaming endpoint returned.
    const created = [];
    const skipped = [];
    const errored = [];
    let total = 0;

    // The shared axios `api` client can't stream response bodies,
    // so we drop to fetch() for this one call. Cookies + JWT are
    // both attached the same way as the axios client uses.
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const form = new FormData();
      form.append("file", file);
      const qs = new URLSearchParams();
      if (defaultLane) qs.set("default_assessment_type", defaultLane);
      if (defaultNote.trim()) qs.set("default_reminder_note", defaultNote.trim());
      const url = `${API_ROOT}/professional/joint-alignment/cases/bulk-csv/stream${
        qs.toString() ? `?${qs}` : ""
      }`;
      // JWT lives in an httpOnly `auth_token` cookie so we just
      // pass `credentials: "include"` and let the browser attach it.
      // fetch() is used here instead of axios because axios can't
      // stream response bodies.
      const res = await fetch(url, {
        method: "POST",
        credentials: "include",
        body: form,
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        let detail = "Upload failed.";
        try {
          const j = await res.json();
          detail = j?.detail || detail;
        } catch { /* body wasn't JSON */ }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Each event is a single \n-terminated line. Keep the tail
        // in `buffer` in case a chunk arrives split mid-line.
        let nl;
        while ((nl = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, nl).trim();
          buffer = buffer.slice(nl + 1);
          if (!line) continue;
          let evt;
          try { evt = JSON.parse(line); } catch { continue; }
          if (evt.event === "start") {
            total = evt.total_rows || 0;
            setProgress((p) => ({ ...p, total }));
          } else if (evt.event === "row") {
            if (evt.status === "created") {
              created.push(evt);
            } else if (evt.status === "skipped") {
              skipped.push(evt);
            } else {
              errored.push(evt);
            }
            setProgress((p) => ({
              total,
              done:    p.done + 1,
              created: created.length,
              skipped: skipped.length,
              errored: errored.length,
              lastRow: evt,
            }));
          } else if (evt.event === "done") {
            setResult({
              total_rows: evt.summary?.total_rows || total,
              created, skipped, errored,
            });
            const c = created.length;
            const s = skipped.length;
            const e = errored.length;
            if (c > 0) toast.success(`Created ${c} case${c === 1 ? "" : "s"}${s ? ` · skipped ${s} duplicates` : ""}${e ? ` · ${e} errored` : ""}`);
            else if (s > 0 && e === 0) toast(`All ${s} row${s === 1 ? "" : "s"} were duplicates — nothing new to send.`);
            else toast.error(`${e} row${e === 1 ? "" : "s"} couldn't be processed.`);
          }
        }
      }
    } catch (err) {
      if (err?.name === "AbortError") {
        toast("Upload cancelled.");
      } else {
        logError("bulk csv streaming upload failed", err);
        const detail = err?.message || "Upload failed.";
        setError(String(detail));
        toast.error(String(detail));
      }
    } finally {
      abortRef.current = null;
      setUploading(false);
    }
  };

  const handleCancelUpload = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const totals = useMemo(() => ({
    created: result?.created?.length || 0,
    skipped: result?.skipped?.length || 0,
    errored: result?.errored?.length || 0,
    total:   result?.total_rows || 0,
  }), [result]);

  const copyAllInvitationUrls = async () => {
    const lines = (result?.created || []).flatMap((c) =>
      (c.parents || []).map((p) => `${c.case_id}\t${p.email}\t${p.invitation_url}`),
    );
    if (lines.length === 0) return;
    const text = "case_id\tparent_email\tinvitation_url\n" + lines.join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied invitation URLs to clipboard.");
    } catch (err) {
      logError("bulk copy urls failed", err);
      toast.error("Copy failed — please copy manually from the table.");
    }
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-center justify-between gap-2 mb-4">
          <Link
            to="/professional/joint-alignment/mine"
            className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"
            data-testid="bulk-back-link"
          >
            <ArrowLeft size={14} /> Back to my cases
          </Link>
          <Link
            to="/professional/joint-alignment/bulk/history"
            className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] hover:underline"
            data-testid="bulk-history-link"
          >
            View past imports →
          </Link>
        </div>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <Sparkles size={12} /> Bulk import
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
          data-testid="bulk-title"
        >
          Create many cases at once
        </h1>
        <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
          Upload a CSV of parent pairs and we&rsquo;ll mint one Joint
          Alignment case per row + email both parents their invitation.
          Up to <strong>100 cases</strong> per upload. Duplicates from a
          previous run are silently skipped so you can safely re-upload.
        </p>

        {/* Step 1 · Template */}
        <section
          className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
          data-testid="bulk-step-template"
        >
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            <FileSpreadsheet size={12} /> Step 1
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] mt-1">Grab the template</h2>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            Two required columns — <code className="bg-[#F5F1FB] rounded px-1">parent1_email</code>{" "}
            and <code className="bg-[#F5F1FB] rounded px-1">parent2_email</code>.
            Optional: <code className="bg-[#F5F1FB] rounded px-1">parent1_name</code>,{" "}
            <code className="bg-[#F5F1FB] rounded px-1">parent2_name</code>,{" "}
            <code className="bg-[#F5F1FB] rounded px-1">assessment_type</code>,{" "}
            <code className="bg-[#F5F1FB] rounded px-1">reminder_note</code>,{" "}
            <code className="bg-[#F5F1FB] rounded px-1">reference</code>.
          </p>
          <button
            type="button"
            onClick={handleTemplate}
            className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] px-4 py-2 text-sm font-semibold transition-colors"
            data-testid="bulk-download-template"
          >
            <Download size={13} /> Download CSV template
          </button>
        </section>

        {/* Step 2 · Defaults */}
        <section
          className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
          data-testid="bulk-step-defaults"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Step 2 (optional)
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] mt-1">Set your defaults</h2>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            When a row omits <code className="bg-[#F5F1FB] rounded px-1">assessment_type</code> or
            <code className="bg-[#F5F1FB] rounded px-1">reminder_note</code>, we&rsquo;ll fill in
            these values instead. Per-row values always win.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="bulk-default-lane"
                className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Default assessment lane
              </label>
              <select
                id="bulk-default-lane"
                value={defaultLane}
                onChange={(e) => setDefaultLane(e.target.value)}
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                data-testid="bulk-default-lane"
              >
                {ASSESSMENT_LANES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="bulk-default-note"
                className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Default reminder note
              </label>
              <input
                id="bulk-default-note"
                type="text"
                value={defaultNote}
                onChange={(e) => setDefaultNote(e.target.value)}
                maxLength={240}
                placeholder='e.g. "See you Thursday - takes about 15 minutes."'
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                data-testid="bulk-default-note"
              />
            </div>
          </div>
        </section>

        {/* Step 3 · Upload */}
        <section
          className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
          data-testid="bulk-step-upload"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Step 3
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] mt-1">Upload your CSV</h2>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="mt-4 rounded-2xl border-2 border-dashed border-[#D6CFE8] bg-[#FBF9FE] p-6 text-center"
            data-testid="bulk-dropzone"
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
              data-testid="bulk-file-input"
            />
            <Upload className="mx-auto text-[#3D1A78]" size={22} />
            {file ? (
              <div className="mt-3 text-sm text-[#1A1330]" data-testid="bulk-file-name">
                <span className="font-semibold">{file.name}</span>
                <span className="text-[#857E9C]"> · {(file.size / 1024).toFixed(1)} KB</span>
              </div>
            ) : (
              <div className="mt-3 text-sm text-[#4B4567]">
                Drop your CSV here, or click to choose a file
              </div>
            )}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold transition-colors"
              data-testid="bulk-choose-file"
            >
              Choose file
            </button>
          </div>

          <div className="mt-5 flex items-center justify-end gap-2">
            {file && !uploading && (
              <button
                type="button"
                onClick={() => setFile(null)}
                className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#FAF8FD] px-4 py-2 text-sm font-semibold"
                data-testid="bulk-clear-file"
              >
                Clear
              </button>
            )}
            {uploading && (
              <button
                type="button"
                onClick={handleCancelUpload}
                className="rounded-full border border-[#F5D0C5] text-[#9A3A23] hover:bg-[#FCE3DC] bg-white px-4 py-2 text-sm font-semibold"
                data-testid="bulk-cancel-upload"
              >
                Cancel
              </button>
            )}
            <button
              type="button"
              onClick={handleUpload}
              disabled={!file || uploading}
              className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-5 py-2 text-sm font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed inline-flex items-center gap-1.5"
              data-testid="bulk-upload-submit"
            >
              {uploading ? (
                <><Loader2 size={13} className="animate-spin" /> Importing…</>
              ) : (
                <><Upload size={13} /> Import cases</>
              )}
            </button>
          </div>

          {uploading && progress.total > 0 && (
            <div className="mt-4" data-testid="bulk-progress">
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-[#4B4567] font-semibold">
                  {progress.done} / {progress.total} rows
                </span>
                <span className="text-[#857E9C]">
                  <span className="text-[#1F5C3B] font-semibold">{progress.created} ✓</span>
                  {" · "}
                  <span className="text-[#3D1A78] font-semibold">{progress.skipped} 〰</span>
                  {" · "}
                  <span className="text-[#9A3A23] font-semibold">{progress.errored} ⚠</span>
                </span>
              </div>
              <div className="h-2 rounded-full bg-[#EFE9F9] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#5B27B8] to-[#3D1A78] transition-[width] duration-300"
                  style={{
                    width: `${Math.min(100, (progress.done / Math.max(1, progress.total)) * 100)}%`,
                  }}
                  data-testid="bulk-progress-bar"
                />
              </div>
              {progress.lastRow && (
                <p className="mt-2 text-[11px] text-[#857E9C] font-mono truncate" data-testid="bulk-progress-lastrow">
                  Row {progress.lastRow.row}:{" "}
                  {progress.lastRow.status === "created"
                    ? `${progress.lastRow.case_id} created`
                    : progress.lastRow.status === "skipped"
                      ? `${progress.lastRow.case_id || ""} skipped (${progress.lastRow.reason})`
                      : `errored — ${progress.lastRow.reason}`}
                </p>
              )}
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="mt-4 rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] px-4 py-3 text-sm"
              data-testid="bulk-error"
            >
              {error}
            </div>
          )}
        </section>

        {/* Results */}
        {result && (
          <section
            className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
            data-testid="bulk-results"
          >
            <h2 className="font-serif text-2xl text-[#1A1330]">
              Results · {totals.total} row{totals.total === 1 ? "" : "s"}
            </h2>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <StatusPill tone="ok"   label="Created" count={totals.created} testid="bulk-tile-created" />
              <StatusPill tone="skip" label="Skipped" count={totals.skipped} testid="bulk-tile-skipped" />
              <StatusPill tone="warn" label="Errored" count={totals.errored} testid="bulk-tile-errored" />
            </div>

            {totals.created > 0 && (
              <div className="mt-6" data-testid="bulk-created-list">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-[#1F5C3B]" /> Created
                  </h3>
                  <button
                    type="button"
                    onClick={copyAllInvitationUrls}
                    className="inline-flex items-center gap-1 rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] px-3 py-1 text-[11px] font-semibold"
                    data-testid="bulk-copy-urls"
                  >
                    <Copy size={11} /> Copy all invitation URLs
                  </button>
                </div>
                <ul className="mt-3 divide-y divide-[#EEE8F7]">
                  {result.created.map((c) => (
                    <li key={c.case_id} className="py-2 text-sm">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className="rounded-full bg-[#EFE9F9] text-[#3D1A78] px-2 py-0.5 text-[11px] font-mono font-semibold"
                          data-testid={`bulk-created-case-${c.case_id}`}
                        >
                          {c.case_id}
                        </span>
                        <span className="text-[#857E9C] text-[11px]">
                          Row {c.row} · {c.assessment_type}
                        </span>
                      </div>
                      <div className="text-[12px] text-[#4B4567] mt-1">
                        {(c.parents || []).map((p) => (
                          <div key={p.email}>
                            {p.email}
                            {(c.email_deliveries || []).find(
                              (d) => d.email === p.email,
                            )?.delivered ? (
                              <span className="text-[#1F5C3B] ml-2">· email sent ✓</span>
                            ) : (
                              <span className="text-[#8A5B00] ml-2">
                                · copy invitation URL manually
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {totals.skipped > 0 && (
              <div className="mt-6" data-testid="bulk-skipped-list">
                <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
                  <MinusCircle size={14} className="text-[#3D1A78]" /> Skipped duplicates
                </h3>
                <p className="text-[12px] text-[#857E9C] mt-1">
                  These pairs already have an active case with you — nothing sent.
                </p>
                <ul className="mt-2 divide-y divide-[#EEE8F7]">
                  {result.skipped.map((s, i) => (
                    <li key={`${s.row}-${i}`} className="py-2 text-sm">
                      <span className="text-[#857E9C]">Row {s.row}</span>
                      {s.case_id && (
                        <span className="ml-2 rounded-full bg-[#F1EEF7] text-[#3D1A78] px-2 py-0.5 text-[11px] font-mono">
                          {s.case_id}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {totals.errored > 0 && (
              <div className="mt-6" data-testid="bulk-errored-list">
                <h3 className="text-sm font-bold text-[#1A1330] inline-flex items-center gap-1.5">
                  <AlertTriangle size={14} className="text-[#9A3A23]" /> Errored rows
                </h3>
                <p className="text-[12px] text-[#857E9C] mt-1">
                  Fix these in your CSV and re-upload — the successfully-created
                  rows will be silently skipped as duplicates.
                </p>
                <ul className="mt-2 divide-y divide-[#EEE8F7]">
                  {result.errored.map((e, i) => (
                    <li key={`${e.row}-${i}`} className="py-2 text-sm">
                      <span className="text-[#9A3A23]">Row {e.row}:</span>{" "}
                      <span className="text-[#1A1330]">{e.reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
