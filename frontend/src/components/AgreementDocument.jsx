import { BrandLogo } from "@/components/Brand";

const STATUS = {
  "Agreed": "bg-align-green/15 text-align-green",
  "Partly agreed": "bg-align-yellow/20 text-yellow-700",
  "Aligned in principle": "bg-teal-50 text-teal-700",
  "Requires resolution": "bg-align-blue/15 text-align-blue",
};

const Bullets = ({ title, items, tone, empty, testId }) => (
  <div data-testid={testId}>
    <p className={`text-xs font-bold uppercase tracking-widest ${tone}`}>{title}</p>
    {items.length === 0 ? (empty ? <p className="mt-1 text-sm italic text-muted-foreground">{empty}</p> : null) : (
      <ul className="mt-1 space-y-1 text-sm leading-relaxed">{items.map((it, i) => <li key={i} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{it}</li>)}</ul>
    )}
  </div>
);

const Group = ({ title, items, tone, border, testId }) => (
  <div className={`rounded-lg border-2 ${border} p-4`} data-testid={testId}>
    <p className={`text-sm font-bold ${tone}`}>{title} <span className="font-normal text-muted-foreground">({items.length})</span></p>
    {items.length === 0 ? <p className="mt-1 text-xs italic text-muted-foreground">None yet.</p> : (
      <ul className="mt-2 space-y-1 text-xs leading-relaxed">{items.slice(0, 12).map((it, i) => <li key={i}>{it}</li>)}{items.length > 12 && <li className="text-muted-foreground">…and {items.length - 12} more below</li>}</ul>
    )}
  </div>
);

export function AgreementDocument({ report }) {
  const sm = report.summary || { alignment: [], specific: [], resolution: [] };
  return (
    <div className="report-paper rounded-lg p-8 sm:p-12" data-testid="agreement-document">
      <div className="text-center border-b border-border pb-8 mb-10">
        <BrandLogo size="text-xl" />
        <h1 className="text-4xl font-extrabold text-brand-purple mt-4" data-testid="agreement-title">{report.report_title}</h1>
        <div className="mt-4 text-sm text-muted-foreground space-y-1">
          <p>Child: <strong className="text-foreground">{report.child_name}</strong></p>
          <p>Parents: {report.parent_a_name} / {report.parent_b_name}</p>
          <p>{report.date}</p>
        </div>
        {report.method_note && <p className="mt-4 text-xs font-semibold tracking-widest text-brand-purple" data-testid="agreement-method">{report.method_note}</p>}
      </div>

      <p className="text-muted-foreground leading-relaxed mb-4" data-testid="agreement-purpose">{report.purpose}</p>
      <div className="bg-secondary/50 border border-border rounded-lg p-4 mb-8 text-xs text-muted-foreground" data-testid="agreement-confidentiality">{report.confidentiality_note}</div>

      <div className="grid gap-4 md:grid-cols-3 mb-10" data-testid="agreement-summary">
        <Group title="Areas of Alignment" items={sm.alignment} tone="text-align-green" border="border-align-green/40" testId="agreement-summary-alignment" />
        <Group title="Specific Agreements" items={sm.specific} tone="text-brand-purple" border="border-brand-purple/40" testId="agreement-summary-specific" />
        <Group title="Issues Still Requiring Resolution" items={sm.resolution} tone="text-align-blue" border="border-align-blue/40" testId="agreement-summary-resolution" />
      </div>

      <div className="space-y-6 mb-10">
        {(report.sections || []).map((s) => (
          <section key={s.key} className="border border-border rounded-lg p-5" data-testid={`agreement-section-${s.key}`}>
            <div className="flex items-center justify-between gap-3 mb-3">
              <h2 className="text-lg font-semibold">{s.num}. {s.label}</h2>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS[s.status] || ""}`} data-testid={`agreement-status-${s.key}`}>{s.status}</span>
            </div>
            <div className="space-y-3">
              <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Shared Goal</p><p className="text-sm leading-relaxed">{s.shared_goal}</p></div>
              <Bullets title="Current Alignment" items={s.current_alignment} tone="text-align-green" empty="The parents' general proposals use different language; see the items below." testId={`agreement-alignment-${s.key}`} />
              <Bullets title="Specific Agreements" items={s.specific_agreements} tone="text-brand-purple" empty="No specific commitments could be confirmed from both parents' answers yet." testId={`agreement-specific-${s.key}`} />
              {[["Communication Method", s.communication_method], ["Decision Process", s.decision_process], ["Review Trigger", s.review_trigger]].filter(([, v]) => v).map(([t, v]) => (
                <div key={t}><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t}</p><p className="text-sm leading-relaxed">{v}</p></div>
              ))}
              <Bullets title="Issues Still Requiring Resolution" items={s.open_issues} tone="text-align-blue" testId={`agreement-open-${s.key}`} />
            </div>
            <details className="mt-4 text-xs">
              <summary className="cursor-pointer text-muted-foreground" data-testid={`agreement-proposals-${s.key}`}>Each parent's general proposal</summary>
              <div className="grid sm:grid-cols-2 gap-3 mt-2">
                <div className="bg-muted/40 rounded-md p-3"><p className="font-semibold mb-1">{report.parent_a_name}</p><p className="leading-relaxed">{s.parent_a}</p></div>
                <div className="bg-muted/40 rounded-md p-3"><p className="font-semibold mb-1">{report.parent_b_name}</p><p className="leading-relaxed">{s.parent_b}</p></div>
              </div>
            </details>
          </section>
        ))}
      </div>

      <p className="text-sm italic text-muted-foreground mb-10" data-testid="agreement-next-note">{report.next_note}</p>

      <div className="grid sm:grid-cols-2 gap-6 mb-10" data-testid="agreement-signatures">
        {[report.parent_a_name, report.parent_b_name].map((name, i) => (
          <div key={i} className="border border-border rounded-lg p-5" data-testid={`signature-block-${i}`}>
            <p className="font-semibold mb-4">{name}</p>
            <p className="text-xs text-muted-foreground mb-1">Signature</p>
            <div className="worksheet-line mb-4" />
            <p className="text-xs text-muted-foreground mb-1">Date</p>
            <div className="worksheet-line" />
          </div>
        ))}
      </div>

      <div className="text-center border-t border-border pt-10">
        <h3 className="font-display text-4xl sm:text-5xl font-bold text-align-purple" data-testid="agreement-philosophy">{report.philosophy_heading}</h3>
        <p className="mt-6 text-sm italic text-muted-foreground max-w-xl mx-auto">"{report.philosophy}"</p>
      </div>
    </div>
  );
}
