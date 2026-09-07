/**
 * FoundationStatementShareModal — lets a parent send their
 * Foundation Statement PDF to a co-parent or mediator (or just
 * download it locally).
 *
 * Backed by:
 *   GET  /api/mediation/foundation-statement.pdf   (download)
 *   POST /api/mediation/foundation-statement/share (email)
 *
 * The parent's raw prompt content never leaves the app in
 * unstructured form — this modal only offers the neutral,
 * disclaimer-stamped PDF as an artefact.
 */
import { useEffect, useRef, useState } from "react";
import { Loader2, X, Send, Download, ShieldCheck, History, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

export default function FoundationStatementShareModal({
  open,
  onClose,
}) {
  const [tab, setTab] = useState("share"); // "share" | "download" | "history"
  const [recipientEmail, setRecipientEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [downloading, setDownloading] = useState(false);
  // Share-history state — loaded lazily when the History tab is
  // first opened, and reloaded after every successful send so the
  // list stays fresh.
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [resendingId, setResendingId] = useState(null);
  const dialogRef = useRef(null);

  // Reset every time the modal reopens.
  useEffect(() => {
    if (open) {
      setTab("share");
      setRecipientEmail("");
      setRecipientName("");
      setNote("");
    }
  }, [open]);

  // Lazy-load history when the tab is first shown, so the modal
  // opens instantly regardless of network latency.
  useEffect(() => {
    if (!open || tab !== "history") return;
    let cancelled = false;
    setHistoryLoading(true);
    api
      .get("/mediation/foundation-statement/shares")
      .then((r) => {
        if (!cancelled) setHistory(r.data?.shares || []);
      })
      .catch((err) => {
        if (!cancelled) {
          logError("foundation history load failed", err);
          toast.error("Couldn't load your share history.");
        }
      })
      .finally(() => { if (!cancelled) setHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [open, tab]);

  // Escape-to-close + focus trap-ish: initial focus on the first
  // input. Full trap left off intentionally — this modal is small
  // enough that Tab cycling within the browser's default order
  // is comfortable for keyboard users.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape" && !sending && !downloading) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, sending, downloading, onClose]);

  if (!open) return null;

  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipientEmail.trim());
  const canSend = validEmail && !sending && !downloading;

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await api.get("/mediation/foundation-statement.pdf", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "foundation-statement.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Downloaded your Foundation Statement.");
      onClose();
    } catch (err) {
      logError("foundation download failed", err);
      const detail = err?.response?.data?.detail || "Download failed.";
      toast.error(String(detail));
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = async (e) => {
    e?.preventDefault?.();
    if (!canSend) return;
    setSending(true);
    try {
      const body = { recipient_email: recipientEmail.trim() };
      if (recipientName.trim()) body.recipient_name = recipientName.trim();
      if (note.trim()) body.personal_note = note.trim();
      await api.post("/mediation/foundation-statement/share", body);
      toast.success(`Sent to ${recipientEmail.trim()}.`);
      onClose();
    } catch (err) {
      logError("foundation share failed", err);
      const detail = err?.response?.data?.detail || "Send failed.";
      toast.error(String(detail));
    } finally {
      setSending(false);
    }
  };

  const handleResend = async (shareId, recipientEmailLabel) => {
    setResendingId(shareId);
    try {
      await api.post(
        `/mediation/foundation-statement/shares/${shareId}/resend`,
        {},
      );
      toast.success(`Re-sent to ${recipientEmailLabel}.`);
      // Refresh the list so the new row appears at the top.
      try {
        const r = await api.get("/mediation/foundation-statement/shares");
        setHistory(r.data?.shares || []);
      } catch {
        /* soft-fail — the send itself succeeded */
      }
    } catch (err) {
      logError("foundation resend failed", err);
      const detail = err?.response?.data?.detail || "Resend failed.";
      toast.error(String(detail));
    } finally {
      setResendingId(null);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4"
      onClick={(!sending && !downloading) ? onClose : undefined}
      data-testid="foundation-share-modal-backdrop"
    >
      <div
        className="bg-white rounded-3xl shadow-xl max-w-md w-full p-6 relative"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="foundation-share-modal-title"
        ref={dialogRef}
        data-testid="foundation-share-modal"
      >
        <button
          type="button"
          onClick={onClose}
          disabled={sending || downloading}
          className="absolute top-3 right-3 text-[#857E9C] hover:text-[#1A1330] disabled:opacity-40"
          aria-label="Close"
          data-testid="foundation-share-modal-close"
        >
          <X size={16} />
        </button>

        <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
          Foundation Statement
        </div>
        <h3
          id="foundation-share-modal-title"
          className="font-serif text-2xl text-[#1A1330] mt-1 leading-tight"
        >
          Send this to a co-parent or mediator
        </h3>
        <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
          We&rsquo;ll email a one-page PDF of your reflection — warm, neutral,
          and stamped with a court-report disclaimer. Handy to send before a
          first mediation session.
        </p>

        {/* Tab strip */}
        <div className="mt-5 inline-flex bg-[#EFE9F9] rounded-full p-1">
          <button
            type="button"
            onClick={() => setTab("share")}
            className={`px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1 transition ${
              tab === "share" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
            }`}
            data-testid="foundation-share-tab-share"
          >
            <Send size={12} /> Email
          </button>
          <button
            type="button"
            onClick={() => setTab("download")}
            className={`px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1 transition ${
              tab === "download" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
            }`}
            data-testid="foundation-share-tab-download"
          >
            <Download size={12} /> Download PDF
          </button>
          <button
            type="button"
            onClick={() => setTab("history")}
            className={`px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1 transition ${
              tab === "history" ? "bg-white text-[#3D1A78] shadow" : "text-[#4B4567]"
            }`}
            data-testid="foundation-share-tab-history"
          >
            <History size={12} /> History
          </button>
        </div>

        {tab === "share" && (
          <form onSubmit={handleShare} className="mt-5 space-y-4" data-testid="foundation-share-form">
            <div>
              <label
                htmlFor="foundation-share-recipient-email"
                className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Recipient email <span className="text-[#C05621]">*</span>
              </label>
              <input
                id="foundation-share-recipient-email"
                type="email"
                required
                autoFocus
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                placeholder="mediator@example.com"
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                data-testid="foundation-share-recipient-email"
              />
            </div>
            <div>
              <label
                htmlFor="foundation-share-recipient-name"
                className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Recipient name (optional)
              </label>
              <input
                id="foundation-share-recipient-name"
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="Sam Mediator"
                maxLength={80}
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                data-testid="foundation-share-recipient-name"
              />
            </div>
            <div>
              <label
                htmlFor="foundation-share-note"
                className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                Personal note (optional)
              </label>
              <textarea
                id="foundation-share-note"
                rows={3}
                maxLength={500}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Looking forward to our session on Thursday — this is where my head is at."
                className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78] resize-none"
                data-testid="foundation-share-note"
              />
              <div className="mt-1 text-[11px] text-[#857E9C] text-right">
                {note.length}/500
              </div>
            </div>

            <div
              className="flex items-start gap-2 rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] px-3 py-2 text-[12px] text-[#3D1A78]"
              data-testid="foundation-share-privacy-strip"
            >
              <ShieldCheck size={14} className="flex-shrink-0 mt-0.5" />
              <p className="!m-0 leading-relaxed text-[#1A1330]">
                The PDF is stamped with a court-report disclaimer so nobody
                mistakes it for an evaluation. Replies come back to your
                email address.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={sending}
                className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#FAF8FD] px-4 py-2 text-sm font-semibold disabled:opacity-60"
                data-testid="foundation-share-cancel"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSend}
                className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                data-testid="foundation-share-submit"
              >
                {sending ? (
                  <><Loader2 size={12} className="animate-spin" /> Sending…</>
                ) : (
                  <><Send size={12} /> Send</>
                )}
              </button>
            </div>
          </form>
        )}

        {tab === "download" && (
          <div className="mt-5 space-y-4" data-testid="foundation-download-panel">
            <p className="text-sm text-[#4B4567] leading-relaxed">
              Download the one-page PDF and forward it however you like —
              email, DM, or print. The PDF is stamped with a court-report
              disclaimer and today&rsquo;s timestamp.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={downloading}
                className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#FAF8FD] px-4 py-2 text-sm font-semibold disabled:opacity-60"
                data-testid="foundation-download-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDownload}
                disabled={downloading}
                className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                data-testid="foundation-download-confirm"
              >
                {downloading ? (
                  <><Loader2 size={12} className="animate-spin" /> Preparing…</>
                ) : (
                  <><Download size={12} /> Download PDF</>
                )}
              </button>
            </div>
          </div>
        )}

        {tab === "history" && (
          <div className="mt-5" data-testid="foundation-history-panel">
            {historyLoading ? (
              <div className="text-sm text-[#857E9C] flex items-center gap-2 py-6">
                <Loader2 size={13} className="animate-spin" /> Loading your share history…
              </div>
            ) : history.length === 0 ? (
              <div
                className="rounded-2xl border border-dashed border-[#D6CFE8] p-5 text-center text-sm text-[#4B4567]"
                data-testid="foundation-history-empty"
              >
                You haven&rsquo;t sent your Foundation Statement to anyone yet.
                <br />
                Once you do, this list will let you re-send with one tap.
              </div>
            ) : (
              <ul className="space-y-2 max-h-[45vh] overflow-y-auto pr-1">
                {history.map((s) => {
                  const when = s.created_at
                    ? new Date(s.created_at).toLocaleString([], {
                        month: "short", day: "numeric",
                        hour: "2-digit", minute: "2-digit",
                      })
                    : "";
                  const busy = resendingId === s.share_id;
                  return (
                    <li
                      key={s.share_id}
                      className="rounded-2xl border border-[#E5E0EE] bg-[#FBF9FE] px-3 py-2.5 flex items-center gap-3"
                      data-testid={`foundation-history-row-${s.share_id}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-[#1A1330] truncate">
                          {s.recipient_name
                            ? `${s.recipient_name} · ${s.recipient_email}`
                            : s.recipient_email}
                        </div>
                        <div className="text-[11px] text-[#857E9C] mt-0.5">
                          {when}
                          {s.personal_note ? " · note included" : ""}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleResend(s.share_id, s.recipient_email)}
                        disabled={busy || !!resendingId}
                        className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed"
                        data-testid={`foundation-history-resend-${s.share_id}`}
                      >
                        {busy ? (
                          <Loader2 size={11} className="animate-spin" />
                        ) : (
                          <RefreshCw size={11} />
                        )}{" "}
                        Resend
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
            <p className="mt-3 text-[11px] text-[#857E9C]">
              Resends use your CURRENT Foundation Statement — if you&rsquo;ve
              updated it, the recipient sees the newest version.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
