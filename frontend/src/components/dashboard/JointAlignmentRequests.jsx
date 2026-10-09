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
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ClipboardList,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  Loader2,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";

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
  released: {
    label: "Handed off",
    tone: "bg-[#E1F3E8] text-[#186142] border-[#B7DEC6]",
    icon: ShieldCheck,
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

export default function JointAlignmentRequests() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [cases, setCases] = useState(null); // null = loading, [] = empty
  const [error, setError] = useState(null);
  const [handedOffOpen, setHandedOffOpen] = useState(false);
  const isSignedIn = !!user;

  useEffect(() => {
    if (!isSignedIn) {
      setCases([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/joint-alignment/mine");
        if (cancelled) return;
        setCases(r.data?.cases || []);
      } catch (err) {
        if (cancelled) return;
        const detail = err?.response?.data?.detail || "";
        setError(detail || "Failed to load your cases");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSignedIn]);

  // Split cases into "live" vs "handed off" buckets. A case is
  // handed off once execute-release has fired (`released_at` set on
  // the case). We keep the section collapsible so a parent with a
  // long history doesn't scroll past 20 released cases to find the
  // one in-progress case at the top.
  const { liveCases, handedOffCases } = useMemo(() => {
    const rows = cases || [];
    const live = [];
    const off = [];
    for (const c of rows) {
      if (c.released_at || c.status === "released") off.push(c);
      else live.push(c);
    }
    return { liveCases: live, handedOffCases: off };
  }, [cases]);

  // Hide the whole section when the parent has zero cases at all
  // (loading is still in flight → `cases === null`).
  if (
    cases !== null
    && liveCases.length === 0
    && handedOffCases.length === 0
    && !error
  ) {
    return null;
  }

  return (
    <section
      id="joint-alignment-requests"
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

      {liveCases.length > 0 && (
        <ul
          className="divide-y divide-[#EFE9F9]"
          data-testid="joint-alignment-list"
        >
          {liveCases.map((c) => (
            <CaseRow key={c.case_id} caseData={c} navigate={navigate} />
          ))}
        </ul>
      )}

      {cases && liveCases.length === 0 && handedOffCases.length > 0 && !error && (
        <div
          className="text-[13px] text-[#4B4567] py-2"
          data-testid="joint-alignment-no-live"
        >
          No live cases right now. All past cases sit under
          &ldquo;Handed off&rdquo; below.
        </div>
      )}

      {handedOffCases.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[#EFE9F9]">
          <button
            type="button"
            onClick={() => setHandedOffOpen((v) => !v)}
            className="w-full flex items-center justify-between gap-2 text-left"
            aria-expanded={handedOffOpen}
            data-testid="handed-off-toggle"
          >
            <span className="inline-flex items-center gap-2 text-[12px] uppercase tracking-[0.14em] font-bold text-[#186142]">
              <ShieldCheck size={13} />
              Handed off ({handedOffCases.length})
            </span>
            {handedOffOpen
              ? <ChevronDown size={16} className="text-[#4B4567]" />
              : <ChevronRight size={16} className="text-[#4B4567]" />}
          </button>
          <p className="text-[11.5px] text-[#857E9C] mt-1 leading-relaxed">
            Cases where both parents recorded release consent and the
            Co-Parenting Agreement has already been handed off to a
            named professional.
          </p>
          {handedOffOpen && (
            <ul
              className="mt-3 divide-y divide-[#EFE9F9]"
              data-testid="handed-off-list"
            >
              {handedOffCases.map((c) => (
                <CaseRow
                  key={c.case_id}
                  caseData={c}
                  navigate={navigate}
                  handedOff
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function CaseRow({ caseData, navigate, handedOff = false }) {
  const derivedStatus = handedOff
    ? "released"
    : (caseData.my_status || "invited");
  const meta = STATUS_META[derivedStatus] || STATUS_META.invited;
  const Icon = meta.icon;
  const label = ASSESSMENT_LABELS[caseData.assessment_type] || caseData.assessment_type;
  const route = ASSESSMENT_ROUTES[caseData.assessment_type] || "/dashboard";
  const professional = caseData.professional?.name || "Your professional";
  const isDone = caseData.my_status === "completed";
  const releasedProNice = caseData.released_professional_name || professional;
  const releasedAtNice = caseData.released_at
    ? new Date(caseData.released_at).toLocaleDateString(undefined, { dateStyle: "medium" })
    : null;

  return (
    <li
      className="py-4 flex flex-col sm:flex-row sm:items-center gap-3"
      data-testid={
        handedOff
          ? `handed-off-row-${caseData.case_id}`
          : `joint-alignment-row-${caseData.case_id}`
      }
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
          {handedOff && releasedAtNice ? (
            <>
              Released to{" "}
              <strong className="text-[#1A1330]">{releasedProNice}</strong>
              {" · "}
              <span className="text-[#857E9C]">{releasedAtNice}</span>
            </>
          ) : (
            <>Requested by <strong className="text-[#1A1330]">{professional}</strong></>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {!handedOff && !isDone
          && caseData.my_status !== "cancelled"
          && caseData.my_status !== "expired" && (
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
        {!handedOff && isDone && (
          <span
            className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#186142]"
            data-testid={`joint-alignment-done-${caseData.case_id}`}
          >
            <CheckCircle2 size={14} />
            Awaiting co-parent
          </span>
        )}
        {!handedOff && caseData.status === "both_complete" && (
          <button
            type="button"
            onClick={() => navigate(
              `/joint-alignment/cases/${caseData.case_id}/preview`,
            )}
            className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-[13px] font-semibold hover:bg-[#F5F1FB] transition"
            data-testid={`joint-alignment-preview-${caseData.case_id}`}
          >
            Preview joint outcome
            <ArrowRight size={12} />
          </button>
        )}
        {handedOff && (
          <button
            type="button"
            onClick={() => navigate(
              `/joint-alignment/cases/${caseData.case_id}/preview`,
            )}
            className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#3D1A78] hover:underline"
            data-testid={`handed-off-view-${caseData.case_id}`}
          >
            View receipt
            <ArrowRight size={11} />
          </button>
        )}
      </div>
    </li>
  );
}
