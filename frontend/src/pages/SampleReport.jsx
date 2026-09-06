import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Printer, ShieldAlert } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { samplePdfUrl } from "@/lib/samples";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

function Section({ num, title, children, testId }) {
  return (
    <div className="mb-10" data-testid={testId}>
      <h2 className="text-2xl font-semibold mb-4" data-testid={`${testId}-heading`}>
        <span className="text-accent font-display mr-2">{num}.</span>{title}
      </h2>
      {children}
    </div>
  );
}

export default function SampleReport({ fixedKey }) {
  const { key: paramKey } = useParams();
  const sampleKey = fixedKey || paramKey || "mediation";
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setReport(null);
    setError(null);
    api.get(`/joint/sample/${sampleKey}`).then((r) => setReport(r.data)).catch((e) => setError(formatApiError(e)));
  }, [sampleKey]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6" data-testid="sample-error">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium">{error}</p>
          <Link to="/samples" className="inline-block mt-6"><Button variant="outline" data-testid="sample-error-samples-btn">All sample reports</Button></Link>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="sample-loading">
        <p className="text-muted-foreground text-sm">Loading sample…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="sample-report-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between gap-3">
          <Link to="/samples" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="sample-back-link">
            <ArrowLeft className="h-4 w-4" /> All samples
          </Link>
          <BrandLogo size="text-xl" />
          <Button size="sm" className="gap-2" asChild data-testid="sample-download-pdf-btn">
            <a href={samplePdfUrl(sampleKey)} download>
              <Printer className="h-4 w-4" /> Download Sample PDF
            </a>
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="report-paper rounded-lg p-8 sm:p-12" data-testid="sample-report-document">
          <div className="text-center border-b border-border pb-8 mb-10">
            <BrandLogo size="text-xl" />
            <span className="inline-block mt-4 text-xs font-bold uppercase tracking-widest bg-align-yellow/20 text-yellow-700 px-3 py-1 rounded-full" data-testid="sample-badge">
              Sample — fictional example data
            </span>
            {report.is_safety && (
              <p className="mt-4 mx-auto max-w-lg text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-md px-4 py-2 flex items-center justify-center gap-2" data-testid="sample-safety-notice">
                <ShieldAlert className="h-4 w-4 shrink-0" /> Controlled preview — safety reports are professional-mediated. Parent responses are never exchanged directly.
              </p>
            )}
            <p className="mt-3 text-xs text-muted-foreground max-w-lg mx-auto" data-testid="sample-condensed-note">
              This is a condensed sample. The complete Joint Alignment Report follows a universal
              10-page structure (overview, alignment map, differences, child needs, options, conversation guide, action plan, and summary).
            </p>
            <h1 className="text-4xl font-extrabold text-brand-purple mt-3" data-testid="sample-title">{report.report_title}</h1>
            <div className="mt-4 text-sm text-muted-foreground space-y-1">
              <p data-testid="sample-child">Child: <strong className="text-foreground">{report.child_name}</strong></p>
              <p data-testid="sample-subject">Subject: <strong className="text-foreground">{report.subject_label}</strong></p>
              <p data-testid="sample-participants">Participants: {report.parent_a_name} / {report.parent_b_name}</p>
              <p data-testid="sample-date">{report.date}</p>
            </div>
          </div>

          <Section num={1} title="Purpose of This Report" testId="sr-purpose">
            <p className="text-muted-foreground leading-relaxed">{report.purpose}</p>
            {report.confidentiality_note && (
              <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-4 py-3" data-testid="sr-confidentiality">{report.confidentiality_note}</p>
            )}
          </Section>

          <Section num={2} title="What Both Parents Agree About" testId="sr-alignment">
            <p className="text-sm font-semibold text-align-green mb-3">Strong Alignment — both parents indicated that:</p>
            <ul className="space-y-2" data-testid="sr-alignment-list">
              {report.alignment_statements.map((s, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm" data-testid={`sr-alignment-item-${i}`}>
                  <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {s}
                </li>
              ))}
            </ul>
          </Section>

          <Section num={3} title="Where the Parents See Things Differently" testId="sr-differences">
            {report.differences.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No significant differences in perspective were identified.</p>
            ) : (
              <div className="space-y-5">
                {report.differences.map((d, i) => (
                  <div key={i} className="border border-border rounded-lg p-5" data-testid={`sr-difference-${i}`}>
                    <p className="font-semibold mb-3">{d.area}</p>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="bg-muted/40 rounded-md p-4">
                        <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">{report.parent_a_name}'s Perspective</p>
                        <p className="text-sm leading-relaxed">{d.parent_a}</p>
                      </div>
                      <div className="bg-muted/40 rounded-md p-4">
                        <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">{report.parent_b_name}'s Perspective</p>
                        <p className="text-sm leading-relaxed">{d.parent_b}</p>
                      </div>
                    </div>
                    <p className="mt-3 text-sm italic text-muted-foreground">{d.reframe}</p>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section num={4} title="Child's Identified Needs" testId="sr-needs">
            <ul className="grid sm:grid-cols-2 gap-2" data-testid="sr-needs-list">
              {report.child_needs.map((n) => (
                <li key={n} className="flex items-center gap-2 text-sm bg-muted/40 rounded-md px-4 py-3">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" /> {n}
                </li>
              ))}
            </ul>
          </Section>

          <Section num={5} title="Options and Resources" testId="sr-options">
            <p className="text-sm text-muted-foreground mb-3">Neutral options — SA CoParents does not decide; it builds options:</p>
            <ul className="space-y-2" data-testid="sr-options-list">
              {report.options.map((o, i) => (
                <li key={i} className="border border-border rounded-md px-4 py-3 text-sm" data-testid={`sr-option-${i}`}>{o}</li>
              ))}
            </ul>
          </Section>

          <Section num={6} title="Possible Next Steps" testId="sr-next-steps">
            <div className="grid sm:grid-cols-2 gap-3" data-testid="sr-next-steps-list">
              {report.next_steps.map((s, i) => (
                <div key={i} className="border border-border rounded-md px-4 py-3 text-sm font-medium" data-testid={`sr-next-step-${i}`}>{s}</div>
              ))}
            </div>
          </Section>

          <div className="text-center border-t border-border pt-10">
            <h3 className="font-display text-4xl sm:text-5xl font-bold text-align-purple" data-testid="sr-philosophy-heading">{report.philosophy_heading}</h3>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">{report.philosophy_note}</p>
            <p className="mt-6 text-sm italic text-muted-foreground max-w-xl mx-auto" data-testid="sr-philosophy-line">"{report.philosophy}"</p>
          </div>
        </div>

        <div className="mt-8 bg-white border border-border rounded-lg p-6 text-center" data-testid="sample-cta">
          <p className="font-semibold text-lg">SA CoParents Align is a professional platform.</p>
          <p className="text-sm text-muted-foreground mt-1">Joint reports are initiated by authorized professionals — parents participate through a secure invitation.</p>
          <Link to="/auth?mode=register" className="inline-block mt-4" data-testid="sample-create-own-link">
            <Button className="gap-2" data-testid="sample-create-own-btn">Create a Free Professional Account</Button>
          </Link>
          <p className="mt-3 text-xs text-muted-foreground">Are you a parent? Individual assessments begin at <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="text-primary hover:underline">SA CoParents App</a>.</p>
        </div>
      </main>
    </div>
  );
}
