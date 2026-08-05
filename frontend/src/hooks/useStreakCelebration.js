/**
 * useStreakCelebration — client-side once-per-user celebration for
 * long-running dashboard streaks. Fires a small confetti burst and
 * a toast the first time `streakDays` crosses each configured threshold
 * (default: 30 and 100 days), then remembers the celebration in
 * localStorage so it never repeats on the same device.
 *
 * We deliberately mirror the backend badge thresholds
 * (`month_streak_30`, `hundred_day_streak`) so the client-side
 * celebration always co-occurs with the badge being logged.
 *
 * Uses `canvas-confetti` — a ~7KB canvas-based particle library with
 * no React deps. Import is lazy so the bundle only pays the cost when
 * the celebration actually fires.
 */
import { useEffect, useRef } from "react";
import { toast } from "sonner";

const LS_KEY = "sacop_celebrated_streaks_v1";

// [threshold_days, toast_headline, toast_body]
const THRESHOLDS = [
  [30,  "30 days steady!",   "You've shown up a whole month in a row — that's the kind of consistency your child feels."],
  [100, "A century of care!", "One hundred days on your dashboard. That's not a streak — that's a habit. Extraordinary."],
];

function readCelebrated() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr)
      ? arr.map(Number).filter((n) => Number.isFinite(n) && n > 0)
      : [];
  } catch {
    return [];
  }
}

function writeCelebrated(list) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(list));
  } catch { /* localStorage disabled / private mode — silently skip */ }
}

async function fireConfetti() {
  try {
    const mod = await import("canvas-confetti");
    const confetti = mod.default || mod;
    // Two staggered bursts feel more like a celebration than one blast.
    confetti({
      particleCount: 90,
      spread: 70,
      origin: { x: 0.5, y: 0.3 },
      colors: ["#3D1A78", "#8471B3", "#F1D9A0", "#B5DFC5", "#EFB4B4"],
      disableForReducedMotion: true,
    });
    setTimeout(() => {
      confetti({
        particleCount: 60,
        spread: 100,
        startVelocity: 25,
        origin: { x: 0.5, y: 0.4 },
        colors: ["#3D1A78", "#F1D9A0", "#B5DFC5"],
        disableForReducedMotion: true,
      });
    }, 350);
  } catch { /* canvas-confetti missing / SSR — silently skip */ }
}

/**
 * @param {number|undefined} streakDays — the current streak length from
 *   /api/dashboard/progress. Falsy/undefined values are a no-op.
 */
export default function useStreakCelebration(streakDays) {
  // Prevent double-firing inside the same session if the effect re-runs
  // (e.g. React 18 strict-mode double invocation) before localStorage
  // is written.
  const firedThisMount = useRef(new Set());

  useEffect(() => {
    if (!streakDays || streakDays < THRESHOLDS[0][0]) return;

    const already = new Set(readCelebrated());
    const nowCelebrated = new Set(already);

    for (const [threshold, headline, body] of THRESHOLDS) {
      if (streakDays < threshold) continue;
      if (already.has(threshold)) continue;
      if (firedThisMount.current.has(threshold)) continue;
      firedThisMount.current.add(threshold);
      nowCelebrated.add(threshold);
      // Slight delay so the toast doesn't race with the initial paint.
      setTimeout(() => { fireConfetti(); }, 150);
      toast.success(headline, {
        description: body,
        duration: 6000,
      });
    }

    if (nowCelebrated.size !== already.size) {
      writeCelebrated([...nowCelebrated]);
    }
  }, [streakDays]);
}

// Exported for testing.
export const _internals = {
  LS_KEY,
  THRESHOLDS,
  readCelebrated,
  writeCelebrated,
};
