import React from "react";

import { CourtCompare } from "./CourtCompare";
import { CourtDialog } from "./CourtDialog";

function Results({ items }) {
  return (
    <ul data-testid="court-pillar-items" className="divide-y divide-[#f2ebfc] border border-[#e7dbf8] rounded-xl mb-4">
      {items.map((it, i) => (
        <li key={`${it.source}-${it.text}`} data-testid={`court-pillar-item-${i}`} className="flex items-center justify-between gap-3 px-4 py-2.5">
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-[#202124]">{it.text}</span>
            <span className="block text-[0.6875rem] text-[#5f6368]">From your {it.source}</span>
          </span>
          <span className="shrink-0 text-[0.6875rem] font-bold text-[#3b1566] bg-[#f2ebfc] rounded-full px-2.5 py-1">{it.meta}</span>
        </li>
      ))}
    </ul>
  );
}

function Resources({ resources }) {
  return (
    <div data-testid="court-pillar-resources" className="grid gap-2 mb-4">
      {resources.map((r) => (
        <button
          key={r.key}
          type="button"
          data-testid={`court-resource-${r.key}`}
          onClick={r.onClick}
          className="flex items-center gap-3 text-left border border-[#e7dbf8] hover:border-[#7b2cbf] hover:bg-[#faf8fd] rounded-xl px-4 py-2.5 transition-colors"
        >
          <i className={`fa-solid ${r.icon} w-5 text-center text-[#5c2c8e]`}></i>
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-[#202124]">{r.title}</span>
            <span className="block text-[0.6875rem] text-[#5f6368]">{r.sub}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

export function CourtPillarDialog({ pillar, summary, resources, compare, step4, onClose, onOpenStep, onEnterCase }) {
  if (!pillar) return null;
  const items = pillar.key !== "resources" ? summary?.[pillar.key] || [] : [];
  const empty = pillar.key === "child" ? !summary?.has_child : !items.length;
  return (
    <CourtDialog open onClose={onClose} testid="court-pillar-dialog" title={pillar.title} desc={pillar.intro}>
      {pillar.key === "resources" ? (
        <Resources resources={resources} />
      ) : !summary ? (
        <p data-testid="court-pillar-loading" className="text-sm text-[#5f6368] mb-4"><i className="fa-solid fa-spinner fa-spin mr-2"></i>Loading your results…</p>
      ) : empty ? (
        <div data-testid="court-pillar-empty" className="border border-dashed border-[#e7dbf8] rounded-xl px-4 py-3 mb-4">
          <p className="text-sm text-[#5f6368] mb-2">{pillar.empty}</p>
          <button type="button" data-testid="court-pillar-open-step" onClick={() => onOpenStep(pillar.emptyStep)} className="text-sm font-bold text-[#2fa144] hover:underline">
            Open {pillar.emptyStep === 3 ? "Child's Specific Needs" : "Co-Parenting Assessment"} <i className="fa-solid fa-arrow-right ml-1"></i>
          </button>
        </div>
      ) : (
        <Results items={items} />
      )}
      {pillar.key !== "resources" && <CourtCompare pillar={pillar} compare={compare} step4={step4} onEnterCase={onEnterCase} />}
    </CourtDialog>
  );
}
