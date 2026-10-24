import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import InviteCoparentCard from "../../components/InviteCoparentCard";
import { SelfAssessmentView } from "./SelfAssessmentView";
import { FamilyCheckinCard } from "../../components/caseSettings/FamilyCheckinCard";
import { SafetyFirstBanner } from "../../components/caseSettings/SafetyFirstBanner";
import StartWithSafetyBanner from "../../components/startWithSafety/StartWithSafetyBanner";
import CoparentingBuilderReferral from "../../components/startWithSafety/CoparentingBuilderReferral";
import { SafetyScreenLink } from "./SafetyScreenLink";
import { CourtOrderedView } from "./CourtOrderedView";
import { ParallelParentingView } from "./ParallelParentingView";
import { useSelfAssessmentHistory } from "./selfAssessment/useSelfAssessmentHistory";
import { GoalBanner } from "./selfAssessment/GoalBanner";
import { GoalReachedBanner } from "./selfJourney/GoalReachedBanner";
import { CbJourneyCard } from "./selfJourney/CbJourneyCard";
import { WelcomeArtwork } from "./WelcomeArtwork";
import { JourneyArtCard } from "./selfJourney/JourneyArtCard";
import { ASSESS_ART, ASSESS_ORDER, NEEDS_ART, PP_ART } from "./selfJourney/selfJourneyArt";
import { AssessProgressRing, JourneySummaryButton } from "./selfJourney/AssessProgressRing";
import { JourneyCelebration } from "./selfJourney/JourneyCelebration";
import { useJourneySummary } from "./selfJourney/useJourneySummary";
import { useCoparentingDone } from "./selfJourney/useCoparentingDone";
import { useChildNeeds } from "./childNeeds/useChildNeeds";
import { SendToProvider } from "./childNeeds/SendToProvider";
import { FlowArrow } from "./selfJourney/FlowArrow";
import { useParallelStatus } from "./selfJourney/useParallelDone";
import { useStepsCelebrated } from "./selfJourney/useStepsCelebrated";
import { AllStepsBanner } from "./selfJourney/AllStepsBanner";
import { ContinueStep } from "./selfJourney/ContinueStep";
import { CoparentingAssessmentView } from "./coparenting/CoparentingAssessmentView";
import { useFoundationBuilder } from "./foundation/useFoundationBuilder";
import { ChildNeedsView } from "./ChildNeedsView";
import { FoundationStatementView } from "./FoundationStatementView";
import { CommShareReask } from "../../components/commStyle/CommShareReask";
import JourneyFlow from "../JourneyFlow";
import { PrivacyTag } from "../../components/parentDashboard/ParentDashboard";
import { NEW_HOME_ON } from "../../lib/previewGate";
import { useCalmMode } from "../../lib/useCalmMode";
import { api } from "../../lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";

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
 *                  (opens sacoparentsalign.com in a new tab)
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
const PAIR_CELEBRATED_KEY = "sacoparents_pair_celebrated";

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

// iter265 — Shared "pair milestone" burst for when both the parent
// and their invited co-parent have finished the three primary
// modules. Two bursts converging from top-left and top-right so it
// visually reads as two sides meeting in the middle.
const celebratePairConfetti = () => {
  try {
    const palette = ["#7c3aed", "#10b981", "#2563eb", "#f59e0b", "#ec4899"];
    confetti({
      particleCount: 110,
      spread: 70,
      angle: 300, // from upper-left toward middle
      startVelocity: 50,
      origin: { x: 0.1, y: 0.3 },
      colors: palette,
      ticks: 240,
      scalar: 1.0,
    });
    confetti({
      particleCount: 110,
      spread: 70,
      angle: 240, // from upper-right toward middle
      startVelocity: 50,
      origin: { x: 0.9, y: 0.3 },
      colors: palette,
      ticks: 240,
      scalar: 1.0,
    });
    setTimeout(() => {
      confetti({
        particleCount: 60,
        spread: 110,
        startVelocity: 30,
        origin: { x: 0.5, y: 0.6 },
        colors: palette,
        ticks: 200,
        scalar: 0.9,
      });
    }, 220);
  } catch {
    /* best-effort */
  }
};

const readPairCelebrated = () => {
  try {
    return window.localStorage.getItem(PAIR_CELEBRATED_KEY) === "1";
  } catch {
    return false;
  }
};

const writePairCelebrated = (value) => {
  try {
    if (value) window.localStorage.setItem(PAIR_CELEBRATED_KEY, "1");
    else window.localStorage.removeItem(PAIR_CELEBRATED_KEY);
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

// iter263 — Celebration badge PNG. Drawn on a <canvas> at 2x DPI so
// it looks crisp on both phones and desktop. The caller passes the
// parent's first name (optional) and we return a Promise<Blob>.
const renderCelebrationBadge = (name) => {
  return new Promise((resolve, reject) => {
    try {
      const W = 1200;
      const H = 630;
      const canvas = document.createElement("canvas");
      canvas.width = W;
      canvas.height = H;
      const ctx = canvas.getContext("2d");
      // Gradient background.
      const bg = ctx.createLinearGradient(0, 0, W, H);
      bg.addColorStop(0, "#1e1b4b");
      bg.addColorStop(0.55, "#5b21b6");
      bg.addColorStop(1, "#9333ea");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);
      // Decorative dots.
      ctx.fillStyle = "rgba(255,255,255,0.08)";
      for (let i = 0; i < 60; i++) {
        const x = (i * 97 + 23) % W;
        const y = (i * 71 + 11) % H;
        const r = 4 + ((i * 17) % 10);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      // Soft rounded rectangle (card).
      const padX = 90;
      const padY = 80;
      const r = 32;
      ctx.fillStyle = "rgba(255,255,255,0.07)";
      ctx.strokeStyle = "rgba(255,255,255,0.25)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(padX + r, padY);
      ctx.lineTo(W - padX - r, padY);
      ctx.quadraticCurveTo(W - padX, padY, W - padX, padY + r);
      ctx.lineTo(W - padX, H - padY - r);
      ctx.quadraticCurveTo(W - padX, H - padY, W - padX - r, H - padY);
      ctx.lineTo(padX + r, H - padY);
      ctx.quadraticCurveTo(padX, H - padY, padX, H - padY - r);
      ctx.lineTo(padX, padY + r);
      ctx.quadraticCurveTo(padX, padY, padX + r, padY);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      // Text — Brand pill.
      ctx.fillStyle = "#f5f3ff";
      ctx.font = "bold 26px 'Helvetica Neue', Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("SA COPARENTS", W / 2, padY + 90);
      // Title.
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 72px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("Reflection Milestone", W / 2, padY + 190);
      // Subtitle — chips A · B · C.
      ctx.fillStyle = "#c4b5fd";
      ctx.font = "bold 44px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("A  ·  B  ·  C  —  Complete", W / 2, padY + 265);
      // Name line.
      ctx.fillStyle = "#e9d5ff";
      ctx.font = "500 32px 'Helvetica Neue', Arial, sans-serif";
      const displayName = (name || "A caring parent").trim();
      ctx.fillText(`Earned by ${displayName}`, W / 2, padY + 335);
      // Date line.
      const today = new Date();
      const dateStr = today.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      ctx.fillStyle = "#a78bfa";
      ctx.font = "500 24px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText(dateStr, W / 2, padY + 385);
      // Footer tag.
      ctx.fillStyle = "#ddd6fe";
      ctx.font = "600 20px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("sacoparentsapp.online", W / 2, H - padY - 35);
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error("Badge render returned no blob"));
        },
        "image/png",
        0.95
      );
    } catch (err) {
      reject(err);
    }
  });
};

// iter266 — Joint celebration badge: two-side version of the
// Reflection Milestone, rendered when both parents in the linked
// pair have finished the three primary modules. Uses the same
// 1200×630 canvas footprint but splits the lower half into two
// signed columns so both parents' names are visible side by side.
const renderJointCelebrationBadge = (myName, coparentName) => {
  return new Promise((resolve, reject) => {
    try {
      const W = 1200;
      const H = 630;
      const canvas = document.createElement("canvas");
      canvas.width = W;
      canvas.height = H;
      const ctx = canvas.getContext("2d");
      // Gradient background — emerald → purple to signal "shared".
      const bg = ctx.createLinearGradient(0, 0, W, H);
      bg.addColorStop(0, "#064e3b");
      bg.addColorStop(0.55, "#5b21b6");
      bg.addColorStop(1, "#9333ea");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);
      // Decorative dots.
      ctx.fillStyle = "rgba(255,255,255,0.09)";
      for (let i = 0; i < 70; i++) {
        const x = (i * 103 + 29) % W;
        const y = (i * 61 + 7) % H;
        const r = 4 + ((i * 19) % 12);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      // Rounded outer card.
      const padX = 90;
      const padY = 70;
      const r = 32;
      ctx.fillStyle = "rgba(255,255,255,0.08)";
      ctx.strokeStyle = "rgba(255,255,255,0.28)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(padX + r, padY);
      ctx.lineTo(W - padX - r, padY);
      ctx.quadraticCurveTo(W - padX, padY, W - padX, padY + r);
      ctx.lineTo(W - padX, H - padY - r);
      ctx.quadraticCurveTo(W - padX, H - padY, W - padX - r, H - padY);
      ctx.lineTo(padX + r, H - padY);
      ctx.quadraticCurveTo(padX, H - padY, padX, H - padY - r);
      ctx.lineTo(padX, padY + r);
      ctx.quadraticCurveTo(padX, padY, padX + r, padY);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      // Brand pill.
      ctx.fillStyle = "#ecfdf5";
      ctx.font = "bold 26px 'Helvetica Neue', Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("SA COPARENTS", W / 2, padY + 80);
      // Title.
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 70px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("Shared Reflection", W / 2, padY + 170);
      ctx.fillText("Milestone", W / 2, padY + 240);
      // Subtitle — A · B · C.
      ctx.fillStyle = "#a7f3d0";
      ctx.font = "bold 36px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("A  ·  B  ·  C  —  Complete (both parents)", W / 2, padY + 310);
      // Two name columns.
      const colY = padY + 390;
      const nameA = (myName || "You").trim();
      const nameB = (coparentName || "Your co-parent").trim();
      // Column A.
      ctx.fillStyle = "#e9d5ff";
      ctx.font = "500 24px 'Helvetica Neue', Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Earned by", W * 0.3, colY);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 42px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText(nameA, W * 0.3, colY + 48);
      // Separator.
      ctx.strokeStyle = "rgba(255,255,255,0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(W / 2, colY - 20);
      ctx.lineTo(W / 2, colY + 60);
      ctx.stroke();
      // Column B.
      ctx.fillStyle = "#e9d5ff";
      ctx.font = "500 24px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("With", W * 0.7, colY);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 42px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText(nameB, W * 0.7, colY + 48);
      // Date.
      const today = new Date();
      const dateStr = today.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      ctx.fillStyle = "#a78bfa";
      ctx.font = "500 20px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText(dateStr, W / 2, H - padY - 55);
      // Footer tag.
      ctx.fillStyle = "#ddd6fe";
      ctx.font = "600 20px 'Helvetica Neue', Arial, sans-serif";
      ctx.fillText("sacoparentsapp.online", W / 2, H - padY - 25);
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error("Joint badge render returned no blob"));
        },
        "image/png",
        0.95
      );
    } catch (err) {
      reject(err);
    }
  });
};

export const quickExitAction = () => {
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
    body: "Prepare for tense moments, schedule changes and hand-offs.",
    topic: "safety",
  },
];

// Professional (Align) site opened from the Court Ordered sub-view.
// Env-overridable so the founder can switch the hostname without a
// code change.
export const BUILDER_PATH = "/dashboard?open=parallel-builder";

export const ALIGN_SITE_URL =
  process.env.REACT_APP_ALIGN_SITE_URL ||
  "https://sacoparentsalign.com";

export function JourneyShell({
  user,
  pathPickedAt,
  courtKey = null,
  verifiedMediator = null,
  onEnterParent = () => {},
  onVerifyCourtKey,
  onDownloadCourtPdf,
  courtRequest = 0,
  overlayOpen = false,
  onClearGreyRock = () => {},
  onOpenSafetyRetake = () => {},
  selfAssessmentUrl = "/coparenting-self-assessment-preview.html",
  onOpenBiffCoach = () => {},
  biffCoachOpen = false,
  onOpenCommBuilder = () => {},
  onOpenIntroGuide = () => {},
  onOpenReport = () => {},
  biffAuthoredCount = 0,
  biffPairCount = 0,
  progressByTopic = {},
  pairProgress = null,
  safetyFlagged = false,
  onViewChange = () => {},
  biffReady = true,
  homeRequest = 0,
}) {
  const navigate = useNavigate();

  // Suppress a few unused props so we don't trip the linter; they
  // are still accepted for API compatibility with the handlers in
  // SacoparentsPortal.
  void onEnterParent;
  void biffPairCount;

  // Grey-rock only: the parent's own switch.
  const safetyFlag = safetyFlagged;

  // "door" (landing), "court", "self". Lazy-init from localStorage
  // so returning parents land straight back in the door they last
  // picked. Back clears the memory so a parent who deliberately
  // exits a sub-view returns to the landing on the next visit too.
  // With the new parent home, home is always the dashboard: no door memory.
  const [view, setView] = useState(() => (NEW_HOME_ON ? "door" : readLastDoor() || "door"));
  const { calm } = useCalmMode();
  useEffect(() => {
    onViewChange(view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  const openDoor = (next) => {
    if (!NEW_HOME_ON) writeLastDoor(next);
    setView(next);
  };

  const goBack = () => {
    writeLastDoor(null);
    setView("door");
  };

  // Bottom-nav "Journey" returns to the dashboard.
  useEffect(() => {
    if (homeRequest) goBack();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [homeRequest]);

  // Card 3 can be opened from Self Journey or the Court page; Back returns there.
  const [subFrom, setSubFrom] = useState("self");
  const [childNeedsKey, setChildNeedsKey] = useState(null);
  const [childNeedsJump, setChildNeedsJump] = useState(null);
  const openChildNeeds = (from, key = null, jump = null) => {
    setSubFrom(from);
    setChildNeedsKey(key);
    setChildNeedsJump(jump);
    setView("child_needs");
  };

  // Court entry points outside the shell (Guide chat, follow-up nudge) open the Court page.
  useEffect(() => {
    if (courtRequest) openDoor("court");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courtRequest]);

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

      // iter267 — Fire the warm nudge email to the invited
      // co-parent (if any). The backend is idempotent and
      // enforces the IPV clearance guardrail; the frontend just
      // posts fire-and-forget. 404/503/502/403 are all expected
      // in various no-op cases (no invite, email not configured,
      // IPV flagged) and should be silently ignored.
      api.post("/invites/coparent/pair-nudge").catch(() => {
        /* non-fatal */
      });
    }
  }, [progressByTopic]);

  // iter265 — Pair milestone celebration. Fires once when the
  // linked co-parent has finished their three primary modules. The
  // trigger reads only `pairProgress.coparent_all_three_done`
  // (surfaced by `/api/invites/coparent/pair-progress`), so this is
  // decoupled from THIS parent's own completion state — a parent
  // who hasn't yet started their own reflections still gets the
  // "your co-parent is ready" nudge the moment it happens.
  const pairCelebratedRef = useRef(readPairCelebrated());
  useEffect(() => {
    if (!pairProgress || !pairProgress.paired) return;
    if (!pairProgress.coparent_all_three_done) return;
    if (pairCelebratedRef.current) return;
    const name = pairProgress.coparent_display_name;
    setTimeout(() => {
      celebratePairConfetti();
      try {
        toast.success(
          name
            ? `${name} completed their reflections too`
            : "Your co-parent completed their reflections too",
          {
            description:
              "You're both ready to carry the momentum into the joint report.",
            duration: 7000,
          }
        );
      } catch {
        /* ignore */
      }
    }, 350);
    pairCelebratedRef.current = true;
    writePairCelebrated(true);
  }, [pairProgress]);

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

  // iter263 — Celebration Share + Partner Invite nudge.
  //
  // Both features surface AFTER the all-three finale has been
  // earned. The Partner Invite nudge is additionally suppressed
  // when the parent is safety-flagged (grey-rock on / DV disclosed)
  // — the backend `/api/invites/coparent` endpoint ALSO enforces
  // the IPV safety gate, so this is a defence-in-depth guardrail,
  // not the sole protection.
  const allThreeDone = PRIMARY_MODULES.every(
    (m) => progressByTopic?.[m.topic] === "completed"
  );
  const [inviteOpen, setInviteOpen] = useState(false);

  // iter267 — Badge preview dialog state. The chip taps now
  // render the generated PNG inside a shadcn Dialog so the parent
  // can see what they'll keep before tapping Save. Save then runs
  // the share-sheet / download fallback as before.
  const [badgePreview, setBadgePreview] = useState(null);
  // { kind: "solo" | "joint", blob: Blob, url: string, filename: string }

  const closeBadgePreview = () => {
    if (badgePreview?.url) {
      try {
        URL.revokeObjectURL(badgePreview.url);
      } catch {
        /* ignore */
      }
    }
    setBadgePreview(null);
  };

  const openBadgePreview = async (kind) => {
    try {
      let blob;
      let filename;
      if (kind === "joint") {
        const coparentName = pairProgress?.coparent_display_name || null;
        blob = await renderJointCelebrationBadge(
          greetingName,
          coparentName
        );
        filename = "sa-coparents-joint-reflection-badge.png";
      } else {
        blob = await renderCelebrationBadge(greetingName);
        filename = "sa-coparents-reflection-badge.png";
      }
      const url = URL.createObjectURL(blob);
      setBadgePreview({ kind, blob, url, filename });
    } catch {
      try {
        toast.error("Could not render badge", {
          description:
            "Please try again — if it keeps failing, let us know.",
          duration: 4000,
        });
      } catch {
        /* ignore */
      }
    }
  };

  const saveBadgeFromPreview = async () => {
    if (!badgePreview) return;
    const { blob, filename, kind } = badgePreview;
    const file = new File([blob], filename, { type: "image/png" });
    const shareTitle =
      kind === "joint"
        ? "SA CoParents — Shared Reflection Milestone"
        : "SA CoParents — Reflection Milestone";
    const shareText =
      kind === "joint"
        ? "Both parents finished their reflections. Shared milestone."
        : "A · B · C — complete. My reflection milestone.";
    try {
      if (
        typeof navigator !== "undefined" &&
        navigator.canShare &&
        navigator.canShare({ files: [file] })
      ) {
        try {
          await navigator.share({
            files: [file],
            title: shareTitle,
            text: shareText,
          });
          closeBadgePreview();
          return;
        } catch {
          /* parent cancelled share — fall through to download */
        }
      }
      // Direct download fallback.
      const a = document.createElement("a");
      a.href = badgePreview.url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      try {
        toast.success(
          kind === "joint" ? "Joint badge saved" : "Badge saved",
          {
            description:
              kind === "joint"
                ? "Your Shared Reflection Milestone badge has been downloaded."
                : "Your Reflection Milestone badge has been downloaded.",
            duration: 4000,
          }
        );
      } catch {
        /* ignore */
      }
      closeBadgePreview();
    } catch {
      try {
        toast.error("Could not save badge", {
          description:
            "Please try again — if it keeps failing, let us know.",
          duration: 4000,
        });
      } catch {
        /* ignore */
      }
    }
  };

  // iter268 — new Self Journey "Assess Your Situation" modal state.
  const [assessOpen, setAssessOpen] = useState(false);
  const [ppOpen, setPpOpen] = useState(false);
  const [ppScreen, setPpScreen] = useState("welcome");
  const openPp = (screen = "welcome") => {
    setPpScreen(screen);
    setPpOpen(true);
  };
  const saHistory = useSelfAssessmentHistory(user?.user_id);
  const [assessStartNew, setAssessStartNew] = useState(false);
  const [cpAssessOpen, setCpAssessOpen] = useState(false);
  const childNeeds = useChildNeeds(user?.user_id);
  const cpDone = useCoparentingDone(user?.user_id, cpAssessOpen);
  const ppStatus = useParallelStatus(user?.user_id, ppOpen);
  const ppDone = ppStatus === "done";
  const assessDone = {
    self: saHistory.history.length > 0,
    coparent: cpDone,
    ...Object.fromEntries(["educational", "psychological", "medical"].map((k) => [k, !!childNeeds.state.completed_at?.[k]])),
  };
  const nextAssess = ASSESS_ORDER.find((k) => !assessDone[k]);
  const journeySummary = useJourneySummary(user?.user_id);
  const [celebrating, setCelebrating] = useState(false);
  // First time a parent reaches 5 of 5 on the Self Journey: confetti once, saved on the account.
  useEffect(() => {
    if (view !== "self" || nextAssess || journeySummary.celebrated || assessOpen || cpAssessOpen) return;
    setCelebrating(true);
    journeySummary.markCelebrated();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, nextAssess, journeySummary.celebrated, assessOpen, cpAssessOpen]);
  const foundationBuilder = useFoundationBuilder(
    user?.user_id,
    user?.name ? user.name.split(" ")[0] : null
  );
  const journeySteps = [
    { n: 1, label: "Self-Assessment", to: "door-self-art-assess", done: !!assessDone.self },
    { n: 2, label: "Co-Parenting Assessment", to: "door-self-art-assess", done: !!assessDone.coparent },
    { n: 3, label: "Your Child's Specific Needs", to: "door-self-art-needs", done: NEEDS_ART.items.every((i) => assessDone[i.key]) },
    { n: 4, label: "Foundation Statement", to: "door-self-card-foundation", done: !!foundationBuilder.savedAt },
    { n: 5, label: "Parallel Parenting", to: "door-self-art-parallel", done: ppDone },
    { n: 6, label: "Communication Builder", to: "door-self-card-biff", done: biffAuthoredCount > 0 },
  ];
  const resumeStep = journeySteps.find((s) => !s.done);
  const allStepsDone = !resumeStep;
  const stepsCelebrated = useStepsCelebrated(user?.user_id);
  const [sparkle, setSparkle] = useState(false);
  // First time all 6 Self Journey steps are done: purple sparkle once, saved on the account.
  useEffect(() => {
    if (view !== "self" || !allStepsDone || stepsCelebrated.celebrated || celebrating || ppOpen || assessOpen || cpAssessOpen) return;
    setSparkle(true);
    stepsCelebrated.mark();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, allStepsDone, stepsCelebrated.celebrated, celebrating, ppOpen, assessOpen, cpAssessOpen]);
  const openAssess = (startNew = false) => {
    setAssessStartNew(startNew);
    setAssessOpen(true);
  };
  // Self Journey pictures + progress ring: one entry point per assessment key.
  const openAssessKey = (k) => {
    if (k === "self") openAssess(false);
    else if (k === "coparent") setCpAssessOpen(true);
    else openChildNeeds("self", k);
  };
  const [fbStartOpen, setFbStartOpen] = useState(false);
  const openFoundation = (from, startOpen = false) => {
    setSubFrom(from);
    setFbStartOpen(startOpen);
    setView("foundation");
  };
  // Court page journey steps open the same real pages as the Self Journey cards.
  const openCourtCard = (key, { builder = false } = {}) => {
    if (key === "card1") openAssess(false);
    else if (key === "card2") setCpAssessOpen(true);
    else if (key === "card3") openChildNeeds("court");
    else if (key === "card4") openFoundation("court", builder);
  };

  // Deep links: /dashboard?open=self-assessment | parallel-builder | parallel-builder-steps | court | comm-builder | coparenting-assessment | child-needs | foundation
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const open = params.get("open");
    const keys = ["self-assessment", "parallel-builder", "parallel-builder-steps", "court", "comm-builder", "coparenting-assessment", "child-needs", "foundation"];
    if (!keys.includes(open)) return;
    params.delete("open");
    const qs = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (qs ? `?${qs}` : ""));
    if (open === "court") openDoor("court");
    else if (open === "comm-builder") onOpenCommBuilder();
    else if (open === "parallel-builder") {
      openDoor("self");
      openPp("welcome");
    } else if (open === "parallel-builder-steps") {
      openDoor("self");
      openPp(0);
    } else if (open === "coparenting-assessment") {
      openDoor("self");
      setCpAssessOpen(true);
    } else if (open === "child-needs") {
      openDoor("self");
      openChildNeeds("self");
    } else if (open === "foundation") {
      openDoor("self");
      openFoundation("self");
    } else {
      openDoor("self");
      openAssess(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // iter266 — Both-parents-done condition. Drives the joint
  // badge chip visibility inside the finale rewards block.
  const pairBothDone =
    allThreeDone && !!(pairProgress && pairProgress.coparent_all_three_done);

  const greetingName = user?.name ? user.name.split(" ")[0] : null;

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
            className="text-[0.75rem] font-semibold text-purple-700 hover:text-purple-900"
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
              className="px-2.5 py-1 rounded-full text-[0.625rem] font-bold bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 transition"
            >
              <i className={`fa-solid ${otherIcon} mr-1`}></i>
              Switch to {otherLabel}
            </button>
            <button
              type="button"
              data-testid="door-quick-exit"
              onClick={quickExitAction}
              className="px-2.5 py-1 rounded-md text-[0.625rem] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition"
            >
              <i className="fa-solid fa-bolt mr-1"></i>
              Quick Exit
            </button>
          </div>
        </div>
        <div>
          <div className="text-[0.625rem] uppercase font-bold tracking-wider text-purple-700">
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

  // -----------------------------------------------------------------
  // LANDING — welcome artwork + two doors + goal card.
  // -----------------------------------------------------------------
  const doorButtons = (
          <div className="space-y-3">
            <button
              type="button"
              data-testid="door-court"
              onClick={() => openDoor("court")}
              className="w-full text-left bg-white hover:bg-indigo-50 border-2 border-indigo-300 rounded-2xl p-4 transition-colors flex flex-wrap items-center gap-3"
            >
              <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center">
                <i className="fa-solid fa-gavel text-xl"></i>
              </div>
              <div className="min-w-[8rem] flex-1">
                <div className="text-sm font-bold text-slate-900">
                  Court Ordered
                </div>
                <p className="text-[0.6875rem] text-indigo-700 mt-0.5 leading-snug">
                  Referred by a court, mediator, or attorney.
                </p>
                {NEW_HOME_ON && (
                  <span className="pd-vars block mt-1.5" data-testid="door-tag-court"><PrivacyTag kind="you_pro" small /></span>
                )}
              </div>
              <i aria-hidden="true" className="ml-auto fa-solid fa-chevron-right text-indigo-400"></i>
            </button>
            <button
              type="button"
              data-testid="door-self"
              onClick={() => navigate("/self-journey")}
              className="w-full text-left bg-white hover:bg-purple-50 border-2 border-purple-300 rounded-2xl p-4 transition-colors flex flex-wrap items-center gap-3"
            >
              <div className="shrink-0 w-12 h-12 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center">
                <i className="fa-solid fa-door-open text-xl"></i>
              </div>
              <div className="min-w-[8rem] flex-1">
                <div className="text-sm font-bold text-slate-900">
                  Self Journey
                </div>
                <p className="text-[0.6875rem] text-purple-700 mt-0.5 leading-snug">
                  Starting on my own.
                </p>
                {NEW_HOME_ON && (
                  <span className="pd-vars block mt-1.5" data-testid="door-tag-self"><PrivacyTag kind="share_or_link" small /></span>
                )}
              </div>
              <i aria-hidden="true" className="ml-auto fa-solid fa-chevron-right text-purple-400"></i>
            </button>
            <button
              type="button"
              data-testid="door-comm"
              onClick={() => onOpenCommBuilder()}
              className="w-full text-left bg-white hover:bg-sky-50 border border-dashed border-sky-300 rounded-2xl px-4 py-3 transition-colors flex flex-wrap items-center gap-3"
            >
              <div className="shrink-0 w-10 h-10 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center">
                <i className="fa-solid fa-comments text-lg"></i>
              </div>
              <div className="min-w-[8rem] flex-1">
                <div className="text-sm font-bold text-slate-900">
                  Communication Builder
                </div>
                <p className="text-[0.6875rem] text-sky-800 mt-0.5 leading-snug">
                  Not a separate path. A message-writing tool you can open any time, from either path.
                </p>
                {NEW_HOME_ON && (
                  <span className="pd-vars block mt-1.5" data-testid="door-tag-comm"><PrivacyTag kind="only_you_unless" small /></span>
                )}
              </div>
              <i aria-hidden="true" className="ml-auto fa-solid fa-chevron-right text-sky-400"></i>
            </button>
          </div>
  );
  const welcomeArt = (
    <WelcomeArtwork
      testid="door-welcome-image"
      actions={{
        self: () => navigate("/self-journey"),
        court: () => openDoor("court"),
        comm: () => onOpenCommBuilder(),
      }}
    />
  );
  const goalBanner = (
    <GoalBanner
      testid="door-landing-goal"
      goal={saHistory.currentGoal}
      setAt={saHistory.latest?.completed_at}
      practice={saHistory.practice}
      onPractise={saHistory.practise}
      dueDays={saHistory.dueDays}
      onOpen={() => {
        openDoor("self");
        openAssess(saHistory.dueDays > 0);
      }}
    />
  );

  if (view === "door" && NEW_HOME_ON) {
    return (
      <div data-testid="journey-shell" className={`space-y-4${calm ? " calm-mode" : ""}`}>
        {welcomeArt}
        <CommShareReask />
      </div>
    );
  }

  if (view === "door") {
    return (
      <div data-testid="journey-shell" className="space-y-4">
        <div className="flex justify-end">
          <button
            type="button"
            data-testid="journey-quick-exit"
            onClick={quickExitAction}
            className="min-h-[40px] px-4 rounded-full text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors"
          >
            <i className="fa-solid fa-bolt mr-1" aria-hidden="true"></i>
            Quick Exit
          </button>
        </div>
        <StartWithSafetyBanner />
        <SafetyFirstBanner alignUrl={ALIGN_SITE_URL} onQuickExit={quickExitAction} />
        <CoparentingBuilderReferral
          builderUrl={BUILDER_PATH}
          progress={ppStatus}
          onOpen={(e) => {
            e.preventDefault();
            openDoor("self");
            openPp("welcome");
          }}
        />
        <section
          data-testid="door-landing"
          className="rounded-2xl bg-white border border-slate-200 p-4 shadow-sm"
        >
          <div className="text-center space-y-1 pb-3">
            <div className="text-[0.625rem] uppercase font-bold tracking-wider text-purple-700">
              {greetingName ? `Welcome, ${greetingName}` : "Welcome"}
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              Pick your path
            </h1>
            <p className="text-xs text-slate-600">
              Two ways in. The Communication Builder works with either one.
            </p>
          </div>
          {doorButtons}
        </section>

        {welcomeArt}

        {goalBanner}
      </div>
    );
  }

  // Full-page overlays shared by Self Journey and the Court page.
  const journeyOverlays = (
    <>
      {/* Card 1 — full-page Self-Assessment. */}
      {assessOpen && (
        <SelfAssessmentView
          onClose={() => setAssessOpen(false)}
          parentName={greetingName}
          userId={user?.user_id}
          history={saHistory.history}
          startNew={assessStartNew}
          onCompleted={saHistory.addEntry}
          onEntryUpdate={saHistory.updateEntry}
          onGoalReached={saHistory.markReached}
          onQuickExit={quickExitAction}
          onOpenBiffCoach={onOpenBiffCoach}
          safetyFlag={safetyFlag}
          hidden={biffCoachOpen}
        />
      )}
      {ppOpen && (
        <ParallelParentingView
          onClose={() => setPpOpen(false)}
          onQuickExit={quickExitAction}
          safetyFlag={safetyFlag}
          hidden={overlayOpen || biffCoachOpen}
          initialScreen={ppScreen}
        />
      )}
      {cpAssessOpen && (
        <CoparentingAssessmentView
          userId={user?.user_id}
          onClose={() => setCpAssessOpen(false)}
          onQuickExit={quickExitAction}
          onOpenSelfAssessment={() => {
            setCpAssessOpen(false);
            openAssess(false);
          }}
          safetyFlag={safetyFlag}
        />
      )}
    </>
  );

  // -----------------------------------------------------------------
  // COURT ORDERED SUB-VIEW
  // -----------------------------------------------------------------
  if (view === "court") {
    return (
      <div data-testid="journey-shell">
        <CourtOrderedView
          onBack={goBack}
          onQuickExit={quickExitAction}
          courtKey={courtKey}
          mediator={verifiedMediator}
          onVerify={onVerifyCourtKey}
          onOpenCard={openCourtCard}
          fb={foundationBuilder}
          onOpenParallel={(screen) => openPp(screen)}
          onOpenChildNeeds={(k, jump) => openChildNeeds("court", k, jump)}
          assessDone={assessDone}
          ppDone={ppDone}
          onDownloadPdf={onDownloadCourtPdf}
          onOpenBiffHistory={() => onOpenCommBuilder("history")}
          alignUrl={ALIGN_SITE_URL}
          safetyFlag={safetyFlag}
          signedIn={!!user}
          hidden={overlayOpen || assessOpen || ppOpen || cpAssessOpen}
        />
        {journeyOverlays}
      </div>
    );
  }

  // -----------------------------------------------------------------
  // CHILD-NEEDS SUB-VIEW — iter269.
  // Reached from Card 3 inside Self Journey. Back returns to Self
  // Journey without clearing the door memory.
  // -----------------------------------------------------------------
  if (view === "child_needs") {
    return (
      <ChildNeedsView
        onBack={() => setView(subFrom)}
        onQuickExit={quickExitAction}
        safetyFlag={safetyFlag}
        needs={childNeeds}
        userId={user?.user_id}
        parentName={greetingName}
        initialOpenKey={childNeedsKey}
        initialJump={childNeedsJump}
      />
    );
  }

  // -----------------------------------------------------------------
  // FOUNDATION STATEMENT SUB-VIEW — iter270.
  // Reached from Card 4 inside Self Journey. Back returns to Self
  // Journey without clearing the door memory. Keeps `onOpenReport`
  // as a secondary path (the "Open full report" affordance lives
  // in the finale-rewards block in Self Journey).
  // -----------------------------------------------------------------
  if (view === "foundation") {
    const quickExitChip = (
      <button
        type="button"
        data-testid="door-quick-exit"
        onClick={quickExitAction}
        className="px-2.5 py-1 rounded-md text-[0.625rem] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition"
      >
        <i className="fa-solid fa-bolt mr-1"></i>
        Quick Exit
      </button>
    );
    return (
      <FoundationStatementView
        onBack={() => setView(subFrom)}
        backLabel={subFrom === "court" ? "Back to Court Page" : "Back to Self Journey"}
        startOpen={fbStartOpen}
        parentName={greetingName}
        QuickExit={quickExitChip}
        fb={foundationBuilder}
      />
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
          subtitle="Take the next step to build a safer, calmer, and more child-focused future."
        />
        {/* Same steps as the Journey page; each step opens here, in place. */}
        <JourneyFlow
          embedded
          alignUrl={ALIGN_SITE_URL}
          actions={{
            coparenting: () => setCpAssessOpen(true),
            parallelBuilder: () => openPp(0),
            childNeeds: () => openChildNeeds("self"),
            foundation: () => openFoundation("self"),
          }}
        />

        <GoalBanner
          testid="door-self-goal"
          goal={saHistory.currentGoal}
          setAt={saHistory.latest?.completed_at}
          practice={saHistory.practice}
          onPractise={saHistory.practise}
          dueDays={saHistory.dueDays}
          onOpen={() => openAssess(saHistory.dueDays > 0)}
        />
        <GoalReachedBanner history={saHistory.history} userId={user?.user_id} active={!(assessOpen || ppOpen || cpAssessOpen)} />


        {/* Accomplishments sit at the end, just before the badges. */}
        <div data-testid="door-self-progress" className="space-y-4">
          {allStepsDone && <AllStepsBanner sparkle={sparkle} defaultName={user?.name || ""} />}
          <AssessProgressRing done={assessDone} onOpen={openAssessKey} />
          <div className="flex flex-col sm:flex-row gap-2 [&>*]:flex-1">
            <JourneySummaryButton onClick={journeySummary.downloadPdf} downloading={journeySummary.downloading} />
            {user?.user_id && (
              <SendToProvider
                completedAt={childNeeds.state.completed_at}
                testid="door-self-send-provider"
                className="w-full py-2.5 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-[0.8125rem] font-bold transition-colors"
              />
            )}
          </div>
        </div>

        {/* Keep the finale rewards block (badges + partner invite).
            Only visible once the all-three finale is earned. */}
        {allThreeDone && (
          <div
            data-testid="door-self-finale-rewards"
            className="rounded-xl border border-purple-200 bg-purple-50/70 p-3 space-y-2"
          >
            <div className="text-[0.625rem] uppercase font-bold tracking-wider text-purple-700">
              Keep your momentum
            </div>
            <button
              type="button"
              data-testid="door-self-replay-celebration"
              onClick={replayCelebration}
              className="w-full text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-2 text-[0.6875rem] font-semibold text-purple-800 transition flex items-center gap-2"
            >
              <i className="fa-solid fa-wand-sparkles"></i>
              Replay celebration
              <span className="ml-auto text-[0.625rem] text-slate-500">
                Relive your reflection wins
              </span>
            </button>
            <button
              type="button"
              data-testid="door-self-share-badge"
              onClick={() => openBadgePreview("solo")}
              className="w-full text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-2.5 text-[0.6875rem] font-semibold text-purple-900 transition flex items-center gap-2"
            >
              <i className="fa-solid fa-award"></i>
              Save my Reflection Milestone badge
              <i className="fa-solid fa-arrow-down-to-line ml-auto text-slate-400 text-[0.625rem]"></i>
            </button>
            {pairBothDone && (
              <button
                type="button"
                data-testid="door-self-share-joint-badge"
                onClick={() => openBadgePreview("joint")}
                className="w-full text-left bg-white hover:bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2.5 text-[0.6875rem] font-semibold text-emerald-900 transition flex items-center gap-2"
              >
                <i className="fa-solid fa-award"></i>
                Save our Shared Reflection Milestone badge
                <i className="fa-solid fa-arrow-down-to-line ml-auto text-slate-400 text-[0.625rem]"></i>
              </button>
            )}
            {!safetyFlag && (
              <button
                type="button"
                data-testid="door-self-invite-partner"
                onClick={() => setInviteOpen(true)}
                className="w-full text-left bg-white hover:bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2.5 text-[0.6875rem] font-semibold text-emerald-900 transition flex items-center gap-2"
              >
                <i className="fa-solid fa-user-plus"></i>
                Invite the other parent
                <i className="fa-solid fa-arrow-right ml-auto text-slate-400 text-[0.625rem]"></i>
              </button>
            )}
          </div>
        )}

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


      {/* iter263 — Partner Invite Dialog. Wraps the existing
          `InviteCoparentCard`, which itself calls the backend
          `/api/invites/coparent` endpoint; that endpoint enforces
          the IPV safety gate so this is defence-in-depth. */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent
          data-testid="door-self-invite-dialog"
          className="max-w-md"
        >
          <DialogHeader>
            <DialogTitle>Invite the other parent</DialogTitle>
            <DialogDescription>
              Send a private invite so your co-parent can run their
              own reflections. Nothing of yours is shared without
              your explicit permission.
            </DialogDescription>
          </DialogHeader>
          <InviteCoparentCard variant="summary" />
        </DialogContent>
      </Dialog>

      {/* iter267 — Badge preview dialog. The parent sees the
          generated PNG before deciding to save. The Save button
          runs the share-sheet / download fallback used by the
          previous one-tap flow. */}
      <Dialog
        open={!!badgePreview}
        onOpenChange={(open) => {
          if (!open) closeBadgePreview();
        }}
      >
        <DialogContent
          data-testid="door-self-badge-preview-dialog"
          className="max-w-md"
        >
          <DialogHeader>
            <DialogTitle>
              {badgePreview?.kind === "joint"
                ? "Shared Reflection Milestone"
                : "Reflection Milestone"}
            </DialogTitle>
            <DialogDescription>
              {badgePreview?.kind === "joint"
                ? "Preview the badge both parents can keep. Tap Save to download or share."
                : "Preview your badge before saving. Tap Save to download or share."}
            </DialogDescription>
          </DialogHeader>
          {badgePreview && (
            <div className="space-y-3">
              <img
                data-testid="door-self-badge-preview-image"
                src={badgePreview.url}
                alt={
                  badgePreview.kind === "joint"
                    ? "Shared Reflection Milestone badge preview"
                    : "Reflection Milestone badge preview"
                }
                className="w-full rounded-xl border border-slate-200 shadow-sm"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  data-testid="door-self-badge-preview-cancel"
                  onClick={closeBadgePreview}
                  className="flex-1 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-sm font-semibold transition"
                >
                  Not yet
                </button>
                <button
                  type="button"
                  data-testid="door-self-badge-preview-save"
                  onClick={saveBadgeFromPreview}
                  className="flex-1 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-bold transition"
                >
                  <i className="fa-solid fa-arrow-down-to-line mr-1.5"></i>
                  Save badge
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <JourneyCelebration
        open={celebrating}
        onClose={() => setCelebrating(false)}
        onPdf={journeySummary.downloadPdf}
        downloading={journeySummary.downloading}
      />
      {journeyOverlays}
    </div>
  );
}
