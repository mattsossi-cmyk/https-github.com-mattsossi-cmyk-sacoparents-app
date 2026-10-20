import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Keyboard, Eye, Ear, Contrast, MousePointer2, LifeBuoy } from "lucide-react";

const LAST_UPDATED = "February 26, 2026";

export default function Accessibility() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="accessibility-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="accessibility-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Accessibility</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          Built to work for every parent.
        </h1>
        <p className="text-sm text-[#6E6787] mb-8">Last updated: {LAST_UPDATED}</p>

        <Prose>
          <p>
            Mediation prep should not gatekeep on ability. This page describes
            the accessibility choices we've made, where we know we still fall
            short, and how to reach us if something isn't working for you.
          </p>

          <H2>Our commitment</H2>
          <p>
            We target <strong>WCAG 2.2 Level AA</strong> across the web app, the
            iOS + Android wrappers, and every downloadable PDF. Where a WCAG
            success criterion is context-sensitive (e.g. text alternatives for
            live coaching), we err on the side of clearer language.
          </p>

          <H2>What we ship today</H2>
          <FeatureGrid>
            <Feature icon={<Keyboard size={16} />} title="Full keyboard navigation">
              Every interactive control — assessments, share dialogs, journal entries — is reachable via <kbd>Tab</kbd> / <kbd>Shift+Tab</kbd>. Focus rings are visible, never removed.
            </Feature>
            <Feature icon={<Ear size={16} />} title="Screen-reader ready">
              Semantic landmarks, ARIA labels on icon-only buttons, and live regions announce toast messages. Tested with VoiceOver (iOS/macOS) + TalkBack (Android) + NVDA on Windows.
            </Feature>
            <Feature icon={<Contrast size={16} />} title="Contrast &amp; typography">
              Body text meets 4.5:1 contrast; large headings meet 3:1. Default font sizes scale with your OS text-size setting — nothing is fixed in px-only.
            </Feature>
            <Feature icon={<Eye size={16} />} title="No motion for those who don't want it">
              We honor <code>prefers-reduced-motion</code>. All ambient animations (blur orbs, video autoplays, fade-ups) are disabled if your OS asks us to.
            </Feature>
            <Feature icon={<MousePointer2 size={16} />} title="Tap-target sizing">
              Minimum 44×44px touch targets on mobile. Buttons never sit closer than 8px to their neighbours.
            </Feature>
            <Feature icon={<LifeBuoy size={16} />} title="Emergency exits">
              A one-tap Quick Exit button escapes the app to a neutral URL for survivors who need to abandon a session quickly.
            </Feature>
          </FeatureGrid>

          <H2>PDF reports</H2>
          <p>
            Every generated PDF (Mediation Summary, Co-Parenting Agreement,
            Special Needs Care Plan) is produced with
            structured headings, real text (not scanned images), and a linear
            reading order so screen readers can parse them. Fonts are embedded.
          </p>

          <H2>Known gaps</H2>
          <ul>
            <li>The AI Coach chat replies are streamed as plain text and may not consistently trigger <code>aria-live</code> announcements on every browser. We're working on it.</li>
            <li>Some marketing videos ship with captions but not yet with an audio-description track.</li>
            <li>The color palette (deep purple + teal) meets AA contrast but not always AAA. We prefer this over a monotone theme that loses meaning.</li>
          </ul>

          <H2>Keyboard shortcuts</H2>
          <ul>
            <li><kbd>Esc</kbd> — close any open modal or dialog</li>
            <li><kbd>?</kbd> in the AI Coach — send the current message</li>
            <li><kbd>Tab</kbd> / <kbd>Shift+Tab</kbd> — walk the focus order</li>
            <li>Quick Exit is always focusable as the very first interactive element on the page.</li>
          </ul>

          <H2>Compatibility</H2>
          <p>
            We test the latest two versions of Safari, Chrome, Firefox, and
            Edge. The iOS wrapper supports iOS 15+ and the Android wrapper
            targets Android 8+ (Capacitor 7 baseline).
          </p>

          <H2>Tell us when we get it wrong</H2>
          <p>
            If any part of SA CoParents blocks or confuses you, please email
            {" "}<a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>{" "}
            with a short description (and a screenshot if you can). We treat
            accessibility bug reports as P0 and will get back to you within
            2 business days.
          </p>

          <p className="text-xs text-[#6E6787] italic mt-8">
            SA CoParents · 16607 Blanco #703, San Antonio, Texas 78232
          </p>
        </Prose>
      </div>
    </div>
  );
}

function H2({ children }) {
  return <h2 className="font-serif text-2xl text-[#1A1330] mt-10 mb-3">{children}</h2>;
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#4B4567] [&_strong]:text-[#1A1330] [&_kbd]:bg-[#EFE9F9] [&_kbd]:text-[#3D1A78] [&_kbd]:rounded [&_kbd]:px-1.5 [&_kbd]:py-0.5 [&_kbd]:text-[0.6875rem] [&_kbd]:font-mono [&_code]:bg-[#EFE9F9] [&_code]:text-[#3D1A78] [&_code]:rounded [&_code]:px-1 [&_code]:text-[0.8125rem] text-[15px]">
      {children}
    </div>
  );
}

function FeatureGrid({ children }) {
  return <div className="grid sm:grid-cols-2 gap-3 my-4 not-prose">{children}</div>;
}

function Feature({ icon, title, children }) {
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
      <div className="flex items-center gap-2 text-[#3D1A78]">
        {icon}
        <div className="text-sm font-semibold text-[#1A1330]">{title}</div>
      </div>
      <p className="text-[0.8125rem] text-[#4B4567] mt-2 leading-relaxed">{children}</p>
    </div>
  );
}
