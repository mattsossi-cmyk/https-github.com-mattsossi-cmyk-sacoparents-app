import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
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

  return (
    <AppShell>
      <div className="fade-up">
        <div className="grid lg:grid-cols-3 gap-6 mb-10">
          <div className="card-soft p-8 lg:col-span-2 relative overflow-hidden">
            <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
            <div className="relative">
              <div className="eyebrow mb-3">Your space</div>
              <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight">
                Hello, {user?.name?.split(" ")[0] || "friend"}.
              </h1>
              <p className="text-[#4B4567] mt-3 max-w-lg">
                Take your time. Each step builds toward a calmer, child-centered mediation
                conversation. Nothing here is graded.
              </p>
              <Link
                to="/orientation"
                className="inline-flex items-center gap-1.5 text-[12px] text-[#3D1A78] hover:text-[#2a0f5f] mt-4 underline-offset-2 hover:underline"
                data-testid="dashboard-revisit-orientation"
              >
                <Compass size={12} /> Revisit the orientation walkthrough
              </Link>
              <div className="mt-6">
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-[#857E9C]">
                      Progress
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
            <div className="eyebrow mb-2">Next step</div>
            <div className="font-serif text-2xl text-[#1A1330] mb-1">
              {STEPS.find((s) => !completed[s.key])?.label || "Generate your summary"}
            </div>
            <p className="text-sm text-[#4B4567] mb-6">
              {STEPS.find((s) => !completed[s.key])?.blurb ||
                "You're prepared. Create your mediator-ready summary."}
            </p>
            <Link
              to={STEPS.find((s) => !completed[s.key])?.path || "/summary"}
              className="btn-sage w-full text-center inline-flex items-center justify-center gap-2"
              data-testid="dashboard-continue-button"
            >
              Continue <ArrowRight size={16} />
            </Link>
            <Link to="/summary" className="text-sm text-[#3D1A78] hover:underline mt-3 text-center" data-testid="dashboard-summary-link">
              Go to summary
            </Link>
          </div>
        </div>

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
      </div>
    </AppShell>
  );
}
