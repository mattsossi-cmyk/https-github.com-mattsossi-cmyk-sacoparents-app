import React from "react";
import { ClipboardCheck, ExternalLink } from "lucide-react";

import { useCaseSettings } from "../../lib/useCaseSettings";
import { useCheckinLink } from "../../lib/useCheckinLink";
import { useCheckinReminder } from "../../lib/useCheckinReminder";
import { useCheckinThanks } from "../../lib/useCheckinThanks";
import { ReminderNote, ThanksNote } from "./FamilyCheckinNotes";

// Case-level UTC date, so both parents see the same day.
const finishedOn = (d) =>
  /^\d{4}-\d{2}-\d{2}$/.test(d || "")
    ? new Date(`${d}T00:00:00Z`).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })
    : null;

// Same words for both parents. The check-in itself happens on the Align site; this app never asks or saves anything.
export function FamilyCheckinCard({ alignUrl, testid = "family-checkin", stacked = false }) {
  const settings = useCaseSettings();
  const done = settings?.setup_complete === true;
  const finished = done ? finishedOn(settings.setup_completed_on) : null;
  const [thanks, closeThanks] = useCheckinThanks(done);
  const [reminder, closeReminder] = useCheckinReminder(!!settings && !done);
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
            {finished && (
              <p data-testid={`${testid}-finished-on`} className="text-xs font-semibold text-emerald-800 mt-1">
                Finished on {finished}
              </p>
            )}
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
      {reminder && <ReminderNote testid={testid} onClose={closeReminder} />}
    </section>
  );
}
