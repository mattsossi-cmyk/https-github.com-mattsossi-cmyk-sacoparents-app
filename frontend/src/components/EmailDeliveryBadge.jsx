import { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { api } from "../lib/api";

/**
 * Turns an ISO string into a short human-readable relative-time
 * label. Rolls up to "days ago" past 48h and falls back to a
 * localized date past 30 days.
 */
export function formatRelative(iso) {
  if (!iso) return null;
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffSec = Math.round((now - then) / 1000);
  if (Number.isNaN(diffSec) || diffSec < 0) return "just now";
  if (diffSec < 45) return "just now";
  if (diffSec < 90) return "1 min ago";
  const min = Math.round(diffSec / 60);
  if (min < 45) return `${min} min ago`;
  if (min < 90) return "1 hr ago";
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  if (hr < 48) return "yesterday";
  const day = Math.round(hr / 24);
  if (day < 30) return `${day} days ago`;
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

/**
 * Small "✓ Sent to X · 2 min ago" badge shown next to each report
 * page's Email me button so parents don't tap twice.
 * - Renders nothing until a delivery has actually happened.
 * - Auto-refreshes every 30s so the relative label stays fresh.
 * - `refreshKey` bumps to refetch after the parent taps Email again.
 */
export default function EmailDeliveryBadge({ reportType, refreshKey = 0 }) {
  const [slot, setSlot] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/report-deliveries");
        if (!cancelled) setSlot(r?.data?.[reportType] || null);
      } catch { /* ignore — badge is optional UX */ }
    })();
    return () => { cancelled = true; };
  }, [reportType, refreshKey]);

  // Bump `tick` every 30s so relative time re-renders.
  useEffect(() => {
    const t = setInterval(() => setTick((v) => v + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  if (!slot || !slot.last_sent_at) return null;
  const rel = formatRelative(slot.last_sent_at);
  const iso = slot.last_sent_at;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-[#E1F3E8] border border-[#B7DEC6] text-[#186142] px-2.5 py-0.5 text-[11px] font-semibold"
      title={`Sent to ${slot.last_sent_to} at ${iso}`}
      data-testid={`email-delivery-badge-${reportType}`}
      data-iso={iso}
      data-tick={tick}
    >
      <CheckCircle2 size={11} />
      Sent{slot.last_sent_to ? ` to ${slot.last_sent_to}` : ""} · {rel}
    </span>
  );
}
