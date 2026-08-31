import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Printer, FileText } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { REPORT_PAGES } from "@/components/report/Pages";

export default function ReportView() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    api.get(`/cases/${id}/report`)
      .then((r) => setReport(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [id]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6" data-testid="report-error">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium">{error}</p>
          <Link to="/dashboard" className="inline-block mt-6" data-testid="report-error-back-link">
            <Button variant="outline" data-testid="report-error-back-btn">Back to dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="report-loading">
        <p className="text-muted-foreground text-sm">Generating report…</p>
      </div>
    );
  }

  const CurrentPage = REPORT_PAGES[page - 1];

  return (
    <div className="min-h-screen bg-background" data-testid="report-view">
      <header className="no-print sticky top-0 z-20 bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="report-back-link">
            <ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="h-5 w-5 text-primary shrink-0" />
            <span className="font-display text-lg font-semibold text-primary truncate" data-testid="report-header-title">
              {report.subtitle}
            </span>
          </div>
          <Button size="sm" className="gap-2 shrink-0" onClick={() => window.print()} data-testid="print-report-btn">
            <Printer className="h-4 w-4" /> <span className="hidden sm:inline">Print / Save PDF</span>
          </Button>
        </div>
      </header>

      <nav className="no-print max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4" data-testid="page-nav">
        <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)} className="gap-1.5" data-testid="prev-page-btn">
          <ArrowLeft className="h-4 w-4" /> Prev
        </Button>
        <div className="flex items-center gap-1.5 flex-wrap justify-center" data-testid="page-dots">
          {report.page_titles.map((t, i) => (
            <button
              key={t}
              onClick={() => setPage(i + 1)}
              title={`Page ${i + 1} — ${t}`}
              className={`h-2.5 rounded-full transition-[width,background-color] duration-200 ${page === i + 1 ? "w-6 bg-primary" : "w-2.5 bg-border hover:bg-muted-foreground/40"}`}
              data-testid={`page-dot-${i + 1}`}
            />
          ))}
        </div>
        <Button variant="outline" size="sm" disabled={page === 10} onClick={() => setPage(page + 1)} className="gap-1.5" data-testid="next-page-btn">
          Next <ArrowRight className="h-4 w-4" />
        </Button>
      </nav>

      <p className="no-print text-center text-xs text-muted-foreground mb-4" data-testid="current-page-label">
        Page {page} of 10 — {report.page_titles[page - 1]}
      </p>

      <main className="no-print px-4 sm:px-6 pb-16" key={page}>
        <CurrentPage r={report} />
      </main>

      <div className="print-only" data-testid="print-container">
        {REPORT_PAGES.map((P, i) => (
          <P key={i} r={report} />
        ))}
      </div>
    </div>
  );
}
