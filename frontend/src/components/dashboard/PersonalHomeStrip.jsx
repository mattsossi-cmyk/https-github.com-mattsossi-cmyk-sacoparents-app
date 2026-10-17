/**
 * PersonalHomeStrip — the "just for you" strip that lives on the Dashboard
 * right below the Four-Circle Front Door.
 *
 * Founder ask (2026-03-04): the signed-in home should feel like a guided
 * assistant, not an assessment library. This component pulls the three
 * things a returning parent cares about into one calm strip:
 *
 *   1. Continue where I left off — the most recent in-progress prep item
 *   2. My statements — deep-link to the Foundation / Mediation Statements
 *   3. Joint-report invitations — a compact badge when a professional-
 *      driven Joint Alignment case is waiting for the parent
 *
 * Never renders as an empty scaffold — if there is nothing to surface, the
 * strip renders nothing. Silent by default so a fresh account doesn't see
 * a "Continue: —" box.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  FileText,
  MailCheck,
  Play,
  Sparkles,
} from "lucide-react";
import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

const RESUME_META = {
  snc2: {
    label: "Special Needs assessment",
    to: "/special-needs-v2",
    icon: Play,
  },
  edu_deep: {
    label: "Educational Deep Dive",
    to: "/edu-deep",
    icon: Play,
  },
  med_deep: {
    label: "Medical Deep Dive",
    to: "/med-deep",
    icon: Play,
  },
  psych_deep: {
    label: "Psychological Deep Dive",
    to: "/psych-deep",
    icon: Play,
  },
  communication: {
    label: "Communication reflection",
    to: "/communication",
    icon: Play,
  },
};

function pickResume(sources) {
  // sources: [{key, updated_at, complete}]
  const eligible = sources.filter((s) => s && s.updated_at && !s.complete);
  if (eligible.length === 0) return null;
  eligible.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  return eligible[0];
}

export default function PersonalHomeStrip() {
  const [resume, setResume] = useState(null);
  const [foundationDone, setFoundationDone] = useState(false);
  const [alignmentWaiting, setAlignmentWaiting] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [snc, foundation, jam, comm] = await Promise.all([
        api.get("/snc2/me").catch(() => null),
        api.get("/mediation/reflection").catch(() => null),
        api.get("/joint-alignment/mine").catch(() => null),
        api.get("/communication-reflection/mine").catch(() => null),
      ]);
      if (cancelled) return;

      const sources = [];
      const sncDoc = snc?.data;
      if (sncDoc?.exists) {
        sources.push({
          key: "snc2",
          updated_at: sncDoc.updated_at || sncDoc.created_at,
          complete: !!sncDoc.completed_at,
        });
      }
      const commDoc = comm?.data;
      if (commDoc?.updated_at && commDoc?.score?.answered_count > 0 && commDoc.score.answered_count < 12) {
        sources.push({
          key: "communication",
          updated_at: commDoc.updated_at,
          complete: false,
        });
      }

      setResume(pickResume(sources));
      const foundationDoc = foundation?.data || {};
      const anyPromptFilled = Object.values(foundationDoc?.reflection || {}).some(
        (v) => typeof v === "string" && v.trim().length > 20,
      );
      setFoundationDone(anyPromptFilled);

      const cases = jam?.data?.cases || [];
      const waiting = cases.filter(
        (c) => c.my_status === "invited" || c.my_status === "in_progress",
      ).length;
      setAlignmentWaiting(waiting);
      setLoaded(true);
    })().catch((e) => logError("personal-home-strip", e));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loaded) return null;

  const hasResume = !!resume;
  const hasStatements = foundationDone;
  const hasJoint = alignmentWaiting > 0;

  if (!hasResume && !hasStatements && !hasJoint) return null;

  return (
    <section
      className="mt-4 rounded-3xl border border-[#E5E0EE] bg-white p-4 sm:p-6 shadow-sm"
      data-testid="personal-home-strip"
    >
      <div className="text-[0.6875rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-3">
        Just for you
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {hasResume && (
          <ResumeTile resume={resume} />
        )}
        {hasStatements && (
          <QuickTile
            testid="personal-home-my-statements"
            to="/my-plan"
            icon={FileText}
            label="My Statements"
            hint="Foundation, Mediation Statement & Prep"
            tone="purple"
          />
        )}
        {hasJoint && (
          <QuickTile
            testid="personal-home-joint-invitations"
            to="/dashboard#joint-alignment-requests"
            icon={MailCheck}
            label={`${alignmentWaiting} Joint-report invitation${alignmentWaiting > 1 ? "s" : ""}`}
            hint="Your professional is waiting"
            tone="teal"
          />
        )}
      </div>
    </section>
  );
}

function ResumeTile({ resume }) {
  const meta = RESUME_META[resume.key];
  if (!meta) return null;
  const Icon = meta.icon;
  return (
    <Link
      to={meta.to}
      data-testid="personal-home-continue-tile"
      className="group flex items-start gap-3 rounded-2xl border-2 border-[#3D1A78]/30 bg-gradient-to-br from-[#F4EFFC] to-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all"
    >
      <div className="w-10 h-10 rounded-full bg-[#3D1A78] text-white grid place-items-center shrink-0">
        <Icon size={16} strokeWidth={2.2} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
          Continue where you left off
        </div>
        <div className="font-serif text-base text-[#1A1330] leading-tight mt-0.5">
          {meta.label}
        </div>
        <div className="text-[0.6875rem] text-[#4B4567] mt-1 inline-flex items-center gap-1">
          Pick up from your last answer <ArrowRight size={11} className="group-hover:translate-x-0.5 transition" />
        </div>
      </div>
    </Link>
  );
}

function QuickTile({ testid, to, icon: Icon, label, hint, tone }) {
  const tones = {
    purple: "border-[#E5E0EE] hover:border-[#3D1A78] text-[#3D1A78]",
    teal: "border-[#CDE9E4] hover:border-[#1E7A55] text-[#1E7A55]",
  };
  return (
    <Link
      to={to}
      data-testid={testid}
      className={`group flex items-start gap-3 rounded-2xl border bg-white p-4 hover:shadow-md transition-all ${tones[tone]}`}
    >
      <div className="w-10 h-10 rounded-full bg-white text-current grid place-items-center shrink-0 border">
        <Icon size={16} strokeWidth={2.2} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-current">
          <Sparkles size={9} className="inline mr-1" />
          For you
        </div>
        <div className="font-serif text-base text-[#1A1330] leading-tight mt-0.5">
          {label}
        </div>
        <div className="text-[0.6875rem] text-[#4B4567] mt-1 inline-flex items-center gap-1">
          {hint} <ArrowRight size={11} className="group-hover:translate-x-0.5 transition" />
        </div>
      </div>
    </Link>
  );
}
