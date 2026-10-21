import React from "react";
import "./StartWithSafetyBanner.css";
import defaultPhoto from "./start-with-safety-photo.jpg";

/**
 * "Start with Safety" banner.
 *
 * Props (all optional):
 *  - photoSrc:    image URL for the photo band (defaults to the bundled photo)
 *  - photoAlt:    alt text for the photo ("" = decorative)
 *  - headingLevel: 1–6, the heading tag used for "Start with Safety" (default 2)
 *  - ctaLabel:    text for an optional button under the features
 *  - onCtaClick:  click handler for that button (button only renders if both are set)
 *  - className:   extra class names for the outer card
 */
export default function StartWithSafetyBanner({
  photoSrc = defaultPhoto,
  photoAlt = "A parent hugging their child outdoors at sunset",
  headingLevel = 2,
  ctaLabel,
  onCtaClick,
  className = "",
  testid = "start-with-safety-banner",
}) {
  const Heading = `h${Math.min(Math.max(headingLevel, 1), 6)}`;

  return (
    <section
      className={`sws-banner ${className}`.trim()}
      aria-labelledby="sws-banner-title"
      data-testid={testid}
    >
      <div className="sws-top">
        <div className="sws-emblem" aria-hidden="true">
          <Rays side="left" />
          <FamilyShield />
          <Rays side="right" />
        </div>

        <Heading id="sws-banner-title" className="sws-title">
          <span className="sws-title-small">Start with</span>
          <span className="sws-title-big">Safety</span>
        </Heading>
        <span className="sws-underline" aria-hidden="true" />

        <p className="sws-tagline">
          A safer process for you.
          <br />
          A healthier future for your child.
        </p>
      </div>

      <div className="sws-photo">
        <img src={photoSrc} alt={photoAlt} loading="lazy" />
        <svg
          className="sws-wave"
          viewBox="0 0 1000 120"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            className="sws-wave-back"
            d="M0 40 C 220 0, 420 10, 600 50 S 880 95, 1000 30 L1000 120 L0 120 Z"
          />
          <path
            className="sws-wave-front"
            d="M0 70 C 240 30, 440 50, 640 85 S 900 110, 1000 60 L1000 120 L0 120 Z"
          />
        </svg>
      </div>

      <ul className="sws-features">
        <li>
          <CheckShieldIcon />
          <span>
            Your Safety
            <br />
            Matters
          </span>
        </li>
        <li>
          <FamilyIcon />
          <span>
            Child‑Focused
            <br />
            Solutions
          </span>
        </li>
        <li>
          <HandshakeIcon />
          <span>
            Support at
            <br />
            Every Step
          </span>
        </li>
      </ul>

      {ctaLabel && onCtaClick && (
        <div className="sws-cta-wrap">
          <button type="button" className="sws-cta" onClick={onCtaClick} data-testid={`${testid}-cta`}>
            {ctaLabel}
          </button>
        </div>
      )}
    </section>
  );
}

/* ---------- Icons (inline SVG, colour comes from CSS) ---------- */

function Rays({ side }) {
  return (
    <svg className={`sws-rays sws-rays-${side}`} viewBox="0 0 60 90">
      <line x1="8" y1="12" x2="48" y2="30" />
      <line x1="4" y1="45" x2="50" y2="45" />
      <line x1="8" y1="78" x2="48" y2="60" />
    </svg>
  );
}

function FamilyShield() {
  return (
    <svg className="sws-shield" viewBox="0 0 120 140">
      <defs>
        <linearGradient id="sws-shield-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#ece4fb" />
        </linearGradient>
      </defs>
      <path
        className="sws-shield-outline"
        d="M60 6 L110 24 V64 C110 98 88 122 60 134 C32 122 10 98 10 64 V24 Z"
      />
      <path
        d="M60 16 L100 31 V64 C100 92 82 112 60 123 C38 112 20 92 20 64 V31 Z"
        fill="url(#sws-shield-fill)"
      />
      {/* heart */}
      <path
        className="sws-ink"
        d="M60 40 c-3-5-11-4-11 2 0 5 6 8 11 12 5-4 11-7 11-12 0-6-8-7-11-2z"
      />
      {/* parent left */}
      <circle className="sws-ink" cx="42" cy="58" r="9" />
      <path
        className="sws-ink"
        d="M27 96 c0-16 7-26 15-26 6 0 10 4 12 9 l-8 9 c-3 3-5 6-5 8 z"
      />
      {/* parent right */}
      <circle className="sws-ink" cx="78" cy="58" r="9" />
      <path
        className="sws-ink"
        d="M93 96 c0-16-7-26-15-26-6 0-10 4-12 9 l8 9 c3 3 5 6 5 8 z"
      />
      {/* child, arms up */}
      <circle className="sws-ink" cx="60" cy="78" r="7.5" />
      <path
        className="sws-ink"
        d="M46 82 c3 6 8 9 14 9 s11-3 14-9 l4 3 c-3 7-8 11-13 12 v14 h-10 v-14 c-5-1-10-5-13-12 z"
      />
    </svg>
  );
}

function CheckShieldIcon() {
  return (
    <svg className="sws-icon" viewBox="0 0 48 48" aria-hidden="true">
      <path d="M24 3 L42 9 V23 C42 35 34 42 24 46 C14 42 6 35 6 23 V9 Z" />
      <path
        className="sws-icon-cut"
        d="M24 9 L36 13 V23 C36 31 31 36 24 39 C17 36 12 31 12 23 V13 Z"
      />
      <path
        d="M17 24 l5 5 l10 -11"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FamilyIcon() {
  return (
    <svg className="sws-icon" viewBox="0 0 48 48" aria-hidden="true">
      <circle cx="24" cy="9" r="6" />
      <path d="M15 34 c0-11 4-17 9-17 s9 6 9 17 z" />
      <circle cx="10" cy="22" r="4.5" />
      <path d="M3 42 c0-8 3-13 7-13 s7 5 7 13 z" />
      <circle cx="38" cy="22" r="4.5" />
      <path d="M31 42 c0-8 3-13 7-13 s7 5 7 13 z" />
      <path d="M17 42 c0-6 3-9 7-9 s7 3 7 9 z" />
    </svg>
  );
}

function HandshakeIcon() {
  return (
    <svg className="sws-icon" viewBox="0 0 48 48" aria-hidden="true">
      <path d="M2 16 l7-5 l9 13 l-7 5 z" />
      <path d="M46 16 l-7-5 l-9 13 l7 5 z" />
      <path d="M13 18 l9-6 c2-1 4-1 6 0 l9 6 l-6 9 l-6-4 l-6 5 c-2 1-4 0-4-2 l6-6 l-3-2 z" />
      <path d="M12 28 l3 3 m2-2 l3 4 m2-2 l3 4 m2-1 l3 3"
        fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M13 30 l11 10 c1 1 3 1 4 0 l9-9 l-4-4 l-8 7 z" />
    </svg>
  );
}
