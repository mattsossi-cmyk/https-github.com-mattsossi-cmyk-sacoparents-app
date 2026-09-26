import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

export function FoundationStatements({ rid, items = [], safetyRoute = false }) {
  if (!items.length && !safetyRoute) return null;
  return (
    <section className="bg-white border border-border rounded-lg p-6 mt-6" data-testid="foundation-statements-card">
      <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Parent-Reported · Imported from the SA CoParents app</p>
      <h2 className="text-xl font-semibold mt-1">Foundation Statements</h2>
      <p className="text-sm text-muted-foreground mt-1">Each parent's Child-Focused Foundation Statement, shared into this case. Download as a branded PDF.</p>
      {safetyRoute && <div className="mt-3 rounded-md border border-[#e0b04a] bg-[#fff7df] p-3 text-sm" data-testid="foundation-safety-route-notice"><strong className="text-[#b07d10]">Safety pathway triggered.</strong> A parent's private safety screening indicated a concern, so their statement was not shared and this case should not proceed to a joint agreement or direct negotiation. Use the Family Violence / Safety assessment and a Parallel Parenting structure with safeguards.</div>}
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {items.map((s, i) => (
          <li key={i} className={`rounded-lg border p-4 ${s.side === "a" ? "border-brand-purple/30 bg-[#f3edfb]" : "border-teal-300 bg-[#e8f7f7]"}`} data-testid={`foundation-statement-${s.side}-${i}`}>
            <div className="flex items-start justify-between gap-2">
              <div><p className={`text-xs font-bold uppercase tracking-widest ${s.side === "a" ? "text-brand-purple" : "text-teal-700"}`}>{s.parent}</p><p className="font-semibold flex items-center gap-1.5 mt-0.5"><FileText className="h-4 w-4" /> {s.title}</p></div>
              <Button size="sm" variant="outline" asChild data-testid={`foundation-pdf-${s.side}`}><a href={`${process.env.REACT_APP_BACKEND_URL}/api/joint/reports/${rid}/foundation/${s.side}/pdf`} download><Download className="h-4 w-4 mr-1" /> PDF</a></Button>
            </div>
            <p className="mt-2 text-sm leading-relaxed line-clamp-6 whitespace-pre-wrap">{s.content}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
