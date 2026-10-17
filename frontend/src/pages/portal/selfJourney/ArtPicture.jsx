import React from "react";

import { Spot } from "../court/CourtJourneyArt";

// Artwork with tappable panels (+ optional round arrows). Optional done ticks, active ring and next-step glow.
// `onPicture` makes the whole picture tappable underneath the spots.
export function ArtPicture({ tp, art, onAction, done = {}, activeKey, nextKey, onPicture, tickClass = "bg-[#2f9e44]" }) {
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
      {onPicture && (
        <button type="button" data-testid={`${tp}-open`} aria-label={`Open ${art.alt.split(".")[0]}`} onClick={onPicture} className="absolute inset-0 w-full h-full cursor-pointer" />
      )}
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
                className={`absolute top-1.5 left-1.5 w-6 h-6 rounded-full ${tickClass} text-white text-[0.6875rem] flex items-center justify-center shadow ring-2 ring-white`}
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
