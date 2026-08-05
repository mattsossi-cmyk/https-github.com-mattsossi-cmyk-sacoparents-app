/**
 * GmailComposer — modal composer for a new / reply email, extracted
 * from `pages/Gmail.jsx` so both the full Gmail page and the
 * dashboard mini-inbox can use it without code duplication.
 *
 * Behaviour is unchanged from the original inline component:
 *   - Optional `prefill = { to, subject, body }` for reply-to flows.
 *   - Optional `sourceMessage = { subject, from, body, snippet }`
 *     powers the "Draft a co-parenting reply" AI helper via
 *     POST /api/gmail/draft-reply.
 *   - Sends via POST /api/gmail/send.
 *   - `onClose()` fires when the user cancels or the send succeeds.
 *   - `onSent()` fires after a successful send (before onClose) so
 *     callers can refresh their inbox list.
 */
import { useState } from "react";
import { Loader2, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";

export default function GmailComposer({ prefill, sourceMessage, onClose, onSent }) {
  const [to, setTo] = useState(prefill?.to || "");
  const [subject, setSubject] = useState(prefill?.subject || "");
  const [body, setBody] = useState(prefill?.body || "");
  const [sending, setSending] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [toneNotes, setToneNotes] = useState([]);

  const submit = async (e) => {
    e.preventDefault();
    if (!to || !subject || !body) {
      toast.error("Please fill in recipient, subject, and body.");
      return;
    }
    setSending(true);
    try {
      await api.post("/gmail/send", { to, subject, body });
      toast.success("Email sent.");
      onSent?.();
      onClose?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to send email.");
    } finally {
      setSending(false);
    }
  };

  const draftWithCoach = async () => {
    if (!sourceMessage) {
      toast.error("The coach needs the original message to draft from.");
      return;
    }
    setDrafting(true);
    try {
      const { data } = await api.post("/gmail/draft-reply", {
        original_body:    sourceMessage.body || sourceMessage.snippet || "",
        original_subject: sourceMessage.subject || "",
        original_from:    sourceMessage.from || "",
        my_draft:         body || undefined,
      });
      setBody(data.draft || "");
      setToneNotes(data.tone_notes || []);
      if (data.safety_flag) {
        toast.warning("Safety concern detected — see the Safety page before replying directly.");
      } else {
        toast.success("Coach-drafted reply ready.");
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "The coach couldn't draft this one.");
    } finally {
      setDrafting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" data-testid="gmail-composer">
      <form
        onSubmit={submit}
        className="bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-xl p-6 shadow-2xl max-h-[95vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif text-xl text-[#1A1330]">New email</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-[#857E9C] hover:text-[#1A1330]"
            data-testid="composer-close-btn"
          >
            Close
          </button>
        </div>
        <label className="block text-xs font-semibold text-[#4B4567] mb-1">To</label>
        <input
          type="email"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="w-full border border-[#E5E0EE] rounded-lg px-3 py-2 mb-3 text-sm"
          required
          data-testid="composer-to"
        />
        <label className="block text-xs font-semibold text-[#4B4567] mb-1">Subject</label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full border border-[#E5E0EE] rounded-lg px-3 py-2 mb-3 text-sm"
          required
          data-testid="composer-subject"
        />
        <div className="flex items-center justify-between mb-1">
          <label className="block text-xs font-semibold text-[#4B4567]">Message</label>
          {sourceMessage && (
            <button
              type="button"
              onClick={draftWithCoach}
              disabled={drafting}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] hover:underline disabled:opacity-60"
              data-testid="composer-draft-coach-btn"
            >
              {drafting ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
              {drafting ? "Coach is drafting…" : body ? "Rewrite with coach" : "Draft a co-parenting reply"}
            </button>
          )}
        </div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={10}
          className="w-full border border-[#E5E0EE] rounded-lg px-3 py-2 mb-2 text-sm"
          required
          data-testid="composer-body"
        />
        {toneNotes.length > 0 && (
          <div className="mb-4 rounded-lg bg-[#F5F2FA] border border-[#E5E0EE] p-3" data-testid="composer-tone-notes">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-1.5">
              <Sparkles size={11} /> Coach&apos;s notes
            </div>
            <ul className="text-xs text-[#4B4567] space-y-1">
              {toneNotes.map((n, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-[#3D1A78]">•</span>
                  <span>{n}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-[#4B4567] hover:bg-[#F5F2FA]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={sending}
            className="px-4 py-2 rounded-lg bg-[#3D1A78] text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
            data-testid="composer-send-btn"
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
