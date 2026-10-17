/**
 * FrontDoorHero — the primary parent entry point (iter196).
 *
 * Replaces the crowded dashboard hero with ONE decision:
 *   1. "Starting on My Own"          → /situation (topic picker)
 *   2. "Court Ordered / Referred"    → /join      (access code entry)
 * plus a slim "Already started? Continue My Assessment →" strip and
 * a persistent "Were you ordered or referred?" banner.
 *
 * Mounted at the top of BOTH `/` (unauth) and `/dashboard` (authed)
 * so every parent hits the same two-question opener regardless of
 * how they arrived. All downstream assessments, journeys, tools,
 * and reports still exist — they're just not front-and-center here.
 *
 * Design tokens match `sacoparentsalign.com`: white background,
 * `#3D1A78` purple accents, serif headings, generous spacing.
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, User, Scale, KeyRound } from "lucide-react";

/**
 * @param {object} props
 * @param {boolean} props.showContinue — render the "Already started?
 *   Continue My Assessment →" strip. True for authed users on
 *   `/dashboard`, false for the anonymous landing hero.
 * @param {string=} props.startAssessmentRoute — override the default
 *   destination for the "Starting on My Own" card. Defaults to
 *   `/situation` so both unauth + authed users hit the topic picker.
 * @param {string=} props.continueRoute — override the "Continue"
 *   destination. Defaults to `/dashboard#more-tools` on dashboard.
 * @param {string=} props.testidPrefix — prefix for data-testids so
 *   we can differentiate landing vs dashboard mounts in tests.
 */
export default function FrontDoorHero({
  showContinue = false,
  startAssessmentRoute = "/situation",
  continueRoute = "/dashboard#more-tools",
  testidPrefix = "front-door-hero",
}) {
  return (
    <section
      className="bg-white rounded-3xl border border-[#EFE9F9] shadow-sm px-5 sm:px-8 py-8 sm:py-12"
      data-testid={testidPrefix}
    >
      <header className="text-center max-w-3xl mx-auto">
        <div className="text-[11px] uppercase tracking-[0.28em] font-bold text-[#3D1A78]">
          SA CoParents
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-tight mt-3"
          data-testid={`${testidPrefix}-headline`}
        >
          Start with your situation.
        </h1>
        <p
          className="text-base sm:text-lg text-[#4B4567] mt-4 leading-relaxed"
          data-testid={`${testidPrefix}-subhead`}
        >
          We&rsquo;ll guide you from there. Two clear paths — pick the one
          that fits how you&rsquo;re arriving today.
        </p>
      </header>

      {/* The two decisive cards. */}
      <div
        className="mt-10 grid gap-4 sm:grid-cols-2 max-w-4xl mx-auto"
        data-testid={`${testidPrefix}-choices`}
      >
        <FrontDoorCard
          testid={`${testidPrefix}-solo`}
          icon={User}
          eyebrow="Starting on My Own"
          headline="I want to explore my situation"
          body="For parents assessing their co-parenting relationship, identifying a child's needs, communication, safety concerns, or preparing for mediation."
          cta="Start My Assessment"
          to={startAssessmentRoute}
          tone="purple"
        />
        <FrontDoorCard
          testid={`${testidPrefix}-court`}
          icon={Scale}
          eyebrow="Court Ordered / Referred"
          headline="I have a case or access code"
          body="For parents ordered or referred by a court, judge, attorney, mediator, therapist, or parent facilitator."
          cta="Enter My Case / Access Code"
          to="/join"
          tone="teal"
        />
      </div>

      {/* Slim "already started" strip — only for authed dashboard mount. */}
      {showContinue && (
        <div
          className="mt-8 max-w-4xl mx-auto rounded-2xl border border-[#E5E0EE] bg-[#FAF8FD] px-5 py-4 flex items-center justify-between gap-4 flex-wrap"
          data-testid={`${testidPrefix}-continue`}
        >
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Already started?
            </div>
            <div className="text-sm text-[#4B4567] mt-1">
              Continue where you left off — reports, invitations, and every
              tool you&rsquo;ve unlocked are just below.
            </div>
          </div>
          <Link
            to={continueRoute}
            data-testid={`${testidPrefix}-continue-link`}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78]/25 hover:border-[#3D1A78] px-4 py-2 text-sm font-semibold text-[#3D1A78] transition"
          >
            Continue My Assessment
            <ArrowRight size={14} />
          </Link>
        </div>
      )}

      {/* Persistent "were you ordered/referred?" banner — keeps a
          solo-arriving parent from accidentally starting a new case
          when they actually have a code sitting in their inbox. */}
      <CourtOrderBanner testidPrefix={testidPrefix} />
    </section>
  );
}

function FrontDoorCard({ testid, icon: Icon, eyebrow, headline, body, cta, to, tone }) {
  const navigate = useNavigate();
  const palette = {
    purple: {
      border: "border-[#D6CFE8] hover:border-[#3D1A78]",
      chipBg: "bg-[#EFE9F9]",
      chipText: "text-[#3D1A78]",
      ctaBg: "bg-[#3D1A78] hover:bg-[#2A0F5F]",
      arrowText: "text-[#3D1A78]",
    },
    teal: {
      border: "border-[#B7E0E0] hover:border-[#0E7A7A]",
      chipBg: "bg-[#E4F3F3]",
      chipText: "text-[#0E7A7A]",
      ctaBg: "bg-[#0E7A7A] hover:bg-[#0B5F5F]",
      arrowText: "text-[#0E7A7A]",
    },
  }[tone] || {};
  return (
    <button
      type="button"
      onClick={() => navigate(to)}
      data-testid={testid}
      className={`group text-left rounded-3xl bg-white border-2 ${palette.border} p-6 sm:p-8 transition-all hover:-translate-y-0.5 hover:shadow-lg flex flex-col`}
    >
      <div className={`inline-flex items-center gap-2 self-start rounded-full ${palette.chipBg} ${palette.chipText} px-3 py-1 text-[10px] uppercase tracking-[0.22em] font-bold`}>
        <Icon size={12} strokeWidth={2.4} />
        {eyebrow}
      </div>
      <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-4 leading-tight">
        {headline}
      </h2>
      <p className="text-sm sm:text-[15px] text-[#4B4567] mt-3 leading-relaxed flex-1">
        {body}
      </p>
      <span
        className={`mt-5 inline-flex items-center gap-2 self-start rounded-full text-white ${palette.ctaBg} px-5 py-2.5 text-sm font-semibold transition-colors group-hover:gap-3`}
        data-testid={`${testid}-cta`}
      >
        {cta}
        <ArrowRight size={14} />
      </span>
    </button>
  );
}

function CourtOrderBanner({ testidPrefix }) {
  return (
    <div
      className="mt-6 max-w-4xl mx-auto rounded-2xl border border-[#F1D9B7] bg-[#FFF6EA] px-5 py-4 flex items-start gap-3 text-[13px] leading-relaxed"
      data-testid={`${testidPrefix}-court-banner`}
    >
      <KeyRound
        size={16}
        className="text-[#904B0E] flex-shrink-0 mt-0.5"
      />
      <div className="flex-1">
        <span className="text-[#5A3C10]">
          <strong>Were you ordered or referred to SA CoParents?</strong>{" "}
          Enter your court or professional access code instead of starting
          a new assessment —{" "}
        </span>
        <Link
          to="/join"
          data-testid={`${testidPrefix}-court-banner-link`}
          className="text-[#3D1A78] font-semibold hover:underline whitespace-nowrap"
        >
          Enter Access Code →
        </Link>
      </div>
    </div>
  );
}
