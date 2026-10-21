import React, { useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import ParentDashboard, { buildSteps } from "../../../components/parentDashboard/ParentDashboard";
import { useCaseSettings } from "../../../lib/useCaseSettings";
import { useDashboardData } from "./useDashboardData";
import { useDashboardCelebrations } from "./useDashboardCelebrations";
import { WeeklyWinNote } from "./WeeklyWinNote";

const PATH_PROP = { court_ordered: "court", self_journey: "self", mediation_prep: "mediation" };
// Dashboard step -> court-code "requested" key. Only the Self-Assessment is requestable.
const REQUESTED_KEY = { selfAssessment: "self" };
const IMAGES = {
  selfAssessment: "/images/sa-self-assessment-640.webp",
  communication: "/images/comm-builder-art-640.webp",
  courtChecklist: "/images/court-journey-640.webp",
};
const OPEN = {
  self: "/dashboard?open=self-assessment",
  comm: "/dashboard?open=comm-builder",
  court: "/dashboard?open=court",
};

const hasDraft = (d) => !!d && (d.started || Object.keys(d.answers || {}).length > 0);

function stepStatus({ checkinDone, saHistory, data, biffCount }) {
  const prepAny = Object.values(data.prep?.completed || {}).some(Boolean);
  const c = data.checklist;
  return {
    prepAny,
    status: {
      checkin: checkinDone ? "done" : "unknown",
      selfAssessment: saHistory.history.length ? "done" : hasDraft(data.draft) ? "in_progress" : "todo",
      communication: biffCount > 0 ? "done" : "todo",
      order: data.agreements.length ? "done" : prepAny ? "in_progress" : "todo",
      courtChecklist: c?.total && c.done >= c.total ? "done" : c?.done > 0 ? "in_progress" : "todo",
    },
  };
}

const burst = () => {
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  try {
    confetti({ particleCount: 60, spread: 70, startVelocity: 35, origin: { x: 0.5, y: 0.75 }, colors: ["#7c3aed", "#2563eb", "#10b981", "#f59e0b"], ticks: 150, scalar: 0.9 });
  } catch {
    /* best-effort */
  }
};

// Parent home: wires ParentDashboard to real step status, links, celebrations and the weekly note.
export function ParentHome({ user, saHistory, biffCount, biffReady, actions, builderPath, top, afterSteps }) {
  const navigate = useNavigate();
  const path = PATH_PROP[user?.journey_path] || null;
  const data = useDashboardData(user?.user_id, path === "court");
  const checkinDone = useCaseSettings()?.setup_complete === true;
  const celebrations = useDashboardCelebrations(user?.user_id);
  const { status, prepAny } = stepStatus({ checkinDone, saHistory, data, biffCount });

  const links = useMemo(
    () => ({
      checkin: "/start-with-safety",
      selfAssessment: OPEN.self,
      communication: OPEN.comm,
      order: prepAny ? "/summary" : "/prep/child-goals",
      courtChecklist: OPEN.court,
      whoCanSee: "/who-can-see-my-information",
      privacy: "/privacy-notice",
      getHelp: "/help",
    }),
    [prepAny]
  );
  const steps = buildSteps(path, status, links);
  const requested = new Set([...(data.requested?.keys || []), ...(data.requested?.professional_keys || [])]);
  const open = steps.filter((s) => s.id !== "checkin" && s.status !== "done");
  const nextId = (open.find((s) => requested.has(REQUESTED_KEY[s.id])) || open[0])?.id || null;

  const ready = !!user && data.ready && data.ok && saHistory.loaded && biffReady && celebrations.steps !== undefined;
  const doneKeys = steps.filter((s) => s.id !== "checkin" && s.status === "done").map((s) => s.id);
  const handled = useRef(null);
  useEffect(() => {
    const sig = doneKeys.join(",");
    if (!ready || handled.current === sig) return;
    handled.current = sig;
    if (celebrations.steps === null) {
      celebrations.record(doneKeys, true);
      return;
    }
    const fresh = doneKeys.filter((k) => !celebrations.steps[k]);
    if (!fresh.length) return;
    burst();
    toast.success("Step done", { description: steps.filter((s) => fresh.includes(s.id)).map((s) => s.title).join(", ") });
    celebrations.record(fresh, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, doneKeys.join(",")]);

  const onNavigate = (href) => {
    const action = { [OPEN.self]: actions.openSelfAssessment, [OPEN.comm]: actions.openCommBuilder, [OPEN.court]: actions.openCourt, [builderPath]: actions.openBuilder }[href];
    if (action) action();
    else navigate(href);
  };

  return (
    <div className="-mx-4 -mt-4">
      <ParentDashboard
        parentName={user?.name ? user.name.split(" ")[0] : null}
        path={path}
        status={status}
        links={links}
        onNavigate={onNavigate}
        images={IMAGES}
        nextId={nextId}
        extras={{ order: { label: "Parallel Parenting Option Builder", href: builderPath } }}
        top={<div className="pd-top-slot">{top}</div>}
        belowNext={<WeeklyWinNote steps={steps} celebrated={celebrations.steps} />}
        afterSteps={afterSteps}
      />
    </div>
  );
}
