import React, { useEffect, useState } from "react";
import { MailX } from "lucide-react";

import { api } from "../../lib/api";

const shown = (c) => (c.fewer_than_5 ? "fewer than 5" : String(c.count));

// Admin-only: reminder emails held back for safety in the last 30 days. Counts only, never who.
export function HeldEmailsCount({ onForbidden }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    api
      .get("/admin/safety-audit-log/held-emails")
      .then((r) => setData(r.data))
      .catch((e) => e?.response?.status === 403 && onForbidden?.());
  }, [onForbidden]);
  if (!data) return null;
  return (
    <section data-testid="held-emails-card" className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 space-y-3">
      <p className="text-base font-bold text-[#1A1330] inline-flex items-center gap-2" data-testid="held-emails-total">
        <MailX size={16} className="text-[#3D1A78]" aria-hidden="true" />
        Reminders held back for safety (last {data.days} days): {shown(data.total)}
      </p>
      <ul className="divide-y divide-[#F0ECF6] text-sm" data-testid="held-emails-list">
        {data.kinds.map((k) => (
          <li key={k.kind} className="flex justify-between gap-4 py-1.5" data-testid={`held-emails-${k.kind}`}>
            <span className="text-[#4B4567]">{k.label}</span>
            <span className="font-semibold text-[#1A1330] tabular-nums">{shown(k)}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-[#6E6787]">
        Emails not sent because a parent has an older saved safety result. Counts only: no names, emails or case codes are kept.
      </p>
    </section>
  );
}
