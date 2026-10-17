/**
 * PathwayEndCTA.jsx — the single, unambiguous "what's next" card that
 * closes every pathway (Co-Parenting Agreement, Communication, Safety,
 * Child Needs).
 *
 * Founder rule 2026-03-05: "End each pathway with one clear button so
 * parents never see two competing next steps." Toolbars (download,
 * regenerate, refresh) still live at the top of each report — those
 * are utilities, not next steps. This card sits at the very bottom of
 * the page and points to the single action that moves the pathway
 * forward.
 *
 * Usage:
 *   <PathwayEndCTA
 *     eyebrow="Communication pathway"
 *     title="Ready to send this to a mediator?"
 *     description="You've reflected and aligned — now share the report."
 *     primary={{ label: "Send to my mediator", to: "/professionals" }}
 *   />
 *
 * If the primary action is a callback (e.g., open a modal) pass
 * `primary.onClick` instead of `to`.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";

const TONE_STYLES = {
  purple: {
    ring: "border-[#3D1A78]/25",
    icon: "bg-[#3D1A78] text-white",
    eyebrow: "text-[#3D1A78]",
    button: "bg-[#3D1A78] hover:bg-[#2A0F5F] text-white",
  },
  green: {
    ring: "border-[#1E7A55]/25",
    icon: "bg-[#1E7A55] text-white",
    eyebrow: "text-[#1E7A55]",
    button: "bg-[#1E7A55] hover:bg-[#166241] text-white",
  },
  amber: {
    ring: "border-[#B45F13]/25",
    icon: "bg-[#B45F13] text-white",
    eyebrow: "text-[#904B0E]",
    button: "bg-[#B45F13] hover:bg-[#8A4610] text-white",
  },
  blue: {
    ring: "border-[#1E6FA8]/25",
    icon: "bg-[#1E6FA8] text-white",
    eyebrow: "text-[#1E6FA8]",
    button: "bg-[#1E6FA8] hover:bg-[#0E4C7A] text-white",
  },
};

export default function PathwayEndCTA({
  eyebrow,
  title,
  description,
  primary,
  tone = "purple",
  icon: Icon = Sparkles,
  testId = "pathway-end-cta",
}) {
  const style = TONE_STYLES[tone] || TONE_STYLES.purple;

  const ButtonInner = (
    <>
      {primary.label}
      <ArrowRight size={16} strokeWidth={2.4} />
    </>
  );

  return (
    <section
      className={`mt-10 rounded-3xl border-2 ${style.ring} bg-white p-6 sm:p-8 shadow-md`}
      data-testid={testId}
    >
      <div className="flex flex-col sm:flex-row items-start gap-5">
        <div
          className={`w-14 h-14 rounded-full grid place-items-center ${style.icon} shrink-0 shadow-md`}
          aria-hidden
        >
          <Icon size={24} strokeWidth={2.2} />
        </div>
        <div className="flex-1 min-w-0">
          {eyebrow && (
            <div
              className={`text-[0.625rem] uppercase tracking-[0.22em] font-bold ${style.eyebrow} mb-1`}
              data-testid={`${testId}-eyebrow`}
            >
              {eyebrow}
            </div>
          )}
          <h2
            className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight"
            data-testid={`${testId}-title`}
          >
            {title}
          </h2>
          {description && (
            <p className="text-[15px] text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
              {description}
            </p>
          )}
          <div className="mt-5">
            {primary.to ? (
              <Link
                to={primary.to}
                data-testid={`${testId}-primary`}
                className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-base font-semibold shadow-md hover:shadow-lg transition-all ${style.button}`}
              >
                {ButtonInner}
              </Link>
            ) : (
              <button
                type="button"
                onClick={primary.onClick}
                disabled={primary.disabled}
                data-testid={`${testId}-primary`}
                className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-base font-semibold shadow-md hover:shadow-lg transition-all disabled:opacity-60 ${style.button}`}
              >
                {ButtonInner}
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
