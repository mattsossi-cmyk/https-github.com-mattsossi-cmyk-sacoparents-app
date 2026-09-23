import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Printer, CheckCircle2, Mail } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

export default function CompleteReport() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/reports/complete").then((r) => setReport(r.data)).catch((e) => setError(formatApiError(e)));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6" data-testid="complete-error">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium">{error}</p>
          <Link to="/hub" className="inline-block mt-6"><Button variant="outline" data-testid="complete-error-back-btn">Back to Hub</Button></Link>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="complete-loading">
        <p className="text-muted-foreground text-sm">Bringing together all available assessments…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="complete-report-page">
      <header className="no-print bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/hub" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="complete-back-link">
            <ArrowLeft className="h-4 w-4" /> Joint Report Hub
          </Link>
          <BrandLogo size="text-xl" />
          {!report.is_empty && (
            <Button size="sm" className="gap-2" asChild data-testid="complete-print-btn">
              <a href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/complete/pdf`} download>
                <Printer className="h-4 w-4" /> Download PDF
              </a>
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="report-paper rounded-lg p-8 sm:p-12">
          <div className="text-center border-b border-border pb-8 mb-10">
            <BrandLogo size="text-xl" />
            <h1 className="text-4xl font-extrabold text-brand-purple mt-4" data-testid="complete-title">{report.title}</h1>
            <p className="text-sm uppercase tracking-widest text-accent font-semibold mt-2">{report.subtitle}</p>
            <div className="mt-4 text-sm text-muted-foreground space-y-1">
              {report.children.length > 0 && <p data-testid="complete-children">Children: <strong className="text-foreground">{report.children.join(", ")}</strong></p>}
              <p data-testid="complete-date">{report.generated_at}</p>
            </div>
          </div>

          <p className="text-muted-foreground leading-relaxed mb-8" data-testid="complete-purpose">{report.purpose}</p>

          {report.is_empty ? (
            <div className="text-center py-10" data-testid="complete-empty">
              <p className="text-lg font-medium mb-6 max-w-lg mx-auto">{report.empty_note}</p>
              <div className="flex flex-wrap gap-3 justify-center">
                <Link to="/joint/new"><Button className="gap-2" data-testid="complete-empty-joint-btn"><Mail className="h-4 w-4" /> Create a Joint Report</Button></Link>
              </div>
            </div>
          ) : (
            <>
              <div className="border border-border rounded-lg p-6 bg-muted/40 mb-10" data-testid="complete-totals">
                <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-4">Overall Alignment Snapshot</p>
                <div className="flex flex-wrap gap-8 justify-center">
                  <div className="text-center" data-testid="total-aligned"><p className="font-display text-4xl font-semibold text-align-green">{report.totals.aligned}</p><p className="text-xs text-muted-foreground mt-1">Aligned</p></div>
                  <div className="text-center" data-testid="total-different"><p className="font-display text-4xl font-semibold text-align-yellow">{report.totals.different}</p><p className="text-xs text-muted-foreground mt-1">Different perspectives</p></div>
                  <div className="text-center" data-testid="total-info"><p className="font-display text-4xl font-semibold text-align-blue">{report.totals.info}</p><p className="text-xs text-muted-foreground mt-1">Need more information</p></div>
                </div>
                <p className="mt-4 text-sm italic text-muted-foreground text-center">{report.totals_note}</p>
              </div>

              {report.sections.map((s, i) => (
                <div key={i} className="mb-12 border-t border-border pt-8" data-testid={`complete-section-${i}`}>
                  <p className="text-xs uppercase tracking-widest text-accent font-semibold">{s.kind === "assessment" ? "Structured Assessment" : "Focused Joint Report"}</p>
                  <h2 className="text-3xl font-semibold mt-1 mb-6" data-testid={`complete-section-title-${i}`}>{s.title}{s.child_name ? ` — ${s.child_name}` : ""}</h2>

                  <h3 className="font-display text-xl font-semibold mb-3 text-align-green">Areas of Alignment</h3>
                  <ul className="space-y-2 mb-8">
                    {(s.alignments ? s.alignments.map((a) => a.text) : s.alignment_statements || []).map((text, j) => (
                      <li key={j} className="flex items-start gap-2.5 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {text}
                      </li>
                    ))}
                  </ul>

                  {s.differences && s.differences.length > 0 && (
                    <>
                      <h3 className="font-display text-xl font-semibold mb-3 text-align-blue">Different Perspectives</h3>
                      <div className="overflow-x-auto mb-8">
                        <table className="w-full text-sm border border-border rounded-lg overflow-hidden">
                          <thead><tr className="bg-brand-purple/10 text-left text-brand-purple"><th className="px-4 py-3 font-semibold">Issue</th><th className="px-4 py-3 font-semibold">Parent A</th><th className="px-4 py-3 font-semibold">Parent B</th></tr></thead>
                          <tbody>
                            {s.differences.map((d, j) => (
                              <tr key={j} className="border-t border-border">
                                <td className="px-4 py-3 font-medium">{d.topic || d.area}</td>
                                <td className="px-4 py-3 text-muted-foreground">{d.parent_a}</td>
                                <td className="px-4 py-3 text-muted-foreground">{d.parent_b}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}

                  <h3 className="font-display text-xl font-semibold mb-3">Child-Focused Considerations</h3>
                  <div className="flex flex-wrap gap-2 mb-8">
                    {s.child_needs.map((n) => (
                      <span key={n} className="text-xs bg-secondary text-secondary-foreground px-3 py-1.5 rounded-full">{n}</span>
                    ))}
                  </div>

                  <div className="grid sm:grid-cols-2 gap-6">
                    <div>
                      <h3 className="font-display text-xl font-semibold mb-3">Options & Resources</h3>
                      <ul className="space-y-2">
                        {s.options.map((o, j) => <li key={j} className="text-sm flex gap-2"><span className="text-accent">•</span>{o}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h3 className="font-display text-xl font-semibold mb-3">Questions for Discussion</h3>
                      <ul className="space-y-2">
                        {s.questions.map((q, j) => <li key={j} className="text-sm italic text-muted-foreground flex gap-2"><span className="text-accent not-italic">•</span>{q}</li>)}
                      </ul>
                    </div>
                  </div>

                  {s.priority && (
                    <div className="mt-8 border border-border rounded-lg p-5 bg-muted/40">
                      <p className="text-xs uppercase tracking-widest text-accent font-semibold mb-2">Child-Focused Priority</p>
                      <p className="font-display text-lg leading-relaxed">{s.priority}</p>
                    </div>
                  )}
                </div>
              ))}

              <div className="text-center border-t border-border pt-10">
                <h3 className="font-display text-4xl sm:text-5xl font-bold text-align-purple" data-testid="complete-philosophy">{report.philosophy_heading}</h3>
                <p className="mt-3 text-muted-foreground max-w-xl mx-auto">{report.philosophy_note}</p>
                <p className="mt-6 text-sm italic text-muted-foreground max-w-xl mx-auto">"{report.philosophy}"</p>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
