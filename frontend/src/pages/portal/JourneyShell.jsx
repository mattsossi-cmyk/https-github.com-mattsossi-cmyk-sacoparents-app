import React, { useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import { GreyRockToggleChip } from "./AlignmentHub";

/**
 * JourneyShell — iter259 two-door landing (iter260 adds Door Memory
 * + in-door Quick Exit).
 *
 * Per founder: the first page shows only two primary buttons —
 * Court Ordered and Self Journey. Picking a door reveals a lean
 * sub-view with the Safety-First strip, three A/B/C modules, and
 * path-specific extras.
 *
 *   Landing: Court Ordered | Self Journey
 *   Court Ordered: Safety First → A/B/C → Professional report invite
 *                  (opens sacoparentsalign.online in a new tab)
 *   Self Journey:  Safety First → A/B/C → Co-parenting journey →
 *                  Self assessment → Alignment reports → Foundation
 *                  statements → Communication Builder
 *
 * iter260:
 *   • `DOOR_MEMORY_KEY` persists the last door the parent opened so
 *     returning sessions land straight back in that sub-view.
 *   • Both sub-views carry a tiny Quick Exit chip in the top row so
 *     a parent in distress can replace the tab with a neutral page
 *     even once they are deep inside a path.
 *
 * The SA CoParents Guide chatbot modal is NOT auto-opened on this
 * screen (suppressed in SacoparentsPortal `iter259`); it stays
 * reachable from any `onOpenIntroGuide` caller.
 */

const DOOR_MEMORY_KEY = "sacoparents_last_door";
const CELEBRATED_KEY = "sacoparents_celebrated_modules";
const ALL_THREE_KEY = "sacoparents_all_three_celebrated";

const readLastDoor = () => {
  try {
    const v = window.localStorage.getItem(DOOR_MEMORY_KEY);
    return v === "court" || v === "self" ? v : null;
  } catch {
    return null;
  }
};

const writeLastDoor = (door) => {
  try {
    if (door) window.localStorage.setItem(DOOR_MEMORY_KEY, door);
    else window.localStorage.removeItem(DOOR_MEMORY_KEY);
  } catch {
    /* storage unavailable — fail silently */
  }
};

const readCelebrated = () => {
  try {
    const raw = window.localStorage.getItem(CELEBRATED_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
};

const writeCelebrated = (list) => {
  try {
    window.localStorage.setItem(CELEBRATED_KEY, JSON.stringify(list));
  } catch {
    /* storage unavailable — fail silently */
  }
};

// iter261 — subtle confetti burst from the bottom-centre of the
// viewport. Kept quiet (small particle count, short duration) so it
// stays appropriate for a clinical surface.
const celebrateConfetti = () => {
  try {
    confetti({
      particleCount: 60,
      spread: 70,
      startVelocity: 35,
      origin: { x: 0.5, y: 0.75 },
      colors: ["#7c3aed", "#2563eb", "#10b981", "#f59e0b"],
      ticks: 150,
      scalar: 0.9,
    });
  } catch {
    /* best-effort */
  }
};

// iter262 — Finale burst for the all-three completion. Two bursts
// from either side of the viewport so the moment really lands, but
// still restrained enough to remain tasteful on a clinical surface.
const celebrateFinaleConfetti = () => {
  try {
    const palette = ["#7c3aed", "#2563eb", "#10b981", "#f59e0b", "#ef4444"];
    confetti({
      particleCount: 140,
      spread: 90,
      startVelocity: 45,
      origin: { x: 0.2, y: 0.75 },
      colors: palette,
      ticks: 220,
      scalar: 1.05,
    });
    setTimeout(() => {
      confetti({
        particleCount: 140,
        spread: 90,
        startVelocity: 45,
        origin: { x: 0.8, y: 0.75 },
        colors: palette,
        ticks: 220,
        scalar: 1.05,
      });
    }, 180);
  } catch {
    /* best-effort */
  }
};

const readAllThreeCelebrated = () => {
  try {
    return window.localStorage.getItem(ALL_THREE_KEY) === "1";
  } catch {
    return false;
  }
};

const writeAllThreeCelebrated = (value) => {
  try {
    if (value) window.localStorage.setItem(ALL_THREE_KEY, "1");
    else window.localStorage.removeItem(ALL_THREE_KEY);
  } catch {
    /* storage unavailable — fail silently */
  }
};

const quickExitAction = () => {
  // Low-friction DV pattern: replace the tab with a neutral weather
  // page so a back button can't recover the app.
  try {
    window.location.replace("https://www.weather.com/");
  } catch {
    /* best-effort */
  }
};

const PRIMARY_MODULES = [
  {
    letter: "A",
    key: "foundation",
    title: "Child Needs & Priorities",
    body: "Focus on routines, school, and emotional security.",
    topic: "foundation",
  },
  {
    letter: "B",
    key: "coparenting",
    title: "Co-Parenting Dynamics",
    body: "Identify communication styles and decision-making preferences.",
    topic: "coparenting",
  },
  {
    letter: "C",
    key: "safety",
    title: "Conflict Readiness",
    body: "Prepare for conflict and spot safety concerns.",
    topic: "safety",
  },
];

const STATUS_META = {
  completed: {
    label: "Completed",
    chip: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  in_progress: {
    label: "In progress",
    chip: "bg-blue-100 text-blue-800 border-blue-200",
  },
  not_yet: {
    label: "Not started",
    chip: "bg-slate-100 text-slate-700 border-slate-200",
  },
};

// Professional (Align) site opened from the Court Ordered sub-view.
// Env-overridable so the founder can switch the hostname without a
// code change.
const ALIGN_SITE_URL =
  process.env.REACT_APP_ALIGN_SITE_URL ||
  "https://sacoparentsalign.online";

export function JourneyShell({
  user,
  safetyAck,
  pathPickedAt,
  courtKey = null,
  verifiedMediator = null,
  onEnterParent = () => {},
  onEnterCourt = () => {},
  onOpenSafety = () => {},
  onClearGreyRock = () => {},
  onOpenSafetyRetake = () => {},
  selfAssessmentUrl = "/coparenting-self-assessment-preview.html",
  onOpenGuidedJourney = () => {},
  onOpenBiffCoach = () => {},
  onOpenIntroGuide = () => {},
  onOpenReport = () => {},
  biffAuthoredCount = 0,
  biffPairCount = 0,
  progressByTopic = {},
  safetyFlagged = false,
}) {
  // Suppress a few unused props so we don't trip the linter; they
  // are still accepted for API compatibility with the handlers in
  // SacoparentsPortal.
  void onEnterParent;
  void onOpenSafetyRetake;
  void biffPairCount;
  void verifiedMediator;

  const safetyFlag = safetyFlagged || !!(safetyAck && safetyAck.flagged);

  // "door" (landing), "court", "self". Lazy-init from localStorage
  // so returning parents land straight back in the door they last
  // picked. Back clears the memory so a parent who deliberately
  // exits a sub-view returns to the landing on the next visit too.
  const [view, setView] = useState(() => readLastDoor() || "door");

  const openDoor = (next) => {
    writeLastDoor(next);
    setView(next);
  };

  const goBack = () => {
    writeLastDoor(null);
    setView("door");
  };

  // iter261 — Progress celebrations. Fire a quiet confetti + toast
  // the first time each primary module transitions to "completed".
  // The celebrated set is persisted so refreshing or revisiting the
  // sub-view does not re-trigger the celebration.
  //
  // iter262 — When all three primary modules are complete, fire a
  // bigger finale (double confetti burst + special toast) exactly
  // once, de-duped via `ALL_THREE_KEY`.
  const celebratedRef = useRef(readCelebrated());
  const allThreeRef = useRef(readAllThreeCelebrated());
  useEffect(() => {
    const already = celebratedRef.current;
    const newly = PRIMARY_MODULES.filter(
      (m) =>
        progressByTopic?.[m.topic] === "completed" &&
        !already.includes(m.topic)
    );
    const allDoneNow = PRIMARY_MODULES.every(
      (m) => progressByTopic?.[m.topic] === "completed"
    );
    if (newly.length > 0) {
      newly.forEach((m, idx) => {
        setTimeout(() => {
          celebrateConfetti();
          try {
            toast.success(`You completed ${m.title}`, {
              description:
                "Nice work. Your reflection is saved privately.",
              duration: 4500,
            });
          } catch {
            /* toast library absent — ignore */
          }
        }, idx * 500);
      });
      const nextList = Array.from(
        new Set([...already, ...newly.map((m) => m.topic)])
      );
      celebratedRef.current = nextList;
      writeCelebrated(nextList);
    }
    if (allDoneNow && !allThreeRef.current) {
      // Fire the finale after the per-module bursts have had a beat
      // to play out.
      const delay = Math.max(0, newly.length * 500 + 200);
      setTimeout(() => {
        celebrateFinaleConfetti();
        try {
          toast.success("All three reflections complete", {
            description:
              "A, B, and C are done. Your Foundation Statement is ready to review.",
            duration: 6500,
          });
        } catch {
          /* toast library absent — ignore */
        }
      }, delay);
      allThreeRef.current = true;
      writeAllThreeCelebrated(true);
    }
  }, [progressByTopic]);

  // iter262 — Replay celebration. Re-fires the per-module toasts +
  // confetti bursts for every module currently marked completed,
  // plus the finale when applicable. Does NOT touch the celebrated
  // memory, so the first-time auto-celebration still runs normally.
  const replayCelebration = () => {
    const completed = PRIMARY_MODULES.filter(
      (m) => progressByTopic?.[m.topic] === "completed"
    );
    if (completed.length === 0) {
      try {
        toast("No celebrations to replay yet", {
          description:
            "Finish one of the three reflections to earn your first.",
          duration: 4000,
        });
      } catch {
        /* ignore */
      }
      return;
    }
    completed.forEach((m, idx) => {
      setTimeout(() => {
        celebrateConfetti();
        try {
          toast.success(`You completed ${m.title}`, {
            description:
              "Replay — your reflection stays saved privately.",
            duration: 3500,
          });
        } catch {
          /* ignore */
        }
      }, idx * 450);
    });
    if (completed.length === PRIMARY_MODULES.length) {
      setTimeout(() => {
        celebrateFinaleConfetti();
        try {
          toast.success("All three reflections complete", {
            description: "Replay — A, B, and C are done.",
            duration: 5500,
          });
        } catch {
          /* ignore */
        }
      }, completed.length * 450 + 200);
    }
  };

  const greetingName = user?.name ? user.name.split(" ")[0] : null;

  const moduleCta = (m) => {
    // Primary module tap: Conflict Readiness opens the Safety
    // screen because the clinical SafetyScreen is where the
    // "readiness" questions live. The other two open their guided
    // journey topic.
    if (m.topic === "safety") {
      onOpenSafety();
    } else {
      onOpenGuidedJourney(m.topic);
    }
  };

  const renderModuleRow = (m) => {
    const status = progressByTopic?.[m.topic] || "not_yet";
    const meta = STATUS_META[status];
    return (
      <button
        key={m.key}
        type="button"
        data-testid={`door-module-${m.key}`}
        data-status={status}
        onClick={() => moduleCta(m)}
        className="w-full text-left bg-white hover:bg-slate-50 border border-slate-200 rounded-xl p-3 transition flex items-start gap-3"
      >
        <div className="shrink-0 w-9 h-9 rounded-lg bg-purple-100 text-purple-800 font-bold flex items-center justify-center">
          {m.letter}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-sm font-bold text-slate-900 leading-tight">
              {m.title}
            </div>
            <span
              className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${meta.chip}`}
            >
              {meta.label}
            </span>
          </div>
          <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
            {m.body}
          </p>
        </div>
        <i className="fa-solid fa-arrow-right text-slate-400 mt-3"></i>
      </button>
    );
  };

  // Shared sub-view header (brand + back + switch-door + quick-exit).
  const SubViewHeader = ({ title, subtitle }) => {
    const otherDoor = view === "court" ? "self" : "court";
    const otherLabel =
      otherDoor === "self" ? "Self Journey" : "Court Ordered";
    const otherIcon =
      otherDoor === "self" ? "fa-door-open" : "fa-gavel";
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <button
            type="button"
            data-testid="door-back"
            onClick={goBack}
            className="text-[12px] font-semibold text-purple-700 hover:text-purple-900"
          >
            <i className="fa-solid fa-arrow-left mr-1"></i>
            Back
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="door-switch"
              data-target={otherDoor}
              onClick={() => openDoor(otherDoor)}
              className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 transition"
            >
              <i className={`fa-solid ${otherIcon} mr-1`}></i>
              Switch to {otherLabel}
            </button>
            <button
              type="button"
              data-testid="door-quick-exit"
              onClick={quickExitAction}
              className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition"
            >
              <i className="fa-solid fa-bolt mr-1"></i>
              Quick Exit
            </button>
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-purple-700">
            {greetingName ? `Welcome, ${greetingName}` : "Welcome"}
          </div>
          <h2 className="text-lg font-bold text-slate-900 leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              {subtitle}
            </p>
          )}
        </div>
      </div>
    );
  };

  const SafetyStrip = () => (
    <div className="space-y-2">
      <button
        type="button"
        data-testid="door-safety-first"
        onClick={onOpenSafety}
        className="w-full p-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-left transition flex items-center gap-2"
      >
        <i className="fa-solid fa-shield-heart"></i>
        <span className="text-sm font-bold">Safety First</span>
        <span className="ml-auto text-[11px] opacity-90">
          Private · DV &amp; IPV check
        </span>
      </button>
      {safetyFlag && (
        <GreyRockToggleChip
          onClear={onClearGreyRock}
          onRetake={onOpenSafetyRetake}
        />
      )}
    </div>
  );

  const SectionLabel = ({ children, testid }) => (
    <div
      data-testid={testid}
      className="text-[9px] uppercase font-bold tracking-wider text-slate-500 px-1 pt-1"
    >
      {children}
    </div>
  );

  // -----------------------------------------------------------------
  // LANDING — two doors only.
  // -----------------------------------------------------------------
  if (view === "door") {
    return (
      <div data-testid="journey-shell" className="space-y-4">
        <section
          data-testid="door-landing"
          className="rounded-2xl bg-white border border-slate-200 p-4 shadow-sm"
        >
          <div className="text-center space-y-1 pb-3">
            <div className="text-[10px] uppercase font-bold tracking-wider text-purple-700">
              {greetingName ? `Welcome, ${greetingName}` : "Welcome"}
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              Pick your door
            </h1>
            <p className="text-xs text-slate-600">
              Two ways in. Everything else lives behind these two choices.
            </p>
          </div>
          <div className="space-y-3">
            <button
              type="button"
              data-testid="door-court"
              onClick={() => openDoor("court")}
              className="w-full text-left bg-white hover:bg-indigo-50 border-2 border-indigo-300 rounded-2xl p-4 transition flex items-center gap-3"
            >
              <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center">
                <i className="fa-solid fa-gavel text-xl"></i>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-bold text-slate-900">
                  Court Ordered
                </div>
                <p className="text-[11px] text-indigo-700 mt-0.5 leading-snug">
                  Referred by a court, mediator, or attorney.
                </p>
              </div>
              <i className="fa-solid fa-chevron-right text-indigo-400"></i>
            </button>
            <button
              type="button"
              data-testid="door-self"
              onClick={() => openDoor("self")}
              className="w-full text-left bg-white hover:bg-purple-50 border-2 border-purple-300 rounded-2xl p-4 transition flex items-center gap-3"
            >
              <div className="shrink-0 w-12 h-12 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center">
                <i className="fa-solid fa-door-open text-xl"></i>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-bold text-slate-900">
                  Self Journey
                </div>
                <p className="text-[11px] text-purple-700 mt-0.5 leading-snug">
                  Starting on my own.
                </p>
              </div>
              <i className="fa-solid fa-chevron-right text-purple-400"></i>
            </button>
          </div>
        </section>
      </div>
    );
  }

  // -----------------------------------------------------------------
  // COURT ORDERED SUB-VIEW
  // -----------------------------------------------------------------
  if (view === "court") {
    return (
      <div data-testid="journey-shell" className="space-y-4">
        <section data-testid="door-view-court" className="space-y-4">
          <SubViewHeader
            title="Court Ordered"
            subtitle="Finish your Safety-First check, pick where to start, and open the professional invite."
          />

          {courtKey && (
            <div
              data-testid="door-court-banner"
              className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-[11px] text-emerald-900 leading-snug flex items-start gap-2"
            >
              <i className="fa-solid fa-gavel text-emerald-600 mt-0.5"></i>
              <div>
                <span className="font-semibold">Court access verified:</span>{" "}
                Case {courtKey}.
              </div>
            </div>
          )}

          <SafetyStrip />

          <div data-testid="door-court-abc" className="space-y-2">
            <SectionLabel testid="door-court-abc-label">
              Choose where to start
            </SectionLabel>
            {PRIMARY_MODULES.map((m) => renderModuleRow(m))}
          </div>

          <div
            data-testid="door-court-pro-invite"
            className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2"
          >
            <SectionLabel testid="door-court-pro-label">
              Professional report
            </SectionLabel>
            <p className="text-[12px] text-slate-700 leading-snug">
              Your mediator, attorney, or coordinator signs in here
              to review and send the professional report tied to
              your case.
            </p>
            <a
              href={ALIGN_SITE_URL}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="door-court-pro-link"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-bold text-[11px] transition"
            >
              <i className="fa-solid fa-arrow-up-right-from-square"></i>
              Open sacoparentsalign.online
            </a>
          </div>

          {!courtKey && (
            <button
              type="button"
              data-testid="door-court-enter-key"
              onClick={onEnterCourt}
              className="w-full p-2 rounded-xl bg-white hover:bg-indigo-50 border border-indigo-300 text-indigo-800 text-left transition text-xs font-semibold"
            >
              <i className="fa-solid fa-key mr-1.5"></i>
              I have a court access key
            </button>
          )}
        </section>
      </div>
    );
  }

  // -----------------------------------------------------------------
  // SELF JOURNEY SUB-VIEW
  // -----------------------------------------------------------------
  const biffCountLabel =
    biffAuthoredCount === 0
      ? "No rewrites yet"
      : `${biffAuthoredCount} message${biffAuthoredCount === 1 ? "" : "s"} reworked`;

  return (
    <div data-testid="journey-shell" className="space-y-4">
      <section data-testid="door-view-self" className="space-y-4">
        <SubViewHeader
          title="Self Journey"
          subtitle="Private safety check, three choices to start, and your reports — all in one place."
        />

        <SafetyStrip />

        <div data-testid="door-self-abc" className="space-y-2">
          <SectionLabel testid="door-self-abc-label">
            Choose where to start
          </SectionLabel>
          {PRIMARY_MODULES.map((m) => renderModuleRow(m))}
        </div>

        <div className="space-y-2">
          <SectionLabel testid="door-self-journey-label">
            Co-parenting journey
          </SectionLabel>
          <button
            type="button"
            data-testid="door-self-coparenting"
            onClick={() => onOpenGuidedJourney("coparenting")}
            className="w-full text-left bg-white hover:bg-purple-50 border border-purple-300 rounded-xl p-3 transition flex items-center gap-3"
          >
            <div className="shrink-0 w-9 h-9 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center">
              <i className="fa-solid fa-chart-line"></i>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold text-slate-900">
                Take or re-take the 40-Q check
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                Track how we're doing as co-parents over time.
              </p>
            </div>
            <i className="fa-solid fa-arrow-right text-slate-400"></i>
          </button>
        </div>

        <div className="space-y-2">
          <SectionLabel testid="door-self-selfassessment-label">
            Self assessment
          </SectionLabel>
          <a
            href={selfAssessmentUrl}
            target="_blank"
            rel="noreferrer"
            data-testid="door-self-selfassessment"
            className="block w-full text-left bg-white hover:bg-indigo-50 border border-indigo-300 rounded-xl p-3 transition flex items-center gap-3"
          >
            <div className="shrink-0 w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <i className="fa-solid fa-wand-magic-sparkles"></i>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold text-slate-900">
                40-question interactive preview
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                Try the self-assessment without saving anything.
              </p>
            </div>
            <i className="fa-solid fa-arrow-up-right-from-square text-slate-400 text-xs"></i>
          </a>
        </div>

        <div className="space-y-2">
          <SectionLabel testid="door-self-alignment-label">
            Alignment reports
          </SectionLabel>
          <div className="grid grid-cols-3 gap-1.5">
            {[
              {
                key: "educational",
                label: "Educational",
                icon: "fa-graduation-cap",
                hover: "hover:bg-emerald-50",
                border: "border-emerald-200",
                color: "text-emerald-800",
              },
              {
                key: "medical",
                label: "Medical",
                icon: "fa-stethoscope",
                hover: "hover:bg-sky-50",
                border: "border-sky-200",
                color: "text-sky-800",
              },
              {
                key: "psychological",
                label: "Psychological",
                icon: "fa-brain",
                hover: "hover:bg-fuchsia-50",
                border: "border-fuchsia-200",
                color: "text-fuchsia-800",
              },
            ].map((d) => {
              const status = progressByTopic?.[d.key] || "not_yet";
              return (
                <button
                  key={d.key}
                  type="button"
                  data-testid={`door-self-alignment-${d.key}`}
                  data-status={status}
                  onClick={() => onOpenGuidedJourney(d.key)}
                  className={`relative text-center bg-white ${d.hover} border ${d.border} ${d.color} rounded-lg py-2 px-1 text-[11px] font-semibold transition`}
                >
                  {status === "completed" && (
                    <span className="absolute top-1 right-1 text-emerald-600 text-[10px]">
                      <i className="fa-solid fa-check"></i>
                    </span>
                  )}
                  <i className={`fa-solid ${d.icon} block text-sm mb-0.5`}></i>
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <SectionLabel testid="door-self-foundation-label">
            Foundation statements
          </SectionLabel>
          <button
            type="button"
            data-testid="door-self-foundation"
            onClick={onOpenReport}
            className="w-full text-left bg-white hover:bg-slate-50 border border-slate-200 rounded-xl p-3 transition flex items-center gap-3"
          >
            <div className="shrink-0 w-9 h-9 rounded-lg bg-slate-900 text-white flex items-center justify-center">
              <i className="fa-solid fa-file-lines"></i>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold text-slate-900">
                Foundation Statement
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                Open to review, edit, or export the PDF.
              </p>
            </div>
            <i className="fa-solid fa-arrow-right text-slate-400"></i>
          </button>
          <button
            type="button"
            data-testid="door-self-replay-celebration"
            onClick={replayCelebration}
            className="w-full text-left bg-white hover:bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-[11px] font-semibold text-purple-800 transition flex items-center gap-2"
          >
            <i className="fa-solid fa-wand-sparkles"></i>
            Replay celebration
            <span className="ml-auto text-[10px] text-slate-500">
              Relive your reflection wins
            </span>
          </button>
        </div>

        <div className="space-y-2">
          <SectionLabel testid="door-self-communication-label">
            Communication Builder
          </SectionLabel>
          <button
            type="button"
            data-testid="door-self-biff"
            onClick={onOpenBiffCoach}
            className="w-full text-left bg-white hover:bg-amber-50 border border-amber-300 rounded-xl p-3 transition flex items-center gap-3"
          >
            <div className="shrink-0 w-9 h-9 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center">
              <i className="fa-solid fa-wand-magic-sparkles"></i>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold text-slate-900">
                BIFF rewrite + growth record
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                {biffCountLabel}.
              </p>
            </div>
            <i className="fa-solid fa-arrow-right text-slate-400"></i>
          </button>
        </div>

        {!pathPickedAt && (
          <button
            type="button"
            data-testid="door-self-chat-guide"
            onClick={onOpenIntroGuide}
            className="w-full p-2 rounded-xl bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 text-xs font-semibold transition"
          >
            <i className="fa-solid fa-comment-dots mr-1.5"></i>
            Not sure where to start? Chat with the Guide
          </button>
        )}
      </section>
    </div>
  );
}
