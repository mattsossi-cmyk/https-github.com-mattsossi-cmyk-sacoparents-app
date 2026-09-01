/**
 * RecentlySharedWith — compact strip listing the last 3 professionals
 * this parent has emailed the current joint artefact to, with a
 * one-tap re-send button per recipient.
 *
 * Works for both Joint Report and Joint Agreement — the artefact
 * endpoints share the same request/response shape:
 *   GET  /{artefactBase}/{shareId}/recent-recipients
 *   POST /{artefactBase}/{shareId}/email     (used for one-tap resend)
 *
 * Hides itself entirely when there are no recent recipients so it
 * doesn't clutter the page for parents who've never emailed the
 * artefact.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw, Mail } from "lucide-react";
import { api } from "../../lib/api";
import { toast } from "sonner";


const ROLE_LABEL = {
  mediator:                    "Mediator",
  parent_facilitator_ad_litem: "Parent Facilitator Ad Litem",
  trial_court:                 "Trial Court",
  attorney:                    "Family Law Attorney",
  therapist:                   "Therapist / Counsellor",
  other:                       "Reviewer",
};


function formatSince(iso) {
  if (!iso) return null;
  try {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return null;
    const diff = Date.now() - then;
    const days = Math.floor(diff / 86400000);
    if (days < 1) {
      const hrs = Math.floor(diff / 3600000);
      if (hrs < 1) return "just now";
      return `${hrs}h ago`;
    }
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric",
    });
  } catch {
    return null;
  }
}


function initialsOf(name, email) {
  const src = (name || "").trim() || (email || "").split("@")[0] || "?";
  const parts = src.split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}


export default function RecentlySharedWith({
  shareId,
  artefactBase,        // "joint-professional-report" | "joint-agreement"
  artefactLabel,       // "Joint Report" | "Joint Agreement"
}) {
  const [state, setState] = useState({ loading: true, recipients: [] });
  const [resending, setResending] = useState(null);

  const reload = useCallback(async () => {
    if (!shareId) return;
    try {
      const { data } = await api.get(
        `/${artefactBase}/${encodeURIComponent(shareId)}/recent-recipients`,
      );
      setState({
        loading: false,
        recipients: Array.isArray(data?.recipients) ? data.recipients : [],
      });
    } catch {
      setState({ loading: false, recipients: [] });
    }
  }, [shareId, artefactBase]);

  useEffect(() => { reload(); }, [reload]);

  const resend = async (r) => {
    if (!r?.to_email) return;
    setResending(r.to_email);
    try {
      const { data } = await api.post(
        `/${artefactBase}/${encodeURIComponent(shareId)}/email`,
        {
          recipient_email: r.to_email,
          recipient_name:  r.recipient_name || "",
          recipient_role:  r.recipient_role || "other",
          audience_label:  r.audience || undefined,
          parent_message:  "",
        },
      );
      if (data?.ok) {
        toast.success(
          `${artefactLabel} re-sent to ${r.recipient_name || r.to_email}`,
        );
        await reload();
      } else {
        toast.error("Couldn't re-send just now. Please try again.");
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Couldn't re-send right now. Please try again.");
    } finally {
      setResending(null);
    }
  };

  if (state.loading || state.recipients.length === 0) return null;

  return (
    <section
      className="rounded-2xl border border-[#E5E0EE] bg-[#FBFAFD] p-4 sm:p-5"
      data-testid="recently-shared-with"
    >
      <div className="flex items-center gap-2 mb-3">
        <Mail size={13} className="text-[#3D1A78]" />
        <span className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
          Recently shared with
        </span>
        <span className="text-xs text-[#4B4567]">
          · Tap a chip to re-send this {artefactLabel.toLowerCase()}
        </span>
      </div>
      <ul className="flex flex-wrap gap-2">
        {state.recipients.map((r) => {
          const busy = resending === r.to_email;
          const roleLabel = r.audience
            || ROLE_LABEL[r.recipient_role]
            || ROLE_LABEL.other;
          const since = formatSince(r.sent_at);
          const initials = initialsOf(r.recipient_name, r.to_email);
          return (
            <li key={r.to_email}>
              <button
                type="button"
                onClick={() => resend(r)}
                disabled={busy}
                title={`Re-send this ${artefactLabel.toLowerCase()} to ${r.to_email}. A fresh PDF + preview link will go out. Tap to confirm.`}
                data-testid={`recently-shared-with-chip-${r.to_email}`}
                className="group inline-flex items-center gap-2 rounded-full pl-1 pr-3 py-1 bg-white border border-[#E5E0EE] hover:border-[#3D1A78] hover:bg-[#F5F1FB] transition-colors disabled:opacity-60"
              >
                <span
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[#EFE9F9] text-[#3D1A78] text-[11px] font-bold shrink-0"
                  aria-hidden
                >
                  {initials}
                </span>
                <span className="flex flex-col text-left leading-tight min-w-0 max-w-[220px]">
                  <span className="text-xs font-semibold text-[#1A1330] truncate">
                    {r.recipient_name || r.to_email}
                  </span>
                  <span className="text-[10px] text-[#4B4567] truncate">
                    {roleLabel}{since ? ` · ${since}` : ""}
                  </span>
                </span>
                <span
                  className="ml-1 inline-flex items-center gap-1 text-[10px] font-bold text-[#3D1A78] uppercase tracking-[0.14em]"
                  aria-hidden
                >
                  {busy ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <RefreshCw
                      size={12}
                      className="opacity-70 group-hover:opacity-100"
                    />
                  )}
                  {busy ? "Sending" : "Re-send"}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
