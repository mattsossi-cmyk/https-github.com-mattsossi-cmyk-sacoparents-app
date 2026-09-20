import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Circle, Scale } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

const STATUS = { not_started: "Not Started", draft: "Draft", under_review: "Under Review", final: "Final", submitted_to_court: "Submitted to Court" };

export function LegalLensReadiness({ readiness }) {
  return <ul className="grid gap-1 text-xs sm:grid-cols-2" data-testid="lens-readiness-list">{readiness.map((r) => <li key={r.key} className="flex items-center gap-1.5" data-testid={`lens-ready-${r.key}`}>{r.done ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}<span className={r.done ? "" : "text-muted-foreground"}>{r.label}{r.na && !r.done ? " (N/A)" : ""}</span></li>)}</ul>;
}

export default function ProfessionalReportHome() {
  const [cases, setCases] = useState(null);
  useEffect(() => { api.get("/professional-report/cases").then((r) => setCases(r.data)).catch(() => setCases([])); }, []);
  return (
    <div className="min-h-screen bg-white" data-testid="professional-report-home">
      <header className="border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between"><BrandLogo size="text-xl" /><Link to="/dashboard" className="text-sm text-muted-foreground" data-testid="professional-report-dashboard-link">Dashboard</Link></div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-6">
        <div><p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1.5"><Scale className="h-3.5 w-3.5" /> Legal Lens</p><h1 className="text-3xl sm:text-4xl font-extrabold text-brand-purple mt-1" data-testid="professional-report-title">SA CoParents Legal Lens Review and Report to Court</h1><p className="mt-2 text-sm text-muted-foreground max-w-3xl">Select a case to prepare the report. Case information, parent names, assessment findings and readiness are pulled in automatically — you edit the narrative without changing the underlying parent records.</p></div>
        {cases === null ? null : cases.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="professional-report-empty">No cases yet. Create a case from your dashboard first.</p> : (
          <ul className="grid gap-4 md:grid-cols-2" data-testid="professional-report-cases">{cases.map((c) => (
            <li key={c.id} className="rounded-lg border border-border bg-[#f7f3fb] p-5" data-testid={`professional-report-case-${c.id}`}>
              <div className="flex items-start justify-between gap-2"><div><p className="font-mono text-xs text-muted-foreground">{c.case_code}</p><p className="font-semibold">{c.subject_label} — {c.child_name}</p><p className="text-xs text-muted-foreground">{c.parent_a || "Parent A"} &amp; {c.parent_b || "Parent B"}</p></div><span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-brand-purple">{STATUS[c.status]}</span></div>
              <div className="mt-3"><LegalLensReadiness readiness={c.readiness} /></div>
              <Button size="sm" className="mt-4" asChild data-testid={`professional-report-open-${c.id}`}><Link to={`/cases/${c.id}/professional-report`}>Prepare Legal Lens Review &amp; Report to Court</Link></Button>
            </li>))}</ul>
        )}
      </main>
    </div>
  );
}
