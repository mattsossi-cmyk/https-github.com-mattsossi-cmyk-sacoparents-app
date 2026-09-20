import { Link } from "react-router-dom";
import { Eye, FileText, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

const LABEL = { not_started: "Not Started", draft: "Draft", professional_review: "Professional Review", finalized: "Finalized" };

export function ProfessionalLegalReportCard({ rid }) {
  const [status, setStatus] = useState("not_started");
  useEffect(() => { api.get(`/cases/${rid}/professional-legal-report`).then((r) => setStatus(r.data.status)).catch(() => {}); }, [rid]);
  const started = status !== "not_started";
  return (
    <section className="bg-white border border-border rounded-lg p-6" data-testid="legal-report-card">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-brand-purple/10 p-3"><FileText className="h-6 w-6 text-brand-purple" /></div>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">Professional Legal Report</h2>
            <span className="rounded-full bg-brand-purple/10 px-2.5 py-0.5 text-[11px] font-bold tracking-widest text-brand-purple" data-testid="legal-report-badge">LEGAL LENS</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">Review parent assessments, joint findings, child-focused concerns, conflict patterns, and available options and resources through a professional legal lens.</p>
          <p className="mt-2 text-sm font-medium" data-testid="legal-report-status">Status: {LABEL[status] || status}</p>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button variant="outline" asChild data-testid="legal-report-sample-btn"><Link to={`/joint/${rid}/legal-report/sample`}><Eye className="h-4 w-4 mr-1" /> Review Sample Legal Report</Link></Button>
        <Button asChild data-testid="legal-report-create-btn"><Link to={`/joint/${rid}/legal-report`}><Plus className="h-4 w-4 mr-1" /> {started ? "Continue Professional Legal Report" : "Create Professional Legal Report"}</Link></Button>
      </div>
    </section>
  );
}
