import { CheckCircle2, ShieldAlert } from "lucide-react";

const dot = (s) => (s === "Strong alignment" ? "bg-align-green" : s === "Moderate alignment" ? "bg-align-yellow" : "bg-align-blue");

export const CourtReportView = ({ item, index }) => {
  const r = item.report;
  const isAgreement = item.kind === "agreement";
  return (
    <section className="report-paper rounded-lg p-8 sm:p-12 mt-8" data-testid={`court-report-${item.id}`}>
      <div className="text-center border-b border-border pb-6 mb-8">
        <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Enclosure {index}</p>
        <h2 className={`text-3xl font-extrabold mt-2 ${item.is_safety ? "text-red-700" : "text-brand-purple"}`} data-testid={`court-report-title-${item.id}`}>{r.report_title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">Case {item.case_code} · {r.subject_label} · Child: {r.child_name} · {r.parent_a_name} / {r.parent_b_name} · {r.date}</p>
      </div>
      {r.is_safety && <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-800 flex gap-2"><ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />{r.confidentiality_note}</div>}
      {isAgreement ? (
        <div className="space-y-3">
          {(r.terms || []).map((t) => (
            <div key={t.key} className="border border-border rounded-lg p-4">
              <p className="font-semibold text-sm">{t.label} <span className="ml-2 text-xs font-normal text-muted-foreground">{t.status}</span></p>
              <div className="grid sm:grid-cols-2 gap-3 mt-2 text-sm"><p><span className="text-xs uppercase text-muted-foreground">{r.parent_a_name}</span><br />{t.parent_a}</p><p><span className="text-xs uppercase text-muted-foreground">{r.parent_b_name}</span><br />{t.parent_b}</p></div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground leading-relaxed mb-6">{r.purpose}</p>
          <h3 className="font-semibold mb-2">What both parents agree about</h3>
          <ul className="space-y-1.5 text-sm mb-6">{r.alignment_statements.map((s, i) => <li key={i} className="flex gap-2"><CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" />{s}</li>)}</ul>
          <h3 className="font-semibold mb-2">Where the parents see things differently</h3>
          {r.differences.length === 0 ? <p className="text-sm italic text-muted-foreground mb-6">No significant differences identified.</p> : (
            <div className="space-y-3 mb-6">{r.differences.map((d, i) => (
              <div key={i} className="border border-border rounded-lg p-4 text-sm">
                <p className="font-semibold">{d.area}</p>
                <div className="grid sm:grid-cols-2 gap-3 mt-2"><p><span className="text-xs uppercase text-muted-foreground">{r.parent_a_name}</span><br />{d.parent_a}</p><p><span className="text-xs uppercase text-muted-foreground">{r.parent_b_name}</span><br />{d.parent_b}</p></div>
                <p className="mt-2 italic text-muted-foreground">{d.reframe}</p>
              </div>))}</div>
          )}
          <h3 className="font-semibold mb-2">Alignment map</h3>
          <table className="w-full text-sm border border-border rounded-lg overflow-hidden mb-6"><tbody>{r.alignment_map.map((row, i) => (
            <tr key={i} className="border-t border-border"><td className="px-3 py-2">{row.area}</td><td className="px-3 py-2"><span className="inline-flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${dot(row.status)}`} />{row.status}</span></td></tr>))}</tbody></table>
          <div className="grid sm:grid-cols-2 gap-6 text-sm">
            <div><h3 className="font-semibold mb-2">Options raised</h3><ul className="space-y-1.5">{r.options.map((o, i) => <li key={i} className="border border-border rounded-md px-3 py-2">{o}</li>)}</ul></div>
            <div><h3 className="font-semibold mb-2">Possible next steps</h3><ul className="space-y-1.5">{r.next_steps.map((s, i) => <li key={i} className="border border-border rounded-md px-3 py-2">{s}</li>)}</ul></div>
          </div>
        </>
      )}
    </section>
  );
};
