import { Link } from "react-router-dom";
import { FolderKanban, Mail, FileText, Gavel } from "lucide-react";

const Tile = ({ to, icon: Icon, title, desc, count, countLabel, accent, testId }) => (
  <Link to={to} className={`group relative block rounded-lg border-2 bg-white p-5 transition-colors hover:border-brand-purple ${accent ? "border-brand-purple/50" : "border-border"}`} data-testid={testId}>
    <div className="flex items-start justify-between gap-3">
      <span className="rounded-md bg-brand-purple/10 p-2 text-brand-purple"><Icon className="h-5 w-5" /></span>
      {count > 0 && (
        <span className="rounded-full bg-align-yellow px-2.5 py-0.5 text-xs font-bold text-yellow-950" data-testid={`${testId}-count`}>{count} {countLabel}</span>
      )}
    </div>
    <p className="mt-4 text-lg font-semibold">{title}</p>
    <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
  </Link>
);

export const PrimaryTiles = ({ activeCount, readyCount, referralCount }) => (
  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="primary-actions-grid">
    <Tile to="#cases" icon={FolderKanban} title="Manage a Case" desc="Open a case, track both parents, prepare statements." count={activeCount} countLabel={activeCount === 1 ? "active" : "active"} testId="tile-manage-case" />
    <Tile to="/joint/new" icon={Mail} title="Invite Parents" desc="Option 1 · Not court-ordered: you open the case and send each parent a private invitation." testId="tile-invite-parents" />
    <Tile to="#cases" icon={FileText} title="Review Joint Reports" desc="Reports ready to generate or review." count={readyCount} countLabel="ready" testId="tile-review-reports" />
    <Tile to="#court-referrals" icon={Gavel} title="Court-Referred Cases" desc="Option 2 · Court-ordered: the court sends you an invitation to create the reports; accept, then invite the parents." count={referralCount} countLabel="new" accent={referralCount > 0} testId="tile-court-cases" />
  </section>
);
