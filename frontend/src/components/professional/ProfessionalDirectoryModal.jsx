/**
 * ProfessionalDirectoryModal — mediator picks a co-manager from the
 * sacoparentsalign.com directory and dispatches an invitation.
 *
 * Two panes inside one modal:
 *   1. LIST  — searchable list of directory professionals, with a
 *              per-row "Invite" button. Optional case-binding pill
 *              at the top when the modal is opened from a specific
 *              case row on /mine.
 *   2. SEND  — invite composer for the picked professional. Editable
 *              personal note. Submit fires
 *              POST /api/professional/directory/invite.
 *
 * Backed by:
 *   GET  /api/professional/directory?q=&specialty=
 *   POST /api/professional/directory/invite
 *
 * TODO: swap `_MOCK_DIRECTORY` on the backend with the sibling API
 *       once sacoparentsalign.com exposes /api/directory/professionals
 *       (see /app/memory/INTEGRATION_TODO_sacoparentsalign.md).
 */
import { useEffect, useRef, useState } from "react";
import {
  Loader2,
  X,
  Search,
  Send,
  MapPin,
  UserRound,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { logError } from "../../lib/logger";


function ProCard({ pro, onInvite, testidBase }) {
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white px-4 py-3 flex items-start gap-3"
      data-testid={`${testidBase}-${pro.id}`}
    >
      <div className="w-11 h-11 rounded-full bg-[#EFE9F9] text-[#3D1A78] grid place-items-center shrink-0">
        <UserRound size={16} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-[#1A1330] leading-tight">
          {pro.name}
        </div>
        <div className="text-[0.75rem] text-[#4B4567] mt-0.5">
          {pro.title}
          {pro.city && (
            <span className="text-[#6E6787] inline-flex items-center gap-0.5">
              {" · "}<MapPin size={10} className="inline" /> {pro.city}
            </span>
          )}
        </div>
        {pro.bio && (
          <p className="text-[0.75rem] text-[#4B4567] mt-1 leading-snug line-clamp-2">
            {pro.bio}
          </p>
        )}
        {Array.isArray(pro.specialties) && pro.specialties.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {pro.specialties.slice(0, 4).map((s) => (
              <span
                key={s}
                className="rounded-full bg-[#F5F1FB] text-[#3D1A78] px-2 py-0.5 text-[0.625rem] font-semibold"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={() => onInvite(pro)}
        className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold self-center shrink-0"
        data-testid={`${testidBase}-invite-${pro.id}`}
      >
        Invite
      </button>
    </div>
  );
}


export default function ProfessionalDirectoryModal({ open, caseId, onClose }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [pros, setPros] = useState([]);
  const [error, setError] = useState(null);
  // Two panes — "list" or "send" (composer for a picked professional).
  const [pane, setPane] = useState("list");
  const [picked, setPicked] = useState(null);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const dialogRef = useRef(null);
  const searchInputRef = useRef(null);

  // Reset every time the modal opens so it doesn't reopen mid-send.
  useEffect(() => {
    if (open) {
      setPane("list");
      setPicked(null);
      setNote("");
      setError(null);
      setQuery("");
    }
  }, [open, caseId]);

  useEffect(() => {
    if (!open || pane !== "list") return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const t = setTimeout(() => {
      api
        .get("/professional/directory", {
          params: query.trim() ? { q: query.trim() } : {},
        })
        .then((r) => {
          if (!cancelled) setPros(r.data?.professionals || []);
        })
        .catch((err) => {
          if (cancelled) return;
          logError("directory load failed", err);
          const detail = err?.response?.data?.detail || "Couldn't load the directory.";
          setError(String(detail));
        })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, query ? 250 : 0);   // small debounce while typing
    return () => { cancelled = true; clearTimeout(t); };
  }, [open, pane, query]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleInvite = (pro) => {
    setPicked(pro);
    setPane("send");
    setNote("");
  };

  const handleSend = async () => {
    if (!picked || sending) return;
    setSending(true);
    try {
      const body = { professional_id: picked.id };
      if (caseId) body.case_id = caseId;
      if (note.trim()) body.personal_note = note.trim();
      const r = await api.post("/professional/directory/invite", body);
      const to = r.data?.delivered_to || picked.contact_email || picked.name;
      toast.success(`Invitation sent to ${to}.`);
      onClose();
    } catch (err) {
      logError("directory invite failed", err);
      const detail = err?.response?.data?.detail || "Couldn't send the invitation.";
      toast.error(String(detail));
    } finally {
      setSending(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="pdir-backdrop"
    >
      <div
        className="bg-white rounded-3xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col relative"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pdir-title"
        ref={dialogRef}
        data-testid="pdir-modal"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 text-[#6E6787] hover:text-[#1A1330]"
          aria-label="Close"
          data-testid="pdir-close"
        >
          <X size={16} />
        </button>

        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-[#EEE8F7]">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
            <UserRound size={12} /> Professional directory · sacoparentsalign.com
          </div>
          <h3
            id="pdir-title"
            className="font-serif text-2xl text-[#1A1330] mt-1 leading-tight"
          >
            {pane === "list" ? "Invite a professional" : `Invite ${picked?.name}`}
          </h3>
          <p className="text-[0.8125rem] text-[#4B4567] mt-1 leading-relaxed">
            {pane === "list"
              ? "Pick a co-parenting professional from the sacoparentsalign.com directory and we'll email them an invitation to co-manage the case."
              : "We'll email them at sacoparentsalign.com. They'll accept from there — no new login needed."}
          </p>
          {caseId && (
            <div
              className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#F5F1FB] text-[#3D1A78] px-2.5 py-0.5 text-[0.6875rem] font-semibold"
              data-testid="pdir-case-pill"
            >
              Case <span className="font-mono">{caseId}</span>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden">
          {pane === "list" ? (
            <div className="h-full flex flex-col">
              <div className="px-6 py-3 border-b border-[#EEE8F7]">
                <div className="relative">
                  <Search
                    size={13}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6E6787]"
                    aria-hidden
                  />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search name, city, specialty…"
                    className="w-full rounded-full border border-[#E5E0EE] bg-white text-[#1A1330] text-sm pl-9 pr-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                    data-testid="pdir-search"
                  />
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#FBF9FE]">
                {loading ? (
                  <div
                    className="flex items-center gap-2 text-sm text-[#6E6787] justify-center py-8"
                    data-testid="pdir-loading"
                  >
                    <Loader2 size={14} className="animate-spin" /> Loading directory…
                  </div>
                ) : error ? (
                  <div
                    className="rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] px-4 py-3 text-sm"
                    role="alert"
                    data-testid="pdir-error"
                  >
                    {error}
                  </div>
                ) : pros.length === 0 ? (
                  <p
                    className="text-sm text-[#6E6787] text-center py-8"
                    data-testid="pdir-empty"
                  >
                    No professionals match your search.
                  </p>
                ) : (
                  <div className="space-y-3" data-testid="pdir-results">
                    {pros.map((p) => (
                      <ProCard
                        key={p.id}
                        pro={p}
                        onInvite={handleInvite}
                        testidBase="pdir-row"
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="px-6 py-5 overflow-y-auto max-h-[55vh]" data-testid="pdir-send-pane">
              <button
                type="button"
                onClick={() => { setPane("list"); setPicked(null); }}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] hover:underline mb-4"
                data-testid="pdir-back-to-list"
              >
                <ArrowLeft size={12} /> Back to directory
              </button>

              <div className="rounded-2xl border border-[#E5E0EE] bg-white px-4 py-3">
                <div className="text-sm font-semibold text-[#1A1330]">
                  {picked?.name}
                </div>
                <div className="text-[0.75rem] text-[#4B4567] mt-0.5">
                  {picked?.title}
                  {picked?.city && (
                    <span className="text-[#6E6787]"> · {picked.city}</span>
                  )}
                </div>
                <div className="text-[0.6875rem] text-[#6E6787] mt-1">
                  Invitation will be emailed to{" "}
                  <span className="font-mono text-[#3D1A78]">{picked?.contact_email}</span>.
                </div>
              </div>

              <label
                htmlFor="pdir-note"
                className="mt-4 block text-[0.6875rem] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
              >
                A note to include (optional)
              </label>
              <textarea
                id="pdir-note"
                rows={4}
                maxLength={500}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a personal message so they know why you're reaching out…"
                className="mt-1 block w-full rounded-2xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78] resize-none"
                data-testid="pdir-note-input"
              />
              <div className="text-[0.625rem] text-[#6E6787] mt-1 text-right">
                {note.length} / 500
              </div>

              <div className="mt-3 text-[0.6875rem] text-[#6E6787] inline-flex items-start gap-1.5">
                <CheckCircle2 size={11} className="mt-0.5 text-[#1F5C3B]" />
                <span>
                  They'll accept from{" "}
                  <span className="font-mono text-[#3D1A78]">sacoparentsalign.com</span>
                  {" "}— no login required on this app.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#EEE8F7] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#FAF8FD] bg-white px-4 py-2 text-sm font-semibold"
            data-testid="pdir-cancel"
          >
            Cancel
          </button>
          {pane === "send" && (
            <button
              type="button"
              onClick={handleSend}
              disabled={sending}
              className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:bg-[#C9C0DC] disabled:cursor-not-allowed inline-flex items-center gap-1.5"
              data-testid="pdir-send"
            >
              {sending ? (
                <><Loader2 size={13} className="animate-spin" /> Sending…</>
              ) : (
                <><Send size={13} /> Send invitation</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
