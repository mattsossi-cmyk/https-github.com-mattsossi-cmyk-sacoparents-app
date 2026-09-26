import React from "react";

/**
 * SafetyCrisisStrip — persistent one-line crisis strip pinned above
 * the bottom nav. Always visible on every screen (Gateway, Court-Key,
 * Parent Journey). Print-hidden.
 *
 * Clinical guardrail: even when the parent has cleared the Safety
 * Screen, immediate crisis contact info must remain one tap away.
 */
export function SafetyCrisisStrip() {
  return (
    <div
      data-testid="portal-crisis-strip"
      className="no-print fixed bottom-16 left-0 right-0 z-40 max-w-md mx-auto px-3"
    >
      <div className="bg-rose-950/95 text-rose-50 rounded-t-lg px-3 py-1.5 text-[10px] flex items-center gap-2 shadow-lg border-t border-rose-800">
        <i className="fa-solid fa-shield-heart text-rose-300 shrink-0" aria-hidden></i>
        <div className="flex-1 leading-tight">
          <span className="font-bold">In danger?</span>{" "}
          <a
            href="tel:911"
            data-testid="crisis-call-911"
            className="underline decoration-rose-300 hover:text-white"
          >
            Call 911
          </a>
          <span className="mx-1 text-rose-400">·</span>
          <a
            href="tel:18007997233"
            data-testid="crisis-dv-hotline"
            className="underline decoration-rose-300 hover:text-white"
          >
            DV 1-800-799-7233
          </a>
          <span className="mx-1 text-rose-400">·</span>
          <a
            href="sms:88788?body=START"
            data-testid="crisis-text-start"
            className="underline decoration-rose-300 hover:text-white"
          >
            Text START to 88788
          </a>
          <span className="mx-1 text-rose-400">·</span>
          <a
            href="tel:988"
            data-testid="crisis-988"
            className="underline decoration-rose-300 hover:text-white"
          >
            988
          </a>
        </div>
      </div>
    </div>
  );
}
