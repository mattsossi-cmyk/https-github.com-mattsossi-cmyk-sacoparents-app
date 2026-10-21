import React, { useMemo } from "react";
import "./ParentDashboard.css";
import defaultHero from "../startWithSafety/start-with-safety-photo.jpg";

/**
 * Simple parent dashboard: Quick Exit, one "next step", the steps in order
 * (each with a privacy tag), and the footer. The path (Court Ordered / Self Journey /
 * Mediation Prep) is chosen once at sign-up and passed in as `path`.
 *
 * SAFETY RULES built in:
 *  - Nothing on this screen changes based on safety answers, skips or concern level.
 *  - The safety step is called "Private check-in" here (neutral wording).
 *  - The check-in status can be "unknown" (this app may not hear back from Align).
 *    Unknown is shown neutrally ("Open"), never as "not started".
 *
 * Props:
 *  - parentName, path ("court" | "self" | "mediation" | null), status, links, onNavigate,
 *    quickExitUrl, heroImage, images — as in the original file.
 *  - nextId      step id for "Your next step", or null when everything is done.
 *  - extras      { [stepId]: { label, href } } a second link under a step row.
 *  - top / belowNext / afterSteps   extra content slots.
 */

const PRIVACY = {
  checkin: { icon: "lock", text: "You, your professional + a few admins" },
  only_you_answers: { icon: "lock", text: "Only you see your answers" },
  only_you_unless: { icon: "lock", text: "Only you, unless you share it" },
  both_agree: { icon: "people", text: "Shared only if you both agree" },
  you_pro: { icon: "lock", text: "You + your professional" },
};

export function buildSteps(path, status = {}, links = {}) {
  const steps = [
    {
      id: "checkin",
      title: "Private check-in",
      blurb: "A short, private check-in before you begin.",
      minutes: 10,
      privacy: "checkin",
      href: links.checkin,
      status: status.checkin || "unknown",
    },
    {
      id: "selfAssessment",
      title: "Self-Assessment",
      blurb: "Reflect on your own patterns and what matters most to you.",
      minutes: 15,
      privacy: "only_you_answers",
      href: links.selfAssessment,
      status: status.selfAssessment || "todo",
    },
    {
      id: "communication",
      title: "Communication Builder",
      blurb: "Practice calm, child-focused ways to talk with your co-parent.",
      minutes: 15,
      privacy: "only_you_unless",
      href: links.communication,
      status: status.communication || "todo",
    },
    {
      id: "order",
      title: "Co\u2011Parenting Agreement",
      blurb: "Build your parenting plan: schedule, exchanges and decisions.",
      minutes: 25,
      privacy: "both_agree",
      href: links.order,
      status: status.order || "todo",
    },
  ];
  if (path === "court") {
    steps.push({
      id: "courtChecklist",
      title: "Court checklist",
      blurb: "Track what your court asked you to complete.",
      minutes: 5,
      privacy: "you_pro",
      href: links.courtChecklist,
      status: status.courtChecklist || "todo",
    });
  }
  return steps;
}

export default function ParentDashboard({
  parentName,
  path = null,
  status,
  links = {},
  onNavigate,
  quickExitUrl = "https://www.weather.com/",
  heroImage = defaultHero,
  images = {},
  nextId = null,
  extras = {},
  top = null,
  belowNext = null,
  afterSteps = null,
}) {
  const steps = useMemo(() => buildSteps(path, status, links), [path, status, links]);

  // The check-in is never counted: this app can't always know it's done.
  const counted = steps.filter((s) => s.id !== "checkin");
  const doneCount = counted.filter((s) => s.status === "done").length;
  const next = nextId ? steps.find((s) => s.id === nextId) : null;

  const quickExit = () => {
    // replace() so the Back button doesn't return to the app
    window.location.replace(quickExitUrl);
  };

  const linkProps = (href, external) => {
    if (!href) return { href: "#", "aria-disabled": true };
    const p = { href };
    if (external) {
      p.target = "_blank";
      p.rel = "noopener noreferrer";
    }
    if (onNavigate) {
      p.onClick = (e) => {
        if (external) return; // let new-tab links open normally
        e.preventDefault();
        onNavigate(href, external);
      };
    }
    return p;
  };

  return (
    <div className="pd" data-testid="parent-dashboard">
      {/* Top bar */}
      <header className="pd-top">
        <span className="pd-brand">SA CoParents</span>
        <button type="button" className="pd-exit" onClick={quickExit} data-testid="pd-quick-exit">
          Quick Exit <span aria-hidden="true">✕</span>
        </button>
      </header>

      <main className="pd-main">
        {top}

        {/* Greeting + progress */}
        <section className="pd-hello" aria-label="Your progress" data-testid="pd-hello">
          {heroImage && (
            <img className="pd-hero" src={heroImage} alt="" aria-hidden="true" />
          )}
          <div className="pd-hello-body">
            <h1 className="pd-h1" data-testid="pd-greeting">{parentName ? `Hi ${parentName}` : "Welcome"}</h1>
            <p className="pd-hello-sub">Every step you take here is for your child.</p>
            <div className="pd-progress">
              <div
                className="pd-bar"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={counted.length}
                aria-valuenow={doneCount}
                aria-label={`${doneCount} of ${counted.length} steps complete`}
                data-testid="pd-progress-bar"
              >
                <span style={{ width: `${(doneCount / counted.length) * 100}%` }} />
              </div>
              <span className="pd-count" data-testid="pd-progress-count">
                {doneCount} of {counted.length}
              </span>
            </div>
          </div>
        </section>

        {/* Next step */}
        {next ? (
          <section className="pd-next" aria-labelledby="pd-next-title" data-testid="pd-next">
            <div className="pd-next-head">
              <div>
                <p className="pd-eyebrow">Your next step</p>
                <h2 id="pd-next-title" className="pd-next-title" data-testid="pd-next-title">
                  {next.title}
                </h2>
              </div>
              <StepArt id={next.id} src={images[next.id]} big />
            </div>
            <p className="pd-next-blurb">{next.blurb}</p>
            <div className="pd-next-meta">
              <PrivacyTag kind={next.privacy} />
              <span className="pd-time">About {next.minutes} min</span>
            </div>
            <a className="pd-btn" {...linkProps(next.href, next.external)} data-testid="pd-next-button">
              {next.status === "in_progress" ? "Continue" : "Start"}
            </a>
          </section>
        ) : (
          <section className="pd-next pd-next-done" data-testid="pd-caught-up">
            <p className="pd-eyebrow">Your next step</p>
            <h2 className="pd-next-title">You&apos;re all caught up</h2>
            <p className="pd-next-blurb">
              You can revisit any step below at any time.
            </p>
          </section>
        )}

        {belowNext}

        {/* Steps */}
        <section className="pd-section" aria-labelledby="pd-steps-title">
          <h2 id="pd-steps-title" className="pd-h2">
            Your steps
          </h2>
          <ol className="pd-steps">
            {steps.map((s, i) => (
              <li key={s.id} className={`pd-step is-${s.status}`} data-testid={`pd-step-${s.id}`}>
                <a className="pd-step-link" {...linkProps(s.href, s.external)} data-testid={`pd-step-${s.id}-link`}>
                  <span className="pd-art-wrap">
                    <StepArt id={s.id} src={images[s.id]} />
                    <StepMark n={i + 1} status={s.status} />
                  </span>
                  <span className="pd-step-text">
                    <span className="pd-step-title">{s.title}</span>
                    <PrivacyTag kind={s.privacy} small />
                  </span>
                  <span className="pd-step-state" data-testid={`pd-step-${s.id}-state`}>{stateLabel(s.status)}</span>
                </a>
                {extras[s.id] && (
                  <a className="pd-step-extra" {...linkProps(extras[s.id].href)} data-testid={`pd-step-${s.id}-extra`}>
                    {extras[s.id].label} <span aria-hidden="true">→</span>
                  </a>
                )}
              </li>
            ))}
          </ol>
        </section>

        {afterSteps}
      </main>

      <footer className="pd-footer">
        <a {...linkProps(links.whoCanSee)} data-testid="pd-footer-who-can-see">Who can see my information</a>
        <a {...linkProps(links.privacy)} data-testid="pd-footer-privacy">Privacy</a>
        <a {...linkProps(links.getHelp)} data-testid="pd-footer-get-help">Get help</a>
      </footer>
    </div>
  );
}

function stateLabel(s) {
  if (s === "done") return "Done";
  if (s === "in_progress") return "In progress";
  if (s === "unknown") return "Open";
  return "Not yet";
}

function StepMark({ n, status }) {
  if (status === "done") {
    return (
      <span className="pd-mark is-done" aria-hidden="true">
        <svg viewBox="0 0 20 20">
          <path d="M5 10.5l3.2 3.2L15 7" />
        </svg>
      </span>
    );
  }
  return (
    <span className={`pd-mark is-${status}`} aria-hidden="true">
      {n}
    </span>
  );
}

function PrivacyTag({ kind, small }) {
  const p = PRIVACY[kind];
  if (!p) return null;
  return (
    <span className={`pd-tag pd-tag-${kind} ${small ? "is-small" : ""}`}>
      <Icon name={p.icon} />
      {p.text}
    </span>
  );
}

function Icon({ name }) {
  if (name === "people") {
    return (
      <svg className="pd-ico" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="7" cy="6.5" r="2.8" />
        <circle cx="13.5" cy="7" r="2.4" />
        <path d="M1.8 16c0-3.2 2.3-5.3 5.2-5.3s5.2 2.1 5.2 5.3z" />
        <path d="M12.6 16c0-1.7-.5-3.1-1.4-4.1.7-.4 1.4-.6 2.3-.6 2.5 0 4.6 1.9 4.6 4.7z" />
      </svg>
    );
  }
  return (
    <svg className="pd-ico" viewBox="0 0 20 20" aria-hidden="true">
      <rect x="4" y="9" width="12" height="9" rx="2" />
      <path d="M6.5 9V6.5a3.5 3.5 0 0 1 7 0V9" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

/* Step illustrations: the app's own image if provided, otherwise a built-in
   purple illustration in the Start with Safety style. Decorative only. */
function StepArt({ id, src, big }) {
  const cls = `pd-art ${big ? "is-big" : ""}`;
  if (src) {
    return <img className={cls} src={src} alt="" aria-hidden="true" />;
  }
  return (
    <span className={cls} aria-hidden="true">
      <svg viewBox="0 0 48 48">{ART[id] || ART.selfAssessment}</svg>
    </span>
  );
}

const ART = {
  checkin: (
    <>
      <path d="M24 4 L41 10 V23 C41 34 33 41 24 44 C15 41 7 34 7 23 V10 Z" />
      <path className="pd-art-cut" d="M24 10 L35 14 V23 C35 30 30 35 24 38 C18 35 13 30 13 23 V14 Z" />
      <path d="M24 19 c-1.8-3-6.5-2.4-6.5 1.2 0 3 3.6 4.8 6.5 7.2 2.9-2.4 6.5-4.2 6.5-7.2 0-3.6-4.7-4.2-6.5-1.2z" />
    </>
  ),
  selfAssessment: (
    <>
      <circle cx="24" cy="15" r="7" />
      <path d="M11 41 c0-9 6-15 13-15 s13 6 13 15 z" />
      <path className="pd-art-cut" d="M24 31.5 c-1.4-2.3-5-1.8-5 0.9 0 2.3 2.8 3.7 5 5.5 2.2-1.8 5-3.2 5-5.5 0-2.7-3.6-3.2-5-0.9z" />
    </>
  ),
  communication: (
    <>
      <path d="M5 9 h24 a4 4 0 0 1 4 4 v11 a4 4 0 0 1 -4 4 h-13 l-7 6 v-6 h-4 a4 4 0 0 1 -4 -4 v-11 a4 4 0 0 1 4 -4z" />
      <path d="M36 18 h7 a3 3 0 0 1 3 3 v10 a3 3 0 0 1 -3 3 h-2 v5 l-6 -5 h-11 a3 3 0 0 1 -3 -3 v-1 h10 a5 5 0 0 0 5 -5z" opacity="0.55" />
      <circle className="pd-art-cut" cx="11" cy="18.5" r="2" />
      <circle className="pd-art-cut" cx="17" cy="18.5" r="2" />
      <circle className="pd-art-cut" cx="23" cy="18.5" r="2" />
    </>
  ),
  order: (
    <>
      <rect x="7" y="9" width="34" height="33" rx="5" />
      <rect className="pd-art-cut" x="11" y="18" width="26" height="20" rx="2" />
      <rect x="14" y="5" width="4" height="9" rx="2" />
      <rect x="30" y="5" width="4" height="9" rx="2" />
      <rect x="14" y="22" width="6" height="5" rx="1" />
      <rect x="23" y="22" width="6" height="5" rx="1" opacity="0.55" />
      <rect x="14" y="30" width="6" height="5" rx="1" opacity="0.55" />
      <rect x="23" y="30" width="6" height="5" rx="1" />
    </>
  ),
  courtChecklist: (
    <>
      <rect x="9" y="7" width="30" height="37" rx="5" />
      <rect className="pd-art-cut" x="13" y="13" width="22" height="27" rx="2" />
      <rect x="17" y="4" width="14" height="7" rx="3" />
      <path d="M16 20 l2.5 2.5 l4.5 -5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="25" y="18" width="7" height="3" rx="1.5" />
      <path d="M16 30 l2.5 2.5 l4.5 -5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="25" y="28" width="7" height="3" rx="1.5" />
    </>
  ),
};
