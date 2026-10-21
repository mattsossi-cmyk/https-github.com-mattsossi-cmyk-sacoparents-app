import React from "react";

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

// Steps finished in the last 7 days (never the check-in); hidden when there are none.
export function WeeklyWinNote({ steps, celebrated }) {
  const since = Date.now() - WEEK_MS;
  const wins = steps.filter((s) => {
    const at = celebrated?.[s.id];
    return s.id !== "checkin" && s.status === "done" && at && at !== "seeded" && Date.parse(at) >= since;
  });
  if (!wins.length) return null;
  return (
    <section className="pd-win" data-testid="pd-weekly-win" aria-label="Your week">
      <p className="pd-win-title">Your week</p>
      <p className="pd-win-text" data-testid="pd-weekly-win-text">
        In the last 7 days you finished: {wins.map((w) => w.title).join(", ")}.
      </p>
    </section>
  );
}
