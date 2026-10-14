/**
 * `/professional/joint-alignment/mine` — Mediator/Attorney case
 * management console. Shows every Joint Alignment Case the caller
 * minted via the in-app flow, with:
 *   * search (by case_id, professional reference, or parent email)
 *   * status filter chips (all / pending / in progress / both complete / cancelled)
 *   * per-row copy-invitation-link buttons (still-valid tokens only)
 *   * revoke (with confirm) that POSTs to
 *     /api/professional/joint-alignment/cases/{id}/cancel
 *
 * Complements the compact "Cases you've created" sidebar on the
 * `/professional/joint-alignment/new` page — this route is the
 * dedicated management surface.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Copy,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  Filter,
  RefreshCcw,
  Users,
  AlertTriangle,
  X,
  FileDown,
  FileSpreadsheet,
  MessageSquare,
  UserRound,
  Lock,
  Check,
  Mail,
  History,
} from "lucide-react";

import AppShell from "../components/AppShell";
import CaseAnalyticsCard from "../components/professional/CaseAnalyticsCard";
import WeeklyDigestToggle from "../components/professional/WeeklyDigestToggle";
import ReminderPreviewModal from "../components/professional/ReminderPreviewModal";
import ProfessionalDirectoryModal from "../components/professional/ProfessionalDirectoryModal";
import ReminderNoteTemplatePicker from "../components/professional/ReminderNoteTemplatePicker";
import { CourtCodesPanel } from "../components/professional/CourtCodesPanel";
import { RequestedProgress } from "../components/professional/RequestedProgress";
import { ProgressPdfButton } from "../components/professional/ProgressPdfButton";
import { NudgeButton } from "../components/professional/NudgeButton";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const FIRM_NAME_KEY = "sacoparents.pj.mine.firm_name.v1";

const STATUS_FILTERS = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "in_progress", label: "In progress" },
  { key: "both_complete", label: "Both complete" },
  { key: "cancelled", label: "Cancelled" },
];

const STATUS_PILL = {
  pending: "bg-[#F1EEF7] text-[#3D1A78] border-[#D6CFE8]",
  in_progress: "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]",
  both_complete: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  cancelled: "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  expired: "bg-[#F1EEF7] text-[#857E9C] border-[#E5E0EE]",
};

export default function ProfessionalJointAlignmentMine() {
  const navigate = useNavigate();
  const [cases, setCases] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [busyId, setBusyId] = useState(null);
  const [downloadFor, setDownloadFor] = useState(null); // {case_id} or null when closed
  const [firmName, setFirmName] = useState(() => {
    try { return window.localStorage.getItem(FIRM_NAME_KEY) || ""; } catch { return ""; }
  });
  const [downloading, setDownloading] = useState(false);
  const [noteEditingId, setNoteEditingId] = useState(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  // Private "Case notes" — separate from the parent-visible
  // reminder note above. Mediator-only, never surfaced to parents.
  const [caseNotesEditingId, setCaseNotesEditingId] = useState(null);
  const [caseNotesDraft, setCaseNotesDraft] = useState("");
  const [caseNotesSaving, setCaseNotesSaving] = useState(false);
  // Reminder-preview modal — holds the case_id of the row the mediator
  // wants to preview the 5-day gentle-nudge email for.
  const [previewCaseId, setPreviewCaseId] = useState(null);
  // Professional directory (sacoparentsalign.com) modal. When
  // opened from the top-of-page action it invites without binding
  // to a case; when opened from a case row, it pre-fills the
  // case_id and shows a pill in the modal header.
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [directoryCaseId, setDirectoryCaseId] = useState(null);
  const downloadModalRef = useRef(null);
  const downloadTriggerRef = useRef(null);

  // Close the download modal on Escape and restore focus to whichever
  // "Download PDF" button opened it — matches WAI-ARIA APG dialog
  // pattern so keyboard/screen-reader users aren't stranded.
  useEffect(() => {
    if (!downloadFor) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape" && !downloading) {
        setDownloadFor(null);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [downloadFor, downloading]);

  useEffect(() => {
    // Restore focus back to the trigger button once the modal closes.
    if (!downloadFor && downloadTriggerRef.current) {
      try { downloadTriggerRef.current.focus(); } catch { /* noop */ }
      downloadTriggerRef.current = null;
    }
  }, [downloadFor]);

  const load = () => {
    setLoading(true);
    setError(null);
    api.get("/professional/joint-alignment/cases-i-created")
      .then((r) => setCases(r.data?.cases || []))
      .catch((err) => {
        logError("Failed to load cases-i-created:", err);
        setError("Could not load your cases. Please try again.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = useMemo(() => {
    if (!cases) return [];
    const q = search.trim().toLowerCase();
    return cases.filter((c) => {
      if (statusFilter !== "all" && c.status !== statusFilter) return false;
      if (!q) return true;
      if (c.case_id?.toLowerCase().includes(q)) return true;
      if (c.align_case_reference?.toLowerCase().includes(q)) return true;
      return (c.parents || []).some(
        (p) => (p.email || "").toLowerCase().includes(q) ||
               (p.name || "").toLowerCase().includes(q),
      );
    });
  }, [cases, search, statusFilter]);

  const counts = useMemo(() => {
    const base = { all: 0, pending: 0, in_progress: 0, both_complete: 0, cancelled: 0 };
    (cases || []).forEach((c) => {
      base.all += 1;
      if (c.status in base) base[c.status] += 1;
    });
    return base;
  }, [cases]);

  const copyToClipboard = (text, label) => {
    try {
      navigator.clipboard.writeText(text);
      toast.success(`${label} copied`);
    } catch (err) {
      logError("clipboard failed:", err);
      toast.error("Copy failed — long-press the link to copy manually");
    }
  };

  const revoke = async (caseId) => {
    const ok = window.confirm(
      `Revoke case ${caseId}? Any unclaimed invitation links will stop working immediately. Parents who already accepted keep their access to the reflection, but the joint report won't advance.`,
    );
    if (!ok) return;
    setBusyId(caseId);
    try {
      await api.post(`/professional/joint-alignment/cases/${caseId}/cancel`, { reason: null });
      toast.success(`Case ${caseId} revoked`);
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail || "Revoke failed";
      toast.error(String(detail));
    } finally {
      setBusyId(null);
    }
  };

  const openDownload = (caseId, triggerEl) => {
    if (triggerEl) downloadTriggerRef.current = triggerEl;
    setDownloadFor({ caseId });
  };
  const closeDownload = () => {
    if (!downloading) setDownloadFor(null);
  };
  const downloadCaseStatus = async () => {
    if (!downloadFor) return;
    const firm = firmName.trim();
    if (!firm) {
      toast.error("Enter a firm name for the watermark");
      return;
    }
    setDownloading(true);
    try {
      try { window.localStorage.setItem(FIRM_NAME_KEY, firm); } catch { /* best-effort */ }
      const res = await api.get(
        `/professional/joint-alignment/cases/${downloadFor.caseId}/status-report.pdf`,
        { params: { firm }, responseType: "blob" },
      );
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${downloadFor.caseId}-status-report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Downloaded ${downloadFor.caseId} status PDF`);
      setDownloadFor(null);
    } catch (err) {
      logError("download failed:", err);
      toast.error("Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const openNoteEdit = (c) => {
    setNoteEditingId(c.case_id);
    setNoteDraft(c.reminder_note || "");
  };
  const cancelNoteEdit = () => {
    if (noteSaving) return;
    setNoteEditingId(null);
    setNoteDraft("");
  };
  const saveNote = async () => {
    if (!noteEditingId) return;
    setNoteSaving(true);
    try {
      await api.patch(
        `/professional/joint-alignment/cases/${noteEditingId}/reminder-note`,
        { reminder_note: noteDraft.trim() || null },
      );
      toast.success(
        noteDraft.trim() ? "Reminder note saved." : "Reminder note cleared.",
      );
      setNoteEditingId(null);
      setNoteDraft("");
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail || "Save failed";
      toast.error(String(detail));
    } finally {
      setNoteSaving(false);
    }
  };

  // -------- Private "Case notes" editor --------
  const openCaseNotesEdit = (c) => {
    setCaseNotesEditingId(c.case_id);
    setCaseNotesDraft(c.case_notes || "");
  };
  const cancelCaseNotesEdit = () => {
    if (caseNotesSaving) return;
    setCaseNotesEditingId(null);
    setCaseNotesDraft("");
  };
  const saveCaseNotes = async () => {
    if (!caseNotesEditingId) return;
    setCaseNotesSaving(true);
    try {
      await api.patch(
        `/professional/joint-alignment/cases/${caseNotesEditingId}/case-notes`,
        { case_notes: caseNotesDraft.trim() || null },
      );
      toast.success(
        caseNotesDraft.trim() ? "Private notes saved." : "Private notes cleared.",
      );
      setCaseNotesEditingId(null);
      setCaseNotesDraft("");
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail || "Save failed";
      toast.error(String(detail));
    } finally {
      setCaseNotesSaving(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto" data-testid="pj-mine-page">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#1A1330] mb-4"
          data-testid="pj-mine-back"
        >
          <ArrowLeft size={14} /> Back
        </button>

        <div className="flex items-baseline justify-between flex-wrap gap-3 mb-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1 inline-flex items-center gap-2">
              <Users size={12} /> Cases you&rsquo;ve created
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight" data-testid="pj-mine-headline">
              Your Joint Alignment Cases
            </h1>
            <p className="text-sm text-[#4B4567] mt-2 max-w-2xl leading-relaxed">
              Every case you&rsquo;ve minted from inside SA CoParents. Search by
              case ID, email, or reference number — revoke anything that&rsquo;s
              no longer active.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <WeeklyDigestToggle />
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold disabled:opacity-60"
              data-testid="pj-mine-refresh"
            >
              {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCcw size={12} />}
              Refresh
            </button>
            <Link
              to="/professional/joint-alignment/bulk"
              className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors"
              data-testid="pj-mine-bulk"
              title="Import many cases from a CSV"
            >
              <FileSpreadsheet size={12} /> Bulk import
            </Link>
            <Link
              to="/professional/joint-alignment/bulk/history"
              className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors"
              data-testid="pj-mine-bulk-history"
              title="Audit of past CSV imports"
            >
              <History size={12} /> History
            </Link>
            <button
              type="button"
              onClick={() => {
                setDirectoryCaseId(null);
                setDirectoryOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors"
              data-testid="pj-mine-invite-pro"
              title="Invite a professional from the sacoparentsalign.com directory"
            >
              <UserRound size={12} /> Invite a pro
            </button>
            <Link
              to="/professional/joint-alignment/new"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold transition-colors"
              data-testid="pj-mine-new"
            >
              <Sparkles size={12} /> New case
            </Link>
          </div>
        </div>

        {/* Analytics card — hidden when the caller has no cases yet */}
        <CaseAnalyticsCard />

        <CourtCodesPanel />

        {/* Search + status filter */}
        <div
          className="rounded-2xl border border-[#E5E0EE] bg-white p-4 mb-4 space-y-3"
          data-testid="pj-mine-controls"
        >
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#857E9C]"
              aria-hidden
            />
            <input
              type="text"
              placeholder="Search by case ID, email, or reference number…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-9 py-2 rounded-full border border-[#E5E0EE] bg-white text-sm text-[#1A1330] focus:outline-none focus:border-[#3D1A78]"
              data-testid="pj-mine-search"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#857E9C] hover:text-[#1A1330]"
                data-testid="pj-mine-search-clear"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2" data-testid="pj-mine-filter-chips">
            <Filter size={12} className="text-[#857E9C]" aria-hidden />
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setStatusFilter(f.key)}
                aria-pressed={statusFilter === f.key}
                className={`text-xs font-semibold rounded-full px-3 py-1 border transition-colors ${
                  statusFilter === f.key
                    ? "bg-[#3D1A78] border-[#3D1A78] text-white"
                    : "bg-white border-[#E5E0EE] text-[#4B4567] hover:border-[#3D1A78]"
                }`}
                data-testid={`pj-mine-filter-${f.key}`}
              >
                {f.label} <span className="opacity-70">· {counts[f.key] ?? 0}</span>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div
            className="mb-4 flex items-start gap-2 rounded-2xl bg-[#FEE4E2] border border-[#F1B0A9] px-4 py-3 text-[13px] text-[#8A2C1E]"
            role="alert"
            aria-live="polite"
            data-testid="pj-mine-error"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <p className="!m-0 leading-relaxed">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="p-10 text-center text-sm text-[#4B4567]" data-testid="pj-mine-loading">
            <Loader2 size={16} className="animate-spin inline mr-2" /> Loading your cases…
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="rounded-2xl border border-dashed border-[#D6CFE8] bg-[#FAF8FD] p-8 text-center"
            data-testid="pj-mine-empty"
          >
            <Users size={22} className="mx-auto text-[#3D1A78] mb-3" aria-hidden />
            <div className="font-serif text-lg text-[#1A1330]">
              {(cases || []).length === 0
                ? "No cases yet"
                : "No cases match your search"}
            </div>
            <p className="text-sm text-[#4B4567] mt-1 max-w-md mx-auto leading-relaxed">
              {(cases || []).length === 0
                ? "Create your first Joint Alignment case from the button above and both parents will receive private invitation links."
                : "Try a different search term or clear the status filter."}
            </p>
            {(cases || []).length === 0 && (
              <Link
                to="/professional/joint-alignment/new"
                className="inline-flex items-center gap-1.5 mt-4 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold transition-colors"
                data-testid="pj-mine-empty-cta"
              >
                <Sparkles size={13} /> Create your first case
              </Link>
            )}
          </div>
        ) : (
          <ul className="space-y-3" data-testid="pj-mine-list">
            {filtered.map((c) => (
              <li
                key={c.case_id}
                className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
                data-testid={`pj-mine-row-${c.case_id}`}
              >
                <div className="flex items-baseline justify-between flex-wrap gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-base font-semibold text-[#1A1330]">
                        {c.case_id}
                      </span>
                      <span
                        className={`text-[10px] uppercase tracking-[0.15em] font-bold rounded-full px-2 py-0.5 border ${STATUS_PILL[c.status] || STATUS_PILL.expired}`}
                        data-testid={`pj-mine-status-${c.case_id}`}
                      >
                        {c.status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="text-xs text-[#4B4567] mt-1">
                      {c.assessment_type.replace("-", " ")}
                      {c.align_case_reference ? ` · Ref: ${c.align_case_reference}` : ""}
                      {c.created_at ? ` · Created ${new Date(c.created_at).toLocaleDateString()}` : ""}
                    </div>
                  </div>
                  {c.status !== "cancelled" && c.status !== "expired" && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <ProgressPdfButton path={`/professional/joint-alignment/cases/${c.case_id}/progress.pdf`} caseId={c.case_id} testid={`pj-mine-progress-pdf-${c.case_id}`} />
                      <button
                        type="button"
                        onClick={(e) => openDownload(c.case_id, e.currentTarget)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors"
                        data-testid={`pj-mine-download-${c.case_id}`}
                      >
                        <FileDown size={12} /> Download PDF
                      </button>
                      {c.status !== "both_complete" && (
                        <button
                          type="button"
                          onClick={() => revoke(c.case_id)}
                          disabled={busyId === c.case_id}
                          className="inline-flex items-center gap-1.5 rounded-full border border-[#EFB4B4] text-[#B02A2A] hover:bg-[#FEE4E2] px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60"
                          data-testid={`pj-mine-revoke-${c.case_id}`}
                        >
                          {busyId === c.case_id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                          Revoke
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {(c.parents || []).map((p, pi) => (
                    <div
                      key={p.email || pi}
                      className="rounded-xl border border-[#E5E0EE] bg-[#FAF8FD] p-3"
                      data-testid={`pj-mine-parent-${c.case_id}-${pi}`}
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
                            Parent {pi + 1}
                          </div>
                          <div className="text-sm text-[#1A1330] truncate">
                            {p.name || p.email}
                          </div>
                          <div className="text-[11px] text-[#4B4567]">
                            {p.status?.replace("_", " ") || "invited"}
                            {p.assessment_completed_at ? " · completed" : ""}
                          </div>
                        </div>
                        {p.invitation_url && (
                          <button
                            type="button"
                            onClick={() => copyToClipboard(p.invitation_url, `${c.case_id} · P${pi + 1}`)}
                            className="text-[11px] font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1 shrink-0"
                            data-testid={`pj-mine-copy-${c.case_id}-${pi}`}
                          >
                            <Copy size={10} /> Copy link
                          </button>
                        )}
                      </div>
                      <RequestedProgress rows={p.requested_progress} testid={`pj-mine-progress-${c.case_id}-${pi}`} />
                      <NudgeButton caseRef={c.case_id} pid={p.nudge_pid} nextAt={p.nudge_next_at} rows={p.requested_progress} testid={`pj-mine-nudge-${c.case_id}-${pi}`} />
                    </div>
                  ))}
                </div>

                {/* Reminder-note strip — displays the note (if any) and,
                    for non-terminal cases, lets the mediator edit it inline. */}
                {(c.status !== "cancelled" && c.status !== "expired") && (
                  <div className="mt-3" data-testid={`pj-mine-note-${c.case_id}`}>
                    {noteEditingId === c.case_id ? (
                      <div className="rounded-xl border border-[#D6CFE8] bg-[#F5F1FB] p-3">
                        <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-1 inline-flex items-center gap-1">
                          <MessageSquare size={10} /> Reminder note
                        </div>
                        <textarea
                          rows={2}
                          maxLength={240}
                          value={noteDraft}
                          onChange={(e) => setNoteDraft(e.target.value)}
                          placeholder='e.g. "See you Thursday - takes about 15 minutes."'
                          className="w-full rounded-lg border border-[#D6CFE8] bg-white text-sm text-[#1A1330] px-2.5 py-1.5 focus:outline-none focus:border-[#3D1A78] resize-none"
                          data-testid={`pj-mine-note-input-${c.case_id}`}
                        />
                        <ReminderNoteTemplatePicker
                          currentValue={noteDraft}
                          onInsert={(text) => setNoteDraft(text.slice(0, 240))}
                          testidPrefix={`pj-mine-tpl-${c.case_id}`}
                          compact
                        />
                        <div className="mt-2 flex items-center justify-between gap-2 flex-wrap">
                          <span className="text-[11px] text-[#857E9C]">
                            {noteDraft.length}/240 · shown to the parent in the 5-day gentle nudge.
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={cancelNoteEdit}
                              disabled={noteSaving}
                              className="text-xs text-[#4B4567] hover:text-[#1A1330] px-2 py-1 disabled:opacity-60"
                              data-testid={`pj-mine-note-cancel-${c.case_id}`}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={saveNote}
                              disabled={noteSaving}
                              className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1 text-xs font-semibold disabled:bg-[#C9C0DC]"
                              data-testid={`pj-mine-note-save-${c.case_id}`}
                            >
                              {noteSaving ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />} Save
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : c.reminder_note ? (
                      <div className="flex items-stretch gap-2">
                        <button
                          type="button"
                          onClick={() => openNoteEdit(c)}
                          className="flex-1 text-left rounded-xl border border-[#D6CFE8] bg-[#F5F1FB] hover:bg-[#EFE7FA] p-3 transition-colors group"
                          data-testid={`pj-mine-note-preview-${c.case_id}`}
                        >
                          <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-1 inline-flex items-center gap-1">
                            <MessageSquare size={10} /> Reminder note
                            <span className="ml-2 text-[10px] text-[#857E9C] normal-case tracking-normal font-normal group-hover:text-[#3D1A78]">
                              (tap to edit)
                            </span>
                          </div>
                          <div className="text-sm text-[#1A1330] italic leading-snug">
                            &ldquo;{c.reminder_note}&rdquo;
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setPreviewCaseId(c.case_id)}
                          className="rounded-xl border border-[#D6CFE8] bg-white hover:bg-[#F5F1FB] px-3 text-xs font-semibold text-[#3D1A78] inline-flex items-center gap-1 self-stretch"
                          title="Preview the reminder email a parent will receive"
                          data-testid={`pj-mine-note-emailpreview-${c.case_id}`}
                        >
                          <Mail size={12} /> Preview
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 flex-wrap">
                        <button
                          type="button"
                          onClick={() => openNoteEdit(c)}
                          className="text-xs text-[#3D1A78] hover:underline inline-flex items-center gap-1"
                          data-testid={`pj-mine-note-add-${c.case_id}`}
                        >
                          <MessageSquare size={11} /> Add a personal reminder note
                        </button>
                        <button
                          type="button"
                          onClick={() => setPreviewCaseId(c.case_id)}
                          className="text-xs text-[#4B4567] hover:text-[#3D1A78] inline-flex items-center gap-1"
                          title="Preview the reminder email a parent will receive (uses the default template)"
                          data-testid={`pj-mine-note-emailpreview-${c.case_id}`}
                        >
                          <Mail size={11} /> Preview reminder email
                        </button>
                      </div>
                    )}

                    {/* PRIVATE case notes — mediator-only, never surfaced
                        to parents. Separate storage + endpoint from the
                        reminder_note above. */}
                    {caseNotesEditingId === c.case_id ? (
                      <div className="mt-3 rounded-2xl border border-[#D6CFE8] bg-[#FBF9FE] p-3 space-y-2">
                        <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] inline-flex items-center gap-1">
                          <Lock size={10} /> Private notes · never shared with parents
                        </div>
                        <textarea
                          value={caseNotesDraft}
                          onChange={(e) => setCaseNotesDraft(e.target.value)}
                          rows={4}
                          maxLength={2000}
                          placeholder="Internal session context — nobody but you sees this."
                          className="w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78] resize-none"
                          data-testid={`pj-mine-case-notes-textarea-${c.case_id}`}
                        />
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-[#857E9C]">
                            {caseNotesDraft.length}/2000
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={cancelCaseNotesEdit}
                              disabled={caseNotesSaving}
                              className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-white px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                              data-testid={`pj-mine-case-notes-cancel-${c.case_id}`}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={saveCaseNotes}
                              disabled={caseNotesSaving}
                              className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1 text-[11px] font-semibold disabled:bg-[#C9C0DC]"
                              data-testid={`pj-mine-case-notes-save-${c.case_id}`}
                            >
                              {caseNotesSaving ? (
                                <Loader2 size={11} className="animate-spin" />
                              ) : (
                                <Check size={11} />
                              )}{" "}
                              Save
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : c.case_notes ? (
                      <button
                        type="button"
                        onClick={() => openCaseNotesEdit(c)}
                        className="mt-3 group text-left w-full rounded-2xl border border-[#D6CFE8] bg-[#FBF9FE] p-3 hover:border-[#3D1A78] transition-colors"
                        data-testid={`pj-mine-case-notes-preview-${c.case_id}`}
                      >
                        <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-1 inline-flex items-center gap-1">
                          <Lock size={10} /> Private notes · never shared
                          <span className="ml-2 text-[10px] text-[#857E9C] normal-case tracking-normal font-normal group-hover:text-[#3D1A78]">
                            (tap to edit)
                          </span>
                        </div>
                        <div className="text-sm text-[#1A1330] leading-snug whitespace-pre-wrap line-clamp-3">
                          {c.case_notes}
                        </div>
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => openCaseNotesEdit(c)}
                        className="mt-2 text-xs text-[#4B4567] hover:text-[#3D1A78] hover:underline inline-flex items-center gap-1"
                        data-testid={`pj-mine-case-notes-add-${c.case_id}`}
                      >
                        <Lock size={11} /> Add private notes
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        {/* Firm-name / watermark modal for PDF downloads */}
        {downloadFor && (
          <div
            className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4"
            onClick={closeDownload}
            data-testid="pj-download-modal-backdrop"
          >
            <div
              className="bg-white rounded-3xl shadow-xl max-w-md w-full p-6 relative"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-labelledby="pj-download-modal-title"
              ref={downloadModalRef}
              data-testid="pj-download-modal"
            >
              <button
                type="button"
                onClick={closeDownload}
                disabled={downloading}
                className="absolute top-3 right-3 text-[#857E9C] hover:text-[#1A1330] disabled:opacity-40"
                data-testid="pj-download-modal-close"
                aria-label="Close"
              >
                <X size={16} />
              </button>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-2xl bg-[#F5F1FB] text-[#3D1A78] grid place-items-center shrink-0">
                  <FileDown size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
                    Case {downloadFor.caseId}
                  </div>
                  <h3
                    id="pj-download-modal-title"
                    className="font-serif text-xl text-[#1A1330] mt-1 leading-tight"
                  >
                    Download case status PDF
                  </h3>
                  <p className="text-xs text-[#4B4567] mt-2 leading-relaxed">
                    We'll stamp your firm name plus a UTC download
                    timestamp on every page so anyone who receives
                    this copy can prove which version they were given.
                  </p>
                </div>
              </div>

              <label
                htmlFor="pj-firm-name-input"
                className="block mt-5 text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Firm name for watermark
              </label>
              <input
                id="pj-firm-name-input"
                type="text"
                value={firmName}
                onChange={(e) => setFirmName(e.target.value)}
                placeholder="e.g. Acme Legal LLP"
                autoFocus
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                data-testid="pj-download-firm-input"
              />
              <div className="text-[11px] text-[#857E9C] mt-1">
                Saved locally for next time.
              </div>

              <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={closeDownload}
                  disabled={downloading}
                  className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#FAF8FD] px-4 py-2 text-sm font-semibold disabled:opacity-60"
                  data-testid="pj-download-cancel"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={downloadCaseStatus}
                  disabled={downloading || !firmName.trim()}
                  className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                  data-testid="pj-download-confirm"
                >
                  {downloading ? <><Loader2 size={12} className="animate-spin" /> Preparing…</> : <><FileDown size={12} /> Download PDF</>}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      <ReminderPreviewModal
        open={!!previewCaseId}
        caseId={previewCaseId}
        onClose={() => setPreviewCaseId(null)}
      />
      <ProfessionalDirectoryModal
        open={directoryOpen}
        caseId={directoryCaseId}
        onClose={() => setDirectoryOpen(false)}
      />
    </AppShell>
  );
}
