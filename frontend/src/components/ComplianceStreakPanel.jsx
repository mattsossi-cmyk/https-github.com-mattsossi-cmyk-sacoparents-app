/**
 * ComplianceStreakPanel — Rewards & progress display for the weekly
 * compliance streak. Shown at the top of /interventions.
 *
 * Data comes from `GET /api/interventions/streak`:
 *   - current_streak / longest_streak
 *   - badges array (each has `earned` bool)
 *   - next_badge with `weeks_to_go` + `progress_pct`
 *
 * Also fires a one-shot confetti burst the first time a new badge is
 * detected on this device (keyed by badge key in localStorage).
 */
import { useEffect, useRef, useState } from "react";
import { Flame, Award, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const LS_KEY = "sacop_compliance_badges_celebrated_v1";

function readCelebrated() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

function writeCelebrated(set) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify([...set]));
  } catch { /* private mode */ }
}

async function fireConfetti() {
  try {
    const mod = await import("canvas-confetti");
    const confetti = mod.default || mod;
    confetti({
      particleCount: 60,
      spread: 65,
      origin: { y: 0.6 },
      colors: ["#3D1A78", "#2DB5B5", "#F4C15C", "#B95CE0"],
    });
    setTimeout(() => confetti({
      particleCount: 40, spread: 90, origin: { y: 0.4 },
    }), 220);
  } catch { /* SSR / no confetti */ }
}

export default function ComplianceStreakPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const firedRef = useRef(new Set());

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/interventions/streak");
        setData(data);
      } catch (err) {
        logError("Streak load failed", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Celebrate the first time an earned badge is seen on this device.
  useEffect(() => {
    if (!data?.badges) return;
    const already = readCelebrated();
    const next = new Set(already);
    let newlyEarned = null;
    for (const b of data.badges) {
      if (!b.earned) continue;
      if (already.has(b.key)) continue;
      if (firedRef.current.has(b.key)) continue;
      firedRef.current.add(b.key);
      next.add(b.key);
      newlyEarned = b;
    }
    if (newlyEarned) {
      writeCelebrated(next);
      setTimeout(() => fireConfetti(), 200);
      toast.success(`Badge unlocked · ${newlyEarned.label}`, {
        description: newlyEarned.description,
        duration: 7000,
      });
    }
  }, [data]);

  if (loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 inline-flex items-center gap-2 text-xs text-[#4B4567]"
        data-testid="streak-panel-loading"
      >
        <Loader2 size={12} className="animate-spin" /> Loading streak…
      </div>
    );
  }
  if (!data) return null;

  const current = data.current_streak || 0;
  const longest = data.longest_streak || 0;
  const nb = data.next_badge;
  const earnedCount = (data.badges || []).filter((b) => b.earned).length;

  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-[#F8F5FF] to-white p-5 sm:p-6"
      data-testid="compliance-streak-panel"
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Streak &amp; rewards
          </div>
          <div className="mt-1 flex items-baseline gap-2 flex-wrap">
            <Flame size={22} className={current > 0 ? "text-[#E8A628]" : "text-[#B7AECC]"} />
            <span
              className="text-3xl font-bold text-[#1A1330]"
              data-testid="streak-current"
            >
              {current}
            </span>
            <span className="text-sm text-[#4B4567]">
              {current === 1 ? "week in a row" : "weeks in a row"} at ≥{data.threshold_pct}%
            </span>
          </div>
          <div className="text-[11px] text-[#8471B3] mt-1">
            Longest streak: <strong>{longest}</strong> · Badges earned:{" "}
            <strong data-testid="streak-earned-count">{earnedCount}</strong> of {data.badges.length}
          </div>
        </div>
        <div className="inline-flex items-center gap-1.5 text-[11px] text-[#4B4567] italic">
          <Sparkles size={12} className="text-[#3D1A78]" />
          Missing a week resets the streak — silence isn&rsquo;t credit.
        </div>
      </div>

      {/* Next-badge progress */}
      {nb && (
        <div
          className="mt-4 rounded-2xl bg-white border border-[#E5E0EE] p-4"
          data-testid="streak-next-badge"
        >
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
                Next badge
              </div>
              <div className="font-serif text-lg text-[#1A1330] mt-0.5">
                {nb.label}
              </div>
              <div className="text-[11px] text-[#4B4567] mt-0.5">
                {nb.weeks_to_go === 0
                  ? "Complete this week at ≥80% to unlock it!"
                  : `${nb.weeks_to_go} week${nb.weeks_to_go === 1 ? "" : "s"} to go`}
              </div>
            </div>
            <div className="text-sm font-bold text-[#3D1A78]">
              {current} / {nb.weeks}
            </div>
          </div>
          <div className="h-2 mt-3 rounded-full bg-[#F0EEF8] overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
              style={{ width: `${Math.min(100, Math.max(2, nb.progress_pct))}%` }}
            />
          </div>
        </div>
      )}
      {!nb && (
        <div
          className="mt-4 rounded-2xl bg-white border border-[#E5E0EE] p-4 text-sm text-[#4B4567]"
          data-testid="streak-all-earned"
        >
          <Sparkles size={14} className="inline text-[#E8A628] mr-1" />
          You&rsquo;ve earned every compliance badge available. Extraordinary.
        </div>
      )}

      {/* Badge shelf */}
      <div className="mt-4 flex flex-wrap gap-2" data-testid="streak-badge-shelf">
        {data.badges.map((b) => (
          <div
            key={b.key}
            data-testid={`streak-badge-${b.key}`}
            data-earned={b.earned ? "1" : "0"}
            title={b.description}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${
              b.earned
                ? "bg-[#FFF5DA] text-[#8A5B00] border-[#E8A628]"
                : "bg-white text-[#8471B3] border-[#E5E0EE] opacity-70"
            }`}
          >
            <Award size={12} className={b.earned ? "text-[#E8A628]" : "text-[#B7AECC]"} />
            {b.label}
            {b.earned && <span className="text-[9px] uppercase tracking-[0.15em]">Earned</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
