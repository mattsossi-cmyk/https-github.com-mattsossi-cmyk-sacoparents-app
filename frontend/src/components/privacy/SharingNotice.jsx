import React from "react";

import { SHARING_NOTICES } from "../../lib/proVisibility";
import { ProSeeLink } from "./ProSeeLink";

// Short "Who sees this" notice shown inside an assessment.
export function SharingNotice({ area, className = "" }) {
  const n = SHARING_NOTICES[area];
  return (
    <div data-testid={`sharing-notice-${area}`} className={`rounded-xl border border-purple-200 bg-white/85 px-4 py-3 text-[12px] leading-relaxed text-slate-700 ${className}`}>
      <p className="font-bold text-[#3B1C6B] flex items-center gap-1.5 mb-0.5">
        <i className="fa-solid fa-user-lock" aria-hidden="true"></i>
        Who sees this
      </p>
      <p>
        {n.stays} {n.leaves}
      </p>
      <ProSeeLink testid={`sharing-notice-${area}-link`} area={area} className="mt-1 text-[12px]" />
    </div>
  );
}
