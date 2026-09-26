import { Link } from "react-router-dom";
import { CheckCircle2, Circle } from "lucide-react";
import { CaseProgress } from "@/components/CaseProgress";

const STATUS_LABEL = {
  DRAFT: ["Draft", "bg-secondary text-muted-foreground"],
  INVITED: ["Invited", "bg-secondary text-muted-foreground"],
  ONE_COMPLETE: ["One complete", "bg-align-yellow/20 text-yellow-900"],
  READY_FOR_ALIGNMENT: ["Ready for alignment", "bg-align-green/15 text-green-900"],
  REPORT_GENERATED: ["Report generated", "bg-brand-purple/10 text-brand-purple"],
  CLOSED: ["Closed", "bg-secondary text-muted-foreground"],
};

const ParentCell = ({ p, testId }) => (
  <span className="inline-flex items-center gap-1.5 text-xs" data-testid={testId}>
    {p?.completed ? <CheckCircle2 className="h-3.5 w-3.5 text-align-green" /> : <Circle className="h-3.5 w-3.5 text-muted-foreground" />}
    <span className="truncate max-w-[9rem]">{p?.name || "—"}</span>
    <span className="text-muted-foreground">· {p?.completed ? "Complete" : p?.accepted ? "In progress" : "Invited"}</span>
  </span>
);

export const CasesTable = ({ cases, onClose }) => {
  const rows = (cases || []).filter((j) => j.is_creator && !j.archived);
  if (rows.length === 0) return null;
  return (
    <div className="mb-6 overflow-x-auto rounded-lg border border-border bg-white" data-testid="cases-table-wrap">
      <table className="w-full text-sm" data-testid="cases-table">
        <thead className="bg-secondary/60 text-xs uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="text-left font-semibold px-4 py-2.5">Case ID</th>
            <th className="text-left font-semibold px-4 py-2.5">Subject</th>
            <th className="text-left font-semibold px-4 py-2.5">Parent A</th>
            <th className="text-left font-semibold px-4 py-2.5">Parent B</th>
            <th className="text-left font-semibold px-4 py-2.5">Joint Report</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((j) => {
            const [label, cls] = STATUS_LABEL[j.case_status] || STATUS_LABEL.INVITED;
            return (
              <tr key={j.id} className="border-t border-border hover:bg-secondary/30" data-testid={`case-row-${j.id}`}>
                <td className="px-4 py-2.5 whitespace-nowrap">
                  <Link to={`/joint/${j.id}`} className="font-semibold tracking-wider text-brand-purple hover:underline" data-testid={`case-row-code-${j.id}`}>{j.case_code || j.id.slice(0, 8)}</Link>
                  {j.is_demo && <span className="ml-2 rounded-full bg-align-yellow/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-yellow-900" data-testid={`case-row-sample-${j.id}`}>Sample</span>}
                  {j.case_reference && <div className="text-xs text-muted-foreground truncate max-w-[12rem]">{j.case_reference}</div>}
                  {j.court?.judge_email && <div className="text-[11px] font-semibold text-brand-purple truncate max-w-[14rem]" data-testid={`case-row-court-${j.id}`}>{j.court.court_name || "Court"} · {j.court.judge_name}</div>}
                  {j.court_stage && <div className="w-44"><CaseProgress stage={j.court_stage} compact /></div>}
                </td>
                <td className="px-4 py-2.5">{j.subject_label}</td>
                <td className="px-4 py-2.5"><ParentCell p={j.participants?.a} testId={`case-row-a-${j.id}`} /></td>
                <td className="px-4 py-2.5"><ParentCell p={j.participants?.b} testId={`case-row-b-${j.id}`} /></td>
                <td className="px-4 py-2.5 whitespace-nowrap">
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid={`case-row-status-${j.id}`}>{label}</span>
                  {j.case_status === "READY_FOR_ALIGNMENT" && (
                    <Link to={`/joint/${j.id}`} className="ml-2 text-xs font-medium text-primary hover:underline" data-testid={`case-row-generate-${j.id}`}>Generate report →</Link>
                  )}
                  {j.status === "ready" && j.kind !== "agreement" && j.kind !== "foundation" && (
                    <Link to={`/cases/${j.id}/professional-report`} className="ml-2 text-xs font-semibold text-brand-purple hover:underline" data-testid={`case-row-pro-report-${j.id}`}>Professional Report →</Link>
                  )}
                  {onClose && j.case_status !== "CLOSED" && (
                    <button type="button" onClick={() => onClose(j)} className="ml-2 text-xs text-muted-foreground hover:text-foreground hover:underline" data-testid={`case-row-close-${j.id}`}>Close</button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
