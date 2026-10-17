import React from "react";

import { AgreeControls, AgreedList, AgreeProgress } from "./CourtAgreement";

const COPY = {
  no_case: "Accept your court-ordered invite with your case code to compare side by side with your co-parent.",
  not_shared: "See your results side by side with your co-parent on the same case. Nothing is shared until you both turn this on, and you can turn it off anytime.",
  waiting: "You're sharing. The side-by-side view appears once your co-parent shares too.",
  safety_off: "Side-by-side comparison is turned off to keep you safe. Your results stay private to you.",
};
const EMPTY = {
  alignment: "This appears once you and your co-parent both finish the Co-Parenting Assessment or Self-Assessment.",
  difference: "This appears once you and your co-parent both finish the Co-Parenting Assessment or Self-Assessment.",
  child: "This appears once you and your co-parent both fill in a child's needs assessment.",
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
    <span className={`rounded-lg px-2.5 py-1.5 text-[0.6875rem] ${tone}`}>
      <span className="block font-bold uppercase tracking-wider text-[0.5625rem] opacity-70">{label}</span>
      <span className="block font-semibold whitespace-pre-wrap break-words">{value || "Not filled in"}</span>
    </span>
  );
}

function ScoreRows({ rows, aligned, points = {}, extra }) {
  return (
    <ul data-testid="court-compare-rows" className="space-y-2">
      {rows.map((r, i) => (
        <li key={`${r.source}-${r.area}`} data-testid={`court-compare-row-${i}`} className={`border rounded-xl p-3 ${r.agreed ? "border-emerald-200" : "border-[#e7dbf8]"}`}>
          <p className="text-sm font-semibold text-[#202124]">{r.area}</p>
          <p className="text-[0.625rem] text-[#5f6368] mb-2">{r.source}</p>
          <div className="grid grid-cols-2 gap-2">
            <Pair label="You" value={r.mine} tone="bg-[#f2ebfc] text-[#3b1566]" />
            <Pair label="Co-parent" value={r.theirs} tone={aligned ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"} />
          </div>
          {points[r.area] && (
            <p data-testid={`court-talking-point-${i}`} className="mt-2 text-xs italic text-[#3b1566] bg-white border border-[#e7dbf8] rounded-lg px-3 py-2">
              <i className="fa-solid fa-comment-dots mr-1.5 not-italic text-[#7b2cbf]"></i>
              {points[r.area]}
            </p>
          )}
          {extra && extra(r, i)}
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
          <p className="text-[0.6875rem] font-extrabold uppercase tracking-wider text-[#5c2c8e] mb-1.5">{c.category}</p>
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

function TalkingPoints({ compare }) {
  const tp = compare.data.talking_points;
  return (
    <div data-testid="court-talking-points" className="mb-3 flex flex-wrap items-center gap-2">
      <button
        type="button"
        data-testid={tp ? "court-talking-points-refresh" : "court-talking-points-generate"}
        disabled={compare.pointsBusy}
        onClick={compare.suggestPoints}
        className="text-xs font-bold px-3.5 py-2 rounded-full bg-[#3b1566] hover:bg-[#5c2c8e] disabled:opacity-60 text-white transition-colors"
      >
        <i className={`fa-solid ${compare.pointsBusy ? "fa-spinner fa-spin" : tp ? "fa-rotate" : "fa-wand-magic-sparkles"} mr-1.5`}></i>
        {tp ? "Refresh talking points" : "Suggest talking points"}
      </button>
      <span className="text-[0.6875rem] text-[#5f6368]">
        {tp?.stale ? "Your answers changed since these were made. Refresh for updated ones." : tp ? "Shared with your co-parent. One calm opener per area." : "One calm opener per differing area, shared with your co-parent."}
      </span>
    </div>
  );
}

function AddAllToStep4({ rows, step4 }) {
  const withNotes = rows.filter((r) => r.agreed && r.note);
  if (!withNotes.length) return null;
  const left = withNotes.filter((r) => !step4.has(r)).length;
  return (
    <button
      type="button"
      data-testid="court-agree-all-to-step4"
      disabled={!left}
      onClick={() => step4.add(withNotes)}
      className="mb-3 text-xs font-bold px-3.5 py-2 rounded-full bg-white border border-emerald-300 text-emerald-800 hover:bg-emerald-50 disabled:opacity-60 transition-colors"
    >
      <i className="fa-solid fa-file-import mr-1.5"></i>
      {left ? `Add all agreements to your Foundation Statement (${left})` : "All agreements are in your Foundation Statement"}
    </button>
  );
}

function Ready({ pillar, compare, step4 }) {
  const data = compare.data;
  const agreed = data.difference.filter((r) => r.agreed);
  if (pillar.key === "alignment" && (data.alignment.length || agreed.length)) {
    return (
      <>
        {data.alignment.length > 0 && <ScoreRows rows={data.alignment} aligned />}
        {agreed.length > 0 && <AgreedList rows={agreed} />}
      </>
    );
  }
  const rows = pillar.key === "child" ? data.child : data[pillar.key];
  if (!rows?.length) return <p data-testid="court-compare-area-empty" className="text-xs text-[#5f6368]">{EMPTY[pillar.key]}</p>;
  if (pillar.key === "child") return <ChildRows cats={rows} />;
  const tp = data.talking_points;
  const points = tp && !tp.stale ? Object.fromEntries(tp.items.map((p) => [p.area, p.text])) : {};
  return (
    <>
      <AgreeProgress progress={data.progress} notice={data.intent_notice} />
      <AddAllToStep4 rows={rows} step4={step4} />
      <TalkingPoints compare={compare} />
      <ScoreRows rows={rows} aligned={false} points={points} extra={(r, i) => <AgreeControls row={r} i={i} compare={compare} step4={step4} />} />
    </>
  );
}

function PdfButton({ compare }) {
  return (
    <button
      type="button"
      data-testid="court-compare-pdf"
      disabled={compare.pdfBusy}
      onClick={compare.downloadPdf}
      className="mt-3 ml-0 sm:ml-4 inline-flex items-center gap-1.5 text-xs font-bold text-[#2fa144] hover:underline disabled:opacity-60"
    >
      <i className={`fa-solid ${compare.pdfBusy ? "fa-spinner fa-spin" : "fa-file-pdf"}`}></i> Download Comparison PDF
    </button>
  );
}

// Side-by-side section inside the Alignment / Difference / Child-Focused Needs popups.
export function CourtCompare({ pillar, compare, step4, onEnterCase }) {
  const state = compare.data?.state;
  return (
    <section data-testid="court-compare" data-state={state || "loading"} className="mt-1 bg-[#faf8fd] border border-[#e7dbf8] rounded-xl p-4">
      <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#3b1566] flex items-center gap-2 mb-2">
        <i className="fa-solid fa-people-arrows text-[#5c2c8e]"></i> Side by side with your co-parent
      </h4>
      {!compare.data ? (
        <p className="text-xs text-[#5f6368]"><i className="fa-solid fa-spinner fa-spin mr-2"></i>Checking…</p>
      ) : state === "ready" ? (
        <Ready pillar={pillar} compare={compare} step4={step4} />
      ) : (
        <p data-testid="court-compare-message" className="text-xs text-[#5f6368] leading-relaxed">{COPY[state]}</p>
      )}
      {state === "no_case" && (
        <button type="button" data-testid="court-compare-enter-case" onClick={onEnterCase} className="mt-2 text-xs font-bold text-[#2fa144] hover:underline">
          Enter case code <i className="fa-solid fa-arrow-right ml-1"></i>
        </button>
      )}
      <div className="flex flex-wrap items-center">
        {["not_shared", "waiting", "ready"].includes(state) && <ShareSwitch compare={compare} />}
        {state === "ready" && <PdfButton compare={compare} />}
      </div>
    </section>
  );
}
