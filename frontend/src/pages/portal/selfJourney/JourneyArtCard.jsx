import React from "react";

import { ArtPicture } from "./ArtPicture";

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

function SmallButton({ testid, item, onClick }) {
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={onClick}
      className="rounded-xl bg-white border border-purple-200 hover:border-purple-400 hover:bg-purple-50 text-[#3b1566] px-1 py-2 flex flex-col items-center gap-1 text-center shadow-sm transition-[border-color,background-color,transform] active:scale-[0.97]"
    >
      <i className={`fa-solid ${item.icon} text-sm text-[#6b2fb3]`}></i>
      <span className="text-[10px] font-bold leading-tight">{item.label}</span>
    </button>
  );
}

// Self Journey picture card: tappable picture + a row of labeled buttons (and a smaller row for `small` items).
export function JourneyArtCard({ testid, art, done = {}, nextKey, onAction, children }) {
  const main = art.items.filter((it) => !it.small);
  const small = art.items.filter((it) => it.small);
  return (
    <section data-testid={testid} className="space-y-2.5">
      <ArtPicture tp={testid} art={art} nextKey={nextKey} onAction={onAction} />
      <div className={`grid gap-2 ${main.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
        {main.map((it) => (
          <ActionButton key={it.key} testid={`${testid}-btn-${it.key}`} item={it} done={!!done[it.key]} next={it.key === nextKey} onClick={() => onAction(it.key)} />
        ))}
      </div>
      {small.length > 0 && (
        <div className="grid grid-cols-4 gap-1.5">
          {small.map((it) => (
            <SmallButton key={it.key} testid={`${testid}-btn-${it.key}`} item={it} onClick={() => onAction(it.key)} />
          ))}
        </div>
      )}
      {children}
    </section>
  );
}
