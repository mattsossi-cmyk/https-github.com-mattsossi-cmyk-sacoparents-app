import React from "react";
import {
  Sparkles,
  Heart,
  MessageCircle,
  Wrench,
  Sprout,
  Star,
  Trophy,
  Lock,
  Check,
} from "lucide-react";

/**
 * Badge collection for the parenting journey. Each badge unlocks based on
 * server-side progress signals — no client-side unlock hacks.
 *
 * Layout: horizontal shelf of 7 chips. Earned = full color + a small check
 * overlay. Locked = muted with a lock icon.
 */

const BADGE_DEFS = [
  {
    id: "self-reflection",
    label: "Self-Reflection Completed",
    color: "#3C7EC3",           // 🟦
    accent: "#E4EEF9",
    icon: Sparkles,
    condition: (p) => (p?.completed?.length || 0) >= 3,
    unlock_hint: "Complete any 3 prep steps to unlock.",
  },
  {
    id: "child-advocate",
    label: "Child Advocate",
    color: "#3C7858",           // 🟩
    accent: "#DCEEDF",
    icon: Heart,
    condition: (p) => p?.completed?.includes("child_goals"),
    unlock_hint: "Complete Child-Centered Goals to unlock.",
  },
  {
    id: "communication-builder",
    label: "Communication Builder",
    color: "#B58A1F",           // 🟨
    accent: "#FFF3D0",
    icon: MessageCircle,
    condition: (p) => p?.completed?.includes("comm_style"),
    unlock_hint: "Complete Communication Style to unlock.",
  },
  {
    id: "problem-solver",
    label: "Problem Solver",
    color: "#B85A20",           // 🟧
    accent: "#FCE3D0",
    icon: Wrench,
    condition: (p) => p?.completed?.includes("issues"),
    unlock_hint: "Complete Issues & Concerns to unlock.",
  },
  {
    id: "foundation-creator",
    label: "Foundation Creator",
    color: "#7B3AB8",           // 🟪
    accent: "#EFE3F9",
    icon: Sprout,
    condition: (p) => p?.completed?.includes("priority"),
    unlock_hint: "Complete Priority & Agenda to unlock.",
  },
  {
    id: "mediation-ready",
    label: "Mediation Ready",
    color: "#B8891F",           // ⭐
    accent: "#FFF3D0",
    icon: Star,
    condition: (p) => p?.completed?.includes("readiness"),
    unlock_hint: "Complete the Readiness Check to unlock.",
  },
  {
    id: "journey-complete",
    label: "Child-Focused Parent · Journey Complete",
    color: "#B8891F",           // 🏆
    accent: "#FFF3D0",
    icon: Trophy,
    condition: (p, extras) =>
      (p?.completed?.length || 0) >= 5 && (extras?.summaries_generated || 0) >= 1,
    unlock_hint: "Complete all 5 prep steps and generate your Mediation Summary.",
    isCapstone: true,
  },
];

function BadgeChip({ badge, earned }) {
  const Icon = badge.icon;
  const capstone = badge.isCapstone;
  return (
    <div
      className={`flex flex-col items-center text-center w-full ${
        earned ? "" : "opacity-60"
      }`}
      data-testid={`badge-${badge.id}`}
      data-earned={earned ? "true" : "false"}
      title={earned ? "Earned" : badge.unlock_hint}
    >
      <div className="relative">
        <div
          className={`${capstone ? "w-20 h-20 sm:w-24 sm:h-24" : "w-16 h-16 sm:w-20 sm:h-20"} rounded-full grid place-items-center transition-transform shadow-sm ${
            earned ? "" : "grayscale"
          }`}
          style={{
            background: earned
              ? `radial-gradient(circle at 30% 25%, ${badge.accent} 0%, ${badge.color} 90%)`
              : `radial-gradient(circle at 30% 25%, #E5E0EE 0%, #857E9C 90%)`,
          }}
        >
          <Icon
            size={capstone ? 34 : 26}
            className="text-white drop-shadow-sm"
            aria-hidden="true"
          />
        </div>
        {earned ? (
          <span
            className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border-2 border-[#3D1A78] grid place-items-center text-[#3D1A78]"
            aria-label="Earned"
          >
            <Check size={12} />
          </span>
        ) : (
          <span
            className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border border-[#E5E0EE] grid place-items-center text-[#857E9C]"
            aria-label="Locked"
          >
            <Lock size={11} />
          </span>
        )}
      </div>
      <div
        className={`mt-3 text-[11px] leading-tight font-bold ${
          earned ? "text-[#1A1330]" : "text-[#857E9C]"
        } ${capstone ? "sm:text-xs" : ""}`}
      >
        {badge.label}
      </div>
    </div>
  );
}

/**
 * Props:
 *   progress: { completed: string[], ... }
 *   summariesCount: number
 */
export default function BadgeShelf({ progress, summariesCount = 0 }) {
  const extras = { summaries_generated: summariesCount };
  const earnedCount = BADGE_DEFS.filter((b) => b.condition(progress, extras)).length;

  return (
    <section
      className="rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-8 shadow-sm"
      data-testid="badge-shelf"
    >
      <div className="flex items-start justify-between gap-3 mb-6 flex-wrap">
        <div>
          <div className="eyebrow mb-1">Achievements</div>
          <h2 className="font-serif text-2xl text-[#1A1330] leading-tight">
            Your parenting journey badges
          </h2>
          <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
            Earn a badge for each meaningful step you take toward child-focused
            co-parenting.
          </p>
        </div>
        <div
          className="shrink-0 inline-flex items-center gap-2 rounded-full bg-[#EFE9F9] text-[#3D1A78] px-4 py-2 text-sm font-bold"
          data-testid="badge-shelf-count"
        >
          <Trophy size={14} />
          {earnedCount} of {BADGE_DEFS.length} earned
        </div>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-4 sm:gap-6 justify-items-center">
        {BADGE_DEFS.map((b) => (
          <BadgeChip
            key={b.id}
            badge={b}
            earned={!!b.condition(progress, extras)}
          />
        ))}
      </div>
    </section>
  );
}
