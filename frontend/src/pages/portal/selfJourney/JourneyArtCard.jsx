import React from "react";

import { Spot } from "../court/CourtJourneyArt";

function ActionButton({ testid, item, onClick }) {
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={onClick}
      className={`${item.tone} text-white rounded-2xl px-2 py-2.5 shadow-md flex flex-col items-center justify-center gap-1 text-center transition-[background-color,transform] active:scale-[0.97]`}
    >
      <i className={`fa-solid ${item.icon} text-base`}></i>
      <span className="text-[12px] font-extrabold leading-tight">{item.label}</span>
      <span className="text-[10px] font-semibold opacity-90">
        Start <i className="fa-solid fa-chevron-right text-[8px] ml-0.5"></i>
      </span>
    </button>
  );
}

// Assessment artwork with tappable panels + arrow buttons, and a row of labeled buttons underneath.
export function JourneyArtCard({ testid, art, onAction, children }) {
  return (
    <section data-testid={testid} className="space-y-2.5">
      <div className="relative w-full rounded-3xl overflow-hidden shadow-lg border border-purple-100 bg-white">
        <img
          data-testid={`${testid}-img`}
          src={`/images/${art.name}-640.webp`}
          srcSet={`/images/${art.name}-640.webp 640w, /images/${art.name}.webp ${art.width}w`}
          sizes="(min-width: 640px) 448px, 100vw"
          width={art.width}
          height={art.height}
          alt={art.alt}
          loading="lazy"
          className="w-full h-auto block"
        />
        {art.items.map((it) => (
          <React.Fragment key={it.key}>
            <Spot testid={`${testid}-panel-${it.key}`} spot={it.panel} label={`Open ${it.label} Assessment`} onClick={() => onAction(it.key)} />
            <Spot testid={`${testid}-arrow-${it.key}`} spot={it.arrow} label={`Start ${it.label} Assessment`} className="!rounded-full" onClick={() => onAction(it.key)} />
          </React.Fragment>
        ))}
      </div>
      <div className={`grid gap-2 ${art.items.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
        {art.items.map((it) => (
          <ActionButton key={it.key} testid={`${testid}-btn-${it.key}`} item={it} onClick={() => onAction(it.key)} />
        ))}
      </div>
      {children}
    </section>
  );
}
