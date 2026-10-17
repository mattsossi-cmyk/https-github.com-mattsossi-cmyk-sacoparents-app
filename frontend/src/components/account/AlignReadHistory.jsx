import React from "react";

const when = (iso) =>
  new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });

// Last 5 times SA CoParents Align read this parent's account.
export function AlignReadHistory({ reads }) {
  return (
    <div data-testid="align-read-history" className="mt-4 border-t border-[#EFE9F9] pt-3">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6E6787] mb-2">Recent reads by Align</p>
      {reads.length === 0 ? (
        <p data-testid="align-read-history-empty" className="text-xs text-[#4B4567]">Align hasn&rsquo;t read anything from your account yet.</p>
      ) : (
        <ul className="space-y-2">
          {reads.map((r, i) => (
            <li key={`${r.at}-${i}`} data-testid={`align-read-${i}`} className="flex items-start gap-2 text-xs text-[#4B4567] leading-relaxed">
              <i className="fa-solid fa-eye text-[#9B6AD6] text-[10px] mt-1" aria-hidden="true"></i>
              <span className="min-w-0">
                <span className="font-semibold text-[#1A1330]">{when(r.at)}</span> &middot; {r.what}
                {r.redacted && (
                  <span data-testid={`align-read-${i}-redacted`} className="ml-1.5 inline-block rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 px-2 py-0.5 text-[10px] font-bold">
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
