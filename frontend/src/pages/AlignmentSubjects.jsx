/**
 * AlignmentSubjects.jsx — Iter192 · subject picker for the Alignment
 * Reflection flow.
 *
 * Fetches the public subjects list from
 * `/api/alignment-reflection/subjects` and renders 5 cards (General
 * Co-Parenting / Communication / Medical / Educational / Safety).
 * The Safety card carries a "sensitive routing" banner and links to
 * a subject that requires explicit dual-consent before ANY joint
 * comparison — mirrors sacoparentsalign.com's IPV / family-violence
 * carve-out.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  MessagesSquare, Stethoscope, GraduationCap, ShieldAlert, Users,
  Sparkles, ArrowRight, Loader2, ArrowLeft,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


const SUBJECT_ICONS = {
  co_parenting: Users,
  communication: MessagesSquare,
  medical:       Stethoscope,
  educational:   GraduationCap,
  safety:        ShieldAlert,
};


function SubjectCard({ subject }) {
  const Icon = SUBJECT_ICONS[subject.id] || Sparkles;
  const isSensitive = !!subject.sensitive;
  return (
    <Link
      to={`/alignment/reflect/${subject.id}`}
      data-testid={`alignment-subject-${subject.id}`}
      className={`group card-soft p-6 space-y-4 hover:border-[#3D1A78] transition-colors ${
        isSensitive ? "border-[#AA0033]/25 bg-gradient-to-br from-white to-[#FFF3F1]" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div
          className={`rounded-full p-3 ${
            isSensitive
              ? "bg-[#AA0033]/10 text-[#AA0033]"
              : "bg-[#F5EFFB] text-[#3D1A78]"
          }`}
        >
          <Icon size={20} />
        </div>
        {isSensitive && (
          <span
            className="text-[0.625rem] uppercase tracking-[0.14em] font-bold text-[#AA0033]"
            data-testid={`alignment-subject-${subject.id}-sensitive-badge`}
          >
            Dual-consent only
          </span>
        )}
      </div>
      <div>
        <h3 className="font-serif text-xl text-[#1A1330] leading-tight">
          {subject.label}
        </h3>
        <p className="mt-2 text-sm text-[#4B4567] leading-relaxed">
          {subject.blurb}
        </p>
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-[#EEE8F7]">
        <span className="text-[0.625rem] uppercase tracking-[0.14em] font-bold text-[#6E6787]">
          {subject.prompt_count} prompts
        </span>
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78] group-hover:translate-x-0.5 transition-transform">
          Start reflection
          <ArrowRight size={14} />
        </span>
      </div>
    </Link>
  );
}


export default function AlignmentSubjects() {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/alignment-reflection/subjects");
        setSubjects(res.data.subjects || []);
      } catch (err) {
        logError("alignment-subjects load", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <AppShell>
      <div
        className="fade-up max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6"
        data-testid="alignment-subjects-root"
      >
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78]"
        >
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        {/* Hero */}
        <div className="card-soft p-6 sm:p-8 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-[#D4C5F0]/40 pointer-events-none" />
          <div className="relative">
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2">
              <Sparkles size={12} />
              Alignment reflection · Subject picker
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-2 leading-tight">
              Pick the subject you want to reflect on first.
            </h1>
            <p className="mt-2 text-sm text-[#4B4567] max-w-2xl leading-relaxed">
              Each subject uses the same six child-focused prompts. Complete
              one, invite your co-parent, and a neutral Co-Parenting
              Agreement shows where you already agree, where you differ, and
              what your child needs next. You can complete as many
              subjects as fits your family.
            </p>
          </div>
        </div>

        {/* Subject grid */}
        {loading ? (
          <div
            className="grid place-items-center py-12 text-[#6E6787]"
            data-testid="alignment-subjects-loading"
          >
            <Loader2 className="animate-spin" size={20} />
          </div>
        ) : (
          <div
            className="grid grid-cols-1 sm:grid-cols-2 gap-4"
            data-testid="alignment-subjects-grid"
          >
            {subjects.map((s) => (
              <SubjectCard key={s.id} subject={s} />
            ))}
          </div>
        )}

        {/* Safety disclosure — sits BELOW the grid so parents see the
            picker context first, and it never blocks the click path.
            The safety card itself already carries the "Dual-consent
            only" badge, so this footer is a soft echo. */}
        <div
          className="card-soft p-5 flex items-start gap-3"
          data-testid="alignment-subjects-safety-footer"
        >
          <ShieldAlert className="text-[#AA0033] mt-0.5 shrink-0" size={18} />
          <div className="text-xs text-[#4B4567] leading-relaxed">
            <strong className="text-[#1A1330]">Safety is handled
            differently.</strong>{" "}
            Safety reflections stay private to you unless BOTH parents
            explicitly opt in to compare — the joint report never
            auto-merges Safety answers. If you're in immediate danger,
            call your local emergency services first.
          </div>
        </div>

        {/* Sample link — public PDF preview for mediators + curious parents. */}
        <div className="card-soft p-5 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-[#4B4567] max-w-md">
            <strong>Curious what the report looks like?</strong>{" "}
            Download the fictional Alex &amp; Sam sample to see the exact
            10-section flow a real mediator or attorney receives.
          </div>
          <a
            href={`${process.env.REACT_APP_BACKEND_URL}/api/insights/samples/co-parenting-alignment-report.pdf`}
            target="_blank"
            rel="noreferrer"
            data-testid="alignment-subjects-sample-pdf-link"
            className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5EFFB]"
          >
            Preview the sample PDF
          </a>
        </div>
      </div>
    </AppShell>
  );
}
