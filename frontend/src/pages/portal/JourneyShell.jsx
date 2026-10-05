import React, { useMemo, useState } from "react";

import { GreyRockToggleChip } from "./AlignmentHub";

/**
 * JourneyShell — iter244 Phase A.
 *
 * The five-step parent-facing scaffold. The ONE rule set in
 * NORTH_STAR.md: parents should see the five steps and nothing
 * else. Every current tool/assessment/report lives behind one of
 * these steps.
 *
 * Phase A deliberately keeps old components intact. Steps 2–5 for
 * now route into the existing parent-journey screen (which still
 * renders the AlignmentHub + BiffTab + guided journey). Phase B
 * (iter245) will absorb those surfaces INTO the step cards
 * themselves, deleting the toolkit tile grid and hub-section tabs.
 *
 * Testids: `journey-shell`, `journey-step-{n}`, `journey-step-{n}-cta`.
 * Old testids on existing components stay untouched.
 */
const PATHS = [
  {
    key: "self",
    title: "Self Journey",
    tagline: "Start on your own.",
    body: "Private safety check, a quick 40-question profile, a progress tracker, and the Communication Builder — all in one place. Nothing you do here is shared unless you decide to.",
    icon: "fa-door-open",
    tint: "purple",
    expandable: true,
  },
  {
    key: "court",
    title: "Court Ordered",
    tagline: "Referred by a court, mediator, or attorney.",
    body: "Enter the access key the professional gave you. We'll fast-forward you to the assessment they named.",
    icon: "fa-gavel",
    tint: "indigo",
    expandable: false,
  },
];

// iter256 — Communication Builder "?" explainer, lifted out of PATHS
// so it can live inline inside the Self Journey panel.
const BIFF_INFO = {
  title: "What's a BIFF rewrite?",
  body: "BIFF stands for Brief, Informative, Friendly, and Firm — a research-backed way to answer a hot message without matching its heat. You keep the facts, drop the drama, and leave less room for a fight.",
  linkKind: "biff_book",
};

const TINT_CLASSES = {
  purple: {
    ring: "border-purple-300",
    chip: "bg-purple-100 text-purple-800",
    icon: "bg-purple-100 text-purple-700",
    cta: "bg-purple-600 hover:bg-purple-700 text-white",
    accent: "text-purple-700",
  },
  indigo: {
    ring: "border-indigo-300",
    chip: "bg-indigo-100 text-indigo-800",
    icon: "bg-indigo-100 text-indigo-700",
    cta: "bg-indigo-600 hover:bg-indigo-700 text-white",
    accent: "text-indigo-700",
  },
  emerald: {
    ring: "border-emerald-300",
    chip: "bg-emerald-100 text-emerald-800",
    icon: "bg-emerald-100 text-emerald-700",
    cta: "bg-emerald-600 hover:bg-emerald-700 text-white",
    accent: "text-emerald-700",
  },
  amber: {
    ring: "border-amber-300",
    chip: "bg-amber-100 text-amber-800",
    icon: "bg-amber-100 text-amber-700",
    cta: "bg-amber-600 hover:bg-amber-700 text-white",
    accent: "text-amber-700",
  },
  rose: {
    ring: "border-rose-300",
    chip: "bg-rose-100 text-rose-800",
    icon: "bg-rose-100 text-rose-700",
    cta: "bg-rose-600 hover:bg-rose-700 text-white",
    accent: "text-rose-700",
  },
};

function pickCurrentStep() {
  // Deprecated iter254 — the shell no longer tracks a sequential
  // "current step." Kept as a stub only until any lingering import
  // is removed. See `activePath` state inside JourneyShell for the
  // replacement.
  return null;
}

export function JourneyShell({
  user,
  safetyAck,
  pathPickedAt,
  courtKey = null,
  verifiedMediator = null,
  // Path CTAs — same handlers the old Gateway used, so the
  // Safety-First gate still fires before either entry.
  onEnterParent = () => {},
  onEnterCourt = () => {},
  // Self Journey panel — safety check launcher + grey-rock controls.
  onOpenSafety = () => {},
  onClearGreyRock = () => {},
  onOpenSafetyRetake = () => {},
  // Self Journey — self-assessment preview URL (static HTML in /public).
  selfAssessmentUrl = "/coparenting-self-assessment-preview.html",
  // Self Journey — Co-parenting assessment / Guided Journey launcher.
  onOpenGuidedJourney = () => {},
  // Communication Builder — BIFF Coach + growth record signals.
  onOpenBiffCoach = () => {},
  biffAuthoredCount = 0,
  biffPairCount = 0,
  // Intro guide chip (soft, non-blocking).
  onOpenIntroGuide = () => {},
  // Grey-rock chip surface, if applicable.
  safetyFlagged = false,
}) {
  const safetyFlag = safetyFlagged || !!(safetyAck && safetyAck.flagged);

  // iter254 — the three top-level paths aren't sequential steps any
  // more, so there's no "current step." The Self Journey panel is
  // the only one with inline expansion; it auto-opens when the
  // parent has picked that door before (we recognise them as a
  // returning Self Journey parent).
  const [expandedPath, setExpandedPath] = useState(null);
  const activePath =
    expandedPath !== null ? expandedPath : pathPickedAt ? "self" : null;

  // iter253 — which path's "?" info card is currently open (null = none).
  const [infoOpenPath, setInfoOpenPath] = useState(null);

  // iter255 — Privacy Check inline explainer inside Self Journey.
  const [privacyOpen, setPrivacyOpen] = useState(false);

  // iter256 — Communication Builder inline "?" explainer, now nested
  // inside the Self Journey panel instead of its own top-level tile.
  const [biffInfoOpen, setBiffInfoOpen] = useState(false);

  // iter253 — Bill Eddy's BIFF book link. Env-configurable so the
  // user can swap the direct publisher link for an affiliate link
  // without a code change.
  const biffBookUrl = process.env.REACT_APP_BIFF_BOOK_URL || "";
  const biffBookTitle =
    process.env.REACT_APP_BIFF_BOOK_TITLE || "the BIFF book";
  const biffBookAuthor = process.env.REACT_APP_BIFF_BOOK_AUTHOR || "";

  const greetingName = user?.name ? user.name.split(" ")[0] : null;

  return (
    <div
      data-testid="journey-shell"
      className="space-y-4"
    >
      {/* Soft welcome. Not a modal, not a door — just a line of
          text so the parent knows the five cards are a map, not a
          choice to make. */}
      <section className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-10 h-10 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center">
            <i className="fa-solid fa-hand-holding-heart"></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase font-bold tracking-wider text-purple-700">
              Welcome{greetingName ? `, ${greetingName}` : ""}
            </div>
            <h2 className="text-base font-bold text-slate-900 leading-tight">
              Pick your path.
            </h2>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Two ways in. Your Reports and PDF Export stay one
              tap away at the bottom whenever you need them.
            </p>
          </div>
        </div>

        <button
          type="button"
          data-testid="journey-open-intro-guide"
          onClick={onOpenIntroGuide}
          className="mt-3 w-full py-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-lg font-bold text-xs transition"
        >
          <i className="fa-solid fa-comment-dots mr-1.5"></i>
          Not sure where to start? Chat with the Guide
        </button>
      </section>

      {/* iter251 — court-ordered status card. Shown at the top of
          the shell (not inside a step) whenever a court key is
          verified. Replaces the Step-3 inline banner since Step 3
          was deleted. */}
      {courtKey && (
        <div
          data-testid="journey-court-banner"
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

      {/* Grey-rock soft indicator — if the parent is in grey-rock
          mode they already see the chip inside AlignmentHub when
          they tap Step 2–5. The shell adds a tiny banner above
          the step list so it's visible BEFORE they tap anything. */}
      {safetyFlag && (
        <div
          data-testid="journey-grey-rock-banner"
          className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-900 flex items-start gap-2"
        >
          <i className="fa-solid fa-shield-halved text-amber-600 mt-0.5"></i>
          <div className="leading-snug">
            <span className="font-semibold">Grey-rock mode is on.</span>{" "}
            <span className="text-amber-800">
              Tools and language are quietly adapted. You can turn it
              off inside Self Journey.
            </span>
          </div>
        </div>
      )}

      {/* iter254 — three main paths. Self Journey expands inline
          (safety + progress + preview CTAs). Court Ordered and
          Communication Builder tap through to their respective
          flows directly. */}
      <div className="space-y-3">
        {PATHS.map((path) => {
          const tint = TINT_CLASSES[path.tint];
          const isActive = activePath === path.key;
          const isInfoOpen = infoOpenPath === path.key;

          const handleCardClick = () => {
            if (path.key === "self") {
              setExpandedPath(isActive ? "" : "self");
            } else if (path.key === "court") {
              onEnterCourt();
            }
          };

          return (
            <div key={path.key} data-testid={`journey-path-${path.key}`}>
              {/* Primary path button. role="button" (not <button>)
                  so the "?" info button can nest without invalid
                  HTML. Keyboard Enter/Space wired by hand. */}
              <div
                role="button"
                tabIndex={0}
                onClick={handleCardClick}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleCardClick();
                  }
                }}
                data-testid={`journey-path-${path.key}-btn`}
                className={`w-full text-left bg-white rounded-2xl border-2 ${
                  isActive && path.expandable
                    ? tint.ring
                    : "border-slate-200"
                } p-3 transition hover:shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-400`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`shrink-0 w-11 h-11 rounded-xl ${tint.icon} flex items-center justify-center`}
                  >
                    <i className={`fa-solid ${path.icon} text-lg`}></i>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <h3 className="text-sm font-bold text-slate-900 leading-tight">
                        {path.title}
                      </h3>
                      {path.info && (
                        <button
                          type="button"
                          data-testid={`journey-path-${path.key}-info-btn`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setInfoOpenPath(isInfoOpen ? null : path.key);
                          }}
                          aria-label={path.info.title}
                          aria-expanded={isInfoOpen}
                          className="shrink-0 w-5 h-5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center transition"
                        >
                          ?
                        </button>
                      )}
                    </div>
                    <p className={`text-[11px] mt-0.5 leading-snug ${tint.accent}`}>
                      {path.tagline}
                    </p>
                  </div>
                  <i
                    className={`fa-solid ${
                      path.expandable
                        ? isActive
                          ? "fa-chevron-down"
                          : "fa-chevron-right"
                        : "fa-arrow-right"
                    } text-slate-400 mt-3.5`}
                  ></i>
                </div>
              </div>

              {/* iter253 — inline info ("?") explainer. */}
              {isInfoOpen && path.info && (
                <div
                  data-testid={`journey-path-${path.key}-info-card`}
                  className="mt-1 rounded-xl bg-amber-50 border border-amber-200 p-3 text-[12px] text-amber-950 leading-snug space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-bold text-amber-900">
                      {path.info.title}
                    </h4>
                    <button
                      type="button"
                      data-testid={`journey-path-${path.key}-info-close`}
                      onClick={() => setInfoOpenPath(null)}
                      aria-label="Close explainer"
                      className="shrink-0 w-5 h-5 rounded-full bg-white hover:bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center"
                    >
                      <i className="fa-solid fa-xmark"></i>
                    </button>
                  </div>
                  <p>{path.info.body}</p>
                  {biffBookUrl && path.info.linkKind === "biff_book" && (
                    <a
                      href={biffBookUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid={`journey-path-${path.key}-info-book-link`}
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

              {/* Self Journey expanded panel — Privacy Check +
                  Grey Rock Mode + Safety First + Progress tracker
                  + 40-Q interactive preview + Communication Builder. */}
              {path.key === "self" && isActive && (
                <div
                  data-testid="journey-path-self-panel"
                  className="bg-slate-50 rounded-b-2xl border-2 border-t-0 border-purple-300 -mt-1 p-3 pt-4 text-[12px] text-slate-700 leading-snug space-y-2"
                >
                  <p>{path.body}</p>

                  {/* Privacy Check — inline explainer, opens on tap. */}
                  <button
                    type="button"
                    data-testid="journey-path-self-cta-privacy"
                    onClick={() => setPrivacyOpen((v) => !v)}
                    aria-expanded={privacyOpen}
                    className="w-full p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-left transition flex items-center gap-2"
                  >
                    <i className="fa-solid fa-user-shield"></i>
                    <span className="text-sm font-bold flex-1">
                      Privacy Check
                    </span>
                    <i
                      className={`fa-solid ${
                        privacyOpen ? "fa-chevron-up" : "fa-chevron-down"
                      } text-xs opacity-80`}
                    ></i>
                  </button>
                  {privacyOpen && (
                    <div
                      data-testid="journey-path-self-privacy-card"
                      className="rounded-xl bg-indigo-50 border border-indigo-200 p-3 text-[12px] text-indigo-950 leading-snug space-y-2"
                    >
                      <div className="font-bold text-indigo-900">
                        What stays on your device
                      </div>
                      <ul className="list-disc pl-4 space-y-1">
                        <li>
                          Your drafts, answers, and BIFF rewrites live
                          in this browser first (local storage).
                        </li>
                        <li>
                          A private copy syncs to your account so you
                          can pick back up on another device.
                        </li>
                        <li>
                          Nothing is shared with a mediator, court,
                          or anyone else unless you tap{" "}
                          <span className="font-semibold">Share</span>{" "}
                          on a specific report.
                        </li>
                        <li>
                          Grey-rock mode and your Safety-First
                          answers are stored privately — never shown
                          to the other parent.
                        </li>
                      </ul>
                    </div>
                  )}

                  {/* Grey Rock Mode — chip only when safety-flagged
                      (today's behaviour), moved above Safety First. */}
                  {safetyFlag && (
                    <GreyRockToggleChip
                      onClear={onClearGreyRock}
                      onRetake={onOpenSafetyRetake}
                    />
                  )}

                  {/* Safety First — opens the DV/IPV safety screen. */}
                  <button
                    type="button"
                    data-testid="journey-path-self-cta-safety"
                    onClick={onOpenSafety}
                    className="w-full p-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-left transition flex items-center gap-2"
                  >
                    <i className="fa-solid fa-shield-heart"></i>
                    <span className="text-sm font-bold">
                      Safety First
                    </span>
                  </button>
                  <button
                    type="button"
                    data-testid="journey-path-self-cta-progress"
                    onClick={() => onOpenGuidedJourney("coparenting")}
                    className={`w-full p-2.5 rounded-xl ${tint.cta} text-left transition flex items-center gap-2`}
                  >
                    <i className="fa-solid fa-chart-line"></i>
                    <span className="text-sm font-bold">
                      Track my progress (take or re-take the 40-Q check)
                    </span>
                  </button>
                  <a
                    href={selfAssessmentUrl}
                    target="_blank"
                    rel="noreferrer"
                    data-testid="journey-path-self-cta-preview"
                    className="block w-full p-2.5 rounded-xl bg-white hover:bg-indigo-50 border border-indigo-300 text-indigo-800 text-left transition text-sm font-bold"
                  >
                    <i className="fa-solid fa-wand-magic-sparkles mr-1.5"></i>
                    Try the 40-question interactive preview
                  </a>

                  {/* iter256 — Communication Builder, nested inside
                      Self Journey. Keeps the "?" BIFF explainer and
                      the growth record attached. */}
                  <div
                    data-testid="journey-path-self-biff-group"
                    className="rounded-xl border border-amber-200 bg-amber-50/60 p-2.5 space-y-2"
                  >
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid="journey-path-self-cta-biff"
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
                        data-testid="journey-path-self-biff-info-btn"
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
                        data-testid="journey-path-self-biff-info-card"
                        className="rounded-lg bg-white border border-amber-200 p-2.5 text-[12px] text-amber-950 leading-snug space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="font-bold text-amber-900">
                            {BIFF_INFO.title}
                          </h4>
                          <button
                            type="button"
                            data-testid="journey-path-self-biff-info-close"
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
                            data-testid="journey-path-self-biff-info-book-link"
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
                      data-testid="journey-path-self-biff-progress"
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
                            <>
                              No rewrites yet. Your first draft will
                              start the record.
                            </>
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

                  {/* iter254 — "Enter voluntary journey" link,
                      only shown the first time (parent hasn't
                      committed to any path yet). This keeps the
                      clinical Safety-First auto-gate accessible
                      for parents who want the guarded entry. */}
                  {!pathPickedAt && (
                    <button
                      type="button"
                      data-testid="journey-path-self-cta-commit"
                      onClick={onEnterParent}
                      className="w-full p-2 rounded-xl bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 text-left transition text-xs font-semibold"
                    >
                      <i className="fa-solid fa-check mr-1.5"></i>
                      Commit to the Self Journey
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
