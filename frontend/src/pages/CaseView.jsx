/**
 * `/case/:caseId` — Court-Ordered / Referred parent case view (iter196).
 *
 * When a parent enters an access code at `/join` or arrives via a
 * `/join/:token` invitation link, they land here. Unlike `/dashboard`
 * which shows every SA CoParents tool, this page shows ONLY the
 * assessments the professional assigned:
 *
 *   Required by Your Referral
 *     - Co-Parenting Assessment              [Start / Continue / ✓]
 *     - Educational Needs Assessment         [Start / Continue / ✓]
 *
 *   Additional SA CoParents Tools           (collapsed by default)
 *     - Journal · Mediation Prep · Resources
 *
 * The backend endpoint `GET /api/joint-alignment/case/:caseId` returns
 * a caller-scoped view — the co-parent's answers are NEVER exposed,
 * only their presence signals (name, status timestamps).
 */
import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Circle,
  Loader2,
  AlertTriangle,
  Briefcase,
  BookOpen,
  Newspaper,
  ChevronDown,
  Users,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

// Kept in sync with backend `_ASSESSMENT_LABELS` and the frontend
// JoinCode route map. Missing entry → falls back to the label the
// backend already provides on each step.
const ASSESSMENT_ROUTES = {
  "co-parenting":  "/special-needs-v2",
  communication:   "/communication",
  educational:     "/edu-deep",
  medical:         "/med-deep",
  psychological:   "/psych-deep",
  "special-needs": "/special-needs-v2",
};

const ADDITIONAL_TOOLS = [
  {
    key: "journal",
    label: "Journal",
    body: "Private co-parenting journal — never shared automatically.",
    route: "/journal",
    icon: Newspaper,
  },
  {
    key: "mediation-prep",
    label: "Mediation Preparation",
    body: "Child goals · Issues · Priority · Communication · Readiness.",
    route: "/dashboard#dashboard-step1-hero",
    icon: BookOpen,
  },
  {
    key: "resources",
    label: "Resources & Safety",
    body: "Texas crisis hotlines, safety plans, and coordinated-care resources.",
    route: "/safety",
    icon: ShieldCheck,
  },
];

export default function CaseView() {
  const { caseId } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!user || !caseId) return;
    api
      .get(`/joint-alignment/case/${encodeURIComponent(caseId)}`)
      .then((r) => setCaseData(r.data))
      .catch((e) => {
        logError("case-view fetch failed", e);
        const status = e?.response?.status ?? 0;
        if (status === 403) setErr("forbidden");
        else if (status === 404) setErr("not-found");
        else setErr("network");
      });
  }, [user, caseId]);

  if (loading) return null;

  if (err === "forbidden") {
    return (
      <ErrorState
        icon={AlertTriangle}
        title="This case isn't linked to your account"
        body="You may be signed in with a different email than the one your professional invited. Sign in with the email from your invitation, then try again."
        primary={{ label: "Go to my dashboard", to: "/dashboard" }}
        testid="case-view-forbidden"
      />
    );
  }

  if (err === "not-found") {
    return (
      <ErrorState
        icon={AlertTriangle}
        title="We couldn't find that case"
        body="The case may have expired, been cancelled, or you might have mistyped the code. Enter your access code again to try."
        primary={{ label: "Enter access code", to: "/join" }}
        testid="case-view-not-found"
      />
    );
  }

  if (err === "network") {
    return (
      <ErrorState
        icon={AlertTriangle}
        title="We couldn't reach the server"
        body="Please check your connection and try again in a moment."
        primary={{ label: "Retry", to: `/case/${caseId}` }}
        testid="case-view-network-error"
      />
    );
  }

  if (!caseData) {
    return (
      <AppShell>
        <div
          className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center"
          data-testid="case-view-loading"
        >
          <Loader2 size={24} className="text-[#3D1A78] mx-auto animate-spin" />
          <p className="text-sm text-[#4B4567] mt-3">
            Loading your case…
          </p>
        </div>
      </AppShell>
    );
  }

  const me = caseData.me || {};
  const steps = me.steps || [];
  const requiredSteps = steps.filter((s) => s.required);
  const optionalSteps = steps.filter((s) => !s.required);
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const totalCount = steps.length;
  const coparent = (caseData.parents || []).find(
    (p) => (p.email || "").toLowerCase() !== (me.email || "").toLowerCase(),
  );

  const goToStep = (step) => {
    const route = ASSESSMENT_ROUTES[step.assessment_type] || "/dashboard";
    navigate(route);
  };

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12"
        data-testid="case-view-page"
      >
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#3D1A78] mb-6"
          data-testid="case-view-back"
        >
          <ArrowLeft size={14} />
          Back to dashboard
        </Link>

        {/* Case summary header. */}
        <div
          className="rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-8 shadow-sm"
          data-testid="case-view-summary"
        >
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Your Case
          </div>
          <div className="mt-2 flex items-baseline gap-3 flex-wrap">
            <h1
              className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight"
              data-testid="case-view-headline"
            >
              Case {caseData.case_id}
            </h1>
            <span
              className="inline-flex items-center gap-1 rounded-full bg-[#EFE9F9] text-[#3D1A78] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.16em] font-bold"
              data-testid="case-view-status"
            >
              {(caseData.status || "pending").replaceAll("_", " ")}
            </span>
          </div>
          <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">
            <strong>Referred by:</strong>{" "}
            <span data-testid="case-view-professional-name">
              {caseData.professional?.name || "your professional"}
            </span>
          </p>
          {coparent && (
            <p className="text-sm text-[#4B4567] mt-1 leading-relaxed flex items-center gap-1.5">
              <Users size={14} className="text-[#3D1A78]" />
              <span>
                Assigned to you and{" "}
                <strong data-testid="case-view-coparent-name">
                  {coparent.name || coparent.email || "the other parent"}
                </strong>{" "}
                · your answers stay private.
              </span>
            </p>
          )}
          <p className="text-sm text-[#4B4567] mt-3">
            <strong>Your progress:</strong>{" "}
            <span data-testid="case-view-progress">
              {completedCount} of {totalCount} steps completed
            </span>
          </p>
        </div>

        {/* Required steps — the meat of the page. */}
        <section
          className="mt-8"
          data-testid="case-view-required-section"
        >
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#B45F13]">
            Required by Your Referral
          </div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1">
            Your Required Steps
          </h2>
          <p className="text-sm text-[#4B4567] mt-2">
            These are the assessments your professional assigned. Complete
            them at your own pace — your answers stay private until you
            explicitly share.
          </p>
          <ol
            className="mt-5 space-y-3"
            data-testid="case-view-required-steps"
          >
            {requiredSteps.map((step, idx) => (
              <StepRow
                key={step.assessment_type}
                step={step}
                index={idx + 1}
                onStart={() => goToStep(step)}
              />
            ))}
          </ol>
        </section>

        {/* Optional / additional steps assigned to the case. */}
        {optionalSteps.length > 0 && (
          <section
            className="mt-8"
            data-testid="case-view-optional-section"
          >
            <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#0E7A7A]">
              Optional — Recommended by Your Professional
            </div>
            <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight mt-1">
              Nice-to-Complete Steps
            </h2>
            <ol
              className="mt-4 space-y-3"
              data-testid="case-view-optional-steps"
            >
              {optionalSteps.map((step, idx) => (
                <StepRow
                  key={step.assessment_type}
                  step={step}
                  index={idx + 1}
                  optional
                  onStart={() => goToStep(step)}
                />
              ))}
            </ol>
          </section>
        )}

        {/* Additional SA CoParents tools — collapsed by default. */}
        <details
          className="mt-8 group"
          data-testid="case-view-additional-tools"
        >
          <summary
            className="cursor-pointer list-none rounded-2xl border border-[#E5E0EE] bg-white px-5 py-4 flex items-center justify-between hover:border-[#3D1A78] transition-colors"
            data-testid="case-view-additional-tools-summary"
          >
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                Additional SA CoParents Tools
              </div>
              <div className="text-sm text-[#4B4567] mt-0.5">
                Journal, mediation prep, resources — outside your court
                referral but available if useful.
              </div>
            </div>
            <ChevronDown
              size={18}
              className="text-[#3D1A78] group-open:rotate-180 transition-transform"
            />
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            {ADDITIONAL_TOOLS.map((tool) => (
              <AdditionalToolTile key={tool.key} tool={tool} />
            ))}
          </div>
        </details>
      </div>
    </AppShell>
  );
}

function StepRow({ step, index, optional = false, onStart }) {
  const isDone = step.status === "completed";
  const isInProgress = step.status === "in_progress";
  const border = isDone
    ? "border-[#B7DEC6] bg-[#E1F3E8]"
    : optional
    ? "border-[#B7E0E0] bg-white"
    : "border-[#F1D9B7] bg-white";
  const iconColor = isDone ? "text-[#186142]" : "text-[#B45F13]";
  const StatusIcon = isDone ? CheckCircle2 : Circle;
  const cta = isDone
    ? "View my report"
    : isInProgress
    ? "Continue"
    : "Start assessment";
  return (
    <li
      className={`rounded-2xl border ${border} p-5 flex items-start justify-between gap-4 flex-wrap`}
      data-testid={`case-view-step-${step.assessment_type}`}
    >
      <div className="flex items-start gap-3 flex-1 min-w-0">
        <StatusIcon size={22} className={`flex-shrink-0 mt-0.5 ${iconColor}`} />
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
            Step {index}
          </div>
          <div
            className="font-serif text-lg text-[#1A1330] leading-tight mt-1"
            data-testid={`case-view-step-${step.assessment_type}-label`}
          >
            {step.label}
          </div>
          <div className="text-[13px] text-[#4B4567] mt-1">
            Status:{" "}
            <strong
              className={
                isDone ? "text-[#186142]" : isInProgress ? "text-[#B45F13]" : "text-[#3D1A78]"
              }
              data-testid={`case-view-step-${step.assessment_type}-status`}
            >
              {isDone ? "Completed" : isInProgress ? "In progress" : "Not started"}
            </strong>
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={onStart}
        data-testid={`case-view-step-${step.assessment_type}-cta`}
        className={`shrink-0 inline-flex items-center gap-1.5 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors ${
          isDone
            ? "border border-[#186142] text-[#186142] hover:bg-white"
            : "bg-[#3D1A78] text-white hover:bg-[#2A0F5F]"
        }`}
      >
        {cta}
        <ArrowRight size={14} />
      </button>
    </li>
  );
}

function AdditionalToolTile({ tool }) {
  const Icon = tool.icon;
  return (
    <Link
      to={tool.route}
      data-testid={`case-view-tool-${tool.key}`}
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-sm transition flex flex-col"
    >
      <div className="w-10 h-10 rounded-full bg-[#EFE9F9] text-[#3D1A78] grid place-items-center mb-3">
        <Icon size={18} strokeWidth={2.2} />
      </div>
      <div className="font-serif text-lg text-[#1A1330] leading-tight">
        {tool.label}
      </div>
      <p className="text-[12px] text-[#4B4567] mt-1 leading-snug flex-1">
        {tool.body}
      </p>
      <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78]">
        Open <ArrowRight size={12} />
      </span>
    </Link>
  );
}

function ErrorState({ icon: Icon, title, body, primary, testid }) {
  return (
    <AppShell>
      <div
        className="max-w-2xl mx-auto px-4 sm:px-6 py-12"
        data-testid={testid}
      >
        <div className="rounded-3xl bg-white border border-[#E5E0EE] p-8 text-center">
          <div className="w-14 h-14 mx-auto rounded-full bg-[#FFEEDA] grid place-items-center text-[#B45F13]">
            <Icon size={22} />
          </div>
          <h1 className="font-serif text-2xl text-[#1A1330] mt-4 leading-tight">
            {title}
          </h1>
          <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">
            {body}
          </p>
          {primary && (
            <Link
              to={primary.to}
              className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-5 py-2.5 text-sm font-semibold"
              data-testid={`${testid}-primary`}
            >
              <Briefcase size={14} />
              {primary.label}
            </Link>
          )}
        </div>
      </div>
    </AppShell>
  );
}
