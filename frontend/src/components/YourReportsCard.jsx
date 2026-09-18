import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText, Users, GraduationCap, Brain, Pill, Loader2,
  ArrowRight, CheckCircle2, Circle, Download,
} from "lucide-react";
import { downloadPdf as fetchPdfWithGracefulFailure } from "../lib/pdf";

/**
 * YourReportsCard — one of the three above-the-fold blocks on the new
 * dashboard IA (Do This Next / Your Progress / Your Reports).
 *
 * Shows a compact row per report:
 *   * Mediation Summary            — core, always visible
 *   * Special Needs Report         — appears if user is on the SNC pathway
 *   * Educational / Psych / Medical Deep-Dive Reports — appear once the
 *     corresponding deep dive has been started or completed
 *
 * Each row surfaces one of three states: `not_started` (grey), `in_progress`
 * (purple), `ready` (green + Download/Open CTA). Compact by design — this
 * card is a launcher, not the reports themselves.
 */
const STATE_STYLES = {
  ready: {
    pill: "bg-[#F1F9F4] text-[#1F5C3B] border-[#B5DFC5]",
    icon: (props) => <CheckCircle2 {...props} className="text-[#1F5C3B]" />,
    cta: "Open",
  },
  in_progress: {
    pill: "bg-[#F5F1FB] text-[#3D1A78] border-[#D6CFE8]",
    icon: (props) => <Loader2 {...props} className="text-[#3D1A78]" />,
    cta: "Continue",
  },
  not_started: {
    pill: "bg-[#F5F3F0] text-[#857E9C] border-[#E5E0EE]",
    icon: (props) => <Circle {...props} className="text-[#C7BFDA]" />,
    cta: "Start",
  },
};

function ReportRow({ testid, title, subtitle, state, to, Icon }) {
  const s = STATE_STYLES[state] || STATE_STYLES.not_started;
  return (
    <Link
      to={to}
      className="group flex items-center gap-3 p-3 sm:p-3.5 rounded-2xl border border-[#E5E0EE] bg-white hover:bg-[#FCFBFE] hover:border-[#3D1A78] transition-all"
      data-testid={testid}
      data-state={state}
    >
      <div className="shrink-0 h-9 w-9 rounded-xl bg-[#F5F1FB] flex items-center justify-center text-[#3D1A78]">
        <Icon size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-[#1A1330] leading-snug truncate">
          {title}
        </div>
        <div className="text-xs text-[#4B4567] truncate">{subtitle}</div>
      </div>
      <span
        className={`shrink-0 text-[10px] uppercase tracking-[0.14em] font-bold px-2 py-1 rounded-full border ${s.pill}`}
      >
        {state === "ready" ? "Ready" : state === "in_progress" ? "In progress" : "Not started"}
      </span>
      <span className="shrink-0 hidden sm:inline-flex items-center gap-1 text-xs text-[#3D1A78] font-semibold group-hover:underline">
        {s.cta} <ArrowRight size={12} />
      </span>
    </Link>
  );
}

export default function YourReportsCard({
  summariesCount,
  sncStatus,
  deepDives,
  compareStatus,
}) {

  // deep_dives payload shape: { deep_dives: [{id, has_assessment, has_report, ...}] }
  const dd = (deepDives && Array.isArray(deepDives.deep_dives))
    ? deepDives.deep_dives
    : [];
  const findDD = (id) => dd.find((x) => x.id === id) || {};
  const edu = findDD("educational");
  const psych = findDD("psychological");
  const med = findDD("medical");

  const rowFor = (info) => {
    if (info.has_report) return "ready";
    if (info.answered_count > 0 || info.completed) return "in_progress";
    return "not_started";
  };

  const rows = [];
  // Mediation Summary
  rows.push({
    key: "mediation-summary",
    testid: "your-reports-mediation-summary",
    Icon: FileText,
    title: "Mediation Summary",
    subtitle: summariesCount > 0
      ? "Generated · open, download, or email"
      : "Complete the 5 prep modules to generate.",
    state: summariesCount > 0 ? "ready" : "not_started",
    to: "/summary",
  });

  // Special Needs Report — only surface if user has any SNC activity.
  if (sncStatus && (sncStatus.has_report || sncStatus.has_assessment)) {
    rows.push({
      key: "snc-report",
      testid: "your-reports-snc",
      Icon: Users,
      title: "Special Needs Report",
      subtitle: sncStatus.has_report
        ? "Individual parent report · ready to review"
        : "Assessment in progress · finish to generate the report.",
      state: sncStatus.has_report ? "ready" : "in_progress",
      to: sncStatus.has_report ? "/special-needs-v2/report" : "/special-needs-v2",
    });
  }

  // Deep-dive reports — only surface each if the user has started that pathway.
  if (edu.has_assessment) {
    rows.push({
      key: "edu-dd",
      testid: "your-reports-edu-dd",
      Icon: GraduationCap,
      title: "Educational Assessment Report",
      subtitle: edu.has_report
        ? "Deep-dive report · ready"
        : `In progress · ${edu.answered_count || 0} answered`,
      state: rowFor(edu),
      to: edu.has_report
        ? "/special-needs-v2/educational-deep-dive/report"
        : "/special-needs-v2/educational-deep-dive",
    });
  }
  if (psych.has_assessment) {
    rows.push({
      key: "psych-dd",
      testid: "your-reports-psych-dd",
      Icon: Brain,
      title: "Psychological & Behavioural Report",
      subtitle: psych.has_report
        ? "Deep-dive report · ready"
        : `In progress · ${psych.answered_count || 0} answered`,
      state: rowFor(psych),
      to: psych.has_report
        ? "/special-needs-v2/psychological-deep-dive/report"
        : "/special-needs-v2/psychological-deep-dive",
    });
  }
  if (med.has_assessment) {
    rows.push({
      key: "med-dd",
      testid: "your-reports-med-dd",
      Icon: Pill,
      title: "Medical · Prescription Report",
      subtitle: med.has_report
        ? "Deep-dive report · ready"
        : `In progress · ${med.answered_count || 0} answered`,
      state: rowFor(med),
      to: med.has_report
        ? "/special-needs-v2/medical-deep-dive/report"
        : "/special-needs-v2/medical-deep-dive",
    });
  }

  // Co-parent comparison — only surface if user has an active share on any pathway.
  const hasActiveCompare = compareStatus && (compareStatus.total_active > 0 || compareStatus.total_ready_to_view > 0);
  if (hasActiveCompare) {
    rows.push({
      key: "compare",
      testid: "your-reports-compare",
      Icon: Users,
      title: "Co-Parent Comparison",
      subtitle: compareStatus.total_ready_to_view > 0
        ? `${compareStatus.total_ready_to_view} pathway${compareStatus.total_ready_to_view === 1 ? "" : "s"} ready to view.`
        : `${compareStatus.total_active} active share${compareStatus.total_active === 1 ? "" : "s"} awaiting consent.`,
      state: compareStatus.total_ready_to_view > 0 ? "ready" : "in_progress",
      to: "/special-needs-v2/compare",
    });
  }

  const readyCount = rows.filter((r) => r.state === "ready").length;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="your-reports-card"
    >
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            Your reports
          </div>
          <div className="font-serif text-xl text-[#1A1330] leading-snug mt-0.5">
            {readyCount === 0
              ? "Your report shelf starts empty — every module you finish fills it."
              : readyCount === 1
                ? "1 report ready to hand to a professional."
                : `${readyCount} reports ready to hand to a professional.`}
          </div>
        </div>
        <Link
          to="/summary"
          className="text-xs font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1"
          data-testid="your-reports-all-link"
        >
          All reports <ArrowRight size={12} />
        </Link>
      </div>

      <div className="space-y-2">
        {rows.map((r) => (
          <ReportRow
            key={r.key}
            testid={r.testid}
            title={r.title}
            subtitle={r.subtitle}
            state={r.state}
            to={r.to}
            Icon={r.Icon}
          />
        ))}
      </div>

      <BundleDownloadButton readyCount={readyCount} />
    </section>
  );
}


/**
 * BundleDownloadButton — one-click "Download everything I've completed"
 * ZIP. Silently skips any endpoint that returns 404/409 (assessments
 * the parent hasn't finished yet); the backend's manifest tells the
 * parent exactly what's inside. When the parent has literally
 * nothing ready, the backend 409's and the shared `downloadPdf`
 * helper turns that into a friendly toast with a dashboard action.
 */
function BundleDownloadButton({ readyCount }) {
  const [downloading, setDownloading] = useState(false);
  const onClick = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      await fetchPdfWithGracefulFailure("/bundle/my-completed.zip", {
        filename: `sacoparents-my-reports-${new Date().toISOString().slice(0, 10)}.zip`,
        testid: "your-reports-bundle-download",
      });
    } finally {
      setDownloading(false);
    }
  };
  const label = readyCount > 0
    ? `Download everything I've completed (ZIP)`
    : `Download everything I've completed (ZIP)`;
  return (
    <div className="mt-4 pt-4 border-t border-[#E5E0EE]">
      <button
        type="button"
        onClick={onClick}
        disabled={downloading}
        data-testid="your-reports-bundle-download-btn"
        className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white text-sm font-semibold px-4 py-3 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all disabled:opacity-60 disabled:hover:translate-y-0"
      >
        {downloading
          ? <Loader2 size={14} className="animate-spin" />
          : <Download size={14} />}
        {downloading ? "Preparing your bundle…" : label}
      </button>
      <p className="mt-2 text-[11px] text-[#857E9C] leading-relaxed text-center">
        One ZIP with every PDF you've completed and a plain-text manifest —
        nothing is added for assessments you haven't finished yet.
      </p>
    </div>
  );
}
