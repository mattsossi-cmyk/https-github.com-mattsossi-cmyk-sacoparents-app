/**
 * ConsentHistoryModal — self-serve HB 300 paper trail.
 *
 * Lists every consent event on the caller's record:
 *   * marketing_opt_in  / marketing_opt_out  (§181.152)
 *   * hb300_ack                              (§181.154 notice receipt)
 *
 * Each row shows: what happened, when, from which IP, on which
 * device (UA). No writes, no PHI — just a mirror of the caller's
 * own `phi_access_log` rows.
 *
 * Rendered from `MarketingConsentToggle` via a "See history" link.
 */
import React, { useCallback, useEffect, useState } from "react";
import { X, Megaphone, ShieldCheck, Loader2 } from "lucide-react";
import { api } from "../../lib/api";


const ACTION_META = {
  marketing_opt_in: {
    label:  "Opted IN to marketing communications",
    accent: "#1F5C3B", accentBg: "#E7F4EC",
    icon:   Megaphone,
  },
  marketing_opt_out: {
    label:  "Opted OUT of marketing communications",
    accent: "#8A5B00", accentBg: "#FBF3DC",
    icon:   Megaphone,
  },
  hb300_ack: {
    label:  "Acknowledged the HB 300 Notice",
    accent: "#3D1A78", accentBg: "#F5F1FB",
    icon:   ShieldCheck,
  },
};


function formatWhen(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium", timeStyle: "short",
    });
  } catch { return iso; }
}


function EventRow({ ev }) {
  const meta = ACTION_META[ev.action] || {
    label: ev.action, accent: "#3D1A78", accentBg: "#F5F1FB", icon: ShieldCheck,
  };
  const Icon = meta.icon;
  return (
    <li
      className="flex items-start gap-3 py-3 border-b border-[#E5E0EE] last:border-b-0"
      data-testid={`consent-event-${ev.action}`}
    >
      <div
        className="shrink-0 h-8 w-8 rounded-full grid place-items-center"
        style={{ background: meta.accentBg, color: meta.accent }}
        aria-hidden
      >
        <Icon size={13} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-[#1A1330]">
          {meta.label}
        </div>
        <div className="text-[0.6875rem] text-[#4B4567] mt-0.5">
          {formatWhen(ev.at)}
          {ev.ip && <> · <span className="font-mono">{ev.ip}</span></>}
          {ev.resource_id && <> · notice {ev.resource_id}</>}
        </div>
        {ev.user_agent && (
          <div
            className="text-[0.625rem] text-[#6E6787] mt-0.5 truncate max-w-[520px]"
            title={ev.user_agent}
          >
            {ev.user_agent}
          </div>
        )}
      </div>
    </li>
  );
}


export default function ConsentHistoryModal({ open, onClose }) {
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get("/me/hb300/consent-history");
      setEvents(Array.isArray(data?.events) ? data.events : []);
    } catch {
      setError("Couldn't load your consent history right now.");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) reload();
  }, [open, reload]);

  // Close on Escape for a11y.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-3 sm:p-6 bg-[#1A133080] backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-history-title"
      data-testid="consent-history-modal"
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-5 border-b border-[#E5E0EE]">
          <div>
            <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
              HB 300 &sect;181.152 · &sect;181.154
            </div>
            <h2
              id="consent-history-title"
              className="font-serif text-xl text-[#1A1330] mt-0.5 leading-tight"
            >
              Your consent history
            </h2>
            <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">
              Every marketing opt-in / opt-out and every HB&nbsp;300 notice
              acknowledgement on your account, newest first.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close consent history"
            data-testid="consent-history-close"
            className="shrink-0 h-8 w-8 rounded-full grid place-items-center text-[#4B4567] hover:bg-[#F5F1FB] transition-colors"
          >
            <X size={14} />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 pb-5">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-[#4B4567]">
              <Loader2 size={14} className="animate-spin" /> Loading your history...
            </div>
          ) : error ? (
            <div className="py-6 text-sm text-[#B02A2A]" data-testid="consent-history-error">
              {error}
            </div>
          ) : events.length === 0 ? (
            <div className="py-6 text-sm text-[#4B4567]" data-testid="consent-history-empty">
              No consent events on file yet. When you toggle marketing on or
              off, or acknowledge an updated HB&nbsp;300 notice, it&rsquo;ll
              show up here immediately.
            </div>
          ) : (
            <ul className="mt-2" data-testid="consent-history-list">
              {events.map((ev, i) => (
                <EventRow key={`${ev.action}-${ev.at || i}`} ev={ev} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
