import React from "react";
import { Check, ClipboardCheck, ExternalLink, X } from "lucide-react";

import { useCaseSettings } from "../../lib/useCaseSettings";
import { useCheckinLink } from "../../lib/useCheckinLink";
import { useCheckinThanks } from "../../lib/useCheckinThanks";

function ThanksNote({ testid, onClose }) {
  return (
    <div
      role="status"
      data-testid={`${testid}-thanks`}
      className="mt-4 flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 pl-3.5 pr-1 py-1 text-sm text-emerald-900 animate-in fade-in duration-500"
    >
      <Check size={16} className="shrink-0" aria-hidden="true" />
      <p className="flex-1 py-2">Thanks, your check-in is done. There&apos;s nothing else you need to do for it.</p>
      <button
        type="button"
        onClick={onClose}
        data-testid={`${testid}-thanks-close`}
        aria-label="Close message"
        className="shrink-0 w-11 h-11 grid place-items-center rounded-full text-emerald-800 transition-colors hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}

// Same words for both parents. The check-in itself happens on the Align site; this app never asks or saves anything.
export function FamilyCheckinCard({ alignUrl, testid = "family-checkin", stacked = false }) {
  const settings = useCaseSettings();
  const done = settings?.setup_complete === true;
  const [thanks, closeThanks] = useCheckinThanks(done);
  const href = useCheckinLink(alignUrl);
  return (
    <section data-testid={testid} className="rounded-2xl border border-[#e0d5ed] bg-white p-4 sm:p-5 shadow-sm">
      <div className={`flex flex-col gap-4 ${stacked ? "" : "sm:flex-row sm:items-center"}`}>
        <div className="min-w-0 flex-1 flex items-start gap-3">
          <span className="shrink-0 w-11 h-11 rounded-xl bg-[#f2ebfc] text-[#5c2c8e] grid place-items-center" aria-hidden="true">
            <ClipboardCheck size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-extrabold text-[#3b1566]">Family check-in</h3>
              {settings && (
                <span
                  data-testid={`${testid}-status`}
                  data-done={done}
                  className={`text-[0.6875rem] font-bold px-2 py-0.5 rounded-full border ${done ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-slate-100 text-slate-700 border-slate-200"}`}
                >
                  {done ? "Done" : "Not finished yet"}
                </span>
              )}
            </div>
            <p className="text-sm text-[#5f6368] mt-0.5">A short check-in for your case, done on your professional&apos;s site.</p>
          </div>
        </div>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`${testid}-open`}
          aria-label="Open Family check-in (opens in a new tab)"
          className={`shrink-0 self-start ${stacked ? "" : "sm:self-auto"} inline-flex items-center justify-center gap-2 min-h-[44px] rounded-full bg-[#4a2574] px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#3a1d5c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#4a2574]`}
        >
          Open check-in <ExternalLink size={14} aria-hidden="true" />
        </a>
      </div>
      {thanks && <ThanksNote testid={testid} onClose={closeThanks} />}
    </section>
  );
}
