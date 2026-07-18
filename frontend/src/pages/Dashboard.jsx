import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import VerificationBanner from "../components/VerificationBanner";
import EmailHealthBanner from "../components/EmailHealthBanner";
import DemoModeBanner from "../components/DemoModeBanner";
import InviteCoparentCard from "../components/InviteCoparentCard";
import BadgeShelf from "../components/BadgeShelf";
import MeetTheProgramCard from "../components/MeetTheProgramCard";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { registerPushNotifications } from "../lib/native";
import { hasSeenOrientation } from "./Orientation";
import {
  Target,
  AlertCircle,
  ListOrdered,
  MessageCircle,
  HeartHandshake,
  FileText,
  Heart,
  Compass,
  ArrowRight,
  Sprout,
  ExternalLink,
} from "lucide-react";
import { logError } from "../lib/logger";

import { CheckCircle2, ChevronRight, Puzzle } from "lucide-react";

// Human-friendly labels for the compact Progress Report preview on the Dashboard.
const REPORT_LABEL = {
  child_goals: "Identify Your Child's Needs",
  issues: "Name Your Concerns",
  priority: "Rank Your Priorities",
  comm_style: "Co-Parenting Reflection",
  readiness: "Mediation Readiness",
};

const STEPS = [
  {
    key: "child_goals",
    label: "Child-Centered Goals",
    path: "/prep/child-goals",
    icon: Target,
    blurb: "What do you want your child to experience?",
    celebration: "You named what your child needs from you.",
    tip: "Children thrive on predictability. Pick one small routine to keep the same across both homes this week.",
  },
  {
    key: "issues",
    label: "Issues & Concerns",
    path: "/prep/issues",
    icon: AlertCircle,
    blurb: "Map schedule, communication, finances, safety.",
    celebration: "You named the issues honestly and without blame.",
    tip: "One issue per conversation. If you raise three concerns in one text, the other parent hears none of them.",
  },
  {
    key: "priority",
    label: "Priority & Agenda",
    path: "/prep/priority",
    icon: ListOrdered,
    blurb: "Rank what matters most — and where you flex.",
    celebration: "You know which battles are worth having, and which to let go.",
    tip: "Trade small things to protect big things. Be generous where it costs you little; hold firm where it protects your child.",
  },
  {
    key: "comm_style",
    label: "Communication Style",
    path: "/prep/communication",
    icon: MessageCircle,
    blurb: "Notice patterns; receive AI-coached suggestions.",
    celebration: "You noticed the patterns that shape your co-parenting.",
    tip: "Kids don't remember what you said. They remember how the room felt. Aim for one calm exchange today.",
  },
  {
    key: "readiness",
    label: "Readiness Check",
    path: "/prep/readiness",
    icon: HeartHandshake,
    blurb: "How prepared do you feel — honestly?",
    celebration: "You measured yourself honestly. That takes courage.",
    tip: "Sleep before mediation matters more than notes. Rested parents advocate better for their kids.",
  },
];

// Aspirational progress statements shown under the Dashboard progress bar.
// The phrasing is intentional — every parent should feel their prep is
// *transforming* the outcome for their child, not just ticking boxes.
function progressStatement(pct, done, total) {
  if (done === 0) return "The first step is the hardest. Start when you're ready.";
  if (pct === 100) return "You built a full, child-focused parenting plan. Bring it to mediation.";
  return `You're ${pct}% of the way toward a child-focused parenting plan.`;
}

// Time-of-day salutation. Uses the visitor's browser clock so the greeting
// matches the actual moment they log in, not the server's timezone.
function timeGreeting() {
  const h = new Date().getHours();
  if (h < 5) return "Good evening";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

// Average minutes a parent spends per prep step. Used to give an at-a-glance
// "how long till done?" estimate on the Dashboard hero card.
const AVG_MINUTES_PER_STEP = 6;

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [prep, setPrep] = useState({ completed: {} });
  const [summariesCount, setSummariesCount] = useState(0);

  // First-time visitors: send them through the orientation walkthrough.
  useEffect(() => {
    if (!hasSeenOrientation()) {
      navigate("/orientation", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => setPrep(r.data || { completed: {} }))
      .catch((err) => logError("Failed to load prep:", err));
    // Grab the summary count so the "Journey Complete" badge can unlock.
    api
      .get("/analytics/personal")
      .then((r) => setSummariesCount((r.data?.recent_summaries || []).length))
      .catch(() => {
        /* non-blocking */
      });
    // On native mobile builds only — no-op on web.
    registerPushNotifications(api);
  }, []);

  const completed = prep.completed || {};
  const completedKeys = STEPS.filter((s) => completed[s.key]).map((s) => s.key);
  const done = completedKeys.length;
  const pct = Math.round((done / STEPS.length) * 100);
  const nextStep = STEPS.find((s) => !completed[s.key]) || null;

  // "Day N of prep" — counted from when the user started their session
  // (or first wrote to prep_data, whichever came first).
  const startedAt = prep.created_at || user?.created_at;
  let dayOfPrep = 1;
  if (startedAt) {
    try {
      const days = Math.floor(
        (Date.now() - new Date(startedAt).getTime()) / 86_400_000
      );
      dayOfPrep = Math.max(1, days + 1);
    } catch (_e) {
      /* keep default */
    }
  }

  // Human-friendly "last touched" hint to reinforce continuity across visits.
  let lastTouchedLabel = null;
  if (prep.updated_at) {
    try {
      const updated = new Date(prep.updated_at);
      const diffMs = Date.now() - updated.getTime();
      const diffH = diffMs / 3_600_000;
      const diffD = diffMs / 86_400_000;
      if (diffH < 1) lastTouchedLabel = "Last touched just now";
      else if (diffH < 24) lastTouchedLabel = `Last touched ${Math.round(diffH)}h ago`;
      else if (diffD < 7) lastTouchedLabel = `Last touched ${Math.round(diffD)}d ago`;
      else lastTouchedLabel = `Last touched ${updated.toLocaleDateString()}`;
    } catch (_e) {
      /* keep null */
    }
  }

  const allDone = !nextStep;

  return (
    <AppShell>
      <div className="fade-up">
        <EmailHealthBanner />
        <VerificationBanner />
        <DemoModeBanner />
        <div className="grid lg:grid-cols-3 gap-6 mb-10 mt-6">
          <div className="card-soft p-8 lg:col-span-2 relative overflow-hidden">
            <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="eyebrow">Your space</span>
                <span
                  className="text-[10px] uppercase tracking-[0.15em] px-2 py-0.5 rounded-full bg-[#3D1A78]/10 text-[#3D1A78]"
                  data-testid="dashboard-day-of-prep"
                >
                  Day {dayOfPrep} of prep
                </span>
                {lastTouchedLabel && (
                  <span className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C]" data-testid="dashboard-last-touched">
                    · {lastTouchedLabel}
                  </span>
                )}
              </div>
              <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight" data-testid="dashboard-greeting">
                {timeGreeting()}, {user?.name?.split(" ")[0] || "friend"}.
              </h1>
              <p className="text-[#4B4567] mt-3 max-w-lg leading-relaxed">
                Mediation prep happens in pieces — over days, not minutes. Come back
                tomorrow. Pick up where you left off. Nothing here is graded.
              </p>
              <div className="flex items-center gap-4 mt-4 flex-wrap">
                <Link
                  to="/orientation"
                  className="inline-flex items-center gap-1.5 text-[12px] text-[#3D1A78] hover:text-[#2a0f5f] underline-offset-2 hover:underline"
                  data-testid="dashboard-revisit-orientation"
                >
                  <Compass size={12} /> Revisit the orientation walkthrough
                </Link>
                <Link
                  to="/progress"
                  className="inline-flex items-center gap-1.5 text-[12px] text-[#3D1A78] hover:text-[#2a0f5f] underline-offset-2 hover:underline"
                  data-testid="dashboard-view-progress"
                >
                  View my progress →
                </Link>
                <Link
                  to="/reflection"
                  className="inline-flex items-center gap-1.5 text-[12px] text-[#3D1A78] hover:text-[#2a0f5f] underline-offset-2 hover:underline"
                  data-testid="dashboard-open-journal"
                >
                  <Heart size={12} /> Open my journal
                </Link>
              </div>
              <div className="mt-6">
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-[#857E9C]">
                      Today&apos;s progress
                    </div>
                    <div className="font-serif text-3xl text-[#1A1330]">
                      {done} <span className="text-[#857E9C] text-xl">/ {STEPS.length}</span>
                    </div>
                  </div>
                  <div className="text-sm text-[#4B4567]">{pct}%</div>
                </div>
                <div className="h-2 bg-[#E5E0EE] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3D1A78] progress-fill"
                    style={{ width: `${pct}%` }}
                    data-testid="dashboard-progress-bar"
                  />
                </div>
                {!allDone && (
                  <div
                    className="mt-3 text-[11px] uppercase tracking-[0.2em] text-[#857E9C] flex items-center gap-1.5"
                    data-testid="dashboard-estimated-completion"
                  >
                    <Compass size={12} className="text-[#3D1A78]" />
                    Estimated completion ·{" "}
                    <span className="text-[#1A1330] normal-case tracking-normal font-semibold">
                      {(STEPS.length - done) * AVG_MINUTES_PER_STEP} min
                    </span>
                  </div>
                )}
                <ul className="mt-4 space-y-1.5" data-testid="dashboard-step-checklist">
                  {STEPS.map((s) => {
                    const isDone = !!completed[s.key];
                    return (
                      <li
                        key={s.key}
                        className="flex items-center gap-2.5 text-sm"
                        data-testid={`dashboard-checklist-${s.key}`}
                      >
                        {isDone ? (
                          <CheckCircle2
                            size={16}
                            className="text-[#3D1A78] shrink-0"
                            aria-label="Completed"
                          />
                        ) : (
                          <span
                            className="w-4 h-4 rounded border-2 border-[#D6CFE6] shrink-0"
                            aria-label="Not yet"
                          />
                        )}
                        <span
                          className={
                            isDone
                              ? "text-[#1A1330]"
                              : "text-[#4B4567]"
                          }
                        >
                          {s.label}
                        </span>
                      </li>
                    );
                  })}
                </ul>
                <p
                  className="text-sm text-[#4B4567] mt-4 leading-relaxed italic"
                  data-testid="dashboard-progress-statement"
                >
                  {progressStatement(pct, done, STEPS.length)}
                </p>
              </div>
            </div>
          </div>

          <div className="card-soft p-7 flex flex-col">
            <div className="eyebrow mb-2">
              {allDone ? "Ready when you are" : `Next up — Day ${dayOfPrep}`}
            </div>
            <div className="font-serif text-2xl text-[#1A1330] mb-1">
              {nextStep?.label || "Generate your summary"}
            </div>
            <p className="text-sm text-[#4B4567] mb-6">
              {nextStep?.blurb ||
                "You're prepared. Create your mediator-ready summary."}
            </p>
            <Link
              to={nextStep?.path || "/summary"}
              className="btn-sage w-full text-center inline-flex items-center justify-center gap-2"
              data-testid="dashboard-continue-button"
            >
              {allDone ? "Generate summary" : "Continue"} <ArrowRight size={16} />
            </Link>
            {!allDone && (
              <p className="text-[11px] text-[#857E9C] mt-3 text-center leading-relaxed">
                Tip: even 10 minutes of prep moves the needle.
              </p>
            )}
            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 mt-3">
              <Link
                to="/my-plan"
                className="text-sm text-[#3D1A78] hover:underline font-semibold"
                data-testid="dashboard-my-plan-link"
              >
                View Your Plan →
              </Link>
              <Link
                to="/summary"
                className="text-sm text-[#3D1A78] hover:underline"
                data-testid="dashboard-summary-link"
              >
                Go to summary
              </Link>
            </div>
          </div>
        </div>

        <a
          href="/images/sa-coparents-collage.png"
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-3xl overflow-hidden border border-[#E5E0EE] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all mb-10 group"
          data-testid="dashboard-collage-band"
          aria-label="Open the SA Coparents co-parenting overview poster"
        >
          <img
            src="/images/sa-coparents-collage.png"
            alt="SA Coparents co-parenting overview: reflect, prepare, connect for a better co-parenting relationship."
            loading="lazy"
            className="w-full h-auto block bg-[#F8F6EE] group-hover:brightness-[1.03] transition-[filter]"
          />
        </a>

        {/* Compact Progress Report teaser — links to /progress for the full report */}
        {done > 0 && (
          <Link
            to="/progress"
            className="block rounded-3xl bg-white border border-[#E5E0EE] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all mb-8"
            data-testid="dashboard-progress-report-teaser"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="eyebrow mb-1">Progress Report</div>
                <div className="flex items-center gap-2 text-sm text-[#1A1330] mb-1">
                  <CheckCircle2 size={14} className="shrink-0 text-[#3D1A78]" />
                  <span className="truncate">
                    {done === 1 ? "1 step completed" : `${done} steps completed`}
                    {completedKeys.length > 0 && (
                      <>
                        {" — "}
                        <span className="text-[#4B4567]">
                          {REPORT_LABEL[completedKeys[completedKeys.length - 1]]}
                        </span>
                      </>
                    )}
                  </span>
                </div>
                {nextStep && (
                  <div className="text-sm text-[#4B4567]">
                    <span className="font-bold text-[#3D1A78]">Next step:</span>{" "}
                    {REPORT_LABEL[nextStep.key] || nextStep.label}
                  </div>
                )}
                {!nextStep && (
                  <div className="text-sm text-[#1F5C3B]">
                    <span className="font-bold">All prep steps complete.</span>{" "}
                    Bring your Summary to mediation.
                  </div>
                )}
              </div>
              <div className="shrink-0 inline-flex items-center gap-1 text-sm text-[#3D1A78] font-bold">
                See full report
                <ChevronRight size={14} />
              </div>
            </div>
          </Link>
        )}

        {/* Achievement badge shelf */}
        <div className="mb-10">
          <BadgeShelf
            progress={{ completed: completedKeys }}
            summariesCount={summariesCount}
          />
        </div>

        {/* 21-second Meet the Program trailer — playable + downloadable share asset */}
        <div className="mb-4">
          <MeetTheProgramCard trailerId="meet-the-program" />
        </div>

        {/* 45-second Three Reports trailer — Conflict Assessment, Foundation Statement, Mediation Declaration */}
        <div className="mb-10">
          <MeetTheProgramCard trailerId="three-reports" />
        </div>

        {/* Welcome coaching video — plays with the same "before you begin" voice-over
            but uses the wide "Better co-parenting starts with a plan" hero. */}
        <div className="mb-8">
          <div className="eyebrow mb-3">Start here</div>
          <MeetTheProgramCard trailerId="dashboard-welcome" />
        </div>

        <div className="eyebrow mb-4">Preparation modules</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {STEPS.map(({ key, label, path, icon: Icon, blurb, celebration, tip }) => {
            const isDone = !!completed[key];
            return (
              <Link
                to={path}
                key={key}
                className="card-soft p-6 hover:-translate-y-0.5 transition-transform group flex flex-col"
                data-testid={`dashboard-step-${key}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className={`w-11 h-11 rounded-full grid place-items-center ${
                      isDone ? "bg-[#3D1A78] text-white" : "bg-[#EFE9F9] text-[#3D1A78]"
                    }`}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-[#857E9C]">
                    {isDone ? "Today's accomplishment" : "To do"}
                  </div>
                </div>
                <div className="font-serif text-xl text-[#1A1330] mb-1">{label}</div>
                <p className="text-sm text-[#4B4567]">
                  {isDone ? celebration : blurb}
                </p>
                {isDone && tip && (
                  <div
                    className="mt-4 pt-4 border-t border-[#E5E0EE] flex items-start gap-2"
                    data-testid={`dashboard-step-${key}-tip`}
                  >
                    <div className="shrink-0 mt-0.5 w-6 h-6 rounded-full bg-[#DCEEDF] text-[#1F5C3B] grid place-items-center">
                      <Sprout size={12} />
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#1F5C3B] mb-1">
                        Tip you unlocked
                      </div>
                      <p className="text-xs text-[#4B4567] leading-relaxed">{tip}</p>
                    </div>
                  </div>
                )}
              </Link>
            );
          })}

          <Link
            to="/summary"
            className="card-soft p-6 hover:-translate-y-0.5 transition-transform bg-gradient-to-br from-[#EFE9F9] to-[#FFFFFF]"
            data-testid="dashboard-summary-card"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-11 h-11 rounded-full grid place-items-center bg-[#C28771]/15 text-[#C28771]">
                <FileText size={18} />
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#857E9C]">
                Final
              </div>
            </div>
            <div className="font-serif text-xl text-[#1A1330] mb-1">Mediation Summary</div>
            <p className="text-sm text-[#4B4567]">
              AI-synthesized, mediator-ready, downloadable PDF.
            </p>
          </Link>

          <Link
            to="/reflection"
            className="card-soft p-6 hover:-translate-y-0.5 transition-transform"
            data-testid="dashboard-reflection-card"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-11 h-11 rounded-full grid place-items-center bg-[#C28771]/15 text-[#C28771]">
                <Heart size={18} />
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#857E9C]">
                Optional
              </div>
            </div>
            <div className="font-serif text-xl text-[#1A1330] mb-1">Personal Reflection</div>
            <p className="text-sm text-[#4B4567]">
              Private journal + 4-7-8 breathing. Listen to your wiser self.
            </p>
          </Link>
        </div>

        {!user?.is_guest && (
          <div className="mt-2">
            <InviteCoparentCard variant="dashboard" />
          </div>
        )}

        {/* Special Needs Assessment optional pathway */}
        <div className="mt-6">
          <Link
            to="/neurodivergent"
            data-testid="dashboard-neurodivergent-card"
            className="group flex items-center gap-4 rounded-3xl bg-white border border-[#E5E0EE] hover:border-[#3D1A78] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
          >
            <div className="shrink-0 w-12 h-12 rounded-full bg-[#F1EBFA] grid place-items-center text-[#3D1A78]">
              <Puzzle size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
                Special Needs Assessment
              </div>
              <div className="font-serif text-xl text-[#1A1330] leading-tight mb-1">
                Does your child need additional support?
              </div>
              <p className="text-xs sm:text-sm text-[#4B4567] leading-relaxed">
                A 6-pillar, evidence-informed pathway for co-parents whose
                child has neurodivergence, developmental, medical, mental
                health, behavioural, or trauma-informed needs. Generates three
                warm reports to share with a co-parent, teacher, or therapist.
              </p>
            </div>
            <ChevronRight size={16} className="shrink-0 text-[#3D1A78]" />
          </Link>
        </div>

        <div className="mt-8">
          <div className="eyebrow mb-4">For the kids</div>
          <div className="grid gap-4 sm:grid-cols-2">
            <a
              href="https://www.seedsforsuccess.net"
              target="_blank"
              rel="noopener noreferrer"
              data-testid="dashboard-seeds-for-success-card"
              className="group flex items-center gap-4 rounded-3xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white p-5 sm:p-6 shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
            >
              <div className="shrink-0 w-12 h-12 rounded-full bg-white/15 grid place-items-center">
                <Sprout size={22} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold opacity-90 mb-0.5">
                  Support for children of divorce
                </div>
                <div className="font-serif text-xl leading-tight mb-1">
                  Seeds for Success · Website
                </div>
                <p className="text-xs sm:text-sm opacity-95 leading-relaxed">
                  Tools and guidance to help kids feel heard, safe, and supported.
                </p>
              </div>
              <ExternalLink size={16} className="shrink-0 opacity-80" />
            </a>

            <a
              href="https://www.facebook.com/61581958982281"
              target="_blank"
              rel="noopener noreferrer"
              data-testid="dashboard-seeds-facebook-card"
              className="group flex items-center gap-4 rounded-3xl bg-white text-[#1A1330] border border-[#E5E0EE] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
            >
              <div className="shrink-0 w-12 h-12 rounded-full bg-[#1877F2] text-white grid place-items-center font-black text-lg">
                f
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
                  Follow the community
                </div>
                <div className="font-serif text-xl leading-tight mb-1">
                  Seeds for Success · Facebook
                </div>
                <p className="text-xs sm:text-sm text-[#4B4567] leading-relaxed">
                  San Antonio-based, child-focused. Posts for divorcing parents.
                </p>
              </div>
              <ExternalLink size={16} className="shrink-0 text-[#857E9C]" />
            </a>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
