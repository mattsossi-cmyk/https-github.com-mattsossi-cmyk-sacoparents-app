import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, Loader2, Download, Share2, RefreshCw, CheckCircle2,
  Circle, FileText, AlertTriangle, ShieldCheck, TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";

/**
 * Authenticated Family Report page — stitches Co-Parenting + Special Needs +
 * Safety findings into one branded document.
 */

const SAFETY_TONE = {
  1: { label: "urgent",   chip: "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]" },
  2: { label: "elevated", chip: "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]" },
  3: { label: "cautious", chip: "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]" },
  4: { label: "steady",   chip: "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]" },
};

const RATING_CHIP = {
  "Excellent Progress": "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]",
  "Building Progress":  "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]",
  "Early Progress":     "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]",
};

function SourceRow({ label, path, completed, generatedAt, testid }) {
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : null;
  return (
    <div
      className="flex items-center justify-between gap-3 border border-[#E5E0EE] rounded-2xl p-4"
      data-testid={testid}
    >
      <div className="flex items-center gap-3 min-w-0">
        {completed
          ? <CheckCircle2 size={18} className="shrink-0 text-[#1F5C3B]" />
          : <Circle size={18} className="shrink-0 text-[#857E9C]" />}
        <div className="min-w-0">
          <div className="font-semibold text-[#1A1330]">{label}</div>
          <div className="text-xs text-[#857E9C]">
            {completed ? `Completed${date ? ` · ${date}` : ""}` : "Not started"}
          </div>
        </div>
      </div>
      <Link
        to={path}
        className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-3 py-1.5"
      >
        {completed ? "Retake" : "Start"}
      </Link>
    </div>
  );
}

function SectionCard({ title, block, testid }) {
  if (!block) return null;
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid={testid}>
      <h3 className="font-serif text-xl text-[#1A1330] mb-2">{title}</h3>
      {block.overall_rating && (
        <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${RATING_CHIP[block.overall_rating] || RATING_CHIP["Building Progress"]}`}>
          {block.overall_rating}
        </span>
      )}
      {block.overall_summary && (
        <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">{block.overall_summary}</p>
      )}
      {(block.strengths || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#1F5C3B] mb-1 flex items-center gap-1"><TrendingUp size={12} /> Strengths</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {block.strengths.slice(0, 3).map((s) => (
              <li key={s.section_id}><span className="font-semibold">{s.title}</span>{s.detail ? ` — ${s.detail}` : ""}</li>
            ))}
          </ul>
        </div>
      )}
      {(block.growth_areas || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#C2481F] mb-1 flex items-center gap-1"><AlertTriangle size={12} /> Priority focus</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {block.growth_areas.slice(0, 3).map((g) => (
              <li key={g.section_id}><span className="font-semibold">{g.title}</span>{g.rating ? ` (${g.rating})` : ""}{g.first_step ? ` — ${g.first_step}` : ""}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SafetyCard({ safety, testid }) {
  if (!safety) return null;
  const tone = SAFETY_TONE[safety.level] || SAFETY_TONE[3];
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid={testid}>
      <h3 className="font-serif text-xl text-[#1A1330] mb-2 flex items-center gap-2">
        <ShieldCheck size={16} className="text-[#3D1A78]" /> Communication Safety
      </h3>
      <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${tone.chip}`}>
        Level {safety.level}: {safety.pathway_title}
      </span>
      {safety.pathway_headline && (
        <div className="text-sm italic text-[#857E9C] mt-2">{safety.pathway_headline}</div>
      )}
      {safety.pathway_summary && (
        <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{safety.pathway_summary}</p>
      )}
      {(safety.recommendations || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {safety.recommendations.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function FamilyReport() {
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [st, rep] = await Promise.all([
        api.get("/family-report/status"),
        api.get("/family-report").catch(() => ({ data: { report: null } })),
      ]);
      setStatus(st.data);
      if (rep.data?.report_id) {
        setReport(rep.data.report);
        setReportId(rep.data.report_id);
      }
    } catch {
      toast.error("Couldn't load Family Report status.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const { data } = await api.post("/family-report/generate");
      setReport(data.report);
      setReportId(data.report_id);
      toast.success("Family Report generated");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't generate the Family Report.");
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get("/family-report/pdf", { responseType: "blob" });
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Family_Report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Couldn't download the PDF.");
    } finally {
      setDownloading(false);
    }
  };

  const share = async () => {
    if (!reportId) return;
    setSharing(true);
    try {
      const { data } = await api.post(`/family-report/${reportId}/share-link`, {});
      const url = `${window.location.origin}${data.viewer_path}`;
      try {
        await navigator.clipboard.writeText(url);
        toast.success("Share link copied to clipboard");
      } catch {
        toast.info(url);
      }
    } catch {
      toast.error("Couldn't create a share link.");
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[#857E9C]" data-testid="familyreport-loading">
          Loading Family Report…
        </div>
      </AppShell>
    );
  }

  const canGenerate = status?.can_generate;
  const missingCount = (status ? [status.cp, status.sn, status.safety].filter((s) => !s.completed).length : 0);

  return (
    <AppShell>
      <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4" data-testid="familyreport-back">
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>

          <div className="eyebrow text-[#3D1A78]">Family Report</div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1" data-testid="familyreport-title">
            Your Co-Parenting, Special Needs, and Safety findings in one document
          </h1>
          <p className="mt-2 text-[#4B4567] max-w-2xl text-[15px] leading-relaxed">
            A single branded PDF you can share with your co-parent, mediator, or attorney. Uses the reports you already generated — safety details are summarised (level + pathway only), never question-level.
          </p>

          {/* Source status */}
          <div className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-7" data-testid="familyreport-sources">
            <h2 className="font-serif text-lg text-[#1A1330] mb-3">Sources</h2>
            <div className="space-y-2.5">
              <SourceRow label={status.cp.label} path={status.cp.path} completed={status.cp.completed} generatedAt={status.cp.generated_at} testid="familyreport-source-cp" />
              <SourceRow label={status.sn.label} path={status.sn.path} completed={status.sn.completed} generatedAt={status.sn.generated_at} testid="familyreport-source-sn" />
              <SourceRow label={status.safety.label} path={status.safety.path} completed={status.safety.completed} generatedAt={status.safety.generated_at} testid="familyreport-source-safety" />
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-[#857E9C]">
                {status.completed_count}/3 assessments completed
                {missingCount > 0 && " · You can still generate with partial data"}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={generate}
                  disabled={!canGenerate || generating}
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] disabled:opacity-50 rounded-full px-4 py-2"
                  data-testid="familyreport-generate-btn"
                >
                  {generating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  {report ? "Regenerate report" : "Generate Family Report"}
                </button>
                {report && (
                  <>
                    <button
                      onClick={downloadPdf}
                      disabled={downloading}
                      className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] disabled:opacity-50 rounded-full px-4 py-2"
                      data-testid="familyreport-pdf-btn"
                    >
                      {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} PDF
                    </button>
                    <button
                      onClick={share}
                      disabled={sharing}
                      className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] disabled:opacity-50 rounded-full px-4 py-2"
                      data-testid="familyreport-share-btn"
                    >
                      {sharing ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />} Share
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Rendered report */}
          {report ? (
            <div className="mt-8 space-y-6" data-testid="familyreport-body">
              <div className="rounded-3xl border border-[#E5E0EE] bg-[#F8F5FF] p-6 sm:p-8">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                  Family Report · {report.included_sources.length}/3 sources
                </div>
                <h2 className="font-serif text-2xl text-[#1A1330]" data-testid="familyreport-overall">
                  {report.prepared_by ? `Prepared for ${report.prepared_by}` : "Your Family Report"}
                </h2>
                <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{report.overall_summary}</p>
                {(report.missing_sources || []).length > 0 && (
                  <div className="mt-3 text-xs italic text-[#8C5A2C]">
                    Not yet completed: {report.missing_sources.join(", ")}
                  </div>
                )}
              </div>

              <SafetyCard safety={report.safety} testid="familyreport-safety" />
              <SectionCard title="Co-Parenting Assessment" block={report.coparenting} testid="familyreport-cp" />
              <SectionCard title="Special Needs Assessment" block={report.special_needs} testid="familyreport-sn" />

              {(report.combined_next_steps || []).length > 0 && (
                <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="familyreport-next-steps">
                  <h3 className="font-serif text-xl text-[#1A1330] mb-3">Combined next steps</h3>
                  <ul className="space-y-2">
                    {report.combined_next_steps.map((s, i) => (
                      <li key={i} className="text-sm text-[#1A1330]" data-testid={`familyreport-step-${i}`}>
                        <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-full border border-[#CFC1EA] bg-[#EFE9F9] text-[#3D1A78] mr-2">
                          {s.source}
                        </span>
                        {s.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-[11px] text-[#857E9C] italic text-center px-4">{report.disclaimer}</p>
            </div>
          ) : (
            <div className="mt-8 rounded-3xl border border-dashed border-[#CFC1EA] p-8 text-center" data-testid="familyreport-empty">
              <FileText size={28} className="mx-auto text-[#3D1A78] mb-2" />
              <div className="font-serif text-lg text-[#1A1330]">No Family Report yet</div>
              <p className="text-sm text-[#4B4567] mt-1">
                {canGenerate
                  ? "Click Generate above to build one from what you've completed."
                  : "Finish at least one of the three assessments to build your first Family Report."}
              </p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
