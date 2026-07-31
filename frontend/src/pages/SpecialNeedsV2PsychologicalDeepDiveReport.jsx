/**
 * SpecialNeedsV2EducationalDeepDiveReport.jsx — the polished report view
 * for the Educational Needs Deep Dive.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Download, Loader2, RefreshCcw, Sparkles } from "lucide-react";
import { logError } from "../lib/logger";


export default function SpecialNeedsV2PsychologicalDeepDiveReport() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.post("/psych-deep/report/generate");
      setReport(r.data?.report || null);
    } catch (err) {
      logError("edu-deep report", err);
      toast.error(err?.response?.data?.detail || "Could not load the report.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const download = async () => {
    setBusy(true);
    try {
      const res = await api.get("/psych-deep/report/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = "Psychological_Deep_Dive.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      logError("edu-deep pdf", err);
      toast.error(err?.response?.data?.detail || "Could not download the PDF.");
    } finally { setBusy(false); }
  };

  if (loading) {
    return <AppShell><div className="p-10 text-sm text-[#4B4567]"><Loader2 className="animate-spin inline" size={14} /> Loading...</div></AppShell>;
  }

  if (!report) {
    return <AppShell><div className="p-10 text-sm text-[#4B4567]">No report available.</div></AppShell>;
  }

  const summary = report.summary || {};
  const profile = report.profile || {};

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="psych-deep-report-root">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
          <Link to="/special-needs-v2/psychological-deep-dive" className="inline-flex items-center gap-1 text-xs text-[#4B4567] underline">
            <ArrowLeft size={12} /> Back to Deep Dive
          </Link>
          <div className="flex gap-2">
            <button onClick={download} disabled={busy} data-testid="psych-deep-report-download"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download PDF
            </button>
            <button onClick={load} disabled={busy} data-testid="psych-deep-report-refresh"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#EEE9F7]">
              <RefreshCcw size={13} /> Refresh
            </button>
          </div>
        </div>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Psychological Needs · Deep Dive</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">Deep Dive Report</h1>

        {/* Profile */}
        <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          <h2 className="font-serif text-xl text-[#1A1330]">1. Psychological Profile</h2>
          {(profile.diagnoses || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Reported diagnoses</div>
              <div className="flex flex-wrap gap-1.5">
                {(profile.diagnoses || []).map((c) => (
                  <span key={c} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]">{c}</span>
                ))}
              </div>
            </div>
          )}
          {(profile.provider_types || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Current providers</div>
              <div className="flex flex-wrap gap-1.5">
                {(profile.provider_types || []).map((c) => (
                  <span key={c} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]">{c}</span>
                ))}
              </div>
            </div>
          )}
          <div className="mt-3 text-xs text-[#4B4567]">
            {[profile.has_medication && `Medication: ${profile.has_medication}`,
              profile.attends_therapy && `Attends therapy: ${profile.attends_therapy}`]
              .filter(Boolean).join(" · ")}
          </div>
          {profile.notes && (
            <div className="mt-3 text-sm text-[#1A1330] whitespace-pre-wrap">{profile.notes}</div>
          )}
        </section>

        {/* Executive summary — AI-generated */}
        {report.ai_summary && (
          <section className="mt-6 bg-gradient-to-br from-[#F1EBFA] to-[#FFFFFF] rounded-3xl border border-[#D6CFE8] p-5 sm:p-7 shadow-sm" data-testid="psych-deep-ai-summary">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2 mb-1">
              <Sparkles size={12} /> AI executive summary
            </div>
            <p className="text-[11px] text-[#8471B3] mb-3 italic">Neutral · non-diagnostic · generated from your answers</p>
            <p className="text-sm text-[#1A1330] whitespace-pre-wrap leading-relaxed">{report.ai_summary}</p>
          </section>
        )}

        {/* At a glance */}
        <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid="psych-deep-summary">
          <h2 className="font-serif text-xl text-[#1A1330]">At a glance</h2>
          <div className="text-sm text-[#4B4567] mt-2">
            <span className="font-semibold text-[#1A1330]">{summary.answered_sections || 0}</span> sections completed.
            <span className="mx-2">·</span>
            <span className="text-[#B02A2A] font-semibold">{summary.flagged_sections || 0} flagged</span>
            <span className="mx-2">·</span>
            <span className="text-[#1F5C3B] font-semibold">{summary.strength_sections || 0} strengths</span>
          </div>
          {(summary.flagged_names || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#B02A2A] mb-1">Sections to follow up on</div>
              <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                {(summary.flagged_names || []).map((n) => (<li key={n}>{n}</li>))}
              </ul>
            </div>
          )}
          {(summary.strength_names || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#1F5C3B] mb-1">Strengths</div>
              <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                {(summary.strength_names || []).map((n) => (<li key={n}>{n}</li>))}
              </ul>
            </div>
          )}
        </section>

        {/* Per-section detail */}
        {(report.sections || []).filter((s) => s.is_flagged || s.is_strength).map((s) => (
          <section key={s.id} className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid={`psych-deep-section-${s.id}`}>
            <h2 className="font-serif text-xl text-[#1A1330]">{s.number}. {s.name}</h2>
            {s.is_strength && (
              <div className="mt-3">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold bg-[#E6F4EC] text-[#1F5C3B] border border-[#B5DFC5]">Strength</span>
                <p className="text-sm text-[#1A1330] mt-2">{s.strength_text}</p>
                {(s.strength_reasons || []).length > 0 && (
                  <p className="text-xs text-[#4B4567] italic mt-1">
                    Signals: {(s.strength_reasons || []).join("; ")}
                  </p>
                )}
              </div>
            )}
            {s.is_flagged && (
              <div className="mt-4">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold bg-[#F8D7D7] text-[#B02A2A] border border-[#EFB4B4]">Area to develop</span>
                <p className="text-sm text-[#1A1330] mt-2">{s.challenge_text}</p>
                {(s.flag_reasons || []).length > 0 && (
                  <p className="text-xs text-[#4B4567] italic mt-1">
                    Signals: {(s.flag_reasons || []).join("; ")}
                  </p>
                )}
                {(s.recommendations || []).length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Recommendations</div>
                    <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1">
                      {(s.recommendations || []).map((r) => (<li key={r}>{r}</li>))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        ))}

        <p className="text-[11px] text-[#4B4567] mt-8 italic">{report.disclaimer}</p>
      </div>
    </AppShell>
  );
}
