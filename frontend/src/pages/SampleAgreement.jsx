import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink } from "lucide-react";
import api from "@/lib/api";
import { AgreementDocument } from "@/components/AgreementDocument";
import { SampleTour, useSampleTour, TourButton, AGREEMENT_TOUR } from "@/components/SampleTour";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

export default function SampleAgreement() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const tour = useSampleTour(!!report, "sa-agreement-sample-tour-seen");
  useEffect(() => {
    api.get("/joint/sample-agreement").then(({ data }) => setReport(data)).catch(() => setError("The sample agreement could not be loaded."));
  }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-agreement/pdf`;
  return (
    <div className="min-h-screen bg-background" data-testid="sample-agreement-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <Link to="/samples" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="sample-agreement-back-link"><ArrowLeft className="h-4 w-4" /> Samples</Link>
          <span className="hidden sm:block"><BrandLogo size="text-xl" /></span>
          <div className="flex flex-wrap gap-2">
            <TourButton onClick={tour.start} testId="agreement-tour-start-btn" />
            <Button variant="outline" size="sm" asChild data-testid="sample-agreement-viewpdf-link"><a href={`${pdf}?inline=1`} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-4 w-4 mr-1" /> View PDF</a></Button>
            <Button size="sm" asChild data-testid="sample-agreement-pdf-link"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> Download PDF</a></Button>
          </div>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-6 rounded-lg border border-brand-purple/30 bg-brand-purple/5 p-4 text-sm" data-testid="sample-agreement-banner">
          <strong className="text-brand-purple">Sample — fictional data.</strong> This is what parents receive after both have privately submitted their proposals for a joint Co-Parenting Agreement. Matching answers become specific agreements; differing answers are listed as issues still requiring resolution.
        </div>
        {error && <p className="text-sm text-red-700" data-testid="sample-agreement-error">{error}</p>}
        {report && <AgreementDocument report={report} />}
        {tour.open && report && <SampleTour steps={AGREEMENT_TOUR} storageKey="sa-agreement-sample-tour-seen" onDone={tour.close} label="How this agreement is built" prefix="agreement-tour" />}
      </main>
    </div>
  );
}
