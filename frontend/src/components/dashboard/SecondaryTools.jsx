import { Link } from "react-router-dom";

const TOOLS = [
  ["Assessments", "/matters", "tool-assessments"],
  ["Professional Statements", "#cases", "tool-statements"],
  ["Reports", "/hub/complete", "tool-reports"],
  ["Sample Reports", "/samples", "tool-samples"],
  ["Professional Directory", "/professionals", "tool-directory"],
  ["Resources", "/resources", "tool-resources"],
  ["Methodology", "/methodology", "tool-methodology"],
];

export const SecondaryTools = () => (
  <nav className="flex flex-wrap items-center gap-2" aria-label="Secondary tools" data-testid="secondary-tools">
    <span className="mr-1 text-xs font-bold uppercase tracking-widest text-muted-foreground">Tools</span>
    {TOOLS.map(([label, to, id]) => (
      <Link key={id} to={to} className="rounded-full border border-border bg-white px-3.5 py-1.5 text-sm font-medium transition-colors hover:border-brand-purple hover:text-brand-purple" data-testid={id}>{label}</Link>
    ))}
  </nav>
);
