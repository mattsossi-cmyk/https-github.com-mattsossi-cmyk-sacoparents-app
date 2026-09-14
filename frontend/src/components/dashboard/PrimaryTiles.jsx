import { Link } from "react-router-dom";
import { FolderKanban, Gavel, FileText, Send } from "lucide-react";

const Tile = ({ to, icon: Icon, title, desc, count, countLabel, accent, danger, testId }) => (
  <Link to={to} className={`group relative block rounded-lg border-2 bg-white p-5 transition-colors hover:border-brand-purple ${danger ? "border-red-500" : accent ? "border-brand-purple/50" : "border-border"}`} data-testid={testId}>
    <div className="flex items-start justify-between gap-3">
      <span className={`rounded-md p-2 ${danger ? "bg-red-50 text-red-700" : "bg-brand-purple/10 text-brand-purple"}`}><Icon className="h-5 w-5" /></span>
      {count > 0 && (
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${danger ? "bg-red-600 text-white" : "bg-align-yellow text-yellow-950"}`} data-testid={`${testId}-count`}>{count} {countLabel}</span>
      )}
    </div>
    <p className="mt-4 text-lg font-semibold">{title}</p>
    <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
  </Link>
);

export const PrimaryTiles = ({ activeCount, readyCount, referralCount, submitCount, overdueCount = 0 }) => (
  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="primary-actions-grid">
    <Tile to="/joint/new" icon={FolderKanban} title="Manage a Case" desc="Option 1 · Not court-ordered: open a case and invite both parents yourself." count={activeCount} countLabel="active" testId="tile-manage-case" />
    <Tile to="#court-referrals" icon={Gavel} title="Judge Referrals" desc="Option 2 · Court-ordered: a judge sends you the referral; accept it, then invite the parents." count={referralCount} countLabel="new" accent={referralCount > 0} testId="tile-court-cases" />
    <Tile to="#cases" icon={FileText} title="Review Joint Reports" desc="Reports ready to generate or review." count={readyCount} countLabel="ready" testId="tile-review-reports" />
    <Tile to="#court-referrals" icon={Send} title="Submit to Court" desc={overdueCount > 0 ? `${overdueCount} hearing${overdueCount === 1 ? "" : "s"} within 7 days with nothing submitted.` : "Accepted court cases awaiting your Professional Statement and final submission."} count={overdueCount > 0 ? overdueCount : submitCount} countLabel={overdueCount > 0 ? "OVERDUE" : "pending"} accent={overdueCount > 0} danger={overdueCount > 0} testId="tile-submit-court" />
  </section>
);
