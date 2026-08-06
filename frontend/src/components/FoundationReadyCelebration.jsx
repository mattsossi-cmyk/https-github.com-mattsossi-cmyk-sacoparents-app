/**
 * FoundationReadyCelebration — one-time confetti burst + "Foundation Ready"
 * badge card that fires when all five Progress Dashboard pills light up.
 *
 * Renders nothing until `done === total`. Dismissable; once dismissed the
 * dismissal is persisted in localStorage so we don't blast confetti at
 * every dashboard visit. If the parent regresses (a pill un-lights) and
 * later re-earns the badge, the celebration replays.
 */
import React, { useEffect, useMemo, useState } from "react";
import { PartyPopper, ShieldCheck, X, Copy } from "lucide-react";
import { toast } from "sonner";

const BURST_COLORS = ["#3D1A78", "#8471B3", "#4AAF7C", "#F1D9A0", "#B5DFC5"];

function Confetti() {
  const particles = useMemo(() => {
    return Array.from({ length: 36 }).map((_, i) => {
      const angle = (Math.PI * 2 * i) / 36 + Math.random() * 0.4;
      const distance = 120 + Math.random() * 100;
      const dx = Math.cos(angle) * distance;
      const dy = Math.sin(angle) * distance * 0.7 - 60;
      const rot = -180 + Math.random() * 360;
      const delay = Math.random() * 160;
      const size = 6 + Math.random() * 7;
      const color = BURST_COLORS[i % BURST_COLORS.length];
      return { id: `fp${i}`, dx, dy, rot, delay, size, color };
    });
  }, []);
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
      data-testid="foundation-ready-confetti"
    >
      {particles.map((p) => (
        <span
          key={p.id}
          className="absolute left-1/2 top-1/2 rounded-[2px] block"
          style={{
            width: `${p.size}px`,
            height: `${p.size * 0.4}px`,
            backgroundColor: p.color,
            transform: "translate(-50%, -50%) rotate(0deg)",
            opacity: 0,
            animation: `sacop-foundation-confetti-burst 1500ms cubic-bezier(0.22, 0.61, 0.36, 1) ${p.delay}ms both`,
            "--dx": `${p.dx}px`,
            "--dy": `${p.dy}px`,
            "--rot": `${p.rot}deg`,
          }}
        />
      ))}
      <style>{`
        @keyframes sacop-foundation-confetti-burst {
          0%   { opacity: 0; transform: translate(-50%, -50%) rotate(0deg) scale(0.5); }
          20%  { opacity: 1; }
          100% { opacity: 0; transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) rotate(var(--rot)) scale(1); }
        }
      `}</style>
    </div>
  );
}

// One-time state per "streak" — as soon as the parent hits 5/5 we mark
// the celebration seen. If they later fall to 4/5, the streak flag is
// cleared so the next 5/5 replays.
const SEEN_KEY = "sacop.foundation_ready_celebrated.v1";
const READY_STREAK_KEY = "sacop.foundation_ready_streak.v1";

export function markFoundationReadyStreak(isReady) {
  try {
    if (!isReady) {
      window.localStorage.removeItem(SEEN_KEY);
      window.localStorage.removeItem(READY_STREAK_KEY);
    } else {
      window.localStorage.setItem(READY_STREAK_KEY, "1");
    }
  } catch {
    /* private-mode — ignore */
  }
}

const SHARE_LINE =
  "I hit all five mediation-prep milestones on SA CoParenting — my Foundation is Ready. 💪";

export default function FoundationReadyCelebration({ done, total }) {
  const isReady = done > 0 && total > 0 && done === total;
  const [dismissed, setDismissed] = useState(() => {
    try {
      return window.localStorage.getItem(SEEN_KEY) === "1";
    } catch {
      return false;
    }
  });

  // Reset the seen flag if the streak breaks (parent went 5→4). The next
  // time they hit 5/5 the celebration fires again.
  useEffect(() => {
    markFoundationReadyStreak(isReady);
    if (!isReady && dismissed) {
      setDismissed(false);
    }
  }, [isReady, dismissed]);

  if (!isReady || dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem(SEEN_KEY, "1");
    } catch {
      /* ignore */
    }
  };

  const share = async () => {
    try {
      await navigator.clipboard.writeText(SHARE_LINE);
      toast.success("Copied — paste it wherever you'd like to share.");
    } catch {
      toast.error("Couldn't copy. Long-press the line to select it manually.");
    }
  };

  return (
    <section
      className="relative mt-6 overflow-hidden rounded-3xl border-2 border-[#F1D9A0] bg-gradient-to-br from-[#FDF4E6] via-[#F1F9F4] to-[#F5F1FB] p-5 sm:p-7 shadow-md"
      data-testid="foundation-ready-celebration"
    >
      <Confetti />
      <div className="relative flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#8C5A2C] flex items-center gap-2">
            <PartyPopper size={12} /> Badge unlocked
          </div>
          <h2
            className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-1 flex items-center gap-2 leading-tight"
            data-testid="foundation-ready-headline"
          >
            <ShieldCheck size={22} className="text-[#1F5C3B] shrink-0" />
            Your Foundation Is Ready.
          </h2>
          <p className="text-sm text-[#4B4567] mt-2 max-w-xl leading-relaxed">
            All five milestones lit — safety filed, child needs mapped,
            communication and mediation prep in hand, and a compare that
            shows real alignment with your co-parent. That's a full
            child-focused foundation. Well done.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={share}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-[#3D1A78] text-white hover:brightness-110 transition-all"
              data-testid="foundation-ready-share"
            >
              <Copy size={12} /> Copy a share line
            </button>
            <button
              type="button"
              onClick={dismiss}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold border border-[#E5E0EE] text-[#3D1A78] bg-white hover:bg-[#F1EEF7] transition-all"
              data-testid="foundation-ready-dismiss"
            >
              Keep celebrating on the dashboard
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="shrink-0 text-[#857E9C] hover:text-[#3D1A78] p-1.5 rounded-full hover:bg-white/60"
          aria-label="Dismiss"
          data-testid="foundation-ready-close"
        >
          <X size={16} />
        </button>
      </div>
    </section>
  );
}

/**
 * FoundationReadyBadge — persistent badge shown next to the count when
 * `done === total`. Complements the one-shot celebration above so the
 * milestone stays visible even after the confetti fades.
 */
export function FoundationReadyBadge({ done, total }) {
  if (!(done > 0 && total > 0 && done === total)) return null;
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-gradient-to-r from-[#F1D9A0] via-[#F1F9F4] to-[#D6CFE8] text-[#1A1330] shadow-sm"
      data-testid="foundation-ready-badge"
      title="You've lit all five milestones."
    >
      <ShieldCheck size={11} className="text-[#1F5C3B]" /> Foundation Ready
    </span>
  );
}
