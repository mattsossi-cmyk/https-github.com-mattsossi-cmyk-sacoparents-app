import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCw, Loader2, FileText, Home, ScrollText, Copy } from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import SpecialNeedsScoreDashboard from "../components/SpecialNeedsScoreDashboard";
import { api } from "../lib/api";

/**
 * Displays the three AI-synthesised neurodivergent-pathway reports.
 * User can regenerate all three from the current answers.
 */

const ICONS = {
  needs_summary: FileText,
  two_home_plan: Home,
  mediation_statement: ScrollText,
};

function ReportCard({ report }) {
  const Icon = ICONS[report.report_type] || FileText;

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(report.content);
      toast.success("Copied to clipboard.");
    } catch {
      toast.error("Could not copy. Please select the text manually.");
    }
  };

  return (
    <section
      className="bg-white rounded-3xl border border-[#E5E0EE] shadow-sm p-6 sm:p-8"
      data-testid={`nd-report-${report.report_type}`}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-11 h-11 rounded-full bg-[#F1EBFA] grid place-items-center text-[#3D1A78]">
          <Icon size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="font-serif text-2xl text-[#1A1330] leading-snug">
            {report.title}
          </h2>
          {report.generated_at && (
            <div className="text-[11px] text-[#857E9C] mt-0.5">
              Generated {new Date(report.generated_at).toLocaleString()}
            </div>
          )}
        </div>
        <button
          onClick={copyToClipboard}
          className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] hover:underline"
          data-testid={`nd-copy-${report.report_type}`}
        >
          <Copy size={12} /> Copy
        </button>
      </div>

      {report.highlights && report.highlights.length > 0 && (
        <div className="mt-5 rounded-2xl bg-[#F5F2FA] border border-[#E5E0EE] p-4">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Key takeaways
          </div>
          <ul className="text-sm text-[#1A1330] space-y-1.5">
            {report.highlights.map((h, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-[#3D1A78]">•</span>
                <span>{h}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 whitespace-pre-wrap text-[15px] leading-relaxed text-[#1A1330] border-t border-[#E5E0EE] pt-5">
        {report.content}
      </div>
    </section>
  );
}

export default function NeurodivergentReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [regen, setRegen] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/neurodivergent/reports");
      setReports(data.reports || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not load reports.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const regenerate = async () => {
    if (!window.confirm("Regenerate all three reports from your current answers?")) return;
    setRegen(true);
    try {
      const { data } = await api.post("/neurodivergent/reports/generate");
      setReports(data.reports || []);
      toast.success("Reports refreshed.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not regenerate.");
    } finally {
      setRegen(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/neurodivergent"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="nd-reports-back-link"
        >
          <ArrowLeft size={14} /> Back to the questions
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="eyebrow text-[#3D1A78]">Special Needs Assessment</div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1" data-testid="nd-reports-title">
              Supporting your child across two homes
            </h1>
            <p className="text-[#4B4567] mt-2 max-w-2xl">
              Three warm, plain-language documents you can share with a
              co-parent, mediator, teacher, or therapist. Not diagnostic. Not
              legal or medical advice.
            </p>
          </div>
          <button
            onClick={regenerate}
            disabled={regen}
            className="inline-flex items-center gap-2 text-sm text-[#3D1A78] border border-[#E5E0EE] rounded-full px-4 py-2 hover:bg-[#F5F2FA] disabled:opacity-60"
            data-testid="nd-regenerate-btn"
          >
            {regen ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            {regen ? "Regenerating…" : "Regenerate"}
          </button>
        </div>

        <div className="mt-6">
          <DemoModeBanner />
        </div>

        <div className="mt-8">
          <SpecialNeedsScoreDashboard />
        </div>

        {loading ? (
          <div className="mt-10 text-[#857E9C]" data-testid="nd-reports-loading">Loading your reports…</div>
        ) : reports.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-dashed border-[#C1B4E0] bg-white p-8 text-center" data-testid="nd-reports-empty">
            <p className="text-[#1A1330] font-medium">
              You haven&apos;t generated your reports yet.
            </p>
            <p className="text-[#4B4567] mt-2 text-sm">
              Answer the questions in the assessment first, then come back here.
            </p>
            <Link
              to="/neurodivergent"
              className="inline-flex items-center gap-2 mt-5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-medium hover:bg-[#2A1256]"
              data-testid="nd-reports-start-btn"
            >
              Start the assessment →
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-6">
            {reports.map((r) => (
              <ReportCard key={r.report_type} report={r} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
