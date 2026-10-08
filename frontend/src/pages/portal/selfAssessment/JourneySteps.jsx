import React from "react";

const CARDS = [
  {
    key: "reflect",
    title: "Reflect on Your Strengths",
    body: "Recognize what's working well for you.",
    icon: "fa-user",
    card: "bg-purple-100/70 border-purple-200/80",
    tile: "bg-purple-500",
    heading: "text-[#3B1C6B]",
    tick: "text-purple-600",
    ring: "ring-purple-400",
    idle: "text-purple-300",
  },
  {
    key: "identify",
    title: "Identify Growth Areas",
    body: "Understand where you want to improve.",
    icon: "fa-chart-line",
    card: "bg-emerald-50 border-emerald-200/80",
    tile: "bg-emerald-500",
    heading: "text-emerald-950",
    tick: "text-emerald-600",
    ring: "ring-emerald-400",
    idle: "text-emerald-300",
  },
  {
    key: "goals",
    title: "Set Personal Goals",
    body: "Choose steps that support you and your child.",
    icon: "fa-bullseye",
    card: "bg-sky-50 border-sky-200/80",
    tile: "bg-sky-500",
    heading: "text-sky-950",
    tick: "text-sky-600",
    ring: "ring-sky-400",
    idle: "text-sky-300",
  },
  {
    key: "track",
    title: "Track Your Progress",
    body: "Retake the assessment over time and see how you're growing.",
    icon: "fa-arrow-trend-up",
    card: "bg-amber-50 border-amber-200/80",
    tile: "bg-amber-500",
    heading: "text-amber-950",
    tick: "text-amber-600",
    ring: "ring-amber-400",
    idle: "text-amber-300",
  },
];

function StatusIcon({ status, c }) {
  if (status === "done") return <i className={`fa-solid fa-circle-check ${c.tick} text-xl`}></i>;
  if (status === "current") return <i className={`fa-solid fa-circle-dot ${c.tick} text-xl animate-pulse`}></i>;
  return <i className={`fa-regular fa-circle ${c.idle} text-xl`}></i>;
}

// statuses: { reflect, identify, goals, track } -> "done" | "current" | "upcoming"
export function JourneySteps({ statuses }) {
  return (
    <div data-testid="sa-journey-steps" className="space-y-3 sm:space-y-4">
      {CARDS.map((c) => {
        const status = statuses[c.key];
        return (
          <div
            key={c.key}
            data-testid={`sa-journey-step-${c.key}`}
            data-status={status}
            className={`step-card border rounded-2xl p-3.5 sm:p-5 flex items-start gap-3 sm:gap-4 ${c.card} ${
              status === "current" ? `ring-2 ${c.ring} shadow-md` : ""
            } ${status === "upcoming" ? "opacity-80" : ""}`}
          >
            <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-2xl ${c.tile} text-white flex items-center justify-center text-lg sm:text-xl shrink-0 shadow-sm`}>
              <i className={`fa-solid ${c.icon}`}></i>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className={`text-base sm:text-lg font-bold ${c.heading}`}>{c.title}</h3>
              <p className="text-xs text-slate-600 mt-0.5 sm:mt-1">{c.body}</p>
            </div>
            <div className="shrink-0 pt-1">
              <StatusIcon status={status} c={c} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
