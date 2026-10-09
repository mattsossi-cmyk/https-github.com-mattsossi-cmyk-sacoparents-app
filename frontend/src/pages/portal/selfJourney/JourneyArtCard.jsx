import React from "react";

import { Spot } from "../court/CourtJourneyArt";

function ActionButton({ testid, item, done, next, onClick }) {
  return (
    <button
      type="button"
      data-testid={testid}
      data-done={done ? "true" : "false"}
      data-next={next ? "true" : "false"}
      onClick={onClick}
      className={`${item.tone} ${next ? "journey-next-glow" : ""} relative text-white rounded-2xl px-2 py-2.5 shadow-md flex flex-col items-center justify-center gap-1 text-center transition-[background-color,transform] active:scale-[0.97]`}
    >
      {next && (
        <span data-testid={`${testid}-next`} className="absolute -top-2 right-2 bg-white text-[#6b2fb3] text-[9px] font-extrabold uppercase tracking-wider rounded-full px-2 py-0.5 shadow">
          Next
        </span>
      )}
      <i className={`fa-solid ${item.icon} text-base`}></i>
      <span className="text-[12px] font-extrabold leading-tight">{item.label}</span>
      {done ? (
        <span data-testid={`${testid}-completed`} className="text-[10px] font-bold bg-white/25 rounded-full px-2 py-0.5 whitespace-nowrap">
          Completed <i className="fa-solid fa-check text-[9px] ml-0.5"></i>
        </span>
      ) : (
        <span className="text-[10px] font-semibold opacity-90">
          Start <i className="fa-solid fa-chevron-right text-[8px] ml-0.5"></i>
        </span>
      )}
    </button>
  );
}

// Assessment artwork with tappable panels + arrow buttons, and a row of labeled buttons underneath.
export function JourneyArtCard({ testid, art, done = {}, nextKey, onAction, children }) {
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
            <Spot testid={`${testid}-panel-${it.key}`} spot={it.panel} label={`Open ${it.label} Assessment`} className={`!rounded-3xl ${it.key === nextKey ? "journey-next-glow" : ""}`} onClick={() => onAction(it.key)} />
            {it.arrow && (
              <Spot testid={`${testid}-arrow-${it.key}`} spot={it.arrow} label={`Start ${it.label} Assessment`} className="!rounded-full" onClick={() => onAction(it.key)} />
            )}
          </React.Fragment>
        ))}
      </div>
      <div className={`grid gap-2 ${art.items.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
        {art.items.map((it) => (
          <ActionButton key={it.key} testid={`${testid}-btn-${it.key}`} item={it} done={!!done[it.key]} next={it.key === nextKey} onClick={() => onAction(it.key)} />
        ))}
      </div>
      {children}
    </section>
  );
}
