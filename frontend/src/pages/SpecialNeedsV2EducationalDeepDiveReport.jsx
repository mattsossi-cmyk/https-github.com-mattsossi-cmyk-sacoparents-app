/**
 * SpecialNeedsV2EducationalDeepDiveReport.jsx — polished SA CoParents
 * journey report for the Educational Needs Deep Dive.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import BackToDashboardLink from "../components/BackToDashboardLink";
import PathwayEndCTA from "../components/PathwayEndCTA";
import ReportSectionCoachStrip from "../components/deepdive/ReportSectionCoachStrip";
import DeepDivePartsNarrative from "../components/deepdive/DeepDivePartsNarrative";
import ReportReviewNotice from "../components/ReportReviewNotice";
import ReportProvenanceFooter from "../components/ReportProvenanceFooter";
import AssessmentResultHandoff from "../components/AssessmentResultHandoff";
import CourtReportDisclaimer from "../components/CourtReportDisclaimer";
import SignDownloadToggle from "../components/SignDownloadToggle";
import { api } from "../lib/api";
import { useAiGuard } from "../components/aiNotice/AiGuard";
import { AddAiSummaryCard } from "../components/deepdive/AddAiSummaryCard";
import { toast } from "sonner";
import { downloadPdf } from "../lib/pdf";
import {
  ArrowLeft, Download, Loader2, Mail, RefreshCcw, Sparkles, Users,
} from "lucide-react";

import EmailDeliveryBadge from "../components/EmailDeliveryBadge";
import { logError } from "../lib/logger";
import { bandPillClass, bandBarClass } from "../lib/scoreBandStyles";


const RATING_STYLES = {
  Strong: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  Developing: "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]",
  "Needs Attention": "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  "Not enough info": "bg-[#F1EEF7] text-[#4B4567] border-[#E5E0EE]",
};

function RatingPill({ rating, testid }) {
  const cls = RATING_STYLES[rating] || RATING_STYLES["Not enough info"];
  return (
    <span data-testid={testid}
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}>
      {rating || "-"}
    </span>
  );
}

function SectionCard({ children, testid }) {
  return (
    <section data-testid={testid}
      className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
      {children}
    </section>
  );
}

function Eyebrow({ children }) {
  return (
    <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">{children}</div>
  );
}


export default function SpecialNeedsV2EducationalDeepDiveReport() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [regenBusy, setRegenBusy] = useState(false);
  const [regenLength, setRegenLength] = useState("standard");
  const [regenModel, setRegenModel] = useState("claude");
  const [report, setReport] = useState(null);
  const [signOnDownload, setSignOnDownload] = useState(false);
  const [signNote, setSignNote] = useState("");
  const [deliveryTick, setDeliveryTick] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.post("/edu-deep/report/generate");
      setReport(r.data?.report || null);
    } catch (err) {
      logError("edu-deep report", err);
      toast.error(err?.response?.data?.detail || "Could not load the report.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const aiGuard = useAiGuard("summary");
  const regenerateSummary = async () => {
    if (!(await aiGuard.confirmSend(""))) return;
    setRegenBusy(true);
    try {
      const r = await api.post("/edu-deep/report/regen-summary", {
        length: regenLength,
        model: regenModel,
      });
      setReport(r.data?.report || null);
      toast.success(
        regenModel === "gpt"
          ? "Summary regenerated with GPT-5.6 Terra."
          : "AI summary refreshed."
      );
    } catch (err) {
      logError("edu-deep regen summary", err);
      toast.error(err?.response?.data?.detail || "Could not regenerate the summary.");
    } finally { setRegenBusy(false); }
  };

  const download = async () => {
    setBusy(true);
    const params = signOnDownload
      ? { sign: true, ...(signNote.trim() ? { note: signNote.trim() } : {}) }
      : undefined;
    await downloadPdf("/edu-deep/report/pdf", {
      filename: "Educational_Assessment_Report.pdf",
      params,
      testid: "edu-deep-report-pdf",
      onSuccess: () => {
        if (signOnDownload) toast.success("Signed & downloaded.");
      },
    });
    setBusy(false);
  };

  const emailReport = async () => {
    setBusy(true);
    try {
      const res = await api.post("/edu-deep/report/email", {});
      toast.success(`Report emailed to ${res.data?.sent_to || "your inbox"}.`);
      setDeliveryTick((v) => v + 1);
    } catch (err) {
      logError("edu-deep email", err);
      toast.error(err?.response?.data?.detail || "Could not email your report right now.");
    } finally { setBusy(false); }
  };

  if (loading) {
    return <AppShell><div className="p-10 text-sm text-[#4B4567]"><Loader2 className="animate-spin inline" size={14} /> Loading...</div></AppShell>;
  }
  if (!report) {
    return <AppShell><div className="p-10 text-sm text-[#4B4567]">No report available yet.</div></AppShell>;
  }

  const cover = report.cover || {};
  const overview = report.overview || {};
  const support = report.support_summary || {};
  const profile = report.child_profile || {};
  const involvement = report.school_involvement || {};
  const coparenting = report.co_parenting_assessment || {};
  const level = report.support_level || {};
  const ratings = support.ratings || [];
  const alignment = report.alignment_areas || [];
  const attention = report.attention_areas || [];
  const options = report.practical_options || [];
  const actionPlan = report.action_plan || [];
  const questions = report.questions_for_school_or_parent || [];

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="edu-deep-report-root">
        <BackToDashboardLink
          className="mb-3"
          testId="edu-deep-report-back-dashboard"
        />
        <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
          <Link to="/special-needs-v2/educational-deep-dive" className="inline-flex items-center gap-1 text-xs text-[#4B4567] underline">
            <ArrowLeft size={12} /> Back to Deep Dive
          </Link>
          <div className="flex gap-2">
            <Link to="/special-needs-v2/educational-deep-dive/compare" data-testid="edu-deep-report-open-compare"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#1F5C3B] text-white hover:brightness-110">
              <Users size={13} /> Compare Our Educational Priorities
            </Link>
            <button onClick={download} disabled={busy} data-testid="edu-deep-report-download"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download PDF
            </button>
            <button onClick={emailReport} disabled={busy} data-testid="edu-deep-report-email"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
              <Mail size={13} /> Email me a private link
            </button>
            <EmailDeliveryBadge reportType="edu_deep" refreshKey={deliveryTick} />
            <button onClick={load} disabled={busy} data-testid="edu-deep-report-refresh"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#EEE9F7]">
              <RefreshCcw size={13} /> Refresh
            </button>
          </div>
        </div>

        {/* Sign & timestamp opt-in */}
        <div className="flex justify-end mb-4">
          <SignDownloadToggle
            checked={signOnDownload}
            onChange={setSignOnDownload}
            note={signNote}
            onNoteChange={setSignNote}
            testid="edu-deep-report-sign-toggle"
          />
        </div>

        <Eyebrow>Educational Needs · SA CoParents Report</Eyebrow>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">Educational Assessment Report</h1>

        <ReportReviewNotice variant="individual" className="mt-5" />

        <AssessmentResultHandoff assessmentType="educational" />

        <CourtReportDisclaimer
          className="mt-6"
          authorName={cover.parent_name || null}
          bothParents={false}
          testId="edu-deep-report-court-disclaimer"
        />

        {/* v2 alignment score card — total, band, per-part breakdown */}
        {report.score_card && (
          <SectionCard testid="edu-report-score-card">
            <div className="flex items-start gap-4 flex-wrap justify-between">
              <div className="min-w-0">
                <Eyebrow>Alignment score</Eyebrow>
                <div className="flex items-baseline gap-2">
                  <div
                    className="font-serif text-5xl leading-none text-[#3D1A78]"
                    data-testid="edu-report-score-total"
                  >
                    {report.score_card.percent}
                  </div>
                  <div className="text-sm text-[#4B4567]">/ 100</div>
                </div>
                <div className="mt-2 text-xs text-[#4B4567]">
                  {report.score_card.answered} of 25 answered
                  {report.score_card.na ? ` · ${report.score_card.na} N/A` : ""}
                </div>
              </div>
              <div className="flex-1 min-w-[220px]">
                <div
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-bold border ${bandPillClass(report.score_card.band)}`}
                  data-testid="edu-report-score-band"
                >
                  {report.score_card.band_label}
                </div>
                <p className="mt-2 text-sm text-[#1A1330]">
                  {report.score_card.band_summary}
                </p>
              </div>
            </div>

            {/* Per-part breakdown */}
            {(report.score_card.sections || []).length > 0 && (
              <div className="mt-5 space-y-2" data-testid="edu-report-score-parts">
                {report.score_card.sections.map((s) => (
                  <div
                    key={s.id}
                    className="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border border-[#E5E0EE] px-3 py-2"
                    data-testid={`edu-report-score-part-${s.id}`}
                  >
                    <div className="text-xs font-bold text-[#3D1A78]">
                      Part {s.number}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-[#1A1330] truncate">
                        {s.name}
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-[#EEE9F7] overflow-hidden">
                        <div
                          className={`h-full transition-all ${bandBarClass(s.band)}`}
                          style={{ width: `${s.percent}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-sm font-bold text-[#1A1330] tabular-nums">
                      {s.answered ? `${s.percent}%` : "—"}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Band next steps */}
            {(report.score_card.next_steps || []).length > 0 && (
              <div
                className="mt-5 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] px-4 py-3"
                data-testid="edu-report-next-steps"
              >
                <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
                  Next steps
                </div>
                <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                  {report.score_card.next_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Format-change banner retired — v2 rich narrative below. */}
          </SectionCard>
        )}

        {/* Rich per-part storytelling (opening + 5 parts + closing). */}
        <DeepDivePartsNarrative
          parts={report.parts_narrative || []}
          opening={report.opening_story || ""}
          closing={report.closing_story || ""}
          testidPrefix="edu-report"
        />

        {/* 1. Report Overview */}
        <SectionCard testid="edu-report-overview">
          <h2 className="font-serif text-xl text-[#1A1330]">1. Report overview</h2>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-[#4B4567]">
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">Parent</dt>
              <dd className="text-[#1A1330] font-semibold">{cover.parent_name}</dd></div>
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">Child</dt>
              <dd className="text-[#1A1330] font-semibold">{cover.child_name}</dd></div>
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">Grade</dt>
              <dd className="text-[#1A1330]">{cover.grade_level}</dd></div>
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">State</dt>
              <dd className="text-[#1A1330]">{cover.school_state}</dd></div>
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">Setting</dt>
              <dd className="text-[#1A1330]">{cover.school_setting}</dd></div>
            <div><dt className="uppercase tracking-widest text-[10px] font-semibold text-[#3D1A78]">Date</dt>
              <dd className="text-[#1A1330]">{cover.assessment_date}</dd></div>
          </dl>
          <h3 className="mt-4 text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78]">Purpose</h3>
          <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1 mt-1">
            {(overview.purpose_bullets || []).map((b) => (<li key={b}>{b}</li>))}
          </ul>
          <p className="text-[11px] text-[#4B4567] italic mt-3">{report.disclaimer}</p>
        </SectionCard>

        {/* 2. Educational Support Summary */}
        <SectionCard testid="edu-report-support-summary">
          <h2 className="font-serif text-xl text-[#1A1330]">2. Your educational support summary</h2>
          <div className="mt-4 space-y-3">
            {ratings.map((r) => (
              <div key={r.id} className="rounded-2xl border border-[#E5E0EE] p-3" data-testid={`edu-report-rating-${r.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="text-sm font-semibold text-[#1A1330]">{r.area}</div>
                  <RatingPill rating={r.rating} testid={`edu-report-rating-${r.id}-pill`} />
                </div>
                {r.narrative && <div className="text-xs text-[#4B4567] mt-1">{r.narrative}</div>}
              </div>
            ))}
          </div>
          {support.overall_narrative && (
            <div className="mt-4 bg-[#FCFBFE] rounded-2xl border border-[#E5E0EE] p-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Overall</div>
              <div className="text-sm text-[#1A1330]">{support.overall_narrative}</div>
            </div>
          )}
        </SectionCard>

        {/* AI Executive Summary (existing feature) */}
        {!report.ai_summary && <AddAiSummaryCard tp="edu-deep" busy={regenBusy} onAdd={regenerateSummary} />}
        {report.ai_summary && (
          <SectionCard testid="edu-deep-ai-summary">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2 mb-1">
                  <Sparkles size={12} /> AI executive summary
                </div>
                <p className="text-[11px] text-[#6A5799] italic">Neutral · non-diagnostic · generated from your answers</p>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="inline-flex rounded-full border border-[#D6CFE8] overflow-hidden text-[10px] font-semibold" data-testid="edu-deep-length-toggle">
                  {["short", "standard", "long"].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setRegenLength(lvl)}
                      disabled={regenBusy}
                      data-testid={`edu-deep-length-${lvl}`}
                      className={`px-3 py-1.5 transition-colors ${regenLength === lvl ? "bg-[#3D1A78] text-white" : "text-[#3D1A78] bg-white hover:bg-[#F5F1FB]"} disabled:opacity-60`}
                    >
                      {lvl === "short" ? "Short" : lvl === "standard" ? "Standard" : "Long"}
                    </button>
                  ))}
                </div>
                {/* AI model picker — Claude (default) or GPT 5.6 Terra.
                    Same prompts + guardrails, different voice. Lets a
                    parent compare reads before sharing. */}
                <div className="inline-flex rounded-full border border-[#D6CFE8] overflow-hidden text-[10px] font-semibold"
                     data-testid="edu-deep-model-toggle"
                     title="Which AI writes this summary. Same prompts, same neutral guardrails - just a different voice.">
                  {[
                    { key: "claude", label: "Claude" },
                    { key: "gpt",    label: "GPT 5.6" },
                  ].map((m) => (
                    <button
                      key={m.key}
                      type="button"
                      onClick={() => setRegenModel(m.key)}
                      disabled={regenBusy}
                      data-testid={`edu-deep-model-${m.key}`}
                      className={`px-3 py-1.5 transition-colors ${regenModel === m.key ? "bg-[#3D1A78] text-white" : "text-[#3D1A78] bg-white hover:bg-[#F5F1FB]"} disabled:opacity-60`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                <button onClick={regenerateSummary} disabled={regenBusy}
                  data-testid="edu-deep-regen-summary"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
                  {regenBusy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCcw size={12} />}
                  {regenBusy ? "Regenerating…" : "Regenerate"}
                </button>
              </div>
            </div>
            <p className="text-sm text-[#1A1330] whitespace-pre-wrap leading-relaxed mt-3">{report.ai_summary}</p>
            {report.ai_summary_regenerated_at && (
              <p className="text-[10px] text-[#6A5799] italic mt-2" data-testid="edu-deep-regen-timestamp">
                Last regenerated: {new Date(report.ai_summary_regenerated_at).toLocaleString()}
                {report.ai_summary_length && ` · ${report.ai_summary_length}`}
                {report.ai_summary_model && ` · ${report.ai_summary_model === "gpt" ? "GPT 5.6 Terra" : "Claude Sonnet 4.5"}`}
              </p>
            )}
          </SectionCard>
        )}

        {/* 3. Child's Educational Profile */}
        <SectionCard testid="edu-report-child-profile">
          <h2 className="font-serif text-xl text-[#1A1330]">3. Your child&apos;s educational profile</h2>
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#1F5C3B] mb-1">Strengths</div>
            <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
              {(profile.strengths || []).map((s) => (<li key={s}>{s}</li>))}
            </ul>
          </div>
          {(profile.concerns || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#B02A2A] mb-1">Concerns</div>
              <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                {(profile.concerns || []).map((c) => (<li key={c}>{c}</li>))}
              </ul>
            </div>
          )}
          {(profile.primary_concern || profile.benefit_from) && (
            <div className="mt-3 text-sm text-[#1A1330]">
              <p><span className="font-semibold">Primary concern:</span> {profile.primary_concern}</p>
              <p className="mt-1"><span className="font-semibold">May benefit from:</span> {profile.benefit_from}</p>
            </div>
          )}
          {profile.notes && (
            <div className="mt-3 text-sm text-[#1A1330] whitespace-pre-wrap italic">{profile.notes}</div>
          )}
        </SectionCard>

        {/* 4. School and Professional Involvement */}
        <SectionCard testid="edu-report-involvement">
          <h2 className="font-serif text-xl text-[#1A1330]">4. School and professional involvement</h2>
          {(involvement.roles || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Currently involved</div>
              <div className="flex flex-wrap gap-1.5">
                {(involvement.roles || []).map((r) => (
                  <span key={r} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]">{r}</span>
                ))}
              </div>
            </div>
          )}
          {(involvement.meetings || []).length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-2">Upcoming or recommended meetings</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[10px] uppercase tracking-[0.14em] text-[#6A5799] border-b border-[#E5E0EE]">
                      <th className="py-2 pr-3">Meeting</th><th className="py-2 pr-3">Status</th><th className="py-2">Suggested next step</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(involvement.meetings || []).map((m) => (
                      <tr key={m.name} className="border-b border-[#F1EEF7] align-top">
                        <td className="py-2 pr-3 text-[#1A1330] font-medium">{m.name}</td>
                        <td className="py-2 pr-3 text-[#4B4567]">{m.current_status}</td>
                        <td className="py-2 text-[#4B4567]">{m.next_step}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </SectionCard>

        {/* 5. Educational Co-Parenting Assessment */}
        <SectionCard testid="edu-report-coparenting">
          <h2 className="font-serif text-xl text-[#1A1330]">5. Educational co-parenting assessment</h2>
          {[
            ["Information sharing", coparenting.information_sharing],
            ["Consistency between homes", coparenting.consistency_between_homes],
            ["Educational decision-making", coparenting.decision_making],
          ].map(([label, block]) => block && (
            <div key={label} className="mt-4">
              <div className="flex items-center gap-2 flex-wrap">
                <div className="text-sm font-semibold text-[#1A1330]">{label}</div>
                <RatingPill rating={block.rating} />
              </div>
              {(block.shared_items || block.items || []).length > 0 && (
                <ul className="list-disc pl-5 text-xs text-[#4B4567] space-y-0.5 mt-1">
                  {(block.shared_items || block.items || []).map((i) => (<li key={i}>{i}</li>))}
                </ul>
              )}
              {(block.gap_items || []).length > 0 && (
                <div className="text-xs text-[#B02A2A] italic mt-1">Possible gaps: {(block.gap_items || []).join(", ")}</div>
              )}
            </div>
          ))}
        </SectionCard>

        {/* 6. Areas of alignment */}
        {alignment.length > 0 && (
          <SectionCard testid="edu-report-alignment">
            <h2 className="font-serif text-xl text-[#1F5C3B]">6. Areas of alignment</h2>
            <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1 mt-3">
              {alignment.map((a) => (<li key={a}>{a}</li>))}
            </ul>
          </SectionCard>
        )}

        {/* 7. Areas requiring attention */}
        {attention.length > 0 && (
          <SectionCard testid="edu-report-attention">
            <h2 className="font-serif text-xl text-[#B02A2A]">7. Areas requiring attention</h2>
            <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1 mt-3">
              {attention.map((a) => (<li key={a}>{a}</li>))}
            </ul>
          </SectionCard>
        )}

        {/* 8. Support Level */}
        <SectionCard testid="edu-report-level">
          <h2 className="font-serif text-xl text-[#1A1330]">8. Recommended educational support level</h2>
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <RatingPill rating={level.level === 1 ? "Strong" : level.level === 2 ? "Developing" : "Needs Attention"} />
            <div className="text-sm font-semibold text-[#1A1330]">Level {level.level} — {level.name}</div>
          </div>
          {level.description && <p className="text-sm text-[#1A1330] mt-2">{level.description}</p>}
          {(level.next_steps || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Suggested next steps</div>
              <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                {(level.next_steps || []).map((s) => (<li key={s}>{s}</li>))}
              </ul>
            </div>
          )}
        </SectionCard>

        {/* 9. Practical options */}
        <SectionCard testid="edu-report-options">
          <h2 className="font-serif text-xl text-[#1A1330]">9. Practical options and resources</h2>
          <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1 mt-3">
            {options.map((o) => (<li key={o}>{o}</li>))}
          </ul>
        </SectionCard>

        {/* 10. Action plan */}
        <SectionCard testid="edu-report-action-plan">
          <h2 className="font-serif text-xl text-[#1A1330]">10. Your educational action plan</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-[0.14em] text-[#6A5799] border-b border-[#E5E0EE]">
                  <th className="py-2 pr-2">#</th><th className="py-2 pr-3">Action</th><th className="py-2 pr-3">Detail</th><th className="py-2 pr-3">Owner</th><th className="py-2">Target date</th>
                </tr>
              </thead>
              <tbody>
                {actionPlan.map((row) => (
                  <tr key={row.priority} className="border-b border-[#F1EEF7] align-top">
                    <td className="py-2 pr-2 text-[#3D1A78] font-bold">{row.priority}</td>
                    <td className="py-2 pr-3 text-[#1A1330] font-medium">{row.action}</td>
                    <td className="py-2 pr-3 text-[#4B4567]">{row.detail}</td>
                    <td className="py-2 pr-3 text-[#4B4567]">{row.responsible}</td>
                    <td className="py-2 text-[#4B4567]">{row.target || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        {/* 11. Foundation Statement */}
        <SectionCard testid="edu-report-foundation">
          <h2 className="font-serif text-xl text-[#1A1330]">11. Educational foundation statement</h2>
          <p className="text-sm text-[#1A1330] mt-3 italic bg-[#FCFBFE] rounded-2xl border border-[#E5E0EE] p-3">
            {report.foundation_statement}
          </p>
        </SectionCard>

        {/* 12. Questions */}
        <SectionCard testid="edu-report-questions">
          <h2 className="font-serif text-xl text-[#1A1330]">12. Questions for the other parent or school</h2>
          <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1 mt-3">
            {questions.map((q) => (<li key={q}>{q}</li>))}
          </ul>
        </SectionCard>

        {/* 13. Final summary */}
        <SectionCard testid="edu-report-final">
          <h2 className="font-serif text-xl text-[#1A1330]">13. Final child-focused summary</h2>
          <p className="text-sm text-[#1A1330] mt-3">{report.final_summary}</p>
        </SectionCard>

        <ReportSectionCoachStrip
          apiPrefix="/edu-deep"
          testidBase="edu-deep"
          userState={profile.school_state || cover.school_state}
        />

        <ReportProvenanceFooter variant="deepdive" className="mt-8" />

        <p className="text-[11px] text-[#4B4567] mt-8 italic">{report.disclaimer}</p>

        {/* One clear ending — the founder-mandated single next action. */}
        <PathwayEndCTA
          eyebrow="Educational pathway"
          title="Compare educational priorities with the other parent"
          description="Your co-parent completes the same 25-question deep dive on their own device. SA CoParents builds a neutral side-by-side view of where you agree and where a small tune-up would help."
          primary={{
            label: "Compare with the other parent",
            to: "/special-needs-v2/educational-deep-dive/compare",
          }}
          tone="green"
          icon={Users}
          testId="edu-deep-report-end-cta"
        />
      </div>
    </AppShell>
  );
}
