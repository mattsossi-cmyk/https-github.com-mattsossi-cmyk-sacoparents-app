import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Plus } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { LegalGeneratedSections, LegalReadOnlyTail } from "@/components/LegalReportSections";

export default function LegalReportSample() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/professional-legal-report/sample").then((r) => setD(r.data)).catch(() => {}); }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/professional-legal-report/sample/pdf`;
  if (!d) return <div className="min-h-screen bg-background" data-testid="legal-sample-loading" />;
  return (
    <div className="min-h-screen bg-background" data-testid="legal-sample-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
        <Link to={id ? `/joint/${id}` : "/samples"} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="legal-sample-back"><ArrowLeft className="h-4 w-4" /> {id ? "Back to Case" : "Sample Reports"}</Link>
        <div className="hidden sm:block"><BrandLogo size="text-xl" /></div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" asChild data-testid="legal-sample-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> PDF</a></Button>
          {id && <Button size="sm" asChild data-testid="legal-sample-create-btn"><Link to={`/joint/${id}/legal-report`}><Plus className="h-4 w-4 mr-1" /> Create My Report</Link></Button>}
        </div>
      </div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-5">
        <div className="rounded-lg border-2 border-brand-purple/30 bg-brand-purple/5 p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">SA CoParents Align · Professional Legal Report · SAMPLE</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold mt-1" data-testid="legal-sample-title">Professional Legal Report — Sample</h1>
          <p className="text-sm text-muted-foreground mt-2">Case ID {d.case.case_code} · {d.professional.name}, {d.professional.pro_role} · {d.case.parent_a} &amp; {d.case.parent_b} · {d.case.child_name} · Report status: SAMPLE ONLY. Completely fictional information.</p>
        </div>
        <LegalGeneratedSections data={d} />
        <LegalReadOnlyTail data={d} />
      </main>
    </div>
  );
}
