import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import SectionCoachCard from "./SectionCoachCard";
import { Loader2, Sparkles } from "lucide-react";
import { logError } from "../../lib/logger";

/**
 * ReportSectionCoachStrip — renders one collapsed SectionCoachCard per
 * section of a Deep Dive assessment on the report page, so the parent can
 * expand and review advice next to the section it came from.
 *
 * Reads the pathway schema on mount. If the schema has a `texas_only`
 * section and the parent is not in Texas, the section is dropped — the
 * report already filters that section out.
 *
 * Props:
 *   apiPrefix   — e.g. "/edu-deep"
 *   testidBase  — e.g. "edu-deep"
 *   userState   — optional state code, used to hide Texas-only sections
 */
export default function ReportSectionCoachStrip({ apiPrefix, testidBase, userState }) {
  const [sections, setSections] = useState(null);

  useEffect(() => {
    api
      .get(`${apiPrefix}/schema`)
      .then((r) => setSections(r.data?.sections || []))
      .catch((err) => logError(`section coach strip schema ${apiPrefix}:`, err));
  }, [apiPrefix]);

  if (sections === null) {
    return (
      <section
        className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid={`${testidBase}-report-section-coach-loading`}
      >
        <Loader2 size={14} className="animate-spin" />
        Loading your section-by-section coach cards…
      </section>
    );
  }

  const visible = (sections || []).filter((s) => {
    if (!s.texas_only) return true;
    return (userState || "").toUpperCase() === "TX";
  });

  if (visible.length === 0) return null;

  return (
    <section
      className="mt-8"
      data-testid={`${testidBase}-report-section-coach-strip`}
    >
      <div className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-[#F5F1FB] to-[#FCFBFE] p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="shrink-0 h-9 w-9 rounded-full bg-white flex items-center justify-center text-[#3D1A78] shadow-sm">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
              AI Personal Coach · Section by Section
            </div>
            <h2 className="font-serif text-2xl text-[#1A1330] leading-snug mt-1">
              Your coach's take on every section you answered.
            </h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-2xl">
              Tap any section below to see strengths, coordination gaps,
              suggested next steps, and recommended resources — generated
              from your own answers, never from your co-parent's.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {visible.map((s) => (
          <SectionCoachCard
            key={s.id}
            apiPrefix={apiPrefix}
            testidBase={`${testidBase}-report-${s.id}`}
            sectionId={s.id}
            sectionName={`${s.number}. ${s.name}`}
          />
        ))}
      </div>
    </section>
  );
}
