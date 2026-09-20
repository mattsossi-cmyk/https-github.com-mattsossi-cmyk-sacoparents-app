import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Scale } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LegalLensReadiness } from "@/pages/ProfessionalReportHome";

const STATUS = { draft: "Draft", under_review: "Under Review", final: "Final", submitted_to_court: "Submitted to Court" };

export function LegalLensCard({ rid }) {
  const [d, setD] = useState(null);
  useEffect(() => { api.get(`/cases/${rid}/professional-report/readiness`).then((r) => setD(r.data)).catch(() => {}); }, [rid]);
  return (
    <section className="bg-white border border-border rounded-lg p-6" data-testid="legal-lens-card">
      <h2 className="text-lg font-semibold flex items-center gap-2"><Scale className="h-5 w-5 text-brand-purple" /> Legal Lens Review &amp; Report to Court{d?.status && <span className="ml-auto rounded-full bg-brand-purple/10 px-2 py-0.5 text-[11px] font-semibold text-brand-purple" data-testid="legal-lens-status">{STATUS[d.status]}</span>}</h2>
      <p className="text-sm text-muted-foreground mt-1">Court-ready professional report: Safety First → individual and joint assessments with 1–10 classification → resources → alignment → conflict management → roadmap → summary → PDF.</p>
      <div className="mt-3">{d ? <LegalLensReadiness readiness={d.readiness} /> : null}</div>
      <Button className="mt-4" asChild data-testid="legal-lens-prepare-btn"><Link to={`/cases/${rid}/professional-report`}>Prepare Legal Lens Review &amp; Report to Court</Link></Button>
    </section>
  );
}
