import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, Loader2, Download, Share2, RefreshCw, CheckCircle2,
  Circle, FileText, Image as ImageIcon,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { FamilyReportBody } from "../components/FamilyReportBody";

/**
 * Authenticated Family Report page.
 * Renders the FULL CP + SN v3 reports embedded in-line, plus Safety pathway.
 * Visual language matches SharedCoParentingReport / SharedSpecialNeedsReport.
 */

const SAMPLE_PDF_URL = "/api/insights/family-report-dynamic-sample.pdf";
const SAMPLE_PNG_URL = "/api/insights/family-report-dynamic-sample.png";

function SampleReportCallout() {
  return (
    <div className="rounded-2xl border border-[#CFC1EA] bg-[#F5F0FE] p-5" data-testid="familyreport-sample-callout">
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-9 h-9 rounded-full bg-white grid place-items-center text-[#3D1A78] border border-[#CFC1EA]">
          <FileText size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-0.5">
            Sample report
          </div>
          <div className="font-semibold text-[#1A1330]">
            See what a completed Family Report looks like
          </div>
          <p className="text-xs sm:text-sm text-[#4B4567] mt-1 leading-relaxed">
            A branded, fictional SA CoParents Family Report using the same
            renderer as your live version. Full detail across all three
            assessments — great to share with your co-parent, mediator, or
            attorney as a preview.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href={SAMPLE_PNG_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] bg-white border border-[#CFC1EA] hover:border-[#3D1A78] rounded-full px-3 py-1.5"
              data-testid="familyreport-sample-preview-btn"
            >
              <ImageIcon size={12} /> Preview sample (PNG)
            </a>
            <a
              href={SAMPLE_PDF_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5"
              data-testid="familyreport-sample-pdf-btn"
            >
              <Download size={12} /> Download sample PDF
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function SourceRow({ label, path, completed, generatedAt, testid }) {
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : null;
  return (
    <div className="flex items-center justify-between gap-3 border border-[#E5E0EE] rounded-2xl p-4" data-testid={testid}>
      <div className="flex items-center gap-3 min-w-0">
        {completed
          ? <CheckCircle2 size={18} className="shrink-0 text-[#1F5C3B]" />
          : <Circle size={18} className="shrink-0 text-[#857E9C]" />}
        <div className="min-w-0">
          <div className="font-semibold text-[#1A1330]">{label}</div>
          <div className="text-xs text-[#857E9C]">{completed ? `Completed${date ? ` · ${date}` : ""}` : "Not started"}</div>
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
      try { await navigator.clipboard.writeText(url); toast.success("Share link copied to clipboard"); }
      catch { toast.info(url); }
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
  const missingCount = status ? [status.cp, status.sn, status.safety].filter((s) => !s.completed).length : 0;

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
            A single branded PDF you can share with your co-parent, mediator, or attorney. Contains the full detail of the reports you already generated — safety findings are summarised (level + pathway only), never question-level.
          </p>

          <div className="mt-6">
            <SampleReportCallout />
          </div>

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

          {report ? (
            <div className="mt-8" data-testid="familyreport-body">
              <FamilyReportBody report={report} />
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
