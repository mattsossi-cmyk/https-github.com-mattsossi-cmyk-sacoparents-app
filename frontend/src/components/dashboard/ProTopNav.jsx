import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export const ProTopNav = ({ cases }) => {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const lookup = (e) => {
    e.preventDefault();
    const needle = q.trim().toUpperCase();
    if (!needle) return;
    const hit = cases.find((j) => (j.case_code || "").toUpperCase() === needle) || cases.find((j) => (j.case_code || "").toUpperCase().includes(needle) || (j.case_reference || "").toUpperCase().includes(needle));
    if (hit) navigate(`/joint/${hit.id}`); else toast.error(`No case matching "${q}"`);
  };
  return (
    <div className="flex flex-wrap lg:flex-nowrap items-center gap-2 sm:gap-3" data-testid="pro-top-nav">
      <form onSubmit={lookup} className="relative flex-1 min-w-[160px] sm:max-w-[220px]">
        <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Case Lookup: Search ID…" className="h-9 w-full rounded-md border border-input bg-white pl-8 pr-2 text-sm uppercase tracking-wider" data-testid="case-lookup-input" />
      </form>
      <Link to="#cases" className="whitespace-nowrap rounded-full border border-border bg-white px-3 py-1.5 text-xs font-semibold hover:border-brand-purple" data-testid="active-cases-count">Active Cases ({cases.length})</Link>
      <Link to="/joint/new" data-testid="new-case-link"><Button size="sm" className="gap-1 whitespace-nowrap bg-brand-purple text-white hover:bg-brand-purple/90" data-testid="new-case-btn"><Plus className="h-4 w-4" /> New Case</Button></Link>
    </div>
  );
};
