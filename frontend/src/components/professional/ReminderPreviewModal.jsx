/**
 * ReminderPreviewModal — shows a mediator EXACTLY what the parent
 * receives when the 5-day gentle-nudge sweep fires. Read-only, no
 * dispatch — pure sanity check.
 *
 * Backed by:
 *   GET /api/professional/joint-alignment/cases/{case_id}/reminder-preview
 *       ?parent_index=0|1
 *
 * The email HTML lands inside a sandboxed <iframe srcdoc=...> so any
 * inline JS in the branded template (there is none today, but this
 * defends against future template drift) can't touch the mediator's
 * session. Two tabs — HTML preview / plaintext fallback — because
 * some mediators forward to inboxes that strip HTML.
 */
import { useEffect, useRef, useState } from "react";
import { Loader2, X, Mail, FileText, User, CheckCircle2, Send } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

export default function ReminderPreviewModal({ open, caseId, onClose }) {
  const [tab, setTab] = useState("html");         // "html" | "text"
  const [parentIndex, setParentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [testSending, setTestSending] = useState(false);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (open) {
      setTab("html");
      setParentIndex(0);
      setPreview(null);
      setError(null);
    }
  }, [open, caseId]);

  useEffect(() => {
    if (!open || !caseId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get(
        `/professional/joint-alignment/cases/${encodeURIComponent(caseId)}/reminder-preview`,
        { params: { parent_index: parentIndex } },
      )
      .then((r) => {
        if (!cancelled) setPreview(r.data);
      })
      .catch((err) => {
        if (cancelled) return;
        logError("reminder preview load failed", err);
        const detail =
          err?.response?.data?.detail || "Couldn't load the preview.";
        setError(String(detail));
        toast.error(String(detail));
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, caseId, parentIndex]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleTestSend = async () => {
    if (!caseId || testSending) return;
    setTestSending(true);
    try {
      const r = await api.post(
        `/professional/joint-alignment/cases/${encodeURIComponent(caseId)}/reminder-preview/send-test`,
        {},
        { params: { parent_index: parentIndex } },
      );
      const to = r.data?.delivered_to || "your inbox";
      toast.success(`Test sent to ${to} · look for the [TEST PREVIEW] tag.`);
    } catch (err) {
      logError("reminder test send failed", err);
      const detail = err?.response?.data?.detail || "Couldn't send the test.";
      toast.error(String(detail));
    } finally {
      setTestSending(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="reminder-preview-backdrop"
    >
      <div
        className="bg-white rounded-3xl shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col relative"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="reminder-preview-title"
        ref={dialogRef}
        data-testid="reminder-preview-modal"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 text-[#857E9C] hover:text-[#1A1330]"
          aria-label="Close"
          data-testid="reminder-preview-close"
        >
          <X size={16} />
        </button>

        <div className="px-6 pt-6 pb-4 border-b border-[#EEE8F7]">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
            <Mail size={12} /> Reminder email preview
          </div>
          <h3
            id="reminder-preview-title"
            className="font-serif text-2xl text-[#1A1330] mt-1 leading-tight"
          >
            {preview?.parent_name || preview?.parent_email
              ? `What ${preview.parent_name || preview.parent_email} will receive`
              : "What the parent will receive"}
          </h3>
          <p className="text-[13px] text-[#4B4567] mt-1 leading-relaxed">
            This is the exact email that the 5-day gentle-nudge sweep sends.
            Nothing is dispatched — this preview is for your eyes only.
          </p>

          {/* Parent selector — only shown when the case has both parents */}
          {preview && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-[#4B4567]">
              <span className="inline-flex items-center gap-1">
                <User size={11} />
                <span className="font-semibold text-[#1A1330]">
                  {preview.parent_email}
                </span>
              </span>
              {preview.parent_accepted && (
                <span
                  className="inline-flex items-center gap-1 text-[#0F766E]"
                  data-testid="reminder-preview-accepted-badge"
                >
                  <CheckCircle2 size={11} /> Already accepted — this email would NOT fire
                </span>
              )}
              <div className="ml-auto inline-flex bg-[#EFE9F9] rounded-full p-0.5">
                <button
                  type="button"
                  onClick={() => setParentIndex(0)}
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition ${
                    parentIndex === 0 ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
                  }`}
                  data-testid="reminder-preview-parent-0"
                >
                  Parent 1
                </button>
                <button
                  type="button"
                  onClick={() => setParentIndex(1)}
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition ${
                    parentIndex === 1 ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
                  }`}
                  data-testid="reminder-preview-parent-1"
                >
                  Parent 2
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-b border-[#EEE8F7] flex items-center gap-2 flex-wrap">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#857E9C]">
            Subject
          </div>
          <div
            className="text-[13px] text-[#1A1330] font-semibold flex-1 truncate"
            data-testid="reminder-preview-subject"
          >
            {preview?.subject || "—"}
          </div>
          <div className="inline-flex bg-[#EFE9F9] rounded-full p-0.5">
            <button
              type="button"
              onClick={() => setTab("html")}
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold inline-flex items-center gap-1 transition ${
                tab === "html" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
              }`}
              data-testid="reminder-preview-tab-html"
            >
              <Mail size={10} /> HTML
            </button>
            <button
              type="button"
              onClick={() => setTab("text")}
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold inline-flex items-center gap-1 transition ${
                tab === "text" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
              }`}
              data-testid="reminder-preview-tab-text"
            >
              <FileText size={10} /> Plain
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden bg-[#F8F7FC] p-3">
          {loading ? (
            <div
              className="h-full flex items-center justify-center text-sm text-[#857E9C] gap-2"
              data-testid="reminder-preview-loading"
            >
              <Loader2 size={14} className="animate-spin" /> Rendering preview…
            </div>
          ) : error ? (
            <div
              className="rounded-xl bg-white border border-[#F5D0C5] px-4 py-6 text-sm text-[#9A3A23] text-center"
              role="alert"
              data-testid="reminder-preview-error"
            >
              {error}
            </div>
          ) : tab === "html" ? (
            <iframe
              title="Reminder email preview"
              srcDoc={preview?.html || ""}
              sandbox=""
              className="w-full h-[55vh] rounded-xl bg-white border border-[#E5E0EE]"
              data-testid="reminder-preview-iframe"
            />
          ) : (
            <pre
              className="w-full h-[55vh] overflow-auto whitespace-pre-wrap font-mono text-[12px] text-[#1A1330] bg-white rounded-xl border border-[#E5E0EE] px-4 py-3"
              data-testid="reminder-preview-plaintext"
            >
              {preview?.text || ""}
            </pre>
          )}
        </div>

        <div className="px-6 py-3 border-t border-[#EEE8F7] flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            onClick={handleTestSend}
            disabled={testSending || loading || !preview}
            className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] bg-white px-4 py-2 text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
            title="Email this exact preview to your own inbox to check rendering"
            data-testid="reminder-preview-test-send"
          >
            {testSending ? (
              <><Loader2 size={13} className="animate-spin" /> Sending…</>
            ) : (
              <><Send size={13} /> Send test to my inbox</>
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
            data-testid="reminder-preview-done"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
