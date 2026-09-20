import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { SAMPLE_REPORTS } from "@/lib/samples";
import { SampleCard } from "@/components/SampleCard";
import { SampleEmailForm } from "@/components/SampleEmailForm";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

export default function Samples() {
  return (
    <div className="min-h-screen bg-background" data-testid="samples-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="samples-back-link">
            <ArrowLeft className="h-4 w-4" /> Home
          </Link>
          <BrandLogo size="text-xl" />
          <Link to="/auth?mode=register" data-testid="samples-register-link">
            <Button size="sm" data-testid="samples-register-btn">Create Professional Account</Button>
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-brand-purple" data-testid="samples-heading">Sample Joint Reports</h1>
          <p className="text-base md:text-lg text-muted-foreground mt-4" data-testid="samples-subheading">
            Every report follows the same neutral, child-focused structure: alignment, differences in
            perspective, the child's needs, options, and next steps. All samples use fictional data.
          </p>
        </div>

        <div className="mb-8 rounded-lg border-2 border-brand-purple/40 bg-white p-6 flex flex-col sm:flex-row sm:items-center gap-4" data-testid="sample-card-professional-report">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Legal · Professional &amp; Court only</p>
            <h3 className="text-lg font-bold mt-1">Sample Professional Report</h3>
            <p className="text-sm text-muted-foreground mt-1">The single legal deliverable submitted to the court: Joint Report findings infused, Co-Parenting Ability Level, Parent Alignment, options &amp; resources, conflict-management techniques, roadmap and attestation. Fictional data.</p>
          </div>
          <div className="flex flex-wrap gap-2 sm:justify-end">
            <Link to="/samples/professional-report" data-testid="sample-view-link-professional-report"><Button variant="outline">View</Button></Link>
            <Button asChild data-testid="sample-pdf-link-professional-report"><a href={`${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-professional-report/pdf`} download>Sample PDF</a></Button>
            <SampleEmailForm endpoint="/joint/sample-professional-report/email" label="Sample Professional Report" idPrefix="sample-pro" />
          </div>
        </div>

        <div className="mb-8 rounded-lg border border-border bg-white p-6 flex flex-col sm:flex-row sm:items-center gap-4" data-testid="sample-card-judicial-preview">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-widest text-accent">For courts &amp; judges</p>
            <h3 className="text-lg font-bold mt-1">Sample Judicial Case Page</h3>
            <p className="text-sm text-muted-foreground mt-1">A read-only preview of exactly what a judge receives in the Judicial Portal after a professional's authorized submission: procedural status, neutral court summary, authorized Joint Report findings, the Professional Report and the Ability Level history. Fictional data.</p>
          </div>
          <Link to="/court/sample" data-testid="sample-view-link-judicial-preview"><Button variant="outline">Preview the Judicial Portal</Button></Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="samples-grid">
          {SAMPLE_REPORTS.map((s) => (
            <SampleCard key={s.key} s={s} />
          ))}
        </div>

        <p className="text-center text-xs text-muted-foreground mt-10" data-testid="samples-footnote">
          Samples are condensed. Every completed Joint Alignment Report follows the full universal 10-page structure.
        </p>
      </main>
    </div>
  );
}
