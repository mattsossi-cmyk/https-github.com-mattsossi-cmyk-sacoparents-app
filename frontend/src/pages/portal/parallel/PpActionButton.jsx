import React from "react";

const ALT = "A child with a purple backpack walks a sunny path between two homes while each parent waves from their own porch.";

// Communication Builder-style picture + big action button at the foot of the Parallel Parenting work column.
export function PpActionButton({ label, onClick }) {
  return (
    <button
      type="button"
      data-testid="pp-action-btn"
      onClick={onClick}
      className="group w-full overflow-hidden rounded-2xl bg-purple-950 text-white shadow-xl hover:shadow-2xl border-2 border-purple-700/50 transition-[transform,box-shadow] hover:-translate-y-0.5 text-left"
    >
      <img
        data-testid="pp-action-image"
        src="/images/sa-parallel-action-640.webp"
        srcSet="/images/sa-parallel-action-640.webp 640w, /images/sa-parallel-action.webp 1264w"
        sizes="(min-width: 1024px) 640px, 100vw"
        alt={ALT}
        width={1264}
        height={848}
        className="w-full h-40 sm:h-52 object-cover transition-transform duration-500 group-hover:scale-[1.03]"
      />
      <span className="flex items-center justify-center gap-3 py-4 px-6 font-extrabold text-lg tracking-wider text-center">
        <span data-testid="pp-action-label">{label}</span>
        <i className="fa-solid fa-arrow-right transition-transform group-hover:translate-x-1" aria-hidden="true"></i>
      </span>
    </button>
  );
}
