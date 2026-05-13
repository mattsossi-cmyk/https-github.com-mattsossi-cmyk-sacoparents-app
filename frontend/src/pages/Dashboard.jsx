import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import {
  Target,
  AlertCircle,
  ListOrdered,
  MessageCircle,
  HeartHandshake,
  FileText,
  BookOpen,
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
  const [prep, setPrep] = useState({ completed: {} });

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => setPrep(r.data || { completed: {} }))
      .catch((err) => logError("Failed to load prep:", err));
  }, []);

  const completed = prep.completed || {};
  const done = STEPS.filter((s) => completed[s.key]).length;
  const pct = Math.round((done / STEPS.length) * 100);

  return (
    <AppShell>
      <div className="fade-up">
        <div className="grid lg:grid-cols-3 gap-6 mb-10">
          <div className="card-soft p-8 lg:col-span-2 relative overflow-hidden">
            <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#E5D9C5]/40" />
            <div className="relative">
              <div className="eyebrow mb-3">Your space</div>
              <h1 className="font-serif text-4xl sm:text-5xl text-[#2A3631] leading-tight">
                Hello, {user?.name?.split(" ")[0] || "friend"}.
              </h1>
              <p className="text-[#5C6B64] mt-3 max-w-lg">
                Take your time. Each step builds toward a calmer, child-centered mediation
                conversation. Nothing here is graded.
              </p>
              <div className="mt-6">
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92]">
                      Progress
                    </div>
                    <div className="font-serif text-3xl text-[#2A3631]">
                      {done} <span className="text-[#8A9A92] text-xl">/ {STEPS.length}</span>
                    </div>
                  </div>
                  <div className="text-sm text-[#5C6B64]">{pct}% complete</div>
                </div>
                <div className="h-2 bg-[#E8ECE9] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#849D8E] progress-fill"
                    style={{ width: `${pct}%` }}
                    data-testid="dashboard-progress-bar"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card-soft p-7 flex flex-col">
            <div className="eyebrow mb-2">Next step</div>
            <div className="font-serif text-2xl text-[#2A3631] mb-1">
              {STEPS.find((s) => !completed[s.key])?.label || "Generate your summary"}
            </div>
            <p className="text-sm text-[#5C6B64] mb-6">
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
            <Link to="/summary" className="text-sm text-[#849D8E] hover:underline mt-3 text-center" data-testid="dashboard-summary-link">
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
                      isDone ? "bg-[#849D8E] text-white" : "bg-[#F5F3E9] text-[#849D8E]"
                    }`}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A9A92]">
                    {isDone ? "Saved" : "To do"}
                  </div>
                </div>
                <div className="font-serif text-xl text-[#2A3631] mb-1">{label}</div>
                <p className="text-sm text-[#5C6B64]">{blurb}</p>
              </Link>
            );
          })}

          <Link
            to="/summary"
            className="card-soft p-6 hover:-translate-y-0.5 transition-transform bg-gradient-to-br from-[#F5F3E9] to-[#FFFFFF]"
            data-testid="dashboard-summary-card"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-11 h-11 rounded-full grid place-items-center bg-[#C28771]/15 text-[#C28771]">
                <FileText size={18} />
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A9A92]">
                Final
              </div>
            </div>
            <div className="font-serif text-xl text-[#2A3631] mb-1">Mediation Summary</div>
            <p className="text-sm text-[#5C6B64]">
              AI-synthesized, mediator-ready, downloadable PDF.
            </p>
          </Link>

          <Link
            to="/resources"
            className="card-soft p-6 hover:-translate-y-0.5 transition-transform"
            data-testid="dashboard-resources-card"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-11 h-11 rounded-full grid place-items-center bg-[#9CB4C4]/20 text-[#5C6B64]">
                <BookOpen size={18} />
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A9A92]">
                Library
              </div>
            </div>
            <div className="font-serif text-xl text-[#2A3631] mb-1">Resource Center</div>
            <p className="text-sm text-[#5C6B64]">
              Short reads & videos: communication, parallel parenting, trust.
            </p>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
