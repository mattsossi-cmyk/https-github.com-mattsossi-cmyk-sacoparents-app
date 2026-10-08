import React from "react";

const COPY = {
  no_case: "Accept your court-ordered invite with your case code to compare side by side with your co-parent.",
  not_shared: "See your results side by side with your co-parent on the same case. Nothing is shared until you both turn this on, and you can turn it off anytime.",
  waiting: "You're sharing. The side-by-side view appears once your co-parent shares too.",
  safety_off: "Side-by-side comparison is turned off to keep you safe. Your results stay private to you.",
};
const EMPTY = {
  alignment: "This appears once you and your co-parent both finish Step 1 or Step 2.",
  difference: "This appears once you and your co-parent both finish Step 1 or Step 2.",
  child: "This appears once you and your co-parent both fill in Step 3.",
};

function ShareSwitch({ compare }) {
  const on = !!compare.data?.shared;
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      data-testid="court-compare-share-toggle"
      disabled={compare.busy}
      onClick={() => compare.setShared(!on)}
      className="mt-3 inline-flex items-center gap-2.5 text-xs font-bold text-[#3b1566] disabled:opacity-60"
    >
      <span className={`relative w-10 h-6 rounded-full transition-colors ${on ? "bg-[#2fa144]" : "bg-slate-300"}`}>
        <span className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${on ? "translate-x-4" : ""}`}></span>
      </span>
      {on ? "Sharing my results for comparison" : "Share my results for comparison"}
    </button>
  );
}

function Pair({ label, value, tone }) {
  return (
    <span className={`rounded-lg px-2.5 py-1.5 text-[11px] ${tone}`}>
      <span className="block font-bold uppercase tracking-wider text-[9px] opacity-70">{label}</span>
      <span className="block font-semibold whitespace-pre-wrap break-words">{value || "Not filled in"}</span>
    </span>
  );
}

function ScoreRows({ rows, aligned }) {
  return (
    <ul data-testid="court-compare-rows" className="space-y-2">
      {rows.map((r, i) => (
        <li key={`${r.source}-${r.area}`} data-testid={`court-compare-row-${i}`} className="border border-[#e7dbf8] rounded-xl p-3">
          <p className="text-sm font-semibold text-[#202124]">{r.area}</p>
          <p className="text-[10px] text-[#5f6368] mb-2">{r.source}</p>
          <div className="grid grid-cols-2 gap-2">
            <Pair label="You" value={r.mine} tone="bg-[#f2ebfc] text-[#3b1566]" />
            <Pair label="Co-parent" value={r.theirs} tone={aligned ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function ChildRows({ cats }) {
  return (
    <div data-testid="court-compare-child" className="space-y-3">
      {cats.map((c) => (
        <div key={c.category}>
          <p className="text-[11px] font-extrabold uppercase tracking-wider text-[#5c2c8e] mb-1.5">{c.category}</p>
          {c.rows.length ? (
            c.rows.map((r) => (
              <div key={r.label} className="border border-[#e7dbf8] rounded-xl p-3 mb-2">
                <p className="text-xs font-semibold text-[#202124] mb-2">{r.label}</p>
                <div className="grid sm:grid-cols-2 gap-2">
                  <Pair label="You" value={r.mine} tone="bg-[#f2ebfc] text-[#3b1566]" />
                  <Pair label="Co-parent" value={r.theirs} tone="bg-sky-50 text-sky-900" />
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-[#5f6368]">Neither of you has filled this in yet.</p>
          )}
        </div>
      ))}
    </div>
  );
}

function Ready({ pillar, data }) {
  const rows = pillar.key === "child" ? data.child : data[pillar.key];
  if (!rows?.length) return <p data-testid="court-compare-area-empty" className="text-xs text-[#5f6368]">{EMPTY[pillar.key]}</p>;
  return pillar.key === "child" ? <ChildRows cats={rows} /> : <ScoreRows rows={rows} aligned={pillar.key === "alignment"} />;
}

// Side-by-side section inside the Alignment / Difference / Child-Focused Needs popups.
export function CourtCompare({ pillar, compare, onEnterCase }) {
  const state = compare.data?.state;
  return (
    <section data-testid="court-compare" data-state={state || "loading"} className="mt-1 bg-[#faf8fd] border border-[#e7dbf8] rounded-xl p-4">
      <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#3b1566] flex items-center gap-2 mb-2">
        <i className="fa-solid fa-people-arrows text-[#5c2c8e]"></i> Side by side with your co-parent
      </h4>
      {!compare.data ? (
        <p className="text-xs text-[#5f6368]"><i className="fa-solid fa-spinner fa-spin mr-2"></i>Checking…</p>
      ) : state === "ready" ? (
        <Ready pillar={pillar} data={compare.data} />
      ) : (
        <p data-testid="court-compare-message" className="text-xs text-[#5f6368] leading-relaxed">{COPY[state]}</p>
      )}
      {state === "no_case" && (
        <button type="button" data-testid="court-compare-enter-case" onClick={onEnterCase} className="mt-2 text-xs font-bold text-[#2fa144] hover:underline">
          Enter case code <i className="fa-solid fa-arrow-right ml-1"></i>
        </button>
      )}
      {["not_shared", "waiting", "ready"].includes(state) && <ShareSwitch compare={compare} />}
    </section>
  );
}
