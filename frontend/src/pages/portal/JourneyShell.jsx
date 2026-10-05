import React, { useMemo, useState } from "react";

import { GreyRockToggleChip } from "./AlignmentHub";

/**
 * JourneyShell — iter258 three-tab dashboard.
 *
 * Replaces the previous two-tile layout with a dashboard that
 * mirrors the founder's Flow-1/3-tab mockup:
 *   • Welcome banner with a progress bar
 *   • Mode toggle (Self-Guided ↔ Court-Ordered) + Privacy Check +
 *     Quick Exit in a controls strip
 *   • Persistent Safety-First strip (Safety First button always
 *     visible; Grey-Rock chip only when the parent is flagged)
 *   • Three top-level tabs:
 *       1. Reflect & Assess (Help-me-choose + three primary modules
 *          + Child-focused deep-dives)
 *       2. Foundation Report (summary + "Open full report" CTA)
 *       3. AI Coach & Tools (BIFF Communication Builder with growth
 *          record and the "?" BIFF explainer + Bill-Eddy book link)
 *
 * Rule preserved from NORTH_STAR.md: the auto-opened SA CoParents
 * Guide chatbot is rendered by the parent and is untouched here.
 */

const PRIMARY_MODULES = [
  {
    key: "foundation",
    title: "1. Child Needs & Priorities",
    body: "Focus on routines, school, and emotional security — the basis of your Foundation Statement.",
    topic: "foundation",
  },
  {
    key: "coparenting",
    title: "2. Co-Parenting Dynamics",
    body: "Identify communication styles and decision-making preferences across 40 questions.",
    topic: "coparenting",
  },
  {
    key: "safety",
    title: "3. Conflict Readiness & Goals",
    body: "Prepare actionable guidelines for resolving future disagreements and spotting safety concerns.",
    topic: "safety",
  },
];

const DEEP_DIVES = [
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
];

const BIFF_INFO = {
  title: "What's a BIFF rewrite?",
  body: "BIFF stands for Brief, Informative, Friendly, and Firm — a research-backed way to answer a hot message without matching its heat. You keep the facts, drop the drama, and leave less room for a fight.",
};

const STATUS_META = {
  completed: {
    label: "Completed",
    chip: "bg-emerald-100 text-emerald-800 border-emerald-200",
    ring: "border-emerald-200 bg-emerald-50/60",
    cta: "bg-emerald-600 hover:bg-emerald-700",
    ctaLabel: "Review responses",
  },
  in_progress: {
    label: "In progress",
    chip: "bg-blue-100 text-blue-800 border-blue-200",
    ring: "border-blue-300 bg-blue-50/40",
    cta: "bg-blue-600 hover:bg-blue-700",
    ctaLabel: "Continue",
  },
  not_yet: {
    label: "Not started",
    chip: "bg-slate-100 text-slate-700 border-slate-200",
    ring: "border-slate-200 bg-white",
    cta: "bg-slate-800 hover:bg-slate-900",
    ctaLabel: "Start",
  },
};

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
  const safetyFlag = safetyFlagged || !!(safetyAck && safetyAck.flagged);

  const [activeTab, setActiveTab] = useState("reflect");
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [helpStage, setHelpStage] = useState(null);
  const [biffInfoOpen, setBiffInfoOpen] = useState(false);

  const biffBookUrl = process.env.REACT_APP_BIFF_BOOK_URL || "";
  const biffBookTitle =
    process.env.REACT_APP_BIFF_BOOK_TITLE || "the BIFF book";
  const biffBookAuthor = process.env.REACT_APP_BIFF_BOOK_AUTHOR || "";

  const greetingName = user?.name ? user.name.split(" ")[0] : null;
  const isCourtMode = !!courtKey;

  // Overall progress — share of the three primary modules that are
  // "completed." Keeps the counting simple and visible.
  const progressPct = useMemo(() => {
    const done = PRIMARY_MODULES.filter(
      (m) => progressByTopic?.[m.topic] === "completed"
    ).length;
    return Math.round((done / PRIMARY_MODULES.length) * 100);
  }, [progressByTopic]);

  const quickExit = () => {
    // Low-friction DV pattern: open a neutral weather page in the
    // same tab so a parent in distress can hide the app instantly.
    try {
      window.location.replace("https://www.weather.com/");
    } catch {
      // best-effort — nothing else to do if replace fails.
    }
  };

  return (
    <div data-testid="journey-shell" className="space-y-4">
      {/* Welcome banner */}
      <section
        data-testid="dashboard-banner"
        className="rounded-2xl p-4 bg-gradient-to-r from-slate-900 to-blue-950 text-white shadow-sm"
      >
        <div className="flex flex-col gap-3">
          <div>
            <div className="text-[10px] uppercase font-bold tracking-wider text-blue-300">
              Welcome{greetingName ? `, ${greetingName}` : ""}
            </div>
            <h2 className="text-base font-bold leading-tight">
              {isCourtMode
                ? "Complete your court-ordered steps."
                : "Complete your reflection steps to build your Foundation Statement."}
            </h2>
          </div>
          <div
            data-testid="dashboard-progress"
            className="bg-slate-800/70 rounded-xl p-3 border border-slate-700"
          >
            <div className="flex justify-between text-[11px] font-medium mb-1.5">
              <span className="text-slate-300">Overall completion</span>
              <span className="text-blue-300" data-testid="dashboard-progress-pct">
                {progressPct}%
              </span>
            </div>
            <div className="w-full bg-slate-700/60 rounded-full h-2">
              <div
                className="bg-blue-400 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Controls strip: mode toggle, privacy, quick exit */}
      <section
        data-testid="dashboard-controls"
        className="flex items-center gap-2 flex-wrap"
      >
        <button
          type="button"
          data-testid="dashboard-mode-toggle"
          onClick={onEnterCourt}
          className={`px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${
            isCourtMode
              ? "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
              : "bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100"
          }`}
        >
          <i
            className={`fa-solid ${
              isCourtMode ? "fa-gavel" : "fa-user"
            } mr-1`}
          ></i>
          {isCourtMode ? "Court-Ordered Mode" : "Self-Guided Mode"}
        </button>
        <button
          type="button"
          data-testid="dashboard-privacy-btn"
          onClick={() => setPrivacyOpen((v) => !v)}
          aria-expanded={privacyOpen}
          className="px-3 py-1.5 rounded-full text-[11px] font-semibold border border-indigo-200 bg-indigo-50 text-indigo-800 hover:bg-indigo-100 transition"
        >
          <i className="fa-solid fa-user-shield mr-1"></i>
          Privacy
        </button>
        <div className="flex-1" />
        <button
          type="button"
          data-testid="dashboard-quick-exit"
          onClick={quickExit}
          className="px-3 py-1.5 rounded-md text-[11px] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition"
        >
          <i className="fa-solid fa-bolt mr-1"></i>
          Quick Exit
        </button>
      </section>

      {privacyOpen && (
        <div
          data-testid="dashboard-privacy-card"
          className="rounded-xl bg-indigo-50 border border-indigo-200 p-3 text-[12px] text-indigo-950 leading-snug space-y-2"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="font-bold text-indigo-900">
              What stays on your device
            </div>
            <button
              type="button"
              data-testid="dashboard-privacy-close"
              onClick={() => setPrivacyOpen(false)}
              aria-label="Close explainer"
              className="shrink-0 w-5 h-5 rounded-full bg-white hover:bg-indigo-100 text-indigo-700 text-[10px] font-bold flex items-center justify-center"
            >
              <i className="fa-solid fa-xmark"></i>
            </button>
          </div>
          <ul className="list-disc pl-4 space-y-1">
            <li>
              Your drafts, answers, and BIFF rewrites live in this
              browser first (local storage).
            </li>
            <li>
              A private copy syncs to your account so you can pick
              back up on another device.
            </li>
            <li>
              Nothing is shared with a mediator, court, or anyone
              else unless you tap <span className="font-semibold">Share</span>{" "}
              on a specific report.
            </li>
            <li>
              Grey-rock mode and your Safety-First answers are stored
              privately — never shown to the other parent.
            </li>
          </ul>
        </div>
      )}

      {/* Court-ordered verified banner (shown above tabs, if any) */}
      {courtKey && (
        <div
          data-testid="dashboard-court-banner"
          className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-[11px] text-emerald-900 leading-snug flex items-start gap-2"
        >
          <i className="fa-solid fa-gavel text-emerald-600 mt-0.5"></i>
          <div>
            <span className="font-semibold">Court access verified:</span>{" "}
            Case {courtKey}
            {verifiedMediator ? ` · ${verifiedMediator}` : ""}. Your
            assessment feeds the mediator's joint report.
          </div>
        </div>
      )}

      {/* Persistent safety strip — Safety First always available,
          Grey-Rock chip only when flagged. */}
      <section data-testid="dashboard-safety-strip" className="space-y-2">
        <button
          type="button"
          data-testid="dashboard-safety-first"
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
      </section>

      {/* Tab bar */}
      <nav
        data-testid="dashboard-tabs"
        className="bg-white rounded-xl border border-slate-200 flex overflow-x-auto"
      >
        {[
          { key: "reflect", label: "1. Reflect & Assess", icon: "fa-list-check" },
          { key: "report", label: "2. Foundation Report", icon: "fa-file-lines" },
          { key: "coach", label: "3. AI Coach & Tools", icon: "fa-comments" },
        ].map((t) => {
          const isActive = activeTab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              data-testid={`dashboard-tab-${t.key}`}
              onClick={() => setActiveTab(t.key)}
              className={`flex-1 min-w-[7rem] px-3 py-2.5 text-[11px] font-semibold whitespace-nowrap flex items-center justify-center gap-1.5 border-b-2 transition ${
                isActive
                  ? "border-blue-600 text-blue-700 bg-blue-50/60"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <i className={`fa-solid ${t.icon}`}></i>
              <span>{t.label}</span>
            </button>
          );
        })}
      </nav>

      {/* -------------------------------------------------------- */}
      {/* TAB 1 — REFLECT & ASSESS                                  */}
      {/* -------------------------------------------------------- */}
      {activeTab === "reflect" && (
        <section
          data-testid="dashboard-view-reflect"
          className="space-y-3"
        >
          {/* Not sure? Chat with the Guide */}
          <button
            type="button"
            data-testid="dashboard-open-intro-guide"
            onClick={onOpenIntroGuide}
            className="w-full py-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-xs transition"
          >
            <i className="fa-solid fa-comment-dots mr-1.5"></i>
            Not sure where to start? Chat with the Guide
          </button>

          {/* Help-me-choose chip */}
          <button
            type="button"
            data-testid="dashboard-cta-help"
            onClick={() =>
              setHelpStage((s) => (s === null ? "main" : null))
            }
            aria-expanded={helpStage !== null}
            className="w-full p-2.5 rounded-xl bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 text-left transition flex items-center gap-2"
          >
            <i className="fa-solid fa-circle-question"></i>
            <span className="text-sm font-bold flex-1">
              Help me choose where to start
            </span>
            <i
              className={`fa-solid ${
                helpStage !== null ? "fa-chevron-up" : "fa-chevron-down"
              } text-xs opacity-70`}
            ></i>
          </button>
          {helpStage !== null && (
            <div
              data-testid="dashboard-help-card"
              className="rounded-xl bg-purple-50 border border-purple-200 p-3 text-[12px] text-slate-800 leading-snug space-y-2"
            >
              <div className="font-bold text-purple-900">
                {helpStage === "child"
                  ? "Which area of your child's life?"
                  : "What brings you here today?"}
              </div>
              {helpStage === "main" && (
                <div className="grid grid-cols-1 gap-2">
                  <button
                    type="button"
                    data-testid="help-choice-coparenting"
                    onClick={() => {
                      setHelpStage(null);
                      onOpenGuidedJourney("coparenting");
                    }}
                    className="text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg p-2.5"
                  >
                    <div className="font-semibold text-purple-900">
                      Improve our co-parenting
                    </div>
                    <div className="text-[11px] text-slate-600">
                      Understand how we're doing as co-parents.
                    </div>
                  </button>
                  <button
                    type="button"
                    data-testid="help-choice-communication"
                    onClick={() => {
                      setHelpStage(null);
                      setActiveTab("coach");
                    }}
                    className="text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg p-2.5"
                  >
                    <div className="font-semibold text-purple-900">
                      Help with communication
                    </div>
                    <div className="text-[11px] text-slate-600">
                      Prepare a message or conversation.
                    </div>
                  </button>
                  <button
                    type="button"
                    data-testid="help-choice-child"
                    onClick={() => setHelpStage("child")}
                    className="text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg p-2.5"
                  >
                    <div className="font-semibold text-purple-900">
                      Focus on my child's needs
                    </div>
                    <div className="text-[11px] text-slate-600">
                      Educational, medical, or psychological.
                    </div>
                  </button>
                  <button
                    type="button"
                    data-testid="help-choice-referral"
                    onClick={() => {
                      setHelpStage(null);
                      onEnterCourt();
                    }}
                    className="text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg p-2.5"
                  >
                    <div className="font-semibold text-purple-900">
                      I was sent here
                    </div>
                    <div className="text-[11px] text-slate-600">
                      A court, mediator or attorney referred me.
                    </div>
                  </button>
                </div>
              )}
              {helpStage === "child" && (
                <div className="grid grid-cols-1 gap-2">
                  {DEEP_DIVES.map((d) => (
                    <button
                      key={d.key}
                      type="button"
                      data-testid={`help-choice-child-${d.key}`}
                      onClick={() => {
                        setHelpStage(null);
                        onOpenGuidedJourney(d.key);
                      }}
                      className="text-left bg-white hover:bg-purple-100 border border-purple-200 rounded-lg p-2.5"
                    >
                      <div className="font-semibold text-purple-900">
                        <i className={`fa-solid ${d.icon} mr-1.5`}></i>
                        {d.label}
                      </div>
                    </button>
                  ))}
                  <button
                    type="button"
                    data-testid="help-choice-child-back"
                    onClick={() => setHelpStage("main")}
                    className="text-left text-[11px] text-purple-700 hover:text-purple-900 px-2 pt-1"
                  >
                    <i className="fa-solid fa-arrow-left mr-1"></i>
                    Back
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Reflection Roadmap card */}
          <div className="bg-white rounded-xl p-3 border border-slate-200 shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-bold text-slate-900">
                Your reflection roadmap
              </h3>
              <span
                data-testid="dashboard-roadmap-badge"
                className="text-[10px] font-semibold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200"
              >
                {progressPct}% complete
              </span>
            </div>
            <div className="grid gap-2.5">
              {PRIMARY_MODULES.map((m) => {
                const status = progressByTopic?.[m.topic] || "not_yet";
                const meta = STATUS_META[status];
                return (
                  <div
                    key={m.key}
                    data-testid={`dashboard-module-${m.key}`}
                    data-status={status}
                    className={`p-3 rounded-lg border ${meta.ring}`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span
                        className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${meta.chip}`}
                      >
                        {meta.label}
                      </span>
                      {status === "completed" && (
                        <i className="fa-solid fa-check text-emerald-600"></i>
                      )}
                    </div>
                    <div className="text-sm font-bold text-slate-900 leading-tight">
                      {m.title}
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                      {m.body}
                    </p>
                    <button
                      type="button"
                      data-testid={`dashboard-module-${m.key}-cta`}
                      onClick={() =>
                        m.topic === "safety"
                          ? onOpenSafety()
                          : onOpenGuidedJourney(m.topic)
                      }
                      className={`mt-2.5 w-full py-2 ${meta.cta} text-white rounded-md text-xs font-bold transition`}
                    >
                      {meta.ctaLabel}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 40-Q interactive preview — kept accessible on Tab 1 */}
          <a
            href={selfAssessmentUrl}
            target="_blank"
            rel="noreferrer"
            data-testid="dashboard-preview-link"
            className="block w-full p-2.5 rounded-xl bg-white hover:bg-indigo-50 border border-indigo-300 text-indigo-800 text-left transition text-sm font-bold"
          >
            <i className="fa-solid fa-wand-magic-sparkles mr-1.5"></i>
            Try the 40-question interactive preview
          </a>

          {/* Deep-dive secondary row */}
          <div data-testid="dashboard-deepdives" className="pt-1">
            <div className="text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1.5 px-1">
              Child-focused deep dives
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {DEEP_DIVES.map((d) => {
                const status = progressByTopic?.[d.key] || "not_yet";
                return (
                  <button
                    key={d.key}
                    type="button"
                    data-testid={`dashboard-deepdive-${d.key}`}
                    data-status={status}
                    onClick={() => onOpenGuidedJourney(d.key)}
                    className={`relative text-center bg-white ${d.hover} border ${d.border} ${d.color} rounded-lg py-1.5 px-1 text-[11px] font-semibold transition`}
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

          {/* First-time commit chip — only before any path pick */}
          {!pathPickedAt && (
            <button
              type="button"
              data-testid="dashboard-cta-commit"
              onClick={onEnterParent}
              className="w-full p-2 rounded-xl bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 text-left transition text-xs font-semibold"
            >
              <i className="fa-solid fa-check mr-1.5"></i>
              Commit to the Self Journey
            </button>
          )}
        </section>
      )}

      {/* -------------------------------------------------------- */}
      {/* TAB 2 — FOUNDATION REPORT                                 */}
      {/* -------------------------------------------------------- */}
      {activeTab === "report" && (
        <section
          data-testid="dashboard-view-report"
          className="space-y-3"
        >
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center">
                <i className="fa-solid fa-file-lines"></i>
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-bold text-slate-900">
                  Foundation Statement Summary
                </h3>
                <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                  Objective, non-blame summary generated from your
                  completed reflections. Open it to review, edit, or
                  export the PDF.
                </p>
              </div>
            </div>
            <button
              type="button"
              data-testid="dashboard-report-open"
              onClick={onOpenReport}
              className="mt-3 w-full py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold transition"
            >
              <i className="fa-solid fa-folder-open mr-1.5"></i>
              Open Foundation Report
            </button>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <h4 className="text-xs font-bold text-slate-700 mb-2">
              What's included
            </h4>
            <ul className="text-[12px] text-slate-700 space-y-1.5 list-disc pl-4 leading-snug">
              <li>Your Foundation Statement (non-blame, child-focused).</li>
              <li>Co-parenting assessment (40-Q) summary when complete.</li>
              <li>Snapshots you filed from the Communication Builder.</li>
              <li>
                Deep-dive notes (Educational, Medical, Psychological)
                if present.
              </li>
            </ul>
          </div>
        </section>
      )}

      {/* -------------------------------------------------------- */}
      {/* TAB 3 — AI COACH & TOOLS                                  */}
      {/* -------------------------------------------------------- */}
      {activeTab === "coach" && (
        <section
          data-testid="dashboard-view-coach"
          className="space-y-3"
        >
          <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="dashboard-cta-biff"
                onClick={onOpenBiffCoach}
                className="flex-1 p-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-left transition flex items-center gap-2"
              >
                <i className="fa-solid fa-wand-magic-sparkles"></i>
                <span className="text-sm font-bold flex-1">
                  Communication Builder
                </span>
              </button>
              <button
                type="button"
                data-testid="dashboard-biff-info-btn"
                onClick={() => setBiffInfoOpen((v) => !v)}
                aria-label={BIFF_INFO.title}
                aria-expanded={biffInfoOpen}
                className="shrink-0 w-8 h-8 rounded-full bg-white hover:bg-amber-100 border border-amber-300 text-amber-800 text-xs font-bold flex items-center justify-center transition"
              >
                ?
              </button>
            </div>
            {biffInfoOpen && (
              <div
                data-testid="dashboard-biff-info-card"
                className="rounded-lg bg-white border border-amber-200 p-2.5 text-[12px] text-amber-950 leading-snug space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-bold text-amber-900">
                    {BIFF_INFO.title}
                  </h4>
                  <button
                    type="button"
                    data-testid="dashboard-biff-info-close"
                    onClick={() => setBiffInfoOpen(false)}
                    aria-label="Close explainer"
                    className="shrink-0 w-5 h-5 rounded-full bg-amber-50 hover:bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center"
                  >
                    <i className="fa-solid fa-xmark"></i>
                  </button>
                </div>
                <p>{BIFF_INFO.body}</p>
                {biffBookUrl && (
                  <a
                    href={biffBookUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="dashboard-biff-info-book-link"
                    className="inline-flex items-center gap-1.5 mt-1 px-3 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-[11px] transition"
                  >
                    <i className="fa-solid fa-book"></i>
                    Get {biffBookTitle}
                    {biffBookAuthor ? ` — ${biffBookAuthor}` : ""}
                    <i className="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-80"></i>
                  </a>
                )}
              </div>
            )}
            <div
              data-testid="dashboard-biff-progress"
              className="rounded-lg bg-white border border-amber-200 p-2 flex items-center gap-2"
            >
              <div className="shrink-0 w-7 h-7 rounded-full bg-amber-200 text-amber-900 flex items-center justify-center font-bold text-[11px]">
                {biffAuthoredCount}
              </div>
              <div className="min-w-0 flex-1 leading-snug">
                <div className="text-[9px] uppercase font-bold tracking-wider text-amber-800">
                  Your growth record
                </div>
                <p className="text-[10px] text-slate-700">
                  {biffAuthoredCount === 0 ? (
                    <>No rewrites yet. Your first draft will start the record.</>
                  ) : (
                    <>
                      {biffAuthoredCount} message
                      {biffAuthoredCount === 1 ? "" : "s"} reworked
                      {biffPairCount > 0
                        ? ` · ${biffPairCount} filed as snapshot${
                            biffPairCount === 1 ? "" : "s"
                          }`
                        : ""}
                      .
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Deep-dive chips repeated on Tab 3 per founder spec */}
          <div data-testid="dashboard-coach-deepdives" className="pt-1">
            <div className="text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1.5 px-1">
              Child-focused deep dives
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {DEEP_DIVES.map((d) => {
                const status = progressByTopic?.[d.key] || "not_yet";
                return (
                  <button
                    key={d.key}
                    type="button"
                    data-testid={`dashboard-coach-deepdive-${d.key}`}
                    data-status={status}
                    onClick={() => onOpenGuidedJourney(d.key)}
                    className={`relative text-center bg-white ${d.hover} border ${d.border} ${d.color} rounded-lg py-1.5 px-1 text-[11px] font-semibold transition`}
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
        </section>
      )}
    </div>
  );
}
