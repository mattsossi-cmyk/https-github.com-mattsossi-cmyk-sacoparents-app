import { Link } from "react-router-dom";
import { ArrowLeft, Download, Eye, ShieldAlert } from "lucide-react";
import { SAMPLE_REPORTS, samplePdfUrl } from "@/lib/samples";
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

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="samples-grid">
          {SAMPLE_REPORTS.map((s) => (
            <div key={s.key} className={`bg-white border rounded-lg p-6 flex flex-col ${s.safety ? "border-red-300" : "border-border"}`} data-testid={`sample-card-${s.key}`}>
              {s.safety && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-700 mb-3" data-testid={`sample-card-safety-badge-${s.key}`}>
                  <ShieldAlert className="h-3.5 w-3.5" /> Professional-mediated preview
                </span>
              )}
              <h2 className="text-lg font-bold" data-testid={`sample-card-title-${s.key}`}>{s.label}</h2>
              <p className="text-sm text-muted-foreground mt-2 flex-1">{s.blurb}</p>
              <div className="flex gap-2 mt-5">
                <Link to={`/samples/${s.key}`} className="flex-1" data-testid={`sample-view-link-${s.key}`}>
                  <Button variant="outline" size="sm" className="w-full gap-2" data-testid={`sample-view-btn-${s.key}`}>
                    <Eye className="h-4 w-4" /> View
                  </Button>
                </Link>
                <Button size="sm" className="flex-1 gap-2" asChild data-testid={`sample-download-btn-${s.key}`}>
                  <a href={samplePdfUrl(s.key)} download>
                    <Download className="h-4 w-4" /> PDF
                  </a>
                </Button>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-muted-foreground mt-10" data-testid="samples-footnote">
          Samples are condensed. Every completed Joint Alignment Report follows the full universal 10-page structure.
        </p>
      </main>
    </div>
  );
}
