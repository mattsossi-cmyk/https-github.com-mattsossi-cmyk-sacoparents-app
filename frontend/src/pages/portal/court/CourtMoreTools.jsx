import React, { useState } from "react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../../../components/ui/collapsible";
import { CourtChecklistCard } from "./CourtChecklistCard";
import { PillarCards } from "./CourtJourneyCards";
import { CourtModulesCard, CourtTools } from "./CourtTools";

// Collapsed by default: everything beyond the requested list and Reports.
export function CourtMoreTools({ cc, courtKey, onCase, onBiff, onPillar, modules, onOpenModule, checklist }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} data-testid="court-more-tools" className="rounded-3xl border border-purple-100 bg-white/80 shadow-sm">
      <CollapsibleTrigger data-testid="court-more-tools-toggle" className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left rounded-3xl hover:bg-[#faf8fd] transition-colors">
        <span>
          <span className="block text-lg font-extrabold text-[#3b1566]">More court tools</span>
          <span className="block text-[12px] text-slate-500">Case code, Communication Builder, the bigger-picture tiles, court modules and your checklist.</span>
        </span>
        <i className={`fa-solid fa-chevron-down text-[#5c2c8e] transition-transform duration-200 ${open ? "rotate-180" : ""}`} aria-hidden="true"></i>
      </CollapsibleTrigger>
      <CollapsibleContent data-testid="court-more-tools-content" className="px-4 sm:px-5 pb-5 space-y-6">
        <CourtTools cc={cc} courtKey={courtKey} onCase={onCase} onBiff={onBiff} />
        <PillarCards onPillar={onPillar} />
        <CourtModulesCard modules={modules} onOpenModule={onOpenModule} />
        <CourtChecklistCard checklist={checklist} showDownload={false} />
      </CollapsibleContent>
    </Collapsible>
  );
}
