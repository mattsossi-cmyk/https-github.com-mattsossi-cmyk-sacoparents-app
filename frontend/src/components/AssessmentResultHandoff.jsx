/**
 * AssessmentResultHandoff — mounted on every deep-dive result page.
 *
 * Two mutually-exclusive states:
 *   1. Parent is linked to an open Align case for this lane and their
 *      slot has flipped to `completed` → show the green
 *      "Your Assessment Is Complete — Awaiting Co-Parent" banner
 *      with the case_id + professional name.
 *   2. Parent is NOT linked to a case for this lane → show the
 *      "Send to a professional" CTA that routes to
 *      `/professionals?assessment=<type>`.
 *
 * When the parent has BOTH — a completed linked case *and* the
 * appetite to send to another professional — the banner takes
 * precedence and a smaller secondary link to the directory sits
 * below it. That reflects the founder's guardrail: an existing
 * professional-driven case already has a home for the report;
 * broadcasting a fresh code is redundant.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  Send,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const ASSESSMENT_LABELS = {
  "co-parenting": "Co-Parenting",
  communication: "Communication",
  educational: "Educational Needs",
  medical: "Medical Needs",
  psychological: "Psychological / Emotional",
  "special-needs": "Special Needs",
};

export default function AssessmentResultHandoff({ assessmentType }) {
  const [linkedCase, setLinkedCase] = useState(null); // null = unknown/none
  const { user } = useAuth();
  const isSignedIn = !!user;

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/joint-alignment/mine");
        if (cancelled) return;
        // Find an active case for this lane where the parent is completed.
        const match = (r.data?.cases || []).find(
          (c) =>
            c.assessment_type === assessmentType &&
            c.my_status === "completed" &&
            c.status !== "cancelled" &&
            c.status !== "expired"
        );
        setLinkedCase(match || null);
      } catch {
        /* silent — this is decorative */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, assessmentType]);

  const label = ASSESSMENT_LABELS[assessmentType] || "assessment";

  if (linkedCase) {
    return (
      <section
        className="mt-6 rounded-3xl border-2 border-[#1E7A55] bg-[#F1F9F4] p-5 sm:p-6"
        data-testid="assessment-result-linked-case-banner"
      >
        <h3 className="font-serif text-2xl text-[#1A1330] flex items-center gap-2 leading-tight">
          <CheckCircle2 size={22} className="text-[#1E7A55]" />
          Your Assessment Is Complete — Awaiting Co-Parent
        </h3>
        <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
          Thank you. Your individual {label} assessment has been marked
          complete on case{" "}
          <span
            className="font-mono text-[#1A1330]"
            data-testid="assessment-result-linked-case-id"
          >
            {linkedCase.case_id}
          </span>{" "}
          {linkedCase.professional?.name ? (
            <>
              (requested by{" "}
              <strong className="text-[#1A1330]">
                {linkedCase.professional.name}
              </strong>
              ).
            </>
          ) : (
            <>.</>
          )}
        </p>
        <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
          Your co-parent will complete their assessment separately. When
          the required assessments have been completed, SA CoParents Align
          can use the designated assessment information to prepare the
          Joint Alignment Report.
        </p>
        <div className="mt-4 rounded-2xl bg-white border border-[#D0EBDE] p-3 flex gap-2 items-start text-[12.5px] text-[#186142] leading-relaxed">
          <ShieldCheck size={14} className="flex-shrink-0 mt-0.5" />
          <span>
            Joint Alignment Status:{" "}
            <strong>Your Assessment Complete ✓</strong>
          </span>
        </div>
      </section>
    );
  }

  return (
    <section
      className="mt-6 rounded-3xl border border-[#D6CFE8] bg-white p-5 sm:p-6"
      data-testid="assessment-result-professional-cta"
    >
      <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
        Ready to hand this off?
      </div>
      <h3 className="font-serif text-2xl text-[#1A1330] mt-1 leading-tight">
        Send your {label} assessment to a professional
      </h3>
      <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
        Pick a mediator, attorney, therapist, or parent facilitator from
        the SA CoParents directory. We&rsquo;ll email them a fresh
        Alignment Code — you keep your individual answers private, and
        the joint report is only prepared after both parents have
        completed the same assessment.
      </p>
      <Link
        to={`/professionals?assessment=${encodeURIComponent(assessmentType)}`}
        className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
        data-testid="assessment-result-goto-professionals"
      >
        <Send size={14} />
        Send to a professional
        <ArrowRight size={13} />
      </Link>
    </section>
  );
}
