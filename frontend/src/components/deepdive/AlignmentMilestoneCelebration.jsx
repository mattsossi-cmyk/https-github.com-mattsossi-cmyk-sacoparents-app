/**
 * AlignmentMilestoneCelebration — subtle inline celebration shown once per
 * newly-crossed milestone in a Deep Dive Compare view.
 *
 * Props:
 *   milestone          number   — the highest milestone the latest snapshot just crossed (50/75/90)
 *   snapshotId         string   — used as the localStorage dedupe key
 *   productLabel       string   — e.g. "Educational Deep Dive"
 *   testidPrefix       string   — e.g. "edu-deep-compare"
 *
 * Behaviour:
 *   - Only renders when we haven't dismissed a celebration for `snapshotId`.
 *   - Emits a lightweight CSS confetti burst on first paint (no dependency).
 *   - "Copy" button copies the milestone line so parents can paste it into
 *     a message with each other.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, Copy, X, PartyPopper } from "lucide-react";
import { toast } from "sonner";

const MILESTONE_COPY = {
  50: {
    eyebrow: "Milestone unlocked",
    headline: "You've agreed on half of your answers.",
    shareLine: "We agreed on 1 in 2 questions in our co-parenting deep dive.",
    tint: { bg: "bg-[#F5F1FB]", border: "border-[#D6CFE8]", text: "text-[#3D1A78]" },
    burstColors: ["#3D1A78", "#8471B3", "#D6CFE8", "#EFE9F9"],
  },
  75: {
    eyebrow: "Milestone unlocked",
    headline: "You've agreed on more than 3 in 4 questions.",
    shareLine: "We agreed on more than 3 in 4 questions in our co-parenting deep dive.",
    tint: { bg: "bg-[#F1F9F4]", border: "border-[#B5DFC5]", text: "text-[#1F5C3B]" },
    burstColors: ["#1F5C3B", "#4AAF7C", "#B5DFC5", "#F1F9F4"],
  },
  90: {
    eyebrow: "Milestone unlocked",
    headline: "You've reached 9-in-10 alignment.",
    shareLine: "We agreed on 9 in 10 questions in our co-parenting deep dive.",
    tint: { bg: "bg-[#FDF4E6]", border: "border-[#F1D9A0]", text: "text-[#8C5A2C]" },
    burstColors: ["#8C5A2C", "#D9A24A", "#F1D9A0", "#FDF4E6"],
  },
};

function Confetti({ colors, testidPrefix }) {
  // 24 tiny CSS particles that fan out from a central point.
  const particles = useMemo(() => {
    return Array.from({ length: 24 }).map((_, i) => {
      const angle = (Math.PI * 2 * i) / 24 + Math.random() * 0.4;
      const distance = 90 + Math.random() * 80;
      const dx = Math.cos(angle) * distance;
      const dy = Math.sin(angle) * distance * 0.7 - 40; // slight upward bias
      const rot = -180 + Math.random() * 360;
      const delay = Math.random() * 120;
      const size = 6 + Math.random() * 6;
      const color = colors[i % colors.length];
      return { dx, dy, rot, delay, size, color };
    });
  }, [colors]);
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden data-testid={`${testidPrefix}-confetti`}>
      {particles.map((p, i) => (
        <span
          key={i}
          className="absolute left-1/2 top-1/2 rounded-[2px] block"
          style={{
            width: `${p.size}px`,
            height: `${p.size * 0.4}px`,
            backgroundColor: p.color,
            transform: "translate(-50%, -50%) rotate(0deg)",
            opacity: 0,
            animation: `sacop-confetti-burst 1200ms cubic-bezier(0.22, 0.61, 0.36, 1) ${p.delay}ms both`,
            "--dx": `${p.dx}px`,
            "--dy": `${p.dy}px`,
            "--rot": `${p.rot}deg`,
          }}
        />
      ))}
      <style>{`
        @keyframes sacop-confetti-burst {
          0%   { opacity: 0; transform: translate(-50%, -50%) rotate(0deg) scale(0.5); }
          20%  { opacity: 1; }
          100% { opacity: 0; transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) rotate(var(--rot)) scale(1); }
        }
      `}</style>
    </div>
  );
}

export default function AlignmentMilestoneCelebration({ milestone, snapshotId, productLabel, testidPrefix }) {
  const storageKey = snapshotId ? `sacop.milestone_dismissed.${snapshotId}` : null;
  const alreadyDismissed = useRef(false);
  const [dismissed, setDismissed] = useState(() => {
    if (!storageKey) return true;
    try {
      const flag = window.localStorage.getItem(storageKey);
      alreadyDismissed.current = !!flag;
      return !!flag;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!storageKey) return;
    // Same one-time flag check as the initial useState — kept only to react
    // to snapshot_id changes (parent moves between shares). No console noise
    // if localStorage is unavailable.
    try {
      if (window.localStorage.getItem(storageKey)) setDismissed(true);
    } catch { /* ignore */ }
  }, [storageKey]);

  const copy = MILESTONE_COPY[milestone];
  if (!copy || !milestone || dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      if (storageKey) window.localStorage.setItem(storageKey, "1");
    } catch {}
  };

  const share = async () => {
    try {
      await navigator.clipboard.writeText(copy.shareLine);
      toast.success("Copied — paste it into your message.");
    } catch {
      toast.error("Couldn't copy. Long-press the line to select it manually.");
    }
  };

  return (
    <section
      className={`relative mt-5 overflow-hidden rounded-3xl border-2 ${copy.tint.border} ${copy.tint.bg} p-5 sm:p-7 shadow-sm`}
      data-testid={`${testidPrefix}-milestone`}
      data-milestone={milestone}
    >
      <Confetti colors={copy.burstColors} testidPrefix={testidPrefix} />
      <div className="relative flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className={`text-[10px] uppercase tracking-[0.22em] font-bold ${copy.tint.text} flex items-center gap-2`}>
            <PartyPopper size={12} /> {copy.eyebrow}
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] mt-1 flex items-center gap-2">
            <Sparkles size={18} className={copy.tint.text} />
            {copy.headline}
          </h2>
          <p className="text-xs text-[#4B4567] mt-2 italic max-w-lg">
            {productLabel} · Neither parent is being scored — this is your shared ground.
          </p>
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={share}
              data-testid={`${testidPrefix}-milestone-share`}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${copy.tint.text} bg-white border ${copy.tint.border} hover:brightness-95`}
            >
              <Copy size={12} /> Copy this line
            </button>
            <button
              type="button"
              onClick={dismiss}
              data-testid={`${testidPrefix}-milestone-dismiss`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs text-[#4B4567] hover:bg-white"
            >
              <X size={12} /> Dismiss
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
