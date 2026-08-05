import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import VerificationBanner from "../components/VerificationBanner";
import EmailHealthBanner from "../components/EmailHealthBanner";
import DemoModeBanner from "../components/DemoModeBanner";
import FivePillarJourney from "../components/FivePillarJourney";
import NextStepJourney from "../components/NextStepJourney";
import PickerChoicePill from "../components/PickerChoicePill";
import InviteCoparentCard from "../components/InviteCoparentCard";
import BadgeShelf from "../components/BadgeShelf";
import MeetTheProgramCard from "../components/MeetTheProgramCard";
import GrowthWidget from "../components/GrowthWidget";
import ProgressDashboardCard from "../components/ProgressDashboardCard";
import PublicMilestoneWall from "../components/PublicMilestoneWall";
import WeeklyEmailPreview from "../components/WeeklyEmailPreview";
import LearningCenterCard from "../components/LearningCenterCard";
import YourReportsCard from "../components/YourReportsCard";
import GmailMiniInbox from "../components/GmailMiniInbox";
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
  Handshake,
  AlertTriangle,
  ShieldCheck,
  Baby,
  Scale,
  BookOpen,
  Stethoscope,
  Brain,
} from "lucide-react";
import { logError } from "../lib/logger";

import { CheckCircle2, ChevronRight, ChevronDown, Shield, Sparkles, RefreshCcw, Users, Eye, Trophy } from "lucide-react";

// Six situations that route the visitor to the safest / most relevant
// next step. Mirrors the language and order used on the Landing page so
// pre- and post-signup experiences feel identical.
const INLINE_SITUATIONS = [
  { key: "cooperate",     label: "We generally cooperate",
    icon: <Handshake size={18} />,       route: "#next-step" },
  { key: "difficult",     label: "Communication is difficult",
    icon: <MessageCircle size={18} />,   route: "#next-step" },
  { key: "high-conflict", label: "We experience ongoing high conflict",
    icon: <AlertTriangle size={18} />,   route: "/safety-assessment" },
  { key: "safety",        label: "I have safety or family-violence concerns",
    icon: <ShieldCheck size={18} />,     route: "/safety-assessment" },
  { key: "special-needs", label: "Our child has unique educational, psychological or medical needs",
    icon: <Baby size={18} />,            route: "/special-needs-v2" },
  { key: "mediation",     label: "I am preparing for mediation or court",
    icon: <Scale size={18} />,           route: "#next-step" },
];

// Situation-memory storage.  We remember the parent's latest pick so
// return visits can highlight the matching prep module in the jump-menu
// and offer a one-tap "you chose X - change my answer" reset instead of
// re-asking the question every login.  Persisted in localStorage so it
// survives page refresh but never crosses devices (that's the correct
// scope — a returning parent on the same browser).
const SITUATION_KEY = "sacoparents_situation_choice_v1";

function readSituation() {
  try {
    return window.localStorage.getItem(SITUATION_KEY) || null;
  } catch {
    return null;
  }
}
function saveSituation(key) {
  try { window.localStorage.setItem(SITUATION_KEY, key); }
  catch { /* private-mode / disabled storage — non-critical */ }
}
function clearSituation() {
  try { window.localStorage.removeItem(SITUATION_KEY); }
  catch { /* best-effort */ }
}

// Maps a situation key to the prep-module keys that best match it.  Used
// to highlight the recommended module(s) in the Preparation Modules card.
// "special-needs" highlights BOTH the Educational and Psychological
// modules because a child with unique needs almost always benefits from
// both alignment checks (learning support + emotional regulation).
const SITUATION_TO_RECOMMENDED_MODULES = {
  "cooperate":     ["mediation-summary"],
  "difficult":     ["mediation-summary"],
  "high-conflict": ["safety-assessment"],
  "safety":        ["safety-assessment"],
  "special-needs": ["educational-assessment", "psychological-assessment"],
  "mediation":     ["mediation-summary"],
};

// The six preparation modules the app builds a PDF for. Rendered as a
// jump-menu below the situation picker so parents can dive straight in.
const PREP_MODULES = [
  { key: "declaration",   label: "Declaration Statement",
    hint: "A one-page statement of your child-focused position.",
    icon: <FileText size={16} />,        route: "/summary" },
  { key: "mediation-summary", label: "Mediation Summary",
    hint: "Your polished, printable brief for the mediator.",
    icon: <Scale size={16} />,           route: "/summary" },
  { key: "safety-assessment", label: "Family Violence & Safety Assessment",
    hint: "Private safety screen; recommends a communication pathway.",
    icon: <ShieldCheck size={16} />,     route: "/safety-assessment" },
  { key: "educational-assessment", label: "Educational Assessment",
    hint: "25-item Special-Ed & ADHD alignment scorer.",
    icon: <BookOpen size={16} />,        route: "/special-needs-v2/educational-deep-dive" },
  { key: "medical-assessment", label: "Medical Assessment",
    hint: "Medical-decision alignment deep dive.",
    icon: <Stethoscope size={16} />,     route: "/special-needs-v2/medical-deep-dive" },
  { key: "psychological-assessment", label: "Psychological Assessment",
    hint: "Emotional / therapy-decision alignment deep dive.",
    icon: <Brain size={16} />,           route: "/special-needs-v2/psychological-deep-dive" },
];

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
    label: "Child-Focused Goals",
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

/**
 * FivePillarJourneyToolkit — the classic 5-pillar view demoted to a
 * collapsible "Full toolkit" section, so it stops competing with the
 * new linear NextStepJourney at the top of the Dashboard.
 *
 * The parent can still reach every module — it's just no longer the
 * first thing they see. Progressive disclosure over overwhelming grids.
 */
function FivePillarJourneyToolkit({ completed, pillarFlags }) {
  return (
    <details className="mt-4 group" data-testid="toolkit-collapsible">
      <summary
        className="cursor-pointer list-none rounded-2xl border border-[#E5E0EE] bg-white px-5 py-4 flex items-center justify-between hover:border-[#3D1A78] transition-colors"
        data-testid="toolkit-summary"
      >
        <div>
          <div className="eyebrow text-[#3D1A78]">Full toolkit</div>
          <div className="text-sm text-[#4B4567] mt-0.5">
            Every module, assessment, and report — organised by the 5 pillars
            of relational mediation prep.
          </div>
        </div>
        <span className="text-[#3D1A78] text-sm font-bold group-open:hidden">
          Show →
        </span>
        <span className="hidden group-open:inline text-[#3D1A78] text-sm font-bold">
          Hide ↑
        </span>
      </summary>
      <div className="mt-4">
        <FivePillarJourney completed={completed} flags={pillarFlags} />
      </div>
    </details>
  );
}

/**
 * DashboardMoreResources — progressive disclosure wrapper for new users.
 *
 * The dashboard packs a lot: badges, three trailer cards, the classic
 * toolkit, invite-a-coparent nudges, Special Needs + Safety pathway
 * cards, and external community resources. That's the right density for
 * a parent who has been in the app for a week — but it's overwhelming
 * on first visit.
 *
 * For new users (fewer than 3 completed prep steps) we collapse all
 * that content behind a single "More resources" toggle. Returning users
 * see it inline as before.
 */
function DashboardMoreResources({ collapsed, children }) {
  if (!collapsed) return <>{children}</>;
  return (
    <details className="mt-8 group" data-testid="dashboard-more-resources">
      <summary
        className="cursor-pointer list-none rounded-full border border-[#E5E0EE] bg-white px-5 py-3 inline-flex items-center gap-2 text-sm font-semibold text-[#3D1A78] hover:border-[#3D1A78] hover:shadow-md transition-all"
        data-testid="dashboard-more-resources-summary"
      >
        <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
        More resources — badges, videos, toolkit, external links
      </summary>
      <div className="mt-6 space-y-6">
        {children}
      </div>
    </details>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [prep, setPrep] = useState({ completed: {} });
  const [summariesCount, setSummariesCount] = useState(0);
  const [pillarFlags, setPillarFlags] = useState({
    hasSummary: false,
    hasNdAnswers: false,
    hasNdReports: false,
    hasSafetyAssessment: false,
    hasCertificate: false,
  });
  const [sncStatus, setSncStatus] = useState(null);
  const [sncHighlights, setSncHighlights] = useState(null);
  const [deepDives, setDeepDives] = useState(null);
  const [compareStatus, setCompareStatus] = useState(null);
  // Situation memory — reads the last situation the parent picked so
  // we can highlight the matching prep module + show a "you chose X"
  // reset chip instead of re-asking the same question every login.
  const [situationChoice, setSituationChoice] = useState(readSituation);
  const recommendedModules = situationChoice
    ? SITUATION_TO_RECOMMENDED_MODULES[situationChoice] || []
    : [];
  const rememberSituation = (key) => {
    saveSituation(key);
    setSituationChoice(key);
  };
  const forgetSituation = () => {
    clearSituation();
    setSituationChoice(null);
  };

  // First-time visitors: send them through the orientation walkthrough.
  useEffect(() => {
    if (!hasSeenOrientation()) {
      navigate("/orientation", { replace: true });
    }
  }, [navigate]);

  // Weekly Progress Email — auto-fire on Sunday (UTC) if we haven't sent
  // one yet this ISO week. Silent no-op every other day. Backend enforces
  // idempotency, so multiple browser tabs on Sunday are safe.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.get("/dashboard/weekly-email/status");
        const should = s.data?.is_sunday_utc && !s.data?.sent_this_week;
        if (!should || cancelled) return;
        await api.post("/dashboard/weekly-email/send", {});
      } catch {
        /* Email is best-effort — silent on failure. */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => setPrep(r.data || { completed: {} }))
      .catch((err) => logError("Failed to load prep:", err));
    // Grab the summary count so downstream badges/journey stages can unlock.
    api
      .get("/analytics/me")
      .then((r) => {
        const s = r.data?.activity?.summaries ?? 0;
        setSummariesCount(s);
        setPillarFlags((p) => ({ ...p, hasSummary: s > 0 }));
      })
      .catch(() => {
        /* non-blocking */
      });

    // Enrich pillar completion flags from the other feature endpoints.
    api
      .get("/safety-assessment/me")
      .then((r) => {
        // Endpoint returns null if not yet taken, or an object with answers otherwise.
        const answered = !!(r.data && (r.data.answers || r.data.risk_level || r.data.id));
        setPillarFlags((p) => ({ ...p, hasSafetyAssessment: answered }));
      })
      .catch(() => { /* non-blocking */ });
    api
      .get("/mediation/certificate/eligibility")
      .then((r) => {
        // Only mark the pillar tool as "done" when the parent has actually
        // hit the completion bar (not just because a demo user can preview).
        const d = r.data || {};
        const completed = (d.completed_steps || []).length;
        const threshold = d.threshold || 5;
        setPillarFlags((p) => ({ ...p, hasCertificate: completed >= threshold }));
      })
      .catch(() => { /* non-blocking */ });

    // On native mobile builds only — no-op on web.
    registerPushNotifications(api);

    // Special Needs Co-Parenting v2 — pull cached-report status for the dashboard card.
    api
      .get("/snc2/report/status")
      .then((r) => setSncStatus(r.data || null))
      .catch(() => { /* non-blocking */ });

    // SNC v2 co-parent comparison "you already agree" highlights for the Growth Wins card.
    api
      .get("/snc2/compare/dashboard/highlights")
      .then((r) => setSncHighlights(r.data || null))
      .catch(() => { /* non-blocking */ });

    // Optional deep-dives progress (Educational / Psychological / Medical).
    api
      .get("/deep-dives/status")
      .then((r) => setDeepDives(r.data || null))
      .catch(() => { /* non-blocking */ });

    // Compare-with-co-parent widget: per-pathway active-share counts.
    api
      .get("/deep-dives/compare-status")
      .then((r) => setCompareStatus(r.data || null))
      .catch(() => { /* non-blocking */ });
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

        {/* Reminder pill for parents who arrived via the landing situation
            picker. Renders only when localStorage has a chosen focus. */}
        <PickerChoicePill />

        {/* Step 1 — "What best describes your situation?" opener.
            Deliberately the FIRST thing above the fold so the greeting a
            parent sees isn't a generic time-of-day but a targeted "let's
            route you to the safest next step" prompt.  Remembers the last
            answer in localStorage so a returning parent gets a soft
            "you chose X - change my answer" instead of the full grid. */}
        <div
          className="mt-4 rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm"
          data-testid="dashboard-step1-hero"
        >
          <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
            Step 1
          </div>
          <h1
            className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight"
            data-testid="dashboard-greeting"
          >
            What best describes your situation
            {user?.name ? `, ${user.name.split(" ")[0]}?` : "?"}
          </h1>
          {situationChoice ? (
            <div
              className="mt-4 flex items-center gap-3 flex-wrap"
              data-testid="dashboard-situation-remembered"
            >
              <div className="inline-flex items-center gap-2 rounded-full bg-[#EFE9F9] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold">
                {(() => {
                  const meta = INLINE_SITUATIONS.find((s) => s.key === situationChoice);
                  return meta ? (
                    <>
                      {meta.icon}
                      <span>You chose: {meta.label}</span>
                    </>
                  ) : <span>Situation remembered</span>;
                })()}
              </div>
              <button
                type="button"
                onClick={forgetSituation}
                className="text-xs text-[#4B4567] hover:text-[#3D1A78] hover:underline"
                data-testid="dashboard-situation-reset"
              >
                Change my answer
              </button>
            </div>
          ) : (
            <>
              <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-2xl">
                There are no wrong answers. Your choice routes you straight
                to the safest and most relevant next step for your family.
              </p>
              <div
                className="mt-5 grid sm:grid-cols-2 gap-2.5"
                data-testid="dashboard-situation-inline-picker"
              >
                {INLINE_SITUATIONS.map((s) => (
                  <Link
                    key={s.key}
                    to={s.route}
                    onClick={() => rememberSituation(s.key)}
                    className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-center gap-3"
                    data-testid={`dashboard-situation-${s.key}`}
                  >
                    <div className="shrink-0 w-9 h-9 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center group-hover:bg-[#3D1A78] group-hover:text-white transition-colors">
                      {s.icon}
                    </div>
                    <span className="text-sm sm:text-[15px] text-[#1A1330] leading-snug">
                      {s.label}
                    </span>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Gmail mini inbox — dashboard peek at the 5 most-recent
            messages so parents can read + reply to a co-parent without
            leaving. When not connected, shows a compact CTA. */}
        <div className="mt-6" data-testid="dashboard-gmail-mini-slot">
          <GmailMiniInbox />
        </div>

        {/* Primary "Do this next" home — auto-detects the parent's current
            stage on the 6-step linear journey and surfaces one big action.
            #next-step anchor is targeted by the situation picker above so
            "cooperate / difficult / mediation" all scroll here. */}
        <div id="next-step" className="mt-6">
          <NextStepJourney
            completed={completed}
            summariesCount={summariesCount}
            hasCertificate={pillarFlags.hasCertificate}
          />
        </div>

        {/* Preparation modules jump-menu — six documents the app can
            generate a downloadable PDF for. Deep-links let a returning
            parent skip straight to the module they came here for. */}
        <div
          className="mt-6 rounded-3xl border border-[#E5E0EE] bg-[#FAF8FD] p-5 sm:p-6"
          data-testid="dashboard-prep-modules"
        >
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
                Preparation modules
              </div>
              <div className="font-serif text-lg text-[#1A1330] mt-1">
                Six documents the app can build for you
              </div>
            </div>
            <div className="text-xs text-[#4B4567]">
              Each one generates a downloadable PDF.
            </div>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {PREP_MODULES.map((m) => {
              const isRec = recommendedModules.includes(m.key);
              return (
                <Link
                  key={m.key}
                  to={m.route}
                  className={`group text-left rounded-2xl px-4 py-3 transition-colors flex items-start gap-3 ${
                    isRec
                      ? "border-2 border-[#3D1A78] bg-white shadow-sm hover:bg-[#F7F4FC]"
                      : "border border-[#E5E0EE] bg-white hover:border-[#3D1A78] hover:bg-[#F7F4FC]"
                  }`}
                  data-testid={`dashboard-prep-module-${m.key}`}
                  data-recommended={isRec ? "true" : undefined}
                >
                  <div
                    className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                      isRec
                        ? "bg-[#3D1A78] text-white"
                        : "bg-[#EFE9F9] text-[#3D1A78] group-hover:bg-[#3D1A78] group-hover:text-white"
                    }`}
                  >
                    {m.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="text-sm font-semibold text-[#1A1330] truncate">
                        {m.label}
                      </div>
                      {isRec && (
                        <span
                          className="text-[9px] uppercase tracking-[0.16em] font-bold text-white bg-[#3D1A78] rounded-full px-2 py-0.5"
                          data-testid={`dashboard-prep-module-${m.key}-recommended`}
                        >
                          Recommended for you
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[#4B4567] mt-0.5">{m.hint}</div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Five-milestone visual progress — small, high-signal ✓ pills that
            light up as parents complete Foundation, Child needs, Comms,
            Mediation prep, and Conflict-reduced criteria. */}
        <div className="mt-6">
          <ProgressDashboardCard />
        </div>

        {/* Your Reports — compact launcher showing which reports are ready
            vs in progress vs not started. Third above-the-fold block. */}
        <div className="mt-6">
          <YourReportsCard
            summariesCount={summariesCount}
            sncStatus={sncStatus}
            deepDives={deepDives}
            compareStatus={compareStatus}
          />
        </div>

        {/* Everything else lives inside "Explore more tools" — kept, not
            removed, so a stressed parent's first fold stays focused on
            Do This Next / Your Progress / Your Reports. */}
        <details
          className="mt-8 group"
          data-testid="dashboard-explore-more-tools"
        >
          <summary
            className="cursor-pointer list-none rounded-full border border-[#E5E0EE] bg-white px-5 py-3 inline-flex items-center gap-2 text-sm font-semibold text-[#3D1A78] hover:border-[#3D1A78] hover:shadow-md transition-all"
            data-testid="dashboard-explore-more-toggle"
          >
            <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
            Explore more tools — community, weekly email, learning center, and more
          </summary>
          <div className="mt-6 space-y-6">

        {/* Opt-in community wall — anonymised badges other parents earned
            this month, so first-timers feel momentum from the community. */}
        <div>
          <PublicMilestoneWall />
        </div>

        {/* Inline preview of the parent's upcoming Sunday email so they see
            exactly what will land in their inbox and can force a send. */}
        <div>
          <WeeklyEmailPreview />
        </div>

        {/* Learning Center entry — short reads on communication, boundaries,
            and mediation prep. Deliberately separate from the milestone system. */}
        <div>
          <LearningCenterCard />
        </div>

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
              <h1
                className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight"
                data-testid="dashboard-greeting-secondary"
              >
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

        <DashboardMoreResources collapsed={done < 3}>

        <a
          href="/images/sa-coparents-collage.png"
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-3xl overflow-hidden border border-[#E5E0EE] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all mb-10 group"
          data-testid="dashboard-collage-band"
          aria-label="Open the SA CoParents co-parenting overview poster"
        >
          <img
            src="/images/sa-coparents-collage.png"
            alt="SA CoParents co-parenting overview: reflect, prepare, connect for a better co-parenting relationship."
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

        {/* Compact growth pulse — hides itself for first-time visitors with
            no summary snapshots yet. Deep-links to the full growth tracker
            on /my-plan. */}
        <GrowthWidget />

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

        <FivePillarJourneyToolkit
          completed={completed}
          pillarFlags={pillarFlags}
        />

        <details className="mt-8 group">
          <summary className="cursor-pointer text-sm text-[#3D1A78] hover:underline inline-flex items-center gap-1" data-testid="dashboard-legacy-modules-toggle">
            Show the classic step-by-step module view →
          </summary>
          <div className="mt-4">
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
              A structured, child-focused report with technology-assisted drafting. Review before sharing.
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
          </div>
        </details>

        {!user?.is_guest && (
          <div className="mt-2">
            <InviteCoparentCard variant="dashboard" />
          </div>
        )}

        {/* Special Needs Co-Parenting (v2) */}
        <div className="mt-6">
          <Link
            to={sncStatus?.has_report ? "/special-needs-v2/report" : "/special-needs-v2"}
            data-testid="dashboard-snc-card"
            className="group flex items-center gap-4 rounded-3xl bg-gradient-to-br from-[#1A1330] to-[#3D1A78] text-white border border-[#3D1A78] hover:brightness-110 p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
          >
            <div className="shrink-0 w-12 h-12 rounded-full bg-white/15 grid place-items-center text-white">
              <Sparkles size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#CFC1EA] mb-0.5">
                Special Needs Co-Parenting · new
              </div>
              <div className="font-serif text-xl leading-tight mb-1">
                Organise the concern, understand the recommendations, build a plan.
              </div>
              <p className="text-xs sm:text-sm text-[#CFC1EA] leading-relaxed">
                Choose whether the concern is medical, educational,
                psychological or behavioural, or a mix. The assessment walks
                you through eight steps and produces a child-focused report you
                can share with your co-parent, mediator, or treating
                professionals.
              </p>
              {sncStatus?.has_report && (
                <div
                  className="mt-2 inline-flex items-center gap-2 text-[11px] text-[#CFC1EA]"
                  data-testid="dashboard-snc-report-status"
                >
                  <span>
                    {sncStatus.stale
                      ? "Answers updated since last report"
                      : "Report ready"}
                  </span>
                  {sncStatus.generated_at && (
                    <span className="opacity-70">
                      · last generated {new Date(sncStatus.generated_at).toLocaleDateString()}
                    </span>
                  )}
                  {sncStatus.stale && <RefreshCcw size={11} />}
                </div>
              )}
            </div>
            <ChevronRight size={16} className="shrink-0 text-[#CFC1EA]" />
          </Link>
        </div>

        {/* Growth Wins — "you already agree" highlights from the co-parent comparison */}
        {sncHighlights?.ready && (sncHighlights.highlights || []).length > 0 && (
          <div className="mt-4" data-testid="dashboard-snc-highlights">
            <Link
              to={`/special-needs-v2/compare/${sncHighlights.share_id}`}
              className="group block rounded-3xl border border-[#B5DFC5] bg-[#F1F9F4] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
            >
              <div className="flex items-center gap-2 text-[#1F5C3B]">
                <Sparkles size={16} />
                <span className="text-[10px] uppercase tracking-[0.22em] font-bold">Where you already agree</span>
              </div>
              <div className="mt-1 font-serif text-lg text-[#1A1330]">
                {sncHighlights.aligned_pct}% aligned with {sncHighlights.partner_name || "your co-parent"}
              </div>
              <p className="text-xs text-[#4B4567] mt-1 mb-3">
                Top wins from your Special Needs comparison. Start your next conversation from your shared ground.
              </p>
              <ol className="space-y-2">
                {(sncHighlights.highlights || []).slice(0, 3).map((h, i) => (
                  <li
                    key={h.section_id && h.item_id ? `${h.section_id}-${h.item_id}` : `dh-${i}-${(h.prompt || "").slice(0, 30)}`}
                    className="flex items-start gap-3"
                    data-testid={`dashboard-highlight-${i}`}
                  >
                    <div className="shrink-0 mt-0.5 w-6 h-6 rounded-full bg-[#1F5C3B] text-white text-[11px] font-bold flex items-center justify-center">{i + 1}</div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-[#1A1330] font-semibold leading-snug truncate">{h.prompt}</div>
                      <div className="text-xs text-[#1F5C3B]">{h.summary}</div>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="mt-3 text-[11px] font-semibold text-[#1F5C3B] inline-flex items-center gap-1">
                See the full comparison <ChevronRight size={12} />
              </div>
            </Link>
          </div>
        )}

        {/* Optional Deep Dives progress */}
        {deepDives && (deepDives.deep_dives || []).some((d) => d.has_assessment) && (
          <div className="mt-4" data-testid="dashboard-deep-dives-card">
            <div className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2">
                    <Sparkles size={12} /> Optional deep dives
                  </div>
                  <div className="mt-1 font-serif text-lg text-[#1A1330]">
                    {deepDives.completed} of {deepDives.total} completed
                  </div>
                </div>
                <Link to="/special-needs-v2" data-testid="dashboard-deep-dives-open"
                  className="inline-flex items-center gap-1 text-xs text-[#3D1A78] font-semibold hover:underline">
                  View all <ChevronRight size={12} />
                </Link>
              </div>
              <ul className="mt-4 space-y-2">
                {(deepDives.deep_dives || []).map((d) => {
                  const statusLabel = d.completed
                    ? "Completed"
                    : d.has_assessment
                    ? `In progress · ${d.answered_count} answered`
                    : "Not started";
                  const statusColor = d.completed
                    ? "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]"
                    : d.has_assessment
                    ? "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]"
                    : "bg-white text-[#8471B3] border-[#E5E0EE]";
                  const targetRoute = d.has_report ? d.report_route : d.route;
                  return (
                    <li key={d.id} data-testid={`dashboard-deep-dive-${d.id}`}>
                      <Link to={targetRoute}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-[#E5E0EE] p-3 hover:border-[#3D1A78] hover:bg-[#FCFBFE] transition-all">
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-[#1A1330] truncate">{d.name}</div>
                          <div className="text-[11px] text-[#4B4567] mt-0.5">
                            {d.has_report ? (
                              <>Report ready {d.report_stale ? "(refresh recommended)" : ""}</>
                            ) : d.has_assessment ? (
                              <>Resume where you left off</>
                            ) : (
                              <>Optional companion assessment</>
                            )}
                          </div>
                        </div>
                        <span className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-semibold border ${statusColor}`}
                          data-testid={`dashboard-deep-dive-${d.id}-status`}>
                          {statusLabel}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}

        {/* Co-parent comparisons widget */}
        {compareStatus && compareStatus.total_active > 0 && (
          <div className="mt-4" data-testid="dashboard-compare-card">
            <div className="rounded-3xl border border-[#B5DFC5] bg-[#F1F9F4] p-5 sm:p-6 shadow-sm">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#1F5C3B] flex items-center gap-2">
                    <Users size={12} /> Co-parent comparisons
                  </div>
                  <div className="mt-1 font-serif text-lg text-[#1A1330]" data-testid="dashboard-compare-headline">
                    {compareStatus.total_active === 1 ? "1 active" : `${compareStatus.total_active} active`}
                    {compareStatus.total_ready_to_view > 0 && (
                      <span className="text-sm text-[#1F5C3B] font-normal ml-2">
                        · {compareStatus.total_ready_to_view} ready to view
                      </span>
                    )}
                  </div>
                </div>
                {compareStatus.total_milestones_unlocked > 0 && (
                  <div
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#FDF4E6] text-[#8C5A2C] border border-[#F1D9A0]"
                    data-testid="dashboard-compare-milestones-total"
                  >
                    <Trophy size={12} />
                    {compareStatus.total_milestones_unlocked === 1
                      ? "1 milestone unlocked"
                      : `${compareStatus.total_milestones_unlocked} milestones unlocked`}
                  </div>
                )}
              </div>
              <ul className="mt-4 grid sm:grid-cols-3 gap-2">
                {(compareStatus.pathways || []).map((p) => {
                  const isReady = p.ready_to_view > 0;
                  const isActive = p.active > 0;
                  const stateLabel = isReady
                    ? `${p.ready_to_view} ready`
                    : isActive
                    ? `${p.active} pending`
                    : "None yet";
                  const statePillCls = isReady
                    ? "bg-[#1F5C3B] text-white border-[#1F5C3B]"
                    : isActive
                    ? "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]"
                    : "bg-white text-[#8471B3] border-[#E5E0EE]";
                  const trophies = p.milestones || [];
                  return (
                    <li key={p.id} data-testid={`dashboard-compare-pathway-${p.id}`}>
                      <Link
                        to={p.compare_route}
                        className="group flex flex-col gap-2 rounded-2xl border border-[#CDE7D6] bg-white p-3 hover:border-[#1F5C3B] hover:shadow-sm transition-all"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-[#1A1330] truncate">{p.name}</div>
                            <div className="text-[11px] text-[#4B4567] mt-0.5 group-hover:text-[#1F5C3B] inline-flex items-center gap-1">
                              {isReady ? <><Eye size={11} /> View comparison</> : <>Open hub <ChevronRight size={11} /></>}
                            </div>
                          </div>
                          <span
                            className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-semibold border ${statePillCls}`}
                            data-testid={`dashboard-compare-pathway-${p.id}-status`}
                          >
                            {stateLabel}
                          </span>
                        </div>
                        {trophies.length > 0 && (
                          <div
                            className="flex items-center gap-1 flex-wrap"
                            data-testid={`dashboard-compare-pathway-${p.id}-trophies`}
                          >
                            {trophies.map((m) => {
                              const styleCls =
                                m === 90
                                  ? "bg-[#FDF4E6] text-[#8C5A2C] border-[#F1D9A0]"
                                  : m === 75
                                  ? "bg-[#F1F9F4] text-[#1F5C3B] border-[#B5DFC5]"
                                  : "bg-[#F5F1FB] text-[#3D1A78] border-[#D6CFE8]";
                              const title =
                                m === 90
                                  ? "9-in-10 alignment unlocked"
                                  : m === 75
                                  ? "More than 3-in-4 alignment unlocked"
                                  : "Half of your answers agreed on";
                              return (
                                <span
                                  key={m}
                                  title={title}
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${styleCls}`}
                                  data-testid={`dashboard-compare-pathway-${p.id}-trophy-${m}`}
                                >
                                  <Trophy size={10} /> {m}%
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}

        {/* Safety Assessment */}
        <div className="mt-6">
          <Link
            to="/safety-assessment"
            data-testid="dashboard-safety-assessment-card"
            className="group flex items-center gap-4 rounded-3xl bg-white border border-[#E5E0EE] hover:border-[#C28771] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"          >
            <div className="shrink-0 w-12 h-12 rounded-full bg-[#F8EDE4] grid place-items-center text-[#C28771]">
              <Shield size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#C28771] mb-0.5">
                Safety Assessment
              </div>
              <div className="font-serif text-xl text-[#1A1330] leading-tight mb-1">
                Is it safe to co-parent through direct communication?
              </div>
              <p className="text-xs sm:text-sm text-[#4B4567] leading-relaxed">
                A confidential, DA-informed intimate-partner-violence
                screening. Not a diagnosis and not legal advice — a private
                space to name what&apos;s happening and, if needed, be pointed
                to safer pathways than mediation.
              </p>
            </div>
            <ChevronRight size={16} className="shrink-0 text-[#C28771]" />
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

        </DashboardMoreResources>
          </div>
        </details>
      </div>
    </AppShell>
  );
}
