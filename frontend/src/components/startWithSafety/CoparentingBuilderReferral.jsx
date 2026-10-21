import React from "react";
import "./StartWithSafetyBanner.css";
import "./CoparentingBuilderReferral.css";

/**
 * "What's next" card shown after a parent completes the Start with Safety step.
 * Sends the parent to the SA CoParents Parallel Parenting Option Builder.
 *
 * IMPORTANT: show this card to EVERY parent who finishes the step, with the same
 * wording. Never show, hide or change it based on answers, skips or concern level:
 * a parent (or someone looking over their shoulder) must not be able to infer
 * anything from whether it appears.
 *
 * Props (all optional):
 *  - builderUrl:  where the button goes (default: the SA CoParents app)
 *  - headingLevel: 1–6, heading tag for the card title (default 2)
 *  - onOpen:      called when the parent clicks the button (e.g. for logging)
 */
export default function CoparentingBuilderReferral({
  builderUrl = "https://sacoparentsapp.online",
  headingLevel = 2,
  onOpen,
  progress = null,
  testid = "builder-referral",
}) {
  const badge = { in_progress: "In progress", done: "Done" }[progress];
  const Heading = `h${Math.min(Math.max(headingLevel, 1), 6)}`;

  // Same tab on purpose: a second tab would stay open after Quick Exit.
  return (
    <section className="sws-banner cbr-card" aria-labelledby="cbr-title" data-testid={testid}>
      <div className="cbr-body">
        <div className="cbr-done" aria-hidden="true">
          <svg viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="22" />
            <path
              d="M13 24 h20 m-7 -7 l7 7 l-7 7"
              fill="none"
              stroke="#fff"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <p className="cbr-eyebrow" data-testid={`${testid}-eyebrow`}>What&apos;s next</p>
        {badge && (
          <p className={`cbr-badge cbr-badge-${progress}`} data-testid={`${testid}-badge`}>
            Builder: {badge}
          </p>
        )}
        <Heading id="cbr-title" className="cbr-title">
          Your next step: build your parallel parenting plan
        </Heading>
        <p className="cbr-text">
          The SA CoParents Parallel Parenting Option Builder walks you through
          schedules, communication and your child's needs, one step at a time,
          so you're ready for mediation.
        </p>
        <p className="cbr-text cbr-note">
          Go at your own pace. If a professional is working with your family,
          they can help you decide what to do next.
        </p>

        <a
          className="sws-cta cbr-button"
          href={builderUrl}
          onClick={onOpen}
          data-testid={`${testid}-open`}
        >
          Open the Parallel Parenting Option Builder
        </a>
      </div>
    </section>
  );
}
