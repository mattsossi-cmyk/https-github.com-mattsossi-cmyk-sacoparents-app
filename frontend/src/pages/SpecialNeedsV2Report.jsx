/**
 * SpecialNeedsV2Report.jsx — SNC v2 report view.
 *
 * Renders the 8-step workflow report split per pathway with the
 * response → finding → child impact → suggested → action step pattern.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  Download, RefreshCcw, Loader2, ArrowLeft, FileText,
} from "lucide-react";
import { logError } from "../lib/logger";


const CLS_COLOR = {
  "Well aligned":               "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  "Generally aligned":          "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  "Coordination opportunity":   "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  "Significant inconsistency":  "bg-[#FBE0D3] text-[#C2481F] border-[#F1BDA1]",
  "Priority concern":           "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  "Not enough data":            "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
  "High reported impact":       "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  "Notable reported impact":    "bg-[#FBE0D3] text-[#C2481F] border-[#F1BDA1]",
  "Moderate reported impact":   "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  "Limited reported impact":    "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  "Minimal reported impact":    "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
};

function Pill({ label }) {
  if (!label) return null;
  const cls = CLS_COLOR[label] || CLS_COLOR["Not enough data"];
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}>{label}</span>;
}

function BulletList({ items = [], testId }) {
  if (!items || items.length === 0) return <div className="text-sm text-[#8471B3] italic">—</div>;
  return <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1" data-testid={testId}>
    {items.map((it, i) => <li key={`${i}-${String(it).slice(0, 30)}`}>{it}</li>)}
  </ul>;
}

function fmtScore(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

function StepBlock({ step }) {
  return (
    <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid={`snc2-report-step-${step.id}`}>
      <h2 className="font-serif text-2xl text-[#1A1330] mb-4">Step {step.number}. {step.name}</h2>
      <div className="space-y-5">
        {(step.pathways || []).map((pw) => (
          <div key={pw.id} className="rounded-2xl border border-[#EEE9F7] bg-[#FBF9FE] p-4" data-testid={`snc2-report-${step.id}-${pw.id}`}>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">{pw.name}</div>
            {pw.finding && (
              <div className="mb-3">
                <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Finding</div>
                <div className="text-sm text-[#1A1330]">{pw.finding}</div>
              </div>
            )}
            {pw.child_impact && (
              <div className="mb-3">
                <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Child impact</div>
                <div className="text-sm text-[#1A1330]">{pw.child_impact}</div>
              </div>
            )}
            {pw.suggested && (
              <div className="mb-3">
                <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Suggested option</div>
                <div className="text-sm text-[#1A1330]">{pw.suggested}</div>
              </div>
            )}
            {pw.action && (
              <div>
                <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-[#3D1A78] mb-1">Action step</div>
                <div className="text-sm text-[#1A1330]">{pw.action}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}


export default function SpecialNeedsV2Report() {
  const [state, setState] = useState({ loading: true, doc: null, status: null });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [rep, st] = await Promise.all([
        api.get("/snc2/report"),
        api.get("/snc2/report/status"),
      ]);
      setState({ loading: false, doc: rep.data?.report ? rep.data : null, status: st.data });
    } catch (err) {
      logError("snc2 report load", err);
      setState({ loading: false, doc: null, status: null });
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setBusy(true);
    try {
      await api.post("/snc2/report/generate");
      await load();
    } catch (err) {
      logError("snc2 generate", err);
      toast.error(err?.response?.data?.detail || "Could not generate the report.");
    } finally { setBusy(false); }
  };

  const regenerate = async () => {
    setBusy(true);
    try {
      await api.post("/snc2/report/regenerate");
      await load();
      toast.success("Report regenerated.");
    } catch (err) {
      logError("snc2 regen", err);
      toast.error(err?.response?.data?.detail || "Regenerate failed.");
    } finally { setBusy(false); }
  };

  const downloadPdf = async () => {
    setBusy(true);
    try {
      const res = await api.get("/snc2/report/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = "Special_Needs_Report.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      logError("snc2 pdf", err);
      toast.error(err?.response?.data?.detail || "Could not download the PDF.");
    } finally { setBusy(false); }
  };

  if (state.loading) {
    return <AppShell><div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]"><Loader2 className="animate-spin inline" /> Loading report…</div></AppShell>;
  }

  if (!state.doc) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Special Needs Co-Parenting Report</h1>
          <p className="text-sm text-[#4B4567] mb-6">No report has been generated yet.</p>
          <div className="flex flex-wrap gap-3">
            <Link to="/special-needs-v2" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110" data-testid="snc2-report-empty-open">
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
  }

  const doc = state.doc;
  const report = doc.report || {};
  const status = state.status || {};
  const generatedAt = doc.generated_at;
  const stale = status.stale === true;
  const summaries = report.pathway_summaries || [];
  const ag = report.at_a_glance || {};

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc2-report-root">
        <Link to="/dashboard" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4" data-testid="snc2-report-back">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Individual Parent Report</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">Special Needs Co-Parenting Report</h1>
        <p className="text-sm text-[#4B4567] mt-3 max-w-3xl">{report.purpose}</p>

        {/* Cache header */}
        <div className="mt-6 rounded-3xl border border-[#E5E0EE] p-4 sm:p-5 bg-white flex flex-wrap items-center justify-between gap-3 shadow-sm" data-testid="snc2-report-cache-bar">
          <div className="text-xs text-[#4B4567]">
            {stale ? <span className="text-[#B02A2A] font-medium">Your answers have changed since this report was generated.</span>
                   : <span>Last generated {generatedAt ? new Date(generatedAt).toLocaleString() : "—"}.</span>}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={downloadPdf} disabled={busy} data-testid="snc2-report-download-pdf"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
              <Download size={13} /> Download PDF
            </button>
            <button onClick={regenerate} disabled={busy} data-testid="snc2-report-regenerate"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCcw size={13} />} Regenerate
            </button>
          </div>
        </div>

        {/* At a glance */}
        <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid="snc2-report-at-a-glance">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3">At a glance</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Concerns as described</div>
              <BulletList items={ag.concerns_by_pathway} testId="snc2-glance-concerns" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">30-day priorities</div>
              <BulletList items={ag.top_priorities} testId="snc2-glance-priorities" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Coordination is working</div>
              <BulletList items={ag.coordination_wins} testId="snc2-glance-wins" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Coordination needs work</div>
              <BulletList items={ag.coordination_gaps} testId="snc2-glance-gaps" />
            </div>
          </div>
        </section>

        {/* Pathway summaries */}
        <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid="snc2-report-summaries">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3">Pathway scores</h2>
          <div className="space-y-3">
            {summaries.map((s) => (
              <div key={s.id} className="p-3 rounded-2xl border border-[#EEE9F7] bg-[#FBF9FE]" data-testid={`snc2-summary-${s.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium text-[#1A1330]">{s.name}</div>
                </div>
                <div className="mt-2 grid sm:grid-cols-3 gap-2 text-xs">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#3D1A78] font-semibold">Reported impact</div>
                    <div className="mt-1 flex items-center gap-2">
                      <Pill label={s.impact?.classification} />
                      <span className="text-[#4B4567]">{fmtScore(s.impact?.score)} / 5</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#3D1A78] font-semibold">Understanding</div>
                    <div className="mt-1 flex items-center gap-2">
                      <Pill label={s.understanding?.classification} />
                      <span className="text-[#4B4567]">{fmtScore(s.understanding?.score)} / 5</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#3D1A78] font-semibold">Coordination</div>
                    <div className="mt-1 flex items-center gap-2">
                      <Pill label={s.coordination?.classification} />
                      <span className="text-[#4B4567]">{fmtScore(s.coordination?.score)} / 5</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-[11px] italic text-[#8471B3] mt-3">Scores reflect the reporting parent&apos;s answers and are not findings of fact.</div>
        </section>

        {/* 8 step blocks */}
        {(report.steps || []).map((step) => <StepBlock key={step.id} step={step} />)}

        <div className="mt-8 text-xs text-[#8471B3] italic">{report.disclaimer}</div>
      </div>
    </AppShell>
  );
}
