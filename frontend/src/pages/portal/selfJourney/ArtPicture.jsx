import React from "react";

import { Spot } from "../court/CourtJourneyArt";

// Artwork with tappable panels (+ optional round arrows). Optional done ticks, active ring and next-step glow.
export function ArtPicture({ tp, art, onAction, done = {}, activeKey, nextKey }) {
  return (
    <div data-testid={`${tp}-picture`} className="relative w-full rounded-3xl overflow-hidden shadow-lg border border-purple-100 bg-white">
      <img
        data-testid={`${tp}-img`}
        src={`/images/${art.name}-640.webp`}
        srcSet={`/images/${art.name}-640.webp 640w, /images/${art.name}.webp ${art.width}w`}
        sizes="(min-width: 1024px) 460px, (min-width: 640px) 448px, 100vw"
        width={art.width}
        height={art.height}
        alt={art.alt}
        className="w-full h-auto block"
      />
      {art.items.map((it) => (
        <React.Fragment key={it.key}>
          <Spot
            testid={`${tp}-panel-${it.key}`}
            spot={it.panel}
            label={`Open ${it.name}`}
            className={`!rounded-3xl ${it.key === nextKey ? "journey-next-glow" : ""} ${it.key === activeKey ? "journey-art-active" : ""}`}
            onClick={() => onAction(it.key)}
          >
            {done[it.key] && (
              <span
                data-testid={`${tp}-done-${it.key}`}
                className="absolute top-1.5 left-1.5 w-6 h-6 rounded-full bg-[#2f9e44] text-white text-[11px] flex items-center justify-center shadow ring-2 ring-white"
              >
                <i className="fa-solid fa-check"></i>
              </span>
            )}
          </Spot>
          {it.arrow && (
            <Spot testid={`${tp}-arrow-${it.key}`} spot={it.arrow} label={`Start ${it.name}`} className="!rounded-full" onClick={() => onAction(it.key)} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
