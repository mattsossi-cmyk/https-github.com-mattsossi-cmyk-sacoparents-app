import React from "react";

import CONTENT from "../childNeedsContent.json";
import { NEEDS_PAGE_ART } from "../childNeeds/needsPageArt";
import { ArtPicture } from "../selfJourney/ArtPicture";
import { JourneyArtCard } from "../selfJourney/JourneyArtCard";
import { PP_ART } from "../selfJourney/selfJourneyArt";

const TITLES = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c.card_title]));

// One Child Needs form picture: tap anywhere to open the form, or an icon to open it at those questions.
function NeedsPicture({ cat, done, onOpen }) {
  const tp = `court-art-needs-${cat}`;
  return (
    <div data-testid={tp} className="space-y-2.5">
      <ArtPicture tp={tp} art={NEEDS_PAGE_ART[cat]} onAction={(k) => onOpen(cat, k === "start" ? null : k)} onPicture={() => onOpen(cat, null)} />
      <button
        type="button"
        data-testid={`${tp}-btn`}
        onClick={() => onOpen(cat, null)}
        className="w-full rounded-2xl bg-[#6b2fb3] hover:bg-[#5a2697] text-white px-3 py-2.5 shadow-md flex items-center justify-center gap-2 text-[13px] font-extrabold transition-colors"
      >
        {TITLES[cat]}
        <span className="text-[10px] font-bold bg-white/25 rounded-full px-2 py-0.5 whitespace-nowrap">
          {done ? <>Completed <i className="fa-solid fa-check text-[9px]"></i></> : <>Start <i className="fa-solid fa-chevron-right text-[8px]"></i></>}
        </span>
      </button>
    </div>
  );
}

// Court page: the three Child Needs form pictures + Parallel Parenting, 2×2 on wider screens.
export function CourtPictureCards({ done, onChildNeeds, onParallel }) {
  return (
    <section data-testid="court-picture-cards" className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-start">
      {["educational", "medical", "psychological"].map((cat) => (
        <NeedsPicture key={cat} cat={cat} done={!!done[cat]} onOpen={onChildNeeds} />
      ))}
      <JourneyArtCard testid="court-art-parallel" art={PP_ART} onAction={(k) => onParallel(PP_ART.items.find((it) => it.key === k).screen)} />
    </section>
  );
}
