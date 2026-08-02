/**
 * SpecialNeedsV2Report.jsx — 9-section polished report view.
 *
 *   1. Report Introduction
 *   2. Your Family Situation
 *   3. Areas of Need
 *   4. Your Co-Parenting Strengths
 *   5. Co-Parenting Challenges
 *   6. Child Impact Summary
 *   7. Detailed Findings by Category
 *   8. Parent Alignment Summary
 *   9. Recommended Co-Parenting Structure
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Download, RefreshCcw, Loader2, ArrowLeft, FileText, ShieldAlert, Users, Mail } from "lucide-react";
import { logError } from "../lib/logger";
import ReportReviewNotice from "../components/ReportReviewNotice";
import ReportProvenanceFooter from "../components/ReportProvenanceFooter";
import SignDownloadToggle from "../components/SignDownloadToggle";

const STATUS_COLOR = {
  "Strength":                          "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  "Developing":                        "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  "Needs Attention":                   "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  "Priority Concern":                  "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  "Professional Guidance Recommended": "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
};

function StatusPill({ status }) {
  if (!status) return null;
  const cls = STATUS_COLOR[status] || STATUS_COLOR.Developing;
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}>{status}</span>;
}

function BulletList({ items = [], testId }) {
  if (!items || items.length === 0) return <div className="text-sm text-[#8471B3] italic">—</div>;
  return <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1" data-testid={testId}>
    {items.map((it, i) => <li key={`${i}-${String(it).slice(0, 40)}`}>{it}</li>)}
  </ul>;
}

function Section({ id, number, title, children }) {
  return (
    <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid={`snc2-report-${id}`}>
      <h2 className="font-serif text-2xl text-[#1A1330] mb-3">{number ? `${number}. ` : ""}{title}</h2>
      {children}
    </section>
  );
}

export default function SpecialNeedsV2Report() {
  const [state, setState] = useState({ loading: true, doc: null, status: null });
  const [busy, setBusy] = useState(false);
  const [signOnDownload, setSignOnDownload] = useState(false);

  const load = useCallback(async () => {
    try {
      const [rep, st] = await Promise.all([api.get("/snc2/report"), api.get("/snc2/report/status")]);
      setState({ loading: false, doc: rep.data?.report ? rep.data : null, status: st.data });
    } catch (err) {
      logError("snc2 report load", err);
      setState({ loading: false, doc: null, status: null });
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setBusy(true);
    try { await api.post("/snc2/report/generate"); await load(); }
    catch (err) { logError("snc2 generate", err); toast.error(err?.response?.data?.detail || "Could not generate the report."); }
    finally { setBusy(false); }
  };
  const regenerate = async () => {
    setBusy(true);
    try { await api.post("/snc2/report/regenerate"); await load(); toast.success("Report regenerated."); }
    catch (err) { logError("snc2 regen", err); toast.error(err?.response?.data?.detail || "Regenerate failed."); }
    finally { setBusy(false); }
  };
  const downloadPdf = async () => {
    setBusy(true);
    try {
      const url = signOnDownload ? "/snc2/report/pdf?sign=true" : "/snc2/report/pdf";
      const res = await api.get(url, { responseType: "blob" });
      const objUrl = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = objUrl; a.download = "Special_Needs_Report.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(objUrl), 2000);
      if (signOnDownload) toast.success("Signed & downloaded.");
    } catch (err) { logError("snc2 pdf", err); toast.error(err?.response?.data?.detail || "Could not download the PDF."); }
    finally { setBusy(false); }
  };
  const emailReport = async () => {
    setBusy(true);
    try {
      const res = await api.post("/snc2/report/email", {});
      toast.success(`Report emailed to ${res.data?.sent_to || "your inbox"}.`);
    } catch (err) {
      logError("snc2 email", err);
      toast.error(err?.response?.data?.detail || "Could not email your report right now.");
    } finally { setBusy(false); }
  };

  if (state.loading) return <AppShell><div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]"><Loader2 className="animate-spin inline" /> Loading report…</div></AppShell>;

  if (!state.doc) return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 py-10">
        <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Special Needs Co-Parenting Report</h1>
        <p className="text-sm text-[#4B4567] mb-6">No report has been generated yet.</p>
        <div className="flex flex-wrap gap-3">
          <Link to="/special-needs-v2" data-testid="snc2-report-empty-open"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110">
            Open the assessment
          </Link>
          {state.status?.has_assessment && (
            <button onClick={generate} disabled={busy} data-testid="snc2-report-empty-generate"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
              {busy ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} Generate report
            </button>
          )}
        </div>
      </div>
    </AppShell>
  );

  const doc = state.doc;
  const r = doc.report || {};
  const status = state.status || {};
  const stale = status.stale === true;
  const cover = r.cover || {};
  const intro = r.intro || {};
  const fam = r.family_situation || {};
  const areas = r.areas_of_need || {};
  const strengths = r.strengths || {};
  const challenges = r.challenges || {};
  const childImpact = r.child_impact || {};
  const detailed = r.detailed_findings || {};
  const alignment = r.parent_alignment || {};
  const structure = r.recommended_structure || {};

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc2-report-root">
        <Link to="/dashboard" data-testid="snc2-report-back" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Individual Parent Report</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {intro.title || "Your Special Needs Co-Parenting Report"}
        </h1>
        <p className="text-sm text-[#4B4567] mt-3 whitespace-pre-wrap max-w-3xl">{intro.body}</p>

        <ReportReviewNotice variant="individual" className="mt-5" />

        {/* Cache header */}
        <div className="mt-6 rounded-3xl border border-[#E5E0EE] p-4 sm:p-5 bg-white flex flex-wrap items-center justify-between gap-3 shadow-sm" data-testid="snc2-report-cache-bar">
          <div className="text-xs text-[#4B4567]">
            {stale ? <span className="text-[#B02A2A] font-medium">Your answers have changed since this report was generated.</span>
                   : <span>Last generated {doc.generated_at ? new Date(doc.generated_at).toLocaleString() : "—"}.</span>}
          </div>
          <div className="flex items-center gap-2">
            <Link to="/special-needs-v2/compare" data-testid="snc2-report-open-compare"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]">
              <Users size={13} /> Co-Parent Compare
            </Link>
            <button onClick={downloadPdf} disabled={busy} data-testid="snc2-report-download-pdf"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download PDF
            </button>
            <button onClick={emailReport} disabled={busy} data-testid="snc2-report-email"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
              <Mail size={13} /> Email me the PDF
            </button>
            <button onClick={regenerate} disabled={busy} data-testid="snc2-report-regenerate"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCcw size={13} />} Regenerate
            </button>
          </div>
        </div>

        {/* Sign & timestamp opt-in — appears next to download so parents
            can add their name + UTC timestamp under the watermark. */}
        <div className="mt-2 flex justify-end">
          <SignDownloadToggle
            checked={signOnDownload}
            onChange={setSignOnDownload}
            testid="snc2-report-sign-toggle"
          />
        </div>

        {/* Cover meta */}
        <div className="mt-4 grid sm:grid-cols-3 gap-3 text-sm">
          <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Parent</div><div>{cover.parent_name || "—"}</div></div>
          <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Child</div><div>{cover.child_name || "—"}</div></div>
          <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Assessment date</div><div>{cover.assessment_date || "—"}</div></div>
        </div>

        {/* 2. Family Situation */}
        <Section id="family" number={2} title={fam.title || "Your Family Situation"}>
          <div className="text-sm text-[#4B4567] whitespace-pre-wrap">{fam.summary}</div>
          <div className="grid sm:grid-cols-2 gap-4 mt-4">
            <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Professionals involved</div>
              <BulletList items={fam.professionals_involved} testId="snc2-fam-pros" /></div>
            <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Decisions needed</div>
              <BulletList items={fam.decisions_needed} testId="snc2-fam-decisions" /></div>
            <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Agreements</div>
              <BulletList items={fam.agreements} testId="snc2-fam-agree" /></div>
            <div><div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Disagreements</div>
              <BulletList items={fam.disagreements} testId="snc2-fam-disagree" /></div>
          </div>
        </Section>

        {/* 3. Areas of Need */}
        <Section id="areas" number={3} title={areas.title || "Areas of Need"}>
          <div className="space-y-3">
            {(areas.blocks || []).map((b) => (
              <div key={b.id} className="p-4 rounded-2xl border border-[#EEE9F7] bg-[#FBF9FE]" data-testid={`snc2-area-${b.id}`}>
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">{b.name}</div>
                {b.concern && <div className="text-sm text-[#1A1330] mb-2"><strong>Concern:</strong> {b.concern}</div>}
                <div className="text-xs text-[#4B4567]">
                  {b.duration && <span>Duration: {b.duration}. </span>}
                  {b.urgency && <span>Urgency: {b.urgency}.</span>}
                </div>
                {(b.current_needs || []).length > 0 && <div className="mt-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Current needs</div>
                  <BulletList items={b.current_needs} />
                </div>}
                {b.professional_summary && <div className="mt-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Professional recommendation summary</div>
                  <div className="text-sm text-[#1A1330]">{b.professional_summary}</div>
                </div>}
              </div>
            ))}
          </div>
        </Section>

        {/* 4. Strengths */}
        <Section id="strengths" number={4} title={strengths.title || "Your Co-Parenting Strengths"}>
          <BulletList items={strengths.items} testId="snc2-strengths-list" />
        </Section>

        {/* 5. Challenges */}
        <Section id="challenges" number={5} title={challenges.title || "Co-Parenting Challenges"}>
          {(challenges.items || []).length === 0 ? (
            <div className="text-sm text-[#8471B3] italic">Your responses do not surface any pathway-level challenges above the concern threshold.</div>
          ) : (
            <div className="space-y-4">
              {challenges.items.map((c, idx) => (
                <div key={`${c.pathway_id}-${idx}`} className="p-4 rounded-2xl border border-[#EEE9F7] bg-white" data-testid={`snc2-challenge-${idx}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="font-serif text-lg text-[#1A1330]">{c.pathway_name}: {c.title}</div>
                    <StatusPill status={c.concern_level} />
                  </div>
                  <div className="mb-2"><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">What you reported</div>
                    <div className="text-sm text-[#1A1330]">{c.reported}</div></div>
                  <div className="mb-2"><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Why this may matter to your child</div>
                    <div className="text-sm text-[#1A1330]">{c.why_it_matters}</div></div>
                  <div><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Options to consider</div>
                    <BulletList items={c.options} /></div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* 6. Child Impact */}
        <Section id="child-impact" number={6} title={childImpact.title || "Child Impact Summary"}>
          <div className="text-xs text-[#8471B3] italic mb-2">Possible effects of the current pattern — not assigning blame.</div>
          <BulletList items={childImpact.possible_effects} testId="snc2-child-impact-list" />
        </Section>

        {/* 7. Detailed Findings */}
        <Section id="detailed" number={7} title={detailed.title || "Detailed Findings by Category"}>
          <div className="space-y-3">
            {(detailed.categories || []).map((row) => (
              <div key={row.id} className="p-4 rounded-2xl border border-[#EEE9F7] bg-white" data-testid={`snc2-detailed-${row.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="font-serif text-lg text-[#1A1330]">{row.name}</div>
                  <StatusPill status={row.status} />
                </div>
                <div className="text-sm text-[#1A1330] mb-2">{row.explanation}</div>
                {(row.strengths || []).length > 0 && <div className="mb-2"><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Existing strengths</div><BulletList items={row.strengths} /></div>}
                {(row.concerns || []).length > 0 && <div className="mb-2"><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Specific concerns</div><BulletList items={row.concerns} /></div>}
                {(row.actions || []).length > 0 && <div className="mb-2"><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Recommended parent actions</div><BulletList items={row.actions} /></div>}
                {(row.resources || []).length > 0 && <div><div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Professional resources to consider</div><BulletList items={row.resources} /></div>}
              </div>
            ))}
          </div>
        </Section>

        {/* 8. Parent Alignment */}
        <Section id="alignment" number={8} title={alignment.title || "Parent Alignment Summary"}>
          <BulletList items={alignment.resolved_labels} testId="snc2-alignment-list" />
          <div className="text-xs text-[#8471B3] italic mt-3">{alignment.note}</div>
        </Section>

        {/* 9. Recommended Structure */}
        <Section id="structure" number={9} title={structure.title || "Recommended Co-Parenting Structure"}>
          <div className="rounded-2xl border-2 border-[#3D1A78]/30 bg-[#F8F5FC] p-4 mb-4" data-testid="snc2-structure-recommendation">
            <div className="font-serif text-xl text-[#1A1330]">{structure.structure_name}</div>
            <div className="text-sm text-[#4B4567] mt-2">{structure.rationale}</div>
          </div>
          <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Safeguards to consider</div>
          <BulletList items={structure.safeguards} testId="snc2-structure-safeguards" />
          <div className="mt-4 rounded-2xl border-2 border-[#F1BDA1] bg-[#FBF2E7] p-3 flex items-start gap-2" data-testid="snc2-structure-safety-notice">
            <ShieldAlert className="text-[#C2481F] shrink-0 mt-0.5" size={18} />
            <div className="text-xs text-[#7A4A2E]">{structure.safety_notice}
              {" "}<Link to="/safety-assessment" className="underline font-semibold">Open the full Safety Assessment</Link>.</div>
          </div>
        </Section>

        <ReportProvenanceFooter variant="snc" className="mt-8" />

        <div className="mt-8 text-xs text-[#8471B3] italic">{r.disclaimer}</div>
      </div>
    </AppShell>
  );
}
