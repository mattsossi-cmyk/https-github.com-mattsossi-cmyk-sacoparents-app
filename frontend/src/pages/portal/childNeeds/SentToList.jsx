import React from "react";

import CONTENT from "../childNeedsContent.json";
import { NEEDS_ART } from "../selfJourney/selfJourneyArt";

const ORDER = NEEDS_ART.items.map((i) => i.key);

const SHORT = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c.card_title.replace(" Assessment", "")]));
const when = (iso) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

// "Sent to" list under a completed form: who received it, which forms, when.
export function SentToList({ shares, category }) {
  const mine = shares.filter((s) => s.categories.includes(category));
  return (
    <div data-testid={`child-needs-sent-to-${category}`} className="mt-5 rounded-lg border border-[#E2E8F0] bg-[#FBF9FC] px-4 py-3">
      <p className="text-[0.6875rem] font-bold uppercase tracking-wider text-[#4A154B] mb-1.5">
        <i className="fa-solid fa-paper-plane mr-1.5"></i>Sent to
      </p>
      {mine.length === 0 ? (
        <p data-testid="child-needs-sent-to-empty" className="text-[0.75rem] text-slate-500">
          Not sent to a provider yet.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {mine.map((s) => (
            <li key={s.share_id} data-testid={`child-needs-sent-to-item-${s.share_id}`} className="text-[0.75rem] text-slate-700 leading-snug">
              <span className="font-semibold text-slate-900">{s.provider_name}</span> · {s.role_label}
              <span className="block text-slate-500">
                {ORDER.filter((k) => s.categories.includes(k)).map((k) => SHORT[k]).join(", ")} · {when(s.sent_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
