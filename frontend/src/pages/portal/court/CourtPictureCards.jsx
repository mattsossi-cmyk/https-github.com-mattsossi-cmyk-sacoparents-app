import React from "react";

import { JourneyArtCard } from "../selfJourney/JourneyArtCard";
import { NEEDS_ART, PP_ART } from "../selfJourney/selfJourneyArt";

// Court page: the same tappable Child Needs + Parallel Parenting pictures used on the Self Journey.
export function CourtPictureCards({ done, onChildNeeds, onParallel }) {
  return (
    <section data-testid="court-picture-cards" className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-start">
      <JourneyArtCard testid="court-art-needs" art={NEEDS_ART} done={done} onAction={onChildNeeds} />
      <JourneyArtCard testid="court-art-parallel" art={PP_ART} onAction={(k) => onParallel(PP_ART.items.find((it) => it.key === k).screen)} />
    </section>
  );
}
