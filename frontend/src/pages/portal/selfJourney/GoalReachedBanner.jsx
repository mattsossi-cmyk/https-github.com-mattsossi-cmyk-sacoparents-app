import React, { useEffect, useMemo, useState } from "react";
import confetti from "canvas-confetti";

const COLORS = ["#047857", "#10b981", "#4a1d7a", "#9b6ad6", "#ffffff"];
const storeKey = (uid) => `sac_goal_celebrated_${uid || "guest"}`;
const readSeen = (uid) => {
  try {
    return JSON.parse(window.localStorage.getItem(storeKey(uid)) || "[]");
  } catch {
    return [];
  }
};
const when = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

// Once per goal: confetti + "Goal reached" banner on the Self Journey page after a goal is marked reached.
export function GoalReachedBanner({ history, userId, active }) {
  const [shown, setShown] = useState(null);
  const pending = useMemo(() => {
    const seen = new Set(readSeen(userId));
    return [...history].reverse().find((h) => h.reached_at && (h.goal || "").trim() && !seen.has(h.id)) || null;
  }, [history, userId]);

  useEffect(() => {
    if (!active || !pending) return;
    try {
      window.localStorage.setItem(storeKey(userId), JSON.stringify([...new Set([...readSeen(userId), pending.id])].slice(-100)));
    } catch {
      /* private mode: celebrate anyway */
    }
    setShown(pending);
    const fire = (x) => confetti({ particleCount: 80, spread: 75, startVelocity: 30, origin: { x, y: 0.35 }, colors: COLORS, zIndex: 70, disableForReducedMotion: true });
    fire(0.3);
    const t = setTimeout(() => fire(0.7), 200);
    return () => clearTimeout(t);
  }, [active, pending, userId]);

  if (!shown) return null;
  return (
    <div data-testid="door-self-goal-reached" role="status" className="relative overflow-hidden rounded-2xl bg-emerald-700 text-white px-5 py-4 flex items-center gap-4 shadow-[0_12px_30px_-12px_rgba(4,120,87,0.7)] animate-in fade-in slide-in-from-top-2 duration-500">
      <span className="shrink-0 w-12 h-12 rounded-full bg-white text-emerald-700 grid place-items-center text-xl shadow-md">
        <i className="fa-solid fa-flag-checkered" aria-hidden="true"></i>
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-base font-extrabold leading-tight">Goal reached</p>
        <p data-testid="door-self-goal-reached-text" className="text-[13px] text-emerald-50 leading-snug mt-0.5 break-words">
          &ldquo;{shown.goal}&rdquo; &middot; {when(shown.reached_at)}. Your child feels this progress too.
        </p>
      </div>
      <button
        type="button"
        data-testid="door-self-goal-reached-dismiss"
        onClick={() => setShown(null)}
        aria-label="Dismiss"
        className="shrink-0 w-8 h-8 rounded-full grid place-items-center bg-white/15 hover:bg-white/25 transition-colors"
      >
        <i className="fa-solid fa-xmark" aria-hidden="true"></i>
      </button>
    </div>
  );
}
