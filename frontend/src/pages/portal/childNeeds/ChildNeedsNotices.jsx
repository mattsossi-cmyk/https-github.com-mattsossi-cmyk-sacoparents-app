import React from "react";

import CONTENT from "../childNeedsContent.json";
import { ProSeeLink } from "../../../components/privacy/ProSeeLink";

const N = CONTENT.notices;
const ICONS = { confidentiality: "fa-lock", privacy: "fa-shield-heart" };
const fmt = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

// Notice of Confidentiality + Health Information Privacy Notice, shown at the top of every Child Needs form.
export function NoticesBox({ ackDate }) {
  return (
    <div data-testid="child-needs-notices" className="rounded-xl border border-purple-200 bg-[#F4EEF5] p-4 space-y-3 text-[0.75rem] leading-relaxed text-slate-700">
      {["confidentiality", "privacy"].map((k) => (
        <div key={k} data-testid={`child-needs-notice-${k}`}>
          <p className="font-bold text-[#4A154B] flex items-center gap-1.5 mb-0.5">
            <i className={`fa-solid ${ICONS[k]}`}></i>
            {N[k].title}
          </p>
          <p>{N[k].body}</p>
        </div>
      ))}
      <ProSeeLink testid="child-needs-notices-pros-see-link" area="child-needs" className="text-[0.75rem]" />
      {ackDate && (
        <p data-testid="child-needs-ack-done" className="text-[0.6875rem] font-semibold text-emerald-700">
          <i className="fa-solid fa-circle-check mr-1"></i>
          {N.ack_done.replace("{date}", fmt(ackDate))}
        </p>
      )}
    </div>
  );
}

// One-time "I understand" tick before the first save (remembered on the account afterwards).
export function AckTick({ checked, onChange }) {
  return (
    <label className="flex items-start gap-2.5 rounded-xl border-2 border-dashed border-purple-300 bg-white p-3 cursor-pointer">
      <input type="checkbox" data-testid="child-needs-ack" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 w-4 h-4 accent-[#4A154B]" />
      <span className="text-[12.5px] font-semibold text-slate-800">{N.ack_label}</span>
    </label>
  );
}
