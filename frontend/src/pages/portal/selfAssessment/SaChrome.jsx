import React, { useEffect } from "react";

export function useLockScroll(active = true) {
  useEffect(() => {
    if (!active) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [active]);
}

export function SafetyBanner({ tp = "sa", icon = "fa-shield-heart", label = "Confidential Portal" }) {
  return (
    <div
      data-testid={`${tp}-safety-banner`}
      className="bg-purple-950 text-purple-200 text-xs py-2 px-4 text-center font-medium shadow-inner max-w-7xl mx-auto rounded-b-lg"
    >
      <i className={`fa-solid ${icon} text-purple-400 mr-2`}></i>
      {label} &bull; In immediate danger? Call{" "}
      <a href="tel:911" data-testid={`${tp}-safety-911`} className="font-bold text-white underline-offset-2 hover:underline">
        911
      </a>{" "}
      &bull; DV Helpline:{" "}
      <a href="tel:18007997233" data-testid={`${tp}-safety-dv`} className="font-bold text-white underline-offset-2 hover:underline">
        1-800-799-7233
      </a>
    </div>
  );
}

export function PageHeader({ onBack, onQuickExit, tp = "sa", backLabel = "Back to Self Journey", tagline = "Align • Support • Thrive", badgeLabel = "Engineered With", tm = false }) {
  return (
    <header className="flex flex-col md:flex-row justify-between items-center gap-4 bg-white/80 backdrop-blur-md rounded-2xl p-4 sm:p-5 mb-8 shadow-sm border border-purple-100/50">
      <div className="flex flex-wrap items-center gap-3 w-full md:w-auto min-w-0">
        <button
          type="button"
          data-testid={`${tp}-back`}
          onClick={onBack}
          aria-label={backLabel}
          className="shrink-0 w-9 h-9 rounded-full bg-purple-50 hover:bg-purple-100 text-purple-800 flex items-center justify-center transition-colors"
        >
          <i className="fa-solid fa-arrow-left"></i>
        </button>
        <div className="shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-purple-700 text-white rounded-2xl flex items-center justify-center text-xl sm:text-2xl shadow-md shadow-purple-200">
          <i className="fa-solid fa-people-roof"></i>
        </div>
        <div className="min-w-[7rem] flex-1">
          <p className="text-lg sm:text-2xl font-extrabold text-[#3B1C6B] tracking-tight">
            SA CoParents{tm && <span className="text-[0.5625rem] font-bold align-top text-purple-700 ml-0.5">TM</span>}
          </p>
          <p data-testid={`${tp}-tagline`} className="text-[0.5625rem] sm:text-xs font-semibold tracking-wider text-purple-600 uppercase sm:whitespace-nowrap">{tagline}</p>
        </div>
        <button
          type="button"
          data-testid={`${tp}-quick-exit`}
          onClick={onQuickExit}
          className="md:hidden ml-auto shrink-0 px-2.5 py-1.5 rounded-md text-[0.625rem] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors"
        >
          <i className="fa-solid fa-bolt mr-1"></i>Quick Exit
        </button>
      </div>
      <div className="flex flex-wrap justify-center items-center gap-3 max-w-full">
        <div data-testid={`${tp}-emergent-badge`} className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-xl shadow-md border border-slate-700 max-w-full min-w-0">
          <div className="flex flex-col text-right">
            <span className="text-[0.625rem] text-purple-300 font-semibold tracking-wider uppercase">{badgeLabel}</span>
            <span className="text-sm font-bold tracking-wide">Powered by Emergent AI</span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-400 flex items-center justify-center text-white">
            <i className="fa-solid fa-wand-magic-sparkles text-sm animate-pulse"></i>
          </div>
        </div>
        <button
          type="button"
          data-testid={`${tp}-quick-exit-desktop`}
          onClick={onQuickExit}
          className="hidden md:inline-flex items-center px-3 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors"
        >
          <i className="fa-solid fa-bolt mr-1.5"></i>Quick Exit
        </button>
      </div>
    </header>
  );
}

export function Hero({ title, subtitle, pill, pct, tp = "sa", textClassName = "" }) {
  return (
    <div className="text-center max-w-2xl mx-auto mb-10">
      <h1 className={`text-4xl md:text-5xl font-extrabold text-[#3B1C6B] tracking-tight mb-3 ${textClassName}`}>{title}</h1>
      <p className={`text-slate-600 text-base md:text-lg leading-relaxed ${textClassName}`}>{subtitle}</p>
      <div data-testid={`${tp}-step-pill`} className="mt-6 inline-flex flex-wrap justify-center items-center gap-3 max-w-full bg-white/90 px-5 py-2 rounded-full shadow-sm border border-purple-100">
        <span className="text-xs font-bold text-purple-800 uppercase tracking-wider">{pill}</span>
        <div className="w-32 max-w-full bg-purple-100 rounded-full h-2">
          <div data-testid={`${tp}-step-bar`} className="bg-purple-600 h-2 rounded-full transition-[width] duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}

export function BottomBanner({ tp = "sa" }) {
  return (
    <div data-testid={`${tp}-bottom-banner`} className="mt-12 bg-white/90 rounded-3xl p-8 border border-purple-100/80 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
      <div className="text-center md:text-left space-y-2">
        <h3 className="text-3xl md:text-4xl font-script text-[#3B1C6B] leading-tight">
          Your Journey. Your Growth.
          <br />A Brighter Future for Your Child. &#9829;
        </h3>
        <p className="text-xs text-slate-500 font-medium">SA CoParents &bull; Assessment &amp; Alignment Portal</p>
      </div>
      <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4 text-center min-w-[200px] shadow-sm">
        <p className="font-script text-lg text-[#3B1C6B] leading-snug">
          A Healthier Me
          <br />A Brighter Future
          <br />for My Child &#9829;
        </p>
      </div>
    </div>
  );
}
