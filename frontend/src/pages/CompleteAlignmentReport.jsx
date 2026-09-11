/**
 * CompleteAlignmentReport — the unified 10-section report viewer.
 *
 * Renders the same skeleton as sacoparentsalign.com's universal Joint
 * Alignment Report, with two variants driven by URL:
 *   - `/complete-alignment-report`             → individual (signed-in parent)
 *   - `/complete-alignment-report/joint/:caseId` → joint (case-scoped)
 *
 * The viewer is intentionally read-only. Its job is to give parents
 * and professionals a live preview of what the downloadable PDF will
 * contain, so they can decide when the reflections have enough
 * substance to send onwards.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, ArrowLeft, Loader2, CheckCircle2, Clock } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

// Section skeleton — kept in lockstep with the backend PDF builder.
// The numeric titles echo the sacoparentsalign.com "one universal
// 10-page report" structure so a professional trained on Align opens
// this viewer and knows exactly where to look.
const SECTIONS = [
  { n: "01", title: "Complete Alignment Overview" },
  { n: "02", title: "Your Child at the Center" },
  { n: "03", title: "Where You Align", indiv: "Your Reflection Summary" },
  { n: "04", title: "Where Your Perspectives Differ", indiv: "Areas You've Explored" },
  { n: "05", title: "What Might Your Child Need?" },
  { n: "06", title: "Options & Resources" },
  { n: "07", title: "Questions for Parent Conversation" },
  { n: "08", title: "Professional Conversation Guide" },
  { n: "09", title: "Parent Action Plan" },
  { n: "10", title: "Complete Alignment Summary" },
];


function StatusBadge({ status }) {
  // 3-state neutral pill — never adjudicative. Matches PDF palette.
  const map = {
    shared: { text: "Shared", bg: "bg-[#E6F5EC]", fg: "text-[#1E6A42]" },
    "one-side": { text: "One-side", bg: "bg-[#FCEFD7]", fg: "text-[#AA6A00]" },
    "not-yet": { text: "Not yet", bg: "bg-[#EEEAF5]", fg: "text-[#4B4567]" },
    completed: { text: "Completed", bg: "bg-[#E6F5EC]", fg: "text-[#1E6A42]" },
    pending: { text: "Not yet", bg: "bg-[#EEEAF5]", fg: "text-[#4B4567]" },
  };
  const cfg = map[status] || map.pending;
  return (
    <span
      className={`inline-flex items-center rounded-full text-[10px] font-bold uppercase tracking-[0.14em] px-2 py-0.5 ${cfg.bg} ${cfg.fg}`}
      data-testid={`complete-report-badge-${status}`}
    >
      {cfg.text}
    </span>
  );
}


function LaneRow({ lane, variant }) {
  const status = variant === "joint" ? lane.status : (lane.completed ? "completed" : "pending");
  return (
    <div
      className="flex items-start justify-between gap-3 border-b border-[#EEEAF5] last:border-b-0 py-2.5"
      data-testid={`complete-report-lane-${lane.id}`}
    >
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-[#1A1330]">{lane.title}</div>
        <div className="text-xs text-[#4B4567] mt-0.5 leading-snug">{lane.blurb}</div>
      </div>
      <StatusBadge status={status} />
    </div>
  );
}


function Section({ n, title, children }) {
  return (
    <section
      className="mt-8"
      data-testid={`complete-report-section-${n}`}
    >
      <div className="flex items-baseline gap-3">
        <span className="text-xs font-bold tracking-[0.22em] text-[#3D1A78]">{n}</span>
        <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330]">{title}</h2>
      </div>
      <div className="mt-3 rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5">
        {children}
      </div>
    </section>
  );
}


export default function CompleteAlignmentReport() {
  const { caseId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);

  const variant = caseId ? "joint" : "individual";
  const jsonPath = caseId
    ? `/complete-report/joint/${caseId}`
    : "/complete-report/mine";
  const pdfPath = caseId
    ? `/complete-report/joint/${caseId}.pdf`
    : "/complete-report/mine.pdf";

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      setError("Please sign in to see your Complete Alignment Report.");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get(jsonPath)
      .then((r) => {
        if (cancelled) return;
        setData(r.data || null);
      })
      .catch((err) => {
        if (cancelled) return;
        logError("complete-report load failed", err);
        const status = err?.response?.status;
        if (status === 404) {
          setError(
            variant === "joint"
              ? "This joint report is not available. Both parents may not have accepted the invitation yet, or you may not be a member of this case."
              : "This report is not available."
          );
        } else if (status === 409) {
          setError("Both parents have not accepted the invitation yet. The joint report will unlock once they do.");
        } else {
          setError("We couldn't load your Complete Alignment Report. Please try again.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, jsonPath, variant]);

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      // Use axios blob so the auth cookie/bearer flow the app already
      // handles for the JSON view is applied to the PDF request too.
      const r = await api.get(pdfPath, { responseType: "blob" });
      const blob = new Blob([r.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = caseId
        ? `SA-CoParents-Complete-Alignment-${caseId}.pdf`
        : "SA-CoParents-Complete-Alignment-Report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      logError("complete-report pdf failed", err);
      alert("We couldn't download the PDF. Please try again in a moment.");
    } finally {
      setDownloading(false);
    }
  };

  const counts = data?.counts || {};
  const lanes = data?.lanes || [];
  const parents = data?.parents || null;
  const child = data?.child_name;

  const headerSubtitle = useMemo(() => {
    if (variant === "joint" && parents?.length === 2) {
      return `Prepared for ${parents[0]} and ${parents[1]}`;
    }
    if (data?.parent_name && data.parent_name !== "You") {
      return `Prepared for ${data.parent_name}`;
    }
    return "Prepared for you";
  }, [variant, parents, data]);

  return (
    <div className="min-h-screen bg-[#FAF8FD]" data-testid="complete-report-page">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Back link */}
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] hover:underline mb-6"
          data-testid="complete-report-back"
        >
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        {/* Header block */}
        <header className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#F5F1FB] p-6 sm:p-8">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-[0.22em] uppercase text-[#3D1A78]">
              {variant === "joint" ? "Joint Report" : "Individual Report"}
            </span>
            <span className="text-[10px] font-semibold text-[#857E9C]">
              Same 10-section structure as sacoparentsalign.com
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-2 leading-tight">
            Complete Alignment Report
          </h1>
          <p className="text-sm text-[#4B4567] mt-2">
            {headerSubtitle}
            {child ? ` · About ${child}` : ""}
          </p>

          {/* Counts strip */}
          {!loading && !error && (
            <div className="mt-5 flex flex-wrap gap-3 items-center">
              {variant === "joint" ? (
                <>
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-[#E6F5EC] text-[#1E6A42] text-xs font-bold px-3 py-1.5">
                    <CheckCircle2 size={12} /> {counts.shared || 0} shared
                  </div>
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-[#FCEFD7] text-[#AA6A00] text-xs font-bold px-3 py-1.5">
                    <Clock size={12} /> {counts.one_side || 0} one-side
                  </div>
                  <div className="text-xs text-[#4B4567]">of {counts.total || 0} lanes</div>
                </>
              ) : (
                <>
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-[#E6F5EC] text-[#1E6A42] text-xs font-bold px-3 py-1.5">
                    <CheckCircle2 size={12} /> {counts.completed || 0} completed
                  </div>
                  <div className="text-xs text-[#4B4567]">of {counts.total || 0} lanes</div>
                </>
              )}
              <button
                type="button"
                onClick={downloadPdf}
                disabled={downloading}
                className="ml-auto inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] disabled:opacity-60 text-white text-xs font-semibold px-4 py-2 transition-colors"
                data-testid="complete-report-download-pdf"
              >
                {downloading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                {downloading ? "Preparing PDF…" : "Download 10-section PDF"}
              </button>
            </div>
          )}
        </header>

        {/* Loading / error states */}
        {loading && (
          <div
            className="mt-8 rounded-2xl border border-[#E5E0EE] bg-white p-6 flex items-center gap-3"
            data-testid="complete-report-loading"
          >
            <Loader2 size={16} className="animate-spin text-[#3D1A78]" />
            <span className="text-sm text-[#4B4567]">Loading your Complete Alignment Report…</span>
          </div>
        )}
        {!loading && error && (
          <div
            className="mt-8 rounded-2xl border border-[#F0D9A1] bg-[#FFF6E5] p-5"
            data-testid="complete-report-error"
          >
            <div className="text-sm text-[#8A5B00]">{error}</div>
          </div>
        )}

        {/* Sections */}
        {!loading && !error && data && (
          <>
            {/* 01 — Overview */}
            <Section n={SECTIONS[0].n} title={SECTIONS[0].title}>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                {variant === "joint"
                  ? "This report brings both parents' reflections into one place. It follows the same ten-section structure every SA CoParents Align report uses — a mediator, attorney, or therapist reading it always knows where to look."
                  : "This report brings every reflection you've completed on SA CoParents into one place. It follows the same ten-section structure every SA CoParents Align report uses, so the professional you share it with always knows where to look."}
              </p>
              <p className="text-xs text-[#857E9C] italic mt-3">
                Educational and organizational tool — not a diagnosis or court submission.
              </p>
            </Section>

            {/* 02 — Child */}
            <Section n={SECTIONS[1].n} title={SECTIONS[1].title}>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                Every section that follows keeps <strong>{child || "your child"}</strong> — not the dispute — at the center of the conversation. Neutral, non-diagnostic, and never a judgment about which parent is right.
              </p>
            </Section>

            {/* 03 — Align / Reflection Summary */}
            <Section
              n={SECTIONS[2].n}
              title={variant === "joint" ? SECTIONS[2].title : SECTIONS[2].indiv}
            >
              {variant === "individual" ? (
                <IndividualFoundation lanes={lanes} />
              ) : (
                <JointLaneList lanes={lanes} filter="shared" empty="Neither parent has completed the same lane yet — the best next step is for each parent to complete the Foundation Statement." />
              )}
            </Section>

            {/* 04 — Differ / Areas explored */}
            <Section
              n={SECTIONS[3].n}
              title={variant === "joint" ? SECTIONS[3].title : SECTIONS[3].indiv}
            >
              {variant === "individual" ? (
                <IndividualAreas lanes={lanes} />
              ) : (
                <JointLaneList lanes={lanes} filter="not-shared" />
              )}
            </Section>

            {/* 05 — Child Needs */}
            <Section n={SECTIONS[4].n} title={SECTIONS[4].title}>
              <ChildNeedsExcerpt data={data} variant={variant} />
            </Section>

            {/* 06 — Options */}
            <Section n={SECTIONS[5].n} title={SECTIONS[5].title}>
              <ul className="text-sm text-[#4B4567] space-y-2 leading-relaxed">
                <li>Set a shared weekly cadence for information exchange — a 15-minute Sunday-evening handover note often lowers weekday friction.</li>
                <li>Agree on one written channel (email or a co-parenting app) for scheduling — keep synchronous calls for time-sensitive decisions only.</li>
                <li>If a lane feels stuck, invite the professional to walk through one Foundation prompt out loud with each parent before returning to the disagreement.</li>
                <li>Book a follow-up reflection 4–6 weeks after any change so the plan can be adjusted before small frictions turn structural.</li>
              </ul>
            </Section>

            {/* 07 — Questions */}
            <Section n={SECTIONS[6].n} title={SECTIONS[6].title}>
              <ul className="text-sm text-[#4B4567] space-y-2 leading-relaxed">
                {(variant === "joint" ? [
                  "Which one part of the weekly rhythm, if it were more predictable, would lower our child's stress the most?",
                  "When did we last agree on something small? What made that agreement possible?",
                  "What do we each need from the other during handovers to keep them calm for our child?",
                  "If a professional could hold one thing steady for us across the next six weeks, what would it be?",
                ] : [
                  "Which reflection surprised me the most — and why?",
                  "Where do I feel most confident in what I wrote? Where am I still working it out?",
                  "If my co-parent read only one paragraph of this report, which one do I hope they read?",
                  "What small step in the next two weeks would move a lane from 'not yet' to 'completed'?",
                ]).map((q, i) => <li key={i}>{q}</li>)}
              </ul>
            </Section>

            {/* 08 — Professional guide */}
            <Section n={SECTIONS[7].n} title={SECTIONS[7].title}>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                A short guide for the professional. Not clinical advice — a scaffold for the first (or next) session that keeps the conversation child-focused. The downloadable PDF contains the full 4-step guide.
              </p>
            </Section>

            {/* 09 — Action plan */}
            <Section n={SECTIONS[8].n} title={SECTIONS[8].title}>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                One small commitment for the next 2–4 weeks. Keep it specific, keep it reviewable. The follow-up session will start here.
              </p>
              <p className="text-xs text-[#857E9C] mt-2 italic">Fillable action lines appear in the downloadable PDF.</p>
            </Section>

            {/* 10 — Summary */}
            <Section n={SECTIONS[9].n} title={SECTIONS[9].title}>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                SA CoParents does not decide which parent is right or wrong. This report organizes reflections into a shared starting point so a mediator, attorney, or therapist can guide the next conversation with the child at the center.
              </p>
              <p className="text-xs text-[#857E9C] italic mt-3">
                Not a diagnosis, not a court submission, not legal or medical advice. Educational and organizational only.
              </p>
            </Section>

            {/* Bottom download */}
            <div className="mt-10 flex justify-center">
              <button
                type="button"
                onClick={downloadPdf}
                disabled={downloading}
                className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] disabled:opacity-60 text-white text-sm font-semibold px-5 py-2.5 transition-colors"
                data-testid="complete-report-download-pdf-bottom"
              >
                {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                {downloading ? "Preparing PDF…" : "Download 10-section PDF"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}


// --- Small helpers -----------------------------------------------------------

function IndividualFoundation({ lanes }) {
  const foundation = lanes.find((l) => l.id === "foundation");
  const prompts = foundation?.prompts || {};
  const rows = [
    ["Through the child's eyes", prompts.child_lens],
    ["The part I own", prompts.own_part],
    ["The best realistic outcome", prompts.best_outcome],
    ["What I want my co-parent to hear", prompts.coparent_feedback],
  ].filter(([_, v]) => v && v.trim());
  if (rows.length === 0) {
    return (
      <div className="text-sm text-[#4B4567] leading-relaxed">
        You haven't completed the Foundation Statement yet. Once you do, your four prompts appear here — the professional reads your own words rather than a paraphrase.{" "}
        <Link to="/reflection" className="font-semibold text-[#3D1A78] hover:underline" data-testid="complete-report-cta-foundation">
          Start the Foundation Statement →
        </Link>
      </div>
    );
  }
  return (
    <dl className="text-sm space-y-3">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt className="text-xs font-bold tracking-[0.16em] uppercase text-[#3D1A78]">{k}</dt>
          <dd className="text-[#1A1330] mt-1 leading-relaxed">{v}</dd>
        </div>
      ))}
    </dl>
  );
}


function IndividualAreas({ lanes }) {
  // Skip Foundation — it's expanded in Section 03.
  const others = lanes.filter((l) => l.id !== "foundation");
  return (
    <div>
      {others.map((lane) => (
        <LaneRow key={lane.id} lane={lane} variant="individual" />
      ))}
    </div>
  );
}


function JointLaneList({ lanes, filter, empty }) {
  const filtered = filter === "shared"
    ? lanes.filter((l) => l.status === "shared")
    : lanes.filter((l) => l.status !== "shared");
  if (filtered.length === 0) {
    return <div className="text-sm text-[#4B4567] leading-relaxed">{empty || "Nothing here yet."}</div>;
  }
  return (
    <div>
      {filtered.map((lane) => (
        <LaneRow key={lane.id} lane={lane} variant="joint" />
      ))}
    </div>
  );
}


function ChildNeedsExcerpt({ data, variant }) {
  const childNeedsLane = (data?.lanes || []).find((l) => l.id === "child_needs");
  const highlights = variant === "joint"
    ? [
        ...(data?.parent_a?.lanes?.find((l) => l.id === "child_needs")?.highlights || []),
        ...(data?.parent_b?.lanes?.find((l) => l.id === "child_needs")?.highlights || []),
      ]
    : (childNeedsLane?.highlights || []);
  if (highlights.length === 0) {
    return (
      <div className="text-sm text-[#4B4567] leading-relaxed">
        The Child Needs Statement hasn't been completed yet. Its highlights will appear here once you finish that reflection.{" "}
        <Link to="/special-needs-v2" className="font-semibold text-[#3D1A78] hover:underline" data-testid="complete-report-cta-child-needs">
          Start Child Needs Statement →
        </Link>
      </div>
    );
  }
  return (
    <ul className="text-sm text-[#4B4567] space-y-2 leading-relaxed list-disc list-inside">
      {highlights.map((h, i) => <li key={i}>{h}</li>)}
    </ul>
  );
}
