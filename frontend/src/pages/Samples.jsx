import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { SAMPLE_REPORTS } from "@/lib/samples";
import { SampleCard } from "@/components/SampleCard";
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
