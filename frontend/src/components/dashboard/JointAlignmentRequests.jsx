/**
 * Dashboard "Joint Alignment Requests" section.
 *
 * Renders the parent's active + past Joint Alignment cases fetched
 * from `GET /api/joint-alignment/mine`. Never shows the co-parent's
 * answers. The row's "Open" CTA routes to the correct assessment
 * for whichever lane the case is on.
 *
 * The section hides itself entirely when the parent has zero cases
 * so a solo parent's dashboard doesn't grow an empty panel.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ClipboardList,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  Loader2,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const ASSESSMENT_LABELS = {
  "co-parenting": "Co-Parenting",
  communication: "Communication",
  educational: "Educational Needs",
  medical: "Medical Needs",
  psychological: "Psychological / Emotional",
  "special-needs": "Special Needs",
};

const ASSESSMENT_ROUTES = {
  "co-parenting": "/special-needs-v2",
  communication: "/communication",
  educational: "/edu-deep",
  medical: "/med-deep",
  psychological: "/psych-deep",
  "special-needs": "/special-needs-v2",
};

const STATUS_META = {
  invited: {
    label: "Invitation received",
    tone: "bg-[#EFE9F9] text-[#3D1A78] border-[#D6CFE8]",
    icon: Clock,
  },
  in_progress: {
    label: "In progress",
    tone: "bg-[#FFF6EA] text-[#8A4610] border-[#F1D9B7]",
    icon: Clock,
  },
  completed: {
    label: "Your assessment complete",
    tone: "bg-[#E1F3E8] text-[#186142] border-[#B7DEC6]",
    icon: CheckCircle2,
  },
  cancelled: {
    label: "Cancelled",
    tone: "bg-[#FDECEC] text-[#8F1D24] border-[#F5C5C5]",
    icon: Clock,
  },
  expired: {
    label: "Expired",
    tone: "bg-[#F1EEF4] text-[#5C5471] border-[#DED8E5]",
    icon: Clock,
  },
};

function getAuthToken() {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
}

export default function JointAlignmentRequests() {
  const navigate = useNavigate();
  const [cases, setCases] = useState(null); // null = loading, [] = empty
  const [error, setError] = useState(null);
  const authToken = getAuthToken();

  useEffect(() => {
    if (!authToken) {
      setCases([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API}/joint-alignment/mine`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        const body = await r.json();
        if (cancelled) return;
        if (r.ok) setCases(body.cases || []);
        else setError(body.detail || "Failed to load your cases");
      } catch (e) {
        if (!cancelled) setError("Network error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authToken]);

  // Hide the whole section when there are no cases so a solo parent's
  // dashboard doesn't grow an empty panel.
  if (cases !== null && cases.length === 0 && !error) return null;

  return (
    <section
      className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-7 shadow-sm"
      data-testid="joint-alignment-requests"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] flex items-center gap-2">
            <ClipboardList size={13} />
            Joint Alignment Requests
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] leading-tight mt-1">
            Cases invited by a professional
          </h2>
        </div>
        <button
          type="button"
          onClick={() => navigate("/join")}
          className="text-[13px] text-[#3D1A78] underline hover:text-[#2A0F5F]"
          data-testid="joint-alignment-manual-code-link"
        >
          Have an Alignment Code?
        </button>
      </div>

      {cases === null && !error && (
        <div className="flex items-center gap-2 text-[#4B4567] text-sm">
          <Loader2 className="animate-spin" size={16} />
          Loading your requests…
        </div>
      )}

      {error && (
        <div className="text-[13px] text-[#8F1D24]" data-testid="joint-alignment-error">
          {error}
        </div>
      )}

      {cases && cases.length > 0 && (
        <ul className="divide-y divide-[#EFE9F9]" data-testid="joint-alignment-list">
          {cases.map((c) => (
            <CaseRow key={c.case_id} caseData={c} navigate={navigate} />
          ))}
        </ul>
      )}
    </section>
  );
}

function CaseRow({ caseData, navigate }) {
  const meta = STATUS_META[caseData.my_status] || STATUS_META.invited;
  const Icon = meta.icon;
  const label = ASSESSMENT_LABELS[caseData.assessment_type] || caseData.assessment_type;
  const route = ASSESSMENT_ROUTES[caseData.assessment_type] || "/dashboard";
  const professional = caseData.professional?.name || "Your professional";
  const isDone = caseData.my_status === "completed";

  return (
    <li
      className="py-4 flex flex-col sm:flex-row sm:items-center gap-3"
      data-testid={`joint-alignment-row-${caseData.case_id}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta.tone}`}
          >
            <Icon size={11} />
            {meta.label}
          </span>
          <span className="text-[11px] text-[#857E9C] font-mono">
            {caseData.case_id}
          </span>
        </div>
        <div className="font-serif text-lg text-[#1A1330] mt-1 leading-tight">
          {label} Assessment
        </div>
        <div className="text-[12.5px] text-[#4B4567] leading-snug mt-0.5">
          Requested by <strong className="text-[#1A1330]">{professional}</strong>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {!isDone && caseData.my_status !== "cancelled" && caseData.my_status !== "expired" && (
          <button
            type="button"
            onClick={() => navigate(route)}
            className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-[13px] font-semibold hover:bg-[#2A0F5F] transition"
            data-testid={`joint-alignment-start-${caseData.case_id}`}
          >
            <Sparkles size={13} />
            {caseData.my_status === "in_progress" ? "Continue" : "Start Assessment"}
            <ArrowRight size={12} />
          </button>
        )}
        {isDone && (
          <span
            className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#186142]"
            data-testid={`joint-alignment-done-${caseData.case_id}`}
          >
            <CheckCircle2 size={14} />
            Awaiting co-parent
          </span>
        )}
      </div>
    </li>
  );
}
