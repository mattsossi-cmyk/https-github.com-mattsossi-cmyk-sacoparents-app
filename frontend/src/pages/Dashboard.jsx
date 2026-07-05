import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import VerificationBanner from "../components/VerificationBanner";
import EmailHealthBanner from "../components/EmailHealthBanner";
import InviteCoparentCard from "../components/InviteCoparentCard";
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
} from "lucide-react";
import { logError } from "../lib/logger";

const STEPS = [
  {
    key: "child_goals",
    label: "Child-Centered Goals",
    path: "/prep/child-goals",
    icon: Target,
    blurb: "What do you want your child to experience?",
  },
  {
    key: "issues",
    label: "Issues & Concerns",
    path: "/prep/issues",
    icon: AlertCircle,
    blurb: "Map schedule, communication, finances, safety.",
  },
  {
    key: "priority",
    label: "Priority & Agenda",
    path: "/prep/priority",
    icon: ListOrdered,
    blurb: "Rank what matters most — and where you flex.",
  },
  {
    key: "comm_style",
    label: "Communication Style",
    path: "/prep/communication",
    icon: MessageCircle,
    blurb: "Notice patterns; receive AI-coached suggestions.",
  },
  {
    key: "readiness",
    label: "Readiness Check",
    path: "/prep/readiness",
    icon: HeartHandshake,
    blurb: "How prepared do you feel — honestly?",
  },
];

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [prep, setPrep] = useState({ completed: {} });

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
    // On native mobile builds only — no-op on web.
    registerPushNotifications(api);
  }, []);

  const completed = prep.completed || {};
  const done = STEPS.filter((s) => completed[s.key]).length;
  const pct = Math.round((done / STEPS.length) * 100);

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

  const nextStep = STEPS.find((s) => !completed[s.key]);
  const allDone = !nextStep;

  return (
    <AppShell>
      <div className="fade-up">
        <EmailHealthBanner />
        <VerificationBanner />
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
              <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight">
                Hello, {user?.name?.split(" ")[0] || "friend"}.
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
                      Modules touched
                    </div>
                    <div className="font-serif text-3xl text-[#1A1330]">
                      {done} <span className="text-[#857E9C] text-xl">/ {STEPS.length}</span>
                    </div>
                  </div>
                  <div className="text-sm text-[#4B4567]">{pct}% complete</div>
                </div>
                <div className="h-2 bg-[#E5E0EE] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3D1A78] progress-fill"
                    style={{ width: `${pct}%` }}
                    data-testid="dashboard-progress-bar"
                  />
                </div>
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
            <Link to="/summary" className="text-sm text-[#3D1A78] hover:underline mt-3 text-center" data-testid="dashboard-summary-link">
              Go to summary
            </Link>
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

        <div className="eyebrow mb-4">Preparation modules</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {STEPS.map(({ key, label, path, icon: Icon, blurb }) => {
            const isDone = !!completed[key];
            return (
              <Link
                to={path}
                key={key}
                className="card-soft p-6 hover:-translate-y-0.5 transition-transform group"
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
                    {isDone ? "Saved" : "To do"}
                  </div>
                </div>
                <div className="font-serif text-xl text-[#1A1330] mb-1">{label}</div>
                <p className="text-sm text-[#4B4567]">{blurb}</p>
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
      </div>
    </AppShell>
  );
}
