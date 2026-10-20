/**
 * PathwayReportUnlockHint — pre-share incentive card shown at the top of
 * a Compare hub when the parent has no fully-consented Compare yet.
 *
 * The idea (product ask iter 93): parents often stall out at the invite
 * step because they don't see enough downstream value. This card names
 * the concrete thing they unlock — the two-parent Dispute Resolution
 * Pathway Report — right where they're about to type their co-parent's
 * email address.
 *
 * Auto-hides if the parent already has an ACTIVE (ready-to-view) share,
 * because at that point the CTA card on the compare *view* is the right
 * place for the pathway report link, not here.
 *
 * Also offers a soft link to `/pathway-report` — the single-parent
 * preview shipped in iter 91 — so a curious parent can look at what the
 * report will look like against their own data first.
 */
import React from "react";
import { Link } from "react-router-dom";
import { Scale, Sparkles } from "lucide-react";


export default function PathwayReportUnlockHint({ shares = [], testidPrefix = "compare" }) {
  const anyActive = (shares || []).some(
    (s) => s.ready_to_view || s.status === "active",
  );
  if (anyActive) return null;

  return (
    <div
      className="mt-6 rounded-3xl border-2 border-dashed border-[#3D1A78]/25 bg-gradient-to-br from-[#F5F1FB] to-white p-5 sm:p-6"
      data-testid={`${testidPrefix}-pathway-unlock-hint`}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 h-9 w-9 rounded-full bg-[#3D1A78] text-white grid place-items-center">
          <Scale size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="inline-flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            <Sparkles size={11} /> Both of you also unlock
          </div>
          <div className="font-serif text-xl text-[#1A1330] leading-snug mt-1">
            The two-parent Dispute Resolution Pathway Report
          </div>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
            Once both parents complete the Companion and
            consent to compare, this app can identify which dispute
            resolution pathway warrants professional consideration:
            <strong> Mediation</strong>,
            <strong> Child-Centered Relational Mediation</strong>,
            <strong> Collaborative Family Law</strong>, or
            <strong> Litigation</strong>.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Link
              to="/pathway-report"
              data-testid={`${testidPrefix}-pathway-unlock-preview`}
              className="text-[0.75rem] font-semibold text-[#3D1A78] underline hover:text-[#0F7676]"
            >
              See a solo preview against your own data →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
