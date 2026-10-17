/**
 * Post-signup onboarding intake — "What would you like help with today?"
 *
 * Shown once, right after signup, before the dashboard. The parent
 * picks the option that matches why they came, we save that focus to
 * localStorage (piggybacking on the same `sac_recommended_focus_v1`
 * key the SituationPicker uses on Landing so the dashboard already
 * prioritises the right journey), and route them to the most helpful
 * starting page.
 *
 * A parent shouldn't have to understand the SA CoParents system before
 * SA CoParents can help them — the last option ("I'm not sure — I just
 * need a place to start") exists precisely for that.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Compass, Baby, MessageCircle, Scale, HeartHandshake, ArrowRightLeft,
  School, HelpCircle, Loader2, ArrowRight,
} from "lucide-react";
import { logError } from "../lib/logger";

const FOCUS_STORAGE_KEY = "sac_recommended_focus_v1";
const INTAKE_DONE_KEY = "sac_onboarding_intake_v1";

const CHOICES = [
  {
    key: "understand_coparenting",
    icon: Compass,
    label: "Understanding where our co-parenting stands",
    focus: "co-parenting-relationship",
    route: "/summary?tab=snc",
  },
  {
    key: "child_needs",
    icon: Baby,
    label: "Figuring out what my child needs",
    focus: "child-needs",
    route: "/special-needs",
  },
  {
    key: "prep_conversation",
    icon: MessageCircle,
    label: "Preparing for a conversation with my co-parent",
    focus: "prep-conversation",
    route: "/summary?tab=prep",
  },
  {
    key: "prep_mediation",
    icon: Scale,
    label: "Preparing for mediation",
    focus: "prep-mediation",
    route: "/dashboard",
  },
  {
    key: "school_health_issue",
    icon: School,
    label: "Working through a school, medical or emotional-health issue",
    focus: "school-health-issue",
    route: "/special-needs",
  },
  {
    key: "improve_communication",
    icon: HeartHandshake,
    label: "Improving communication",
    focus: "improve-communication",
    route: "/dashboard",
  },
  {
    key: "more_structure",
    icon: ArrowRightLeft,
    label: "Creating more structure between our two homes",
    focus: "structure-two-homes",
    route: "/summary?tab=prep",
  },
  {
    key: "not_sure",
    icon: HelpCircle,
    label: "I'm not sure — I just need a place to start",
    focus: "unsure",
    route: "/dashboard",
  },
];


export default function OnboardingIntake() {
  const navigate = useNavigate();
  const [picked, setPicked] = useState(null);
  const [continuing, setContinuing] = useState(false);

  const proceed = (choice) => {
    if (continuing) return;
    setContinuing(true);
    try {
      // Two flags: the focus is what the dashboard listens to; the
      // "intake done" flag stops us from ever showing this again.
      try { localStorage.setItem(FOCUS_STORAGE_KEY, choice.focus); }
      catch (e) { logError("intake focus set failed", e); }
      try { localStorage.setItem(INTAKE_DONE_KEY, "1"); }
      catch (e) { logError("intake done flag set failed", e); }
    } finally {
      // Even if storage is blocked (private mode), send them onward —
      // the app remains fully usable without the pinned focus.
      navigate(choice.route || "/dashboard", { replace: true });
    }
  };

  const skip = () => {
    try { localStorage.setItem(INTAKE_DONE_KEY, "1"); }
    catch (e) { logError("intake skip set failed", e); }
    navigate("/dashboard", { replace: true });
  };

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] px-4 py-10 sm:py-16"
      data-testid="onboarding-intake-root"
    >
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8 sm:mb-10">
          <div className="text-[0.625rem] uppercase tracking-[0.28em] font-bold text-[#3D1A78] mb-3">
            Welcome to SA CoParents
          </div>
          <h1
            className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-[1.1]"
            data-testid="onboarding-intake-title"
          >
            What would you like help with today?
          </h1>
          <p className="mt-5 text-sm sm:text-base text-[#4B4567] max-w-2xl mx-auto leading-relaxed">
            Pick whichever feels closest — you can change direction any
            time. There are no wrong answers, and you don&rsquo;t have to
            understand how SA CoParents works before we can help you.
          </p>
        </div>

        <div
          className="rounded-3xl bg-white/90 backdrop-blur-sm border border-[#E5E0EE] p-4 sm:p-6 shadow-sm"
          data-testid="onboarding-intake-choices"
        >
          <ul className="grid gap-2.5 sm:gap-3">
            {CHOICES.map((c) => {
              const isPicked = picked?.key === c.key;
              return (
                <li key={c.key}>
                  <button
                    type="button"
                    onClick={() => setPicked(c)}
                    onDoubleClick={() => proceed(c)}
                    disabled={continuing}
                    data-testid={`onboarding-choice-${c.key}`}
                    className={`w-full text-left rounded-2xl border p-4 flex items-center gap-4 transition-all ${
                      isPicked
                        ? "border-[#3D1A78] bg-[#F5F1FB] ring-2 ring-[#3D1A78]/20"
                        : "border-[#E5E0EE] bg-white hover:border-[#3D1A78]/60 hover:bg-[#F8F7FC]"
                    } disabled:opacity-60`}
                  >
                    <div
                      className={`shrink-0 w-11 h-11 rounded-full grid place-items-center transition-colors ${
                        isPicked
                          ? "bg-[#3D1A78] text-white"
                          : "bg-[#EFE9F9] text-[#3D1A78]"
                      }`}
                    >
                      <c.icon size={18} strokeWidth={2.2} />
                    </div>
                    <span
                      className={`text-sm sm:text-[15px] leading-snug ${
                        isPicked ? "text-[#1A1330] font-semibold" : "text-[#1A1330]"
                      }`}
                    >
                      {c.label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-5 flex items-center justify-between gap-3 flex-wrap">
            <button
              type="button"
              onClick={skip}
              disabled={continuing}
              data-testid="onboarding-intake-skip"
              className="text-sm text-[#4B4567] hover:text-[#3D1A78] hover:underline disabled:opacity-60"
            >
              Skip for now — go to my dashboard
            </button>
            <button
              type="button"
              onClick={() => picked && proceed(picked)}
              disabled={!picked || continuing}
              data-testid="onboarding-intake-continue"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-md"
            >
              {continuing ? (
                <><Loader2 size={14} className="animate-spin" /> Opening…</>
              ) : (
                <>Continue <ArrowRight size={14} /></>
              )}
            </button>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-[#6E6787]">
          Your account is ready. This intake is optional — everything is
          available from the dashboard whenever you&rsquo;re ready.
          <br />
          By continuing you agree to our{" "}
          <a href="/terms" className="underline hover:text-[#3D1A78]">
            Terms of Use
          </a>{" "}
          and{" "}
          <a href="/privacy" className="underline hover:text-[#3D1A78]">
            Privacy Policy
          </a>
          . SA CoParents provides educational conflict-management tools —
          not legal advice, therapy, or an attorney-client relationship.
        </p>
      </div>
    </div>
  );
}
