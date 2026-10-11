import React from "react";

const ALT =
  "SA CoParents Communication Builder: build calmer, clearer messages to your co-parent, learn strategies and reduce misunderstandings.";

// Self Journey step 6: the Communication Builder picture + its action button (both open the builder).
export function CbJourneyCard({ onOpen, countLabel, done }) {
  return (
    <section data-testid="door-self-cb-card" className="space-y-2.5">
      <button
        type="button"
        data-testid="door-self-card-biff"
        onClick={onOpen}
        aria-label="Open the SA CoParent Communication Builder"
        className="group block w-full rounded-3xl overflow-hidden shadow-lg border border-purple-100 bg-white"
      >
        <img
          data-testid="door-self-cb-img"
          src="/images/comm-builder-art-640.webp"
          srcSet="/images/comm-builder-art-640.webp 640w, /images/comm-builder-art.webp 1024w"
          sizes="(min-width: 1024px) 640px, 100vw"
          alt={ALT}
          width={1024}
          height={1536}
          loading="lazy"
          className="w-full h-auto transition-transform duration-500 group-hover:scale-[1.02]"
        />
      </button>
      <button
        type="button"
        data-testid="door-self-card-biff-open"
        data-done={done ? "true" : "false"}
        onClick={onOpen}
        className="w-full rounded-2xl bg-purple-950 hover:bg-purple-900 text-white py-4 px-6 shadow-xl hover:shadow-2xl border-2 border-purple-700/50 flex items-center justify-center gap-3 font-extrabold text-base sm:text-lg tracking-wider transition-[background-color,box-shadow,transform] active:scale-[0.98]"
      >
        <i className="fa-solid fa-comments" aria-hidden="true"></i>
        <span>OPEN COMMUNICATION BUILDER</span>
        <i className="fa-solid fa-arrow-right" aria-hidden="true"></i>
      </button>
      <p data-testid="door-self-biff-count" className="text-center text-[11px] font-semibold text-purple-800/80">
        {countLabel}.
      </p>
    </section>
  );
}
