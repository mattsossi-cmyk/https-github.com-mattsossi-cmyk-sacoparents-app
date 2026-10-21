import React from "react";

const when = (iso) =>
  new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });

// Last 5 times SA CoParents Align read this parent's account.
export function AlignReadHistory({ reads, linked = true }) {
  return (
    <div data-testid="align-read-history" className="mt-4 border-t border-[#EFE9F9] pt-3">
      <p data-testid="align-read-history-title" className="text-[0.6875rem] font-bold uppercase tracking-[0.14em] text-[#6E6787] mb-2">
        {linked ? "Recent reads by Align" : "Earlier reads, before you unlinked"}
      </p>
      {reads.length === 0 ? (
        <p data-testid="align-read-history-empty" className="text-xs text-[#4B4567]">Align hasn&rsquo;t read anything from your account yet.</p>
      ) : (
        <ul className="space-y-2">
          {reads.map((r, i) => (
            <li key={`${r.at}-${i}`} data-testid={`align-read-${i}`} className="flex items-start gap-2 text-xs text-[#4B4567] leading-relaxed">
              <i className="fa-solid fa-eye text-[#9B6AD6] text-[0.625rem] mt-1" aria-hidden="true"></i>
              <span className="min-w-0">
                <span className="font-semibold text-[#1A1330]">{when(r.at)}</span> &middot; {r.what}
                {r.redacted && (
                  <span data-testid={`align-read-${i}-redacted`} className="ml-1.5 inline-block rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 px-2 py-0.5 text-[0.625rem] font-bold">
                    {r.note}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
