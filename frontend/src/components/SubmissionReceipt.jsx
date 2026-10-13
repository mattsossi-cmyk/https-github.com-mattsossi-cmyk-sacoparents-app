import { Receipt, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

export const SubmissionReceipt = ({ sub, onClose }) => {
  if (!sub) return null;
  const rows = [
    ["Submitted", fmt(sub.submitted_at)],
    ["Packet format", sub.packet_label || "Joint Report"],
    ["Version", `Version ${sub.version}`],
    ["Court", sub.court_name || "—"],
    ["Submitted by", sub.submitted_by || "—"],
    ["Packet SHA-256", sub.sha256],
    ["Report SHA-256", sub.joint_sha256],
    ["Statement SHA-256", sub.statement_sha256],
    ...(sub.legal_report_included ? [["Professional Alignment Report SHA-256", sub.legal_sha256]] : []),
  ];
  return (
    <div className="mt-4 rounded-xl border-2 border-align-green/50 bg-white p-4" role="status" data-testid="submission-receipt">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 text-sm font-bold text-align-green"><Receipt className="h-4 w-4" /> Court submission receipt</p>
        <Button size="icon" variant="ghost" className="h-7 w-7" onClick={onClose} aria-label="Close receipt" data-testid="submission-receipt-close"><X className="h-4 w-4" /></Button>
      </div>
      <dl className="mt-2 divide-y divide-border text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="grid gap-1 py-1.5 sm:grid-cols-[14rem_1fr]"><dt className="text-muted-foreground">{k}</dt><dd className="break-all font-mono text-xs sm:text-sm" data-testid={`receipt-${k.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>{v || "—"}</dd></div>
        ))}
      </dl>
      <p className="mt-2 text-[11px] text-muted-foreground">Both documents are locked and timestamped. Keep this receipt for your file; the same version and hash appear in the Judge Portal.</p>
    </div>
  );
};
